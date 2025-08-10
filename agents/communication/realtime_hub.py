#!/usr/bin/env python3
"""
Real-Time Agent Communication Hub for vLLM Local Swarm
=====================================================

WebSocket-based real-time communication system that enables:
- Agent-to-agent messaging and coordination
- Task status updates and progress tracking
- Event broadcasting and subscription
- Agent presence management
- Performance metrics streaming
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import weakref

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.run(["pip", "install", "websockets"], check=True)
    import websockets
    from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message types for real-time communication"""
    # Agent lifecycle
    AGENT_CONNECT = "agent_connect"
    AGENT_DISCONNECT = "agent_disconnect"
    AGENT_HEARTBEAT = "agent_heartbeat"
    
    # Task coordination
    TASK_ASSIGNMENT = "task_assignment"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETION = "task_completion"
    TASK_FAILURE = "task_failure"
    
    # Agent collaboration
    AGENT_MESSAGE = "agent_message"
    COLLABORATION_REQUEST = "collaboration_request"
    COLLABORATION_RESPONSE = "collaboration_response"
    
    # System events
    SYSTEM_BROADCAST = "system_broadcast"
    PERFORMANCE_METRICS = "performance_metrics"
    ERROR_NOTIFICATION = "error_notification"
    
    # Control messages
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"


class AgentRole(Enum):
    """Agent roles in the swarm"""
    COORDINATOR = "coordinator"
    WORKER = "worker"
    SPECIALIST = "specialist"
    MONITOR = "monitor"
    CLIENT = "client"


@dataclass
class AgentConnection:
    """Agent connection information"""
    agent_id: str
    websocket: WebSocketServerProtocol
    role: AgentRole
    capabilities: List[str]
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0


@dataclass
class Message:
    """Real-time message structure"""
    id: str
    type: MessageType
    sender: str
    recipient: Optional[str] = None  # None for broadcast
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    channel: str = "default"
    priority: int = 5  # 1-10, 10 being highest
    expires_at: Optional[datetime] = None
    requires_ack: bool = False


class RealtimeHub:
    """
    Real-time communication hub for agent coordination
    """
    
    def __init__(self, host: str = "localhost", port: int = 8008):
        self.host = host
        self.port = port
        self.agents: Dict[str, AgentConnection] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self.channels: Dict[str, Set[str]] = defaultdict(set)  # channel -> agent_ids
        
        # Message queuing and delivery
        self.message_queue: Dict[str, List[Message]] = defaultdict(list)
        self.pending_acks: Dict[str, Message] = {}
        
        # Performance tracking
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_transferred': 0,
            'peak_connections': 0,
            'uptime_start': datetime.now()
        }
        
        # Background tasks
        self._running = False
        self._cleanup_task = None
        self._heartbeat_task = None
        self._metrics_task = None
        
    async def start(self):
        """Start the real-time communication hub"""
        if self._running:
            return
            
        self._running = True
        
        # Start WebSocket server
        logger.info(f"🚀 Starting Real-time Hub on {self.host}:{self.port}")
        
        try:
            server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                max_size=10**7,  # 10MB max message size
                compression=None  # Disable compression for lower latency
            )
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._metrics_task = asyncio.create_task(self._metrics_loop())
            
            logger.info(f"✅ Real-time Hub started successfully")
            
            # Keep server running
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"❌ Failed to start Real-time Hub: {e}")
            raise
            
    async def stop(self):
        """Stop the real-time communication hub"""
        self._running = False
        
        # Cancel background tasks
        for task in [self._cleanup_task, self._heartbeat_task, self._metrics_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Disconnect all agents
        for agent_id in list(self.agents.keys()):
            await self._disconnect_agent(agent_id)
            
        logger.info("🛑 Real-time Hub stopped")
        
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        agent_id = None
        
        try:
            # Wait for agent registration
            async for raw_message in websocket:
                message_data = json.loads(raw_message)
                
                if message_data.get('type') == 'agent_connect':
                    agent_id = message_data['agent_id']
                    role = AgentRole(message_data.get('role', 'worker'))
                    capabilities = message_data.get('capabilities', [])
                    metadata = message_data.get('metadata', {})
                    
                    # Register agent
                    await self._register_agent(agent_id, websocket, role, capabilities, metadata)
                    
                    # Send connection confirmation
                    await self._send_to_agent(agent_id, Message(
                        id=f"conn_{int(time.time() * 1000)}",
                        type=MessageType.SYSTEM_BROADCAST,
                        sender="hub",
                        data={
                            'status': 'connected',
                            'agent_id': agent_id,
                            'hub_info': await self._get_hub_info()
                        }
                    ))
                    
                    break
                    
            # Handle messages from this agent
            async for raw_message in websocket:
                await self._process_message(agent_id, raw_message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"🔌 Agent {agent_id} disconnected")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON from agent {agent_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling connection for agent {agent_id}: {e}")
        finally:
            if agent_id:
                await self._disconnect_agent(agent_id)
                
    async def _register_agent(self, agent_id: str, websocket: WebSocketServerProtocol, 
                            role: AgentRole, capabilities: List[str], metadata: Dict[str, Any]):
        """Register a new agent"""
        now = datetime.now()
        
        # Disconnect existing connection if any
        if agent_id in self.agents:
            await self._disconnect_agent(agent_id)
            
        # Create agent connection
        connection = AgentConnection(
            agent_id=agent_id,
            websocket=websocket,
            role=role,
            capabilities=capabilities,
            connected_at=now,
            last_heartbeat=now,
            metadata=metadata
        )
        
        self.agents[agent_id] = connection
        
        # Update stats
        self.stats['peak_connections'] = max(self.stats['peak_connections'], len(self.agents))
        
        # Broadcast agent connection
        await self._broadcast_system_event({
            'event': 'agent_connected',
            'agent_id': agent_id,
            'role': role.value,
            'capabilities': capabilities,
            'total_agents': len(self.agents)
        })
        
        logger.info(f"🤖 Agent {agent_id} ({role.value}) connected with capabilities: {capabilities}")
        
    async def _disconnect_agent(self, agent_id: str):
        """Disconnect and cleanup agent"""
        if agent_id not in self.agents:
            return
            
        connection = self.agents[agent_id]
        
        # Remove from all channels
        for channel, agents in self.channels.items():
            agents.discard(agent_id)
            
        # Close WebSocket
        if not connection.websocket.closed:
            try:
                await connection.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket for {agent_id}: {e}")
                
        # Remove from agents dict
        del self.agents[agent_id]
        
        # Broadcast disconnection
        await self._broadcast_system_event({
            'event': 'agent_disconnected',
            'agent_id': agent_id,
            'total_agents': len(self.agents),
            'connection_duration': (datetime.now() - connection.connected_at).total_seconds()
        })
        
        logger.info(f"🚫 Agent {agent_id} disconnected")
        
    async def _process_message(self, sender_id: str, raw_message: str):
        """Process incoming message from agent"""
        try:
            message_data = json.loads(raw_message)
            message_type = MessageType(message_data['type'])
            
            # Update agent stats
            if sender_id in self.agents:
                self.agents[sender_id].message_count += 1
                self.agents[sender_id].bytes_received += len(raw_message.encode())
                self.agents[sender_id].last_heartbeat = datetime.now()
                
            # Create message object
            message = Message(
                id=message_data.get('id', f"msg_{int(time.time() * 1000)}"),
                type=message_type,
                sender=sender_id,
                recipient=message_data.get('recipient'),
                data=message_data.get('data', {}),
                channel=message_data.get('channel', 'default'),
                priority=message_data.get('priority', 5),
                requires_ack=message_data.get('requires_ack', False)
            )
            
            # Set expiration if specified
            if 'expires_in' in message_data:
                message.expires_at = datetime.now() + timedelta(seconds=message_data['expires_in'])
                
            # Route message
            await self._route_message(message)
            
            # Update stats
            self.stats['messages_received'] += 1
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON from {sender_id}: {e}")
        except ValueError as e:
            logger.error(f"❌ Invalid message type from {sender_id}: {e}")
        except Exception as e:
            logger.error(f"❌ Error processing message from {sender_id}: {e}")
            
    async def _route_message(self, message: Message):
        """Route message to appropriate recipients"""
        try:
            # Handle special message types
            if message.type == MessageType.SUBSCRIBE:
                await self._handle_subscribe(message)
                return
            elif message.type == MessageType.UNSUBSCRIBE:
                await self._handle_unsubscribe(message)
                return
            elif message.type == MessageType.PING:
                await self._handle_ping(message)
                return
            elif message.type == MessageType.AGENT_HEARTBEAT:
                await self._handle_heartbeat(message)
                return
                
            # Route to specific recipient
            if message.recipient:
                if message.recipient in self.agents:
                    await self._send_to_agent(message.recipient, message)
                else:
                    # Queue message for offline agent
                    self.message_queue[message.recipient].append(message)
                    logger.debug(f"📬 Queued message for offline agent {message.recipient}")
                    
            # Broadcast to channel subscribers
            else:
                channel_agents = self.channels.get(message.channel, set())
                for agent_id in channel_agents:
                    if agent_id != message.sender and agent_id in self.agents:
                        await self._send_to_agent(agent_id, message)
                        
            # Call message handlers
            for handler in self.message_handlers.get(message.type, []):
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"❌ Error in message handler: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error routing message: {e}")
            
    async def _send_to_agent(self, agent_id: str, message: Message):
        """Send message to specific agent"""
        if agent_id not in self.agents:
            return False
            
        connection = self.agents[agent_id]
        
        try:
            # Check if message has expired
            if message.expires_at and datetime.now() > message.expires_at:
                logger.debug(f"⏰ Message {message.id} expired, not sending to {agent_id}")
                return False
                
            # Serialize message
            message_data = {
                'id': message.id,
                'type': message.type.value,
                'sender': message.sender,
                'recipient': message.recipient,
                'data': message.data,
                'timestamp': message.timestamp.isoformat(),
                'channel': message.channel,
                'priority': message.priority
            }
            
            raw_message = json.dumps(message_data)
            
            # Send via WebSocket
            await connection.websocket.send(raw_message)
            
            # Update stats
            connection.bytes_sent += len(raw_message.encode())
            self.stats['messages_sent'] += 1
            self.stats['bytes_transferred'] += len(raw_message.encode())
            
            # Handle acknowledgment tracking
            if message.requires_ack:
                self.pending_acks[message.id] = message
                
            return True
            
        except websockets.exceptions.ConnectionClosed:
            logger.debug(f"🚫 Connection closed for agent {agent_id}")
            await self._disconnect_agent(agent_id)
            return False
        except Exception as e:
            logger.error(f"❌ Error sending message to {agent_id}: {e}")
            return False
            
    async def _handle_subscribe(self, message: Message):
        """Handle channel subscription"""
        channel = message.data.get('channel', 'default')
        self.channels[channel].add(message.sender)
        
        # Send confirmation
        await self._send_to_agent(message.sender, Message(
            id=f"sub_{int(time.time() * 1000)}",
            type=MessageType.SYSTEM_BROADCAST,
            sender="hub",
            data={'status': 'subscribed', 'channel': channel}
        ))
        
        logger.debug(f"📢 Agent {message.sender} subscribed to channel {channel}")
        
    async def _handle_unsubscribe(self, message: Message):
        """Handle channel unsubscription"""
        channel = message.data.get('channel', 'default')
        self.channels[channel].discard(message.sender)
        
        # Send confirmation
        await self._send_to_agent(message.sender, Message(
            id=f"unsub_{int(time.time() * 1000)}",
            type=MessageType.SYSTEM_BROADCAST,
            sender="hub",
            data={'status': 'unsubscribed', 'channel': channel}
        ))
        
        logger.debug(f"🔇 Agent {message.sender} unsubscribed from channel {channel}")
        
    async def _handle_ping(self, message: Message):
        """Handle ping message with pong response"""
        pong_message = Message(
            id=f"pong_{message.id}",
            type=MessageType.PONG,
            sender="hub",
            recipient=message.sender,
            data={'original_id': message.id, 'timestamp': datetime.now().isoformat()}
        )
        
        await self._send_to_agent(message.sender, pong_message)
        
    async def _handle_heartbeat(self, message: Message):
        """Handle agent heartbeat"""
        if message.sender in self.agents:
            self.agents[message.sender].last_heartbeat = datetime.now()
            
    async def _broadcast_system_event(self, data: Dict[str, Any]):
        """Broadcast system event to all connected agents"""
        message = Message(
            id=f"sys_{int(time.time() * 1000)}",
            type=MessageType.SYSTEM_BROADCAST,
            sender="hub",
            data=data,
            channel="system"
        )
        
        for agent_id in list(self.agents.keys()):
            await self._send_to_agent(agent_id, message)
            
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._running:
            try:
                now = datetime.now()
                
                # Remove stale agents
                stale_threshold = timedelta(minutes=5)
                stale_agents = []
                
                for agent_id, connection in self.agents.items():
                    if now - connection.last_heartbeat > stale_threshold:
                        stale_agents.append(agent_id)
                        
                for agent_id in stale_agents:
                    logger.warning(f"⚠️ Removing stale agent {agent_id}")
                    await self._disconnect_agent(agent_id)
                    
                # Clean expired messages from queues
                for agent_id, messages in self.message_queue.items():
                    expired = [msg for msg in messages if msg.expires_at and now > msg.expires_at]
                    for msg in expired:
                        messages.remove(msg)
                        
                # Clean pending acknowledgments (timeout after 60 seconds)
                ack_timeout = timedelta(seconds=60)
                expired_acks = []
                
                for msg_id, message in self.pending_acks.items():
                    if now - message.timestamp > ack_timeout:
                        expired_acks.append(msg_id)
                        
                for msg_id in expired_acks:
                    del self.pending_acks[msg_id]
                    
                await asyncio.sleep(30)  # Run cleanup every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in cleanup loop: {e}")
                await asyncio.sleep(60)
                
    async def _heartbeat_loop(self):
        """Background heartbeat monitoring"""
        while self._running:
            try:
                # Send heartbeat requests to all agents
                heartbeat_message = Message(
                    id=f"hb_{int(time.time() * 1000)}",
                    type=MessageType.PING,
                    sender="hub",
                    data={'timestamp': datetime.now().isoformat()}
                )
                
                for agent_id in list(self.agents.keys()):
                    await self._send_to_agent(agent_id, heartbeat_message)
                    
                await asyncio.sleep(60)  # Send heartbeat every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in heartbeat loop: {e}")
                await asyncio.sleep(60)
                
    async def _metrics_loop(self):
        """Background metrics collection and broadcasting"""
        while self._running:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                
                # Broadcast to monitoring agents
                metrics_message = Message(
                    id=f"metrics_{int(time.time() * 1000)}",
                    type=MessageType.PERFORMANCE_METRICS,
                    sender="hub",
                    data=metrics,
                    channel="monitoring"
                )
                
                for agent_id in list(self.agents.keys()):
                    if self.agents[agent_id].role == AgentRole.MONITOR:
                        await self._send_to_agent(agent_id, metrics_message)
                        
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in metrics loop: {e}")
                await asyncio.sleep(60)
                
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current performance metrics"""
        uptime = (datetime.now() - self.stats['uptime_start']).total_seconds()
        
        # Agent metrics
        agent_metrics = {}
        for agent_id, connection in self.agents.items():
            agent_metrics[agent_id] = {
                'role': connection.role.value,
                'connected_duration': (datetime.now() - connection.connected_at).total_seconds(),
                'message_count': connection.message_count,
                'bytes_sent': connection.bytes_sent,
                'bytes_received': connection.bytes_received,
                'last_heartbeat': connection.last_heartbeat.isoformat()
            }
            
        # Channel metrics
        channel_metrics = {}
        for channel, agents in self.channels.items():
            channel_metrics[channel] = {
                'subscriber_count': len(agents),
                'subscribers': list(agents)
            }
            
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime': uptime,
            'total_agents': len(self.agents),
            'messages_sent': self.stats['messages_sent'],
            'messages_received': self.stats['messages_received'],
            'bytes_transferred': self.stats['bytes_transferred'],
            'peak_connections': self.stats['peak_connections'],
            'queued_messages': sum(len(msgs) for msgs in self.message_queue.values()),
            'pending_acks': len(self.pending_acks),
            'agents': agent_metrics,
            'channels': channel_metrics
        }
        
    async def _get_hub_info(self) -> Dict[str, Any]:
        """Get hub information for new connections"""
        return {
            'version': '1.0.0',
            'uptime': (datetime.now() - self.stats['uptime_start']).total_seconds(),
            'total_agents': len(self.agents),
            'available_channels': list(self.channels.keys()),
            'supported_message_types': [mt.value for mt in MessageType]
        }
        
    # Public API methods
    async def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a message handler for specific message types"""
        self.message_handlers[message_type].append(handler)
        
    async def send_message(self, message: Message) -> bool:
        """Send message through the hub"""
        return await self._route_message(message)
        
    async def broadcast_to_channel(self, channel: str, data: Dict[str, Any], 
                                 sender: str = "hub", message_type: MessageType = MessageType.SYSTEM_BROADCAST):
        """Broadcast message to all subscribers of a channel"""
        message = Message(
            id=f"bc_{int(time.time() * 1000)}",
            type=message_type,
            sender=sender,
            data=data,
            channel=channel
        )
        
        await self._route_message(message)
        
    async def get_connected_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all connected agents"""
        agents_info = {}
        
        for agent_id, connection in self.agents.items():
            agents_info[agent_id] = {
                'role': connection.role.value,
                'capabilities': connection.capabilities,
                'connected_at': connection.connected_at.isoformat(),
                'last_heartbeat': connection.last_heartbeat.isoformat(),
                'subscriptions': list(connection.subscriptions),
                'metadata': connection.metadata,
                'stats': {
                    'message_count': connection.message_count,
                    'bytes_sent': connection.bytes_sent,
                    'bytes_received': connection.bytes_received
                }
            }
            
        return agents_info
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current hub metrics"""
        return await self._collect_metrics()


# Example usage and testing
async def main():
    """Example usage of the real-time hub"""
    hub = RealtimeHub()
    
    # Register message handlers
    async def handle_task_assignment(message: Message):
        logger.info(f"📋 Task assignment: {message.data}")
        
    async def handle_agent_collaboration(message: Message):
        logger.info(f"🤝 Agent collaboration: {message.data}")
        
    await hub.register_message_handler(MessageType.TASK_ASSIGNMENT, handle_task_assignment)
    await hub.register_message_handler(MessageType.COLLABORATION_REQUEST, handle_agent_collaboration)
    
    # Start the hub
    try:
        logger.info("🚀 Starting Real-time Communication Hub...")
        await hub.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down hub...")
        await hub.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())