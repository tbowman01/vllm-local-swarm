#!/usr/bin/env python3
"""
Agent WebSocket Client for Real-Time Communication
================================================

Client-side implementation for agents to connect to the real-time hub
and participate in agent coordination and collaboration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import uuid

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.run(["pip", "install", "websockets"], check=True)
    import websockets
    from websockets.client import WebSocketClientProtocol

from .realtime_hub import MessageType, AgentRole, Message

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state for the agent client"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionConfig:
    """Configuration for agent connection"""
    hub_url: str = "ws://localhost:8008"
    agent_id: str = field(default_factory=lambda: f"agent_{uuid.uuid4().hex[:8]}")
    role: AgentRole = AgentRole.WORKER
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    heartbeat_interval: float = 30.0
    message_timeout: float = 30.0


class AgentClient:
    """
    WebSocket client for agents to communicate with the real-time hub
    """
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        
        # Message handling
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.subscriptions: set = set()
        
        # Background tasks
        self._running = False
        self._heartbeat_task = None
        self._receive_task = None
        self._reconnect_task = None
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'reconnect_count': 0,
            'connection_start': None
        }
        
    async def connect(self):
        """Connect to the real-time hub"""
        if self.state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return
            
        self.state = ConnectionState.CONNECTING
        logger.info(f"🔌 Connecting to hub at {self.config.hub_url}")
        
        try:
            # Establish WebSocket connection
            self.websocket = await websockets.connect(
                self.config.hub_url,
                ping_interval=None,  # We'll handle our own heartbeat
                ping_timeout=20,
                max_size=10**7,
                compression=None
            )
            
            # Send agent registration
            await self._send_registration()
            
            # Wait for connection confirmation
            await self._wait_for_confirmation()
            
            # Update state and stats
            self.state = ConnectionState.CONNECTED
            self.stats['connection_start'] = datetime.now()
            self._running = True
            
            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"✅ Connected to hub as agent {self.config.agent_id}")
            
        except Exception as e:
            self.state = ConnectionState.FAILED
            logger.error(f"❌ Failed to connect to hub: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from the real-time hub"""
        self._running = False
        self.state = ConnectionState.DISCONNECTED
        
        # Cancel background tasks
        for task in [self._receive_task, self._heartbeat_task, self._reconnect_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Send disconnect message
        if self.websocket and not self.websocket.closed:
            try:
                await self._send_message({
                    'type': MessageType.AGENT_DISCONNECT.value,
                    'agent_id': self.config.agent_id,
                    'timestamp': datetime.now().isoformat()
                })
                await self.websocket.close()
            except Exception as e:
                logger.debug(f"Error during disconnect: {e}")
                
        self.websocket = None
        logger.info(f"🚫 Disconnected from hub")
        
    async def send_message(self, message_type: MessageType, data: Dict[str, Any], 
                          recipient: Optional[str] = None, channel: str = "default",
                          requires_response: bool = False, timeout: float = None) -> Optional[Dict[str, Any]]:
        """Send a message through the hub"""
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError("Not connected to hub")
            
        message_id = f"msg_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
        timeout = timeout or self.config.message_timeout
        
        message = {
            'id': message_id,
            'type': message_type.value,
            'sender': self.config.agent_id,
            'recipient': recipient,
            'data': data,
            'channel': channel,
            'timestamp': datetime.now().isoformat()
        }
        
        # Set up response waiting if needed
        response_future = None
        if requires_response:
            response_future = asyncio.Future()
            self.pending_responses[message_id] = response_future
            
        try:
            await self._send_message(message)
            
            if requires_response:
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(response_future, timeout=timeout)
                    return response
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ Timeout waiting for response to message {message_id}")
                    return None
                    
        finally:
            # Clean up pending response
            if message_id in self.pending_responses:
                del self.pending_responses[message_id]
                
        return None
        
    async def subscribe_to_channel(self, channel: str):
        """Subscribe to a communication channel"""
        if channel in self.subscriptions:
            return
            
        await self.send_message(
            MessageType.SUBSCRIBE,
            {'channel': channel}
        )
        
        self.subscriptions.add(channel)
        logger.debug(f"📢 Subscribed to channel: {channel}")
        
    async def unsubscribe_from_channel(self, channel: str):
        """Unsubscribe from a communication channel"""
        if channel not in self.subscriptions:
            return
            
        await self.send_message(
            MessageType.UNSUBSCRIBE,
            {'channel': channel}
        )
        
        self.subscriptions.discard(channel)
        logger.debug(f"🔇 Unsubscribed from channel: {channel}")
        
    async def request_collaboration(self, target_agent: str, task_description: str, 
                                   required_capabilities: List[str] = None) -> Optional[Dict[str, Any]]:
        """Request collaboration from another agent"""
        collaboration_data = {
            'task_description': task_description,
            'required_capabilities': required_capabilities or [],
            'requester_capabilities': self.config.capabilities,
            'timestamp': datetime.now().isoformat()
        }
        
        response = await self.send_message(
            MessageType.COLLABORATION_REQUEST,
            collaboration_data,
            recipient=target_agent,
            requires_response=True,
            timeout=30.0
        )
        
        return response
        
    async def respond_to_collaboration(self, request_id: str, requester: str, 
                                     accept: bool, message: str = ""):
        """Respond to a collaboration request"""
        response_data = {
            'request_id': request_id,
            'accept': accept,
            'message': message,
            'agent_capabilities': self.config.capabilities,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.send_message(
            MessageType.COLLABORATION_RESPONSE,
            response_data,
            recipient=requester
        )
        
    async def send_task_progress(self, task_id: str, progress: float, 
                               status: str, details: Dict[str, Any] = None):
        """Send task progress update"""
        progress_data = {
            'task_id': task_id,
            'progress': progress,
            'status': status,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        
        await self.send_message(
            MessageType.TASK_PROGRESS,
            progress_data,
            channel="task_updates"
        )
        
    async def report_task_completion(self, task_id: str, result: Dict[str, Any], 
                                   metrics: Dict[str, Any] = None):
        """Report task completion"""
        completion_data = {
            'task_id': task_id,
            'result': result,
            'metrics': metrics or {},
            'completion_time': datetime.now().isoformat()
        }
        
        await self.send_message(
            MessageType.TASK_COMPLETION,
            completion_data,
            channel="task_updates"
        )
        
    async def report_task_failure(self, task_id: str, error: str, 
                                 details: Dict[str, Any] = None):
        """Report task failure"""
        failure_data = {
            'task_id': task_id,
            'error': error,
            'details': details or {},
            'failure_time': datetime.now().isoformat()
        }
        
        await self.send_message(
            MessageType.TASK_FAILURE,
            failure_data,
            channel="task_updates"
        )
        
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a handler for specific message types"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
        
    def unregister_message_handler(self, message_type: MessageType, handler: Callable):
        """Unregister a message handler"""
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type].remove(handler)
            except ValueError:
                pass
                
    async def get_connected_agents(self) -> Optional[Dict[str, Any]]:
        """Get list of currently connected agents"""
        response = await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {'request': 'connected_agents'},
            requires_response=True
        )
        return response
        
    async def get_hub_metrics(self) -> Optional[Dict[str, Any]]:
        """Get hub performance metrics"""
        response = await self.send_message(
            MessageType.SYSTEM_BROADCAST,
            {'request': 'hub_metrics'},
            requires_response=True
        )
        return response
        
    # Private methods
    async def _send_registration(self):
        """Send agent registration message"""
        registration = {
            'type': 'agent_connect',
            'agent_id': self.config.agent_id,
            'role': self.config.role.value,
            'capabilities': self.config.capabilities,
            'metadata': self.config.metadata,
            'timestamp': datetime.now().isoformat()
        }
        
        await self._send_message(registration)
        
    async def _wait_for_confirmation(self, timeout: float = 10.0):
        """Wait for connection confirmation from hub"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                data = json.loads(message)
                
                if (data.get('type') == MessageType.SYSTEM_BROADCAST.value and 
                    data.get('data', {}).get('status') == 'connected'):
                    return
                    
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
                
        raise TimeoutError("No connection confirmation received from hub")
        
    async def _send_message(self, message_data: Dict[str, Any]):
        """Send raw message to hub"""
        if not self.websocket or self.websocket.closed:
            raise RuntimeError("WebSocket not connected")
            
        raw_message = json.dumps(message_data)
        await self.websocket.send(raw_message)
        
        # Update stats
        self.stats['messages_sent'] += 1
        self.stats['bytes_sent'] += len(raw_message.encode())
        
    async def _receive_loop(self):
        """Background task to receive messages"""
        while self._running and self.websocket:
            try:
                raw_message = await self.websocket.recv()
                await self._process_received_message(raw_message)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("🔌 Connection closed by hub")
                self.state = ConnectionState.DISCONNECTED
                if self._running:
                    await self._attempt_reconnect()
                break
                
            except Exception as e:
                logger.error(f"❌ Error in receive loop: {e}")
                await asyncio.sleep(1.0)
                
    async def _process_received_message(self, raw_message: str):
        """Process a received message from the hub"""
        try:
            message_data = json.loads(raw_message)
            message_type = MessageType(message_data['type'])
            
            # Update stats
            self.stats['messages_received'] += 1
            self.stats['bytes_received'] += len(raw_message.encode())
            
            # Handle response to pending request
            message_id = message_data.get('id')
            if message_id in self.pending_responses:
                future = self.pending_responses[message_id]
                if not future.done():
                    future.set_result(message_data.get('data', {}))
                return
                
            # Call registered handlers
            handlers = self.message_handlers.get(message_type, [])
            for handler in handlers:
                try:
                    await handler(message_data)
                except Exception as e:
                    logger.error(f"❌ Error in message handler: {e}")
                    
            # Handle special message types
            if message_type == MessageType.PONG:
                logger.debug("🏓 Received pong from hub")
            elif message_type == MessageType.SYSTEM_BROADCAST:
                await self._handle_system_broadcast(message_data)
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON received: {e}")
        except ValueError as e:
            logger.error(f"❌ Invalid message type received: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing received message: {e}")
            
    async def _handle_system_broadcast(self, message_data: Dict[str, Any]):
        """Handle system broadcast messages"""
        data = message_data.get('data', {})
        event = data.get('event')
        
        if event == 'agent_connected':
            logger.debug(f"🤖 Agent {data.get('agent_id')} connected")
        elif event == 'agent_disconnected':
            logger.debug(f"🚫 Agent {data.get('agent_id')} disconnected")
            
    async def _heartbeat_loop(self):
        """Background heartbeat task"""
        while self._running:
            try:
                if self.state == ConnectionState.CONNECTED:
                    await self.send_message(
                        MessageType.AGENT_HEARTBEAT,
                        {'timestamp': datetime.now().isoformat()}
                    )
                    
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in heartbeat loop: {e}")
                await asyncio.sleep(self.config.heartbeat_interval)
                
    async def _attempt_reconnect(self):
        """Attempt to reconnect to the hub"""
        if self.state == ConnectionState.RECONNECTING:
            return
            
        self.state = ConnectionState.RECONNECTING
        
        for attempt in range(self.config.reconnect_attempts):
            try:
                logger.info(f"🔄 Reconnect attempt {attempt + 1}/{self.config.reconnect_attempts}")
                
                # Wait before reconnecting
                await asyncio.sleep(self.config.reconnect_delay)
                
                # Try to reconnect
                await self.connect()
                
                self.stats['reconnect_count'] += 1
                logger.info("✅ Reconnection successful")
                return
                
            except Exception as e:
                logger.warning(f"❌ Reconnect attempt {attempt + 1} failed: {e}")
                
        logger.error("❌ All reconnect attempts failed")
        self.state = ConnectionState.FAILED
        
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = self.stats.copy()
        stats['state'] = self.state.value
        stats['uptime'] = None
        
        if stats['connection_start']:
            stats['uptime'] = (datetime.now() - stats['connection_start']).total_seconds()
            
        return stats


# Example usage
async def example_agent():
    """Example usage of the agent client"""
    
    # Configure agent
    config = ConnectionConfig(
        agent_id="example_agent_001",
        role=AgentRole.WORKER,
        capabilities=["text_processing", "data_analysis"],
        metadata={"version": "1.0.0", "description": "Example agent"}
    )
    
    # Create and connect client
    client = AgentClient(config)
    
    # Register message handlers
    async def handle_collaboration_request(message_data):
        logger.info(f"🤝 Collaboration request received: {message_data}")
        # Auto-accept collaboration requests for demo
        await client.respond_to_collaboration(
            message_data['id'],
            message_data['sender'],
            accept=True,
            message="Happy to collaborate!"
        )
        
    async def handle_task_assignment(message_data):
        logger.info(f"📋 Task assignment received: {message_data}")
        task_id = message_data.get('data', {}).get('task_id', 'unknown')
        
        # Simulate task processing
        await client.send_task_progress(task_id, 0.5, "in_progress", {"step": "processing"})
        await asyncio.sleep(2)
        await client.report_task_completion(task_id, {"result": "completed"})
        
    client.register_message_handler(MessageType.COLLABORATION_REQUEST, handle_collaboration_request)
    client.register_message_handler(MessageType.TASK_ASSIGNMENT, handle_task_assignment)
    
    try:
        await client.connect()
        
        # Subscribe to channels
        await client.subscribe_to_channel("task_updates")
        await client.subscribe_to_channel("system")
        
        # Keep agent running
        while client.state == ConnectionState.CONNECTED:
            await asyncio.sleep(10)
            
            # Send periodic status update
            await client.send_message(
                MessageType.AGENT_MESSAGE,
                {"status": "active", "timestamp": datetime.now().isoformat()},
                channel="status_updates"
            )
            
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down agent...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_agent())