#!/usr/bin/env python3
"""
Integration Layer for Real-Time Communication with Task Router
============================================================

Bridges the real-time communication hub with the task router system
to enable seamless agent coordination and task management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .realtime_hub import RealtimeHub, MessageType, Message, AgentRole
from .agent_client import AgentClient, ConnectionConfig
from ..coordination.task_router import TaskRouter, Task, AgentProfile, AgentCapability, TaskRequirements, TaskPriority

logger = logging.getLogger(__name__)


class CommunicationTaskBridge:
    """
    Bridge between the real-time communication hub and task router
    """
    
    def __init__(self, task_router: TaskRouter, realtime_hub: RealtimeHub):
        self.task_router = task_router
        self.realtime_hub = realtime_hub
        self.agent_clients: Dict[str, AgentClient] = {}
        
        # Setup message handlers
        self._setup_message_handlers()
        
    async def start(self):
        """Start the communication bridge"""
        logger.info("🌉 Starting Communication-Task Bridge...")
        
        # Start the real-time hub
        asyncio.create_task(self.realtime_hub.start())
        
        # Start the task router
        await self.task_router.start()
        
        logger.info("✅ Communication-Task Bridge started")
        
    async def stop(self):
        """Stop the communication bridge"""
        logger.info("🛑 Stopping Communication-Task Bridge...")
        
        # Disconnect all agent clients
        for client in self.agent_clients.values():
            await client.disconnect()
            
        # Stop components
        await self.task_router.stop()
        await self.realtime_hub.stop()
        
        logger.info("✅ Communication-Task Bridge stopped")
        
    def _setup_message_handlers(self):
        """Setup message handlers for the bridge"""
        
        # Register handlers with the real-time hub
        asyncio.create_task(
            self.realtime_hub.register_message_handler(
                MessageType.AGENT_CONNECT, self._handle_agent_connect
            )
        )
        
        asyncio.create_task(
            self.realtime_hub.register_message_handler(
                MessageType.AGENT_DISCONNECT, self._handle_agent_disconnect
            )
        )
        
        asyncio.create_task(
            self.realtime_hub.register_message_handler(
                MessageType.TASK_PROGRESS, self._handle_task_progress
            )
        )
        
        asyncio.create_task(
            self.realtime_hub.register_message_handler(
                MessageType.TASK_COMPLETION, self._handle_task_completion
            )
        )
        
        asyncio.create_task(
            self.realtime_hub.register_message_handler(
                MessageType.TASK_FAILURE, self._handle_task_failure
            )
        )
        
    async def _handle_agent_connect(self, message: Message):
        """Handle agent connection and register with task router"""
        try:
            agent_id = message.sender
            data = message.data
            
            # Convert communication role to agent capabilities
            role = AgentRole(data.get('role', 'worker'))
            capabilities = self._convert_to_agent_capabilities(data.get('capabilities', []))
            
            # Create agent profile for task router
            agent_profile = AgentProfile(
                agent_id=agent_id,
                name=data.get('name', agent_id),
                capabilities=capabilities,
                max_concurrent_tasks=data.get('max_concurrent_tasks', 3),
                memory_capacity_mb=data.get('memory_capacity_mb', 1024),
                average_response_time=data.get('average_response_time', 5.0),
                success_rate=data.get('success_rate', 0.95),
                metadata=data.get('metadata', {})
            )
            
            # Register with task router
            await self.task_router.register_agent(agent_profile)
            
            # Send welcome message with available tasks
            await self._send_agent_welcome(agent_id)
            
            logger.info(f"🤖 Agent {agent_id} registered with task router")
            
        except Exception as e:
            logger.error(f"❌ Error handling agent connect: {e}")
            
    async def _handle_agent_disconnect(self, message: Message):
        """Handle agent disconnection"""
        try:
            agent_id = message.sender
            
            # Unregister from task router
            await self.task_router.unregister_agent(agent_id)
            
            logger.info(f"🚫 Agent {agent_id} unregistered from task router")
            
        except Exception as e:
            logger.error(f"❌ Error handling agent disconnect: {e}")
            
    async def _handle_task_progress(self, message: Message):
        """Handle task progress updates"""
        try:
            data = message.data
            task_id = data.get('task_id')
            progress = data.get('progress', 0.0)
            status = data.get('status', 'unknown')
            
            # Broadcast progress to interested parties
            await self.realtime_hub.broadcast_to_channel(
                "task_monitoring",
                {
                    'task_id': task_id,
                    'agent_id': message.sender,
                    'progress': progress,
                    'status': status,
                    'details': data.get('details', {}),
                    'timestamp': datetime.now().isoformat()
                },
                message_type=MessageType.TASK_PROGRESS
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling task progress: {e}")
            
    async def _handle_task_completion(self, message: Message):
        """Handle task completion"""
        try:
            data = message.data
            task_id = data.get('task_id')
            result = data.get('result', {})
            
            # Update task status in router
            # Note: This would require extending TaskRouter with completion handling
            
            # Broadcast completion
            await self.realtime_hub.broadcast_to_channel(
                "task_monitoring",
                {
                    'task_id': task_id,
                    'agent_id': message.sender,
                    'status': 'completed',
                    'result': result,
                    'completion_time': data.get('completion_time'),
                    'metrics': data.get('metrics', {})
                },
                message_type=MessageType.TASK_COMPLETION
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling task completion: {e}")
            
    async def _handle_task_failure(self, message: Message):
        """Handle task failure"""
        try:
            data = message.data
            task_id = data.get('task_id')
            error = data.get('error')
            
            # Broadcast failure
            await self.realtime_hub.broadcast_to_channel(
                "task_monitoring",
                {
                    'task_id': task_id,
                    'agent_id': message.sender,
                    'status': 'failed',
                    'error': error,
                    'details': data.get('details', {}),
                    'failure_time': data.get('failure_time')
                },
                message_type=MessageType.TASK_FAILURE
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling task failure: {e}")
            
    async def _send_agent_welcome(self, agent_id: str):
        """Send welcome message to newly connected agent"""
        try:
            # Get current task router statistics
            stats = await self.task_router.get_routing_stats()
            
            welcome_data = {
                'welcome': True,
                'agent_id': agent_id,
                'hub_info': await self.realtime_hub._get_hub_info(),
                'task_stats': stats,
                'available_channels': ['task_updates', 'task_monitoring', 'collaboration'],
                'instructions': {
                    'subscribe_to_tasks': 'Subscribe to task_updates channel for task assignments',
                    'report_progress': 'Send task_progress messages for status updates',
                    'request_help': 'Use collaboration_request for agent-to-agent help'
                }
            }
            
            # Send welcome message
            await self.realtime_hub.broadcast_to_channel(
                "system",
                welcome_data,
                message_type=MessageType.SYSTEM_BROADCAST
            )
            
        except Exception as e:
            logger.error(f"❌ Error sending agent welcome: {e}")
            
    def _convert_to_agent_capabilities(self, comm_capabilities: List[str]) -> List[AgentCapability]:
        """Convert communication capabilities to task router capabilities"""
        capability_map = {
            'research': AgentCapability.RESEARCH,
            'analysis': AgentCapability.ANALYSIS,
            'writing': AgentCapability.WRITING,
            'coding': AgentCapability.CODING,
            'math': AgentCapability.MATH,
            'reasoning': AgentCapability.REASONING,
            'memory': AgentCapability.MEMORY,
            'coordination': AgentCapability.COORDINATION,
            'text_processing': AgentCapability.ANALYSIS,
            'data_analysis': AgentCapability.ANALYSIS,
            'specialized': AgentCapability.SPECIALIZED
        }
        
        capabilities = []
        for cap_str in comm_capabilities:
            cap_str = cap_str.lower().replace('-', '_').replace(' ', '_')
            if cap_str in capability_map:
                capabilities.append(capability_map[cap_str])
            else:
                # Default to specialized for unknown capabilities
                capabilities.append(AgentCapability.SPECIALIZED)
                
        return capabilities or [AgentCapability.SPECIALIZED]
        
    async def assign_task_to_agent(self, task: Task) -> bool:
        """Assign a task to an agent via real-time communication"""
        try:
            # Find best agent through task router
            # This would need to be exposed in TaskRouter's public API
            
            # For now, let's broadcast task to all agents and let them self-select
            task_data = {
                'task_id': task.task_id,
                'description': task.description,
                'requirements': {
                    'capabilities': [cap.value for cap in task.requirements.capabilities],
                    'min_memory_mb': task.requirements.min_memory_mb,
                    'max_execution_time': task.requirements.max_execution_time,
                    'complexity_score': task.requirements.complexity_score,
                    'expected_tokens': task.requirements.expected_tokens
                },
                'priority': task.priority.value,
                'deadline': task.deadline.isoformat() if task.deadline else None,
                'context': task.context,
                'created_at': task.created_at.isoformat()
            }
            
            # Broadcast task assignment
            await self.realtime_hub.broadcast_to_channel(
                "task_updates",
                task_data,
                message_type=MessageType.TASK_ASSIGNMENT
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error assigning task via communication: {e}")
            return False
            
    async def get_agent_communications_status(self) -> Dict[str, Any]:
        """Get status of all agents from communication perspective"""
        try:
            connected_agents = await self.realtime_hub.get_connected_agents()
            task_router_agents = {}
            
            # Get agent info from task router
            for agent_id in connected_agents:
                agent_status = await self.task_router.get_agent_status(agent_id)
                if agent_status:
                    task_router_agents[agent_id] = agent_status
                    
            # Combine information
            combined_status = {}
            for agent_id, comm_info in connected_agents.items():
                combined_status[agent_id] = {
                    'communication': comm_info,
                    'task_routing': task_router_agents.get(agent_id, {}),
                    'last_activity': max(
                        comm_info.get('last_heartbeat', ''),
                        task_router_agents.get(agent_id, {}).get('last_seen', '')
                    )
                }
                
            return combined_status
            
        except Exception as e:
            logger.error(f"❌ Error getting agent status: {e}")
            return {}


class SmartAgentClient(AgentClient):
    """
    Enhanced agent client with task router integration
    """
    
    def __init__(self, config: ConnectionConfig, auto_accept_tasks: bool = True):
        super().__init__(config)
        self.auto_accept_tasks = auto_accept_tasks
        self.current_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Register enhanced handlers
        self.register_message_handler(MessageType.TASK_ASSIGNMENT, self._handle_task_assignment)
        self.register_message_handler(MessageType.COLLABORATION_REQUEST, self._handle_collaboration_request)
        
    async def _handle_task_assignment(self, message_data: Dict[str, Any]):
        """Handle incoming task assignments"""
        try:
            data = message_data.get('data', {})
            task_id = data.get('task_id')
            description = data.get('description', '')
            requirements = data.get('requirements', {})
            
            logger.info(f"📋 Received task assignment: {task_id}")
            logger.debug(f"Task description: {description}")
            
            # Check if agent can handle this task
            required_caps = requirements.get('capabilities', [])
            agent_caps = [cap.lower() for cap in self.config.capabilities]
            
            can_handle = any(req_cap.lower() in agent_caps for req_cap in required_caps)
            
            if self.auto_accept_tasks and can_handle:
                # Accept and start task
                self.current_tasks[task_id] = {
                    'description': description,
                    'requirements': requirements,
                    'started_at': datetime.now().isoformat(),
                    'status': 'accepted'
                }
                
                # Send acceptance and start processing
                await self.send_task_progress(task_id, 0.0, "accepted", {"message": "Task accepted"})
                
                # Start task processing (in a separate coroutine)
                asyncio.create_task(self._process_task(task_id, description, requirements))
                
            else:
                logger.info(f"🚫 Cannot handle task {task_id} - missing capabilities")
                
        except Exception as e:
            logger.error(f"❌ Error handling task assignment: {e}")
            
    async def _handle_collaboration_request(self, message_data: Dict[str, Any]):
        """Handle collaboration requests from other agents"""
        try:
            data = message_data.get('data', {})
            requester = message_data.get('sender')
            task_description = data.get('task_description', '')
            required_capabilities = data.get('required_capabilities', [])
            
            logger.info(f"🤝 Collaboration request from {requester}: {task_description}")
            
            # Simple acceptance logic - accept if we have any matching capabilities
            agent_caps = set(cap.lower() for cap in self.config.capabilities)
            required_caps = set(cap.lower() for cap in required_capabilities)
            
            can_collaborate = bool(agent_caps.intersection(required_caps)) or not required_capabilities
            
            # Send response
            await self.respond_to_collaboration(
                message_data.get('id'),
                requester,
                accept=can_collaborate,
                message=f"Can collaborate: {can_collaborate}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling collaboration request: {e}")
            
    async def _process_task(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Process an assigned task (override this in subclasses)"""
        try:
            logger.info(f"🔄 Processing task {task_id}")
            
            # Simulate task processing with progress updates
            total_steps = 5
            for step in range(1, total_steps + 1):
                await asyncio.sleep(2)  # Simulate work
                
                progress = step / total_steps
                await self.send_task_progress(
                    task_id, 
                    progress, 
                    "in_progress", 
                    {"step": step, "total_steps": total_steps}
                )
                
            # Mark task as completed
            self.current_tasks[task_id]['status'] = 'completed'
            
            result = {
                "status": "success",
                "description": f"Completed: {description}",
                "processing_time": "10 seconds"
            }
            
            await self.report_task_completion(task_id, result)
            logger.info(f"✅ Completed task {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing task {task_id}: {e}")
            await self.report_task_failure(task_id, str(e))


# Example usage
async def main():
    """Example integration usage"""
    
    # Create components
    task_router = TaskRouter()
    realtime_hub = RealtimeHub()
    bridge = CommunicationTaskBridge(task_router, realtime_hub)
    
    # Start the integrated system
    await bridge.start()
    
    # Create a smart agent client
    config = ConnectionConfig(
        agent_id="smart_agent_001",
        role=AgentRole.WORKER,
        capabilities=["research", "analysis", "writing"],
        metadata={"integration": "enabled"}
    )
    
    agent = SmartAgentClient(config)
    
    try:
        await agent.connect()
        
        # Subscribe to relevant channels
        await agent.subscribe_to_channel("task_updates")
        await agent.subscribe_to_channel("collaboration")
        
        # Simulate some task submissions
        await asyncio.sleep(2)
        
        # Submit a test task through the task router
        test_task = Task(
            task_id="test_task_001",
            description="Analyze some test data",
            requirements=TaskRequirements(
                capabilities=[AgentCapability.ANALYSIS],
                complexity_score=0.6
            ),
            priority=TaskPriority.MEDIUM
        )
        
        await bridge.assign_task_to_agent(test_task)
        
        # Keep running
        await asyncio.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down integration example...")
    finally:
        await agent.disconnect()
        await bridge.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())