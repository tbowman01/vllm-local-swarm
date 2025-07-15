"""
Base Agent Class for SPARC Multi-Agent Framework

This module provides the foundational BaseAgent class that all specialized agents inherit from.
It implements common functionality including communication protocols, memory management,
tool access, and lifecycle management following SPARC methodology.
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging

import ray


class AgentStatus(Enum):
    """Agent lifecycle status enumeration"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETE = "complete"


class MessageType(Enum):
    """Inter-agent message types for structured communication"""
    TASK_ASSIGNMENT = "task_assignment"
    RESULT_RETURN = "result_return"
    STATUS_UPDATE = "status_update"
    FEEDBACK = "feedback"
    QUERY = "query"
    MEMORY_UPDATE = "memory_update"


class AgentMessage:
    """Structured message format for inter-agent communication"""
    
    def __init__(
        self,
        message_type: MessageType,
        sender: str,
        recipient: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.message_type = message_type
        self.sender = sender
        self.recipient = recipient
        self.payload = payload
        self.task_id = task_id
        self.correlation_id = correlation_id
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format"""
        return {
            "id": self.id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create message from dictionary format"""
        msg = cls(
            message_type=MessageType(data["message_type"]),
            sender=data["sender"],
            recipient=data["recipient"],
            payload=data["payload"],
            task_id=data.get("task_id"),
            correlation_id=data.get("correlation_id")
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        return msg


@ray.remote
class BaseAgent(ABC):
    """
    Base class for all SPARC agents providing common functionality:
    - Structured communication protocols
    - Memory management and context handling
    - Tool access and capability management
    - Lifecycle management and status tracking
    - Observability and logging integration
    """
    
    def __init__(
        self,
        agent_id: str,
        role: str,
        capabilities: List[str],
        model_config: Dict[str, Any],
        memory_config: Dict[str, Any],
        **kwargs
    ):
        self.agent_id = agent_id
        self.role = role
        self.capabilities = capabilities
        self.model_config = model_config
        self.memory_config = memory_config
        
        # Status tracking
        self.status = AgentStatus.IDLE
        self.current_task_id: Optional[str] = None
        self.session_id: Optional[str] = None
        
        # Communication
        self.message_queue: List[AgentMessage] = []
        self.pending_responses: Dict[str, Any] = {}
        
        # Memory and context
        self.working_memory: Dict[str, Any] = {}
        self.context_history: List[Dict[str, Any]] = []
        
        # Tools and capabilities
        self.available_tools: Dict[str, Any] = {}
        
        # Observability
        self.logger = logging.getLogger(f"agent.{self.role}.{self.agent_id}")
        self.metrics: Dict[str, Any] = {
            "tasks_completed": 0,
            "errors_encountered": 0,
            "total_tokens_used": 0,
            "average_response_time": 0.0
        }
        
        # Initialize agent-specific configuration
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize agent-specific configuration and tools"""
        # Load role-specific prompt template
        self.system_prompt = self._load_system_prompt()
        
        # Initialize tools based on capabilities
        self._initialize_tools()
        
        # Set up memory access
        self._setup_memory_access()
        
        self.logger.info(f"Initialized {self.role} agent {self.agent_id}")
    
    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load role-specific system prompt template"""
        pass
    
    @abstractmethod
    def _initialize_tools(self):
        """Initialize role-specific tools and capabilities"""
        pass
    
    def _setup_memory_access(self):
        """Setup memory access based on configuration"""
        # This would initialize connections to Redis, vector DB, etc.
        # For now, using local memory with future extension points
        pass
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Process incoming message according to type and agent capabilities
        
        Args:
            message: Incoming message to process
            
        Returns:
            Optional response message
        """
        self.logger.info(f"Processing {message.message_type.value} from {message.sender}")
        
        try:
            if message.message_type == MessageType.TASK_ASSIGNMENT:
                return await self._handle_task_assignment(message)
            elif message.message_type == MessageType.QUERY:
                return await self._handle_query(message)
            elif message.message_type == MessageType.FEEDBACK:
                return await self._handle_feedback(message)
            elif message.message_type == MessageType.MEMORY_UPDATE:
                await self._handle_memory_update(message)
            else:
                self.logger.warning(f"Unknown message type: {message.message_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.metrics["errors_encountered"] += 1
            self.status = AgentStatus.ERROR
            
            # Return error response
            return AgentMessage(
                message_type=MessageType.RESULT_RETURN,
                sender=self.agent_id,
                recipient=message.sender,
                payload={
                    "status": "error",
                    "error": str(e),
                    "task_id": message.task_id
                },
                task_id=message.task_id,
                correlation_id=message.correlation_id
            )
    
    async def _handle_task_assignment(self, message: AgentMessage) -> AgentMessage:
        """Handle task assignment from orchestrator or other agents"""
        task_data = message.payload
        self.current_task_id = message.task_id
        self.status = AgentStatus.PROCESSING
        
        # Store task context in working memory
        self.working_memory[f"task_{message.task_id}"] = task_data
        
        # Execute the task using agent-specific logic
        result = await self._execute_task(task_data)
        
        # Update metrics
        self.metrics["tasks_completed"] += 1
        
        # Return result
        return AgentMessage(
            message_type=MessageType.RESULT_RETURN,
            sender=self.agent_id,
            recipient=message.sender,
            payload={
                "status": "completed",
                "result": result,
                "task_id": message.task_id,
                "agent_metadata": {
                    "role": self.role,
                    "capabilities_used": self._get_capabilities_used(task_data),
                    "tokens_used": result.get("tokens_used", 0),
                    "processing_time": result.get("processing_time", 0)
                }
            },
            task_id=message.task_id,
            correlation_id=message.correlation_id
        )
    
    @abstractmethod
    async def _execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent-specific task logic
        
        Args:
            task_data: Task specification and context
            
        Returns:
            Task execution result
        """
        pass
    
    async def _handle_query(self, message: AgentMessage) -> AgentMessage:
        """Handle queries from other agents or orchestrator"""
        query_data = message.payload
        
        # Process query using agent capabilities
        response = await self._process_query(query_data)
        
        return AgentMessage(
            message_type=MessageType.RESULT_RETURN,
            sender=self.agent_id,
            recipient=message.sender,
            payload=response,
            correlation_id=message.correlation_id
        )
    
    @abstractmethod
    async def _process_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process queries specific to agent role"""
        pass
    
    async def _handle_feedback(self, message: AgentMessage) -> None:
        """Handle feedback from other agents"""
        feedback_data = message.payload
        
        # Store feedback for learning and improvement
        self.context_history.append({
            "type": "feedback",
            "source": message.sender,
            "data": feedback_data,
            "timestamp": message.timestamp
        })
        
        # Process feedback for immediate adjustments
        await self._process_feedback(feedback_data)
    
    async def _process_feedback(self, feedback_data: Dict[str, Any]):
        """Process feedback for agent improvement"""
        # Default implementation stores feedback
        # Specialized agents can override for specific behavior
        pass
    
    async def _handle_memory_update(self, message: AgentMessage):
        """Handle memory updates from system or other agents"""
        memory_data = message.payload
        
        if "working_memory" in memory_data:
            self.working_memory.update(memory_data["working_memory"])
        
        if "context" in memory_data:
            self.context_history.append(memory_data["context"])
    
    def _get_capabilities_used(self, task_data: Dict[str, Any]) -> List[str]:
        """Determine which capabilities were used for a task"""
        # This would analyze the task and determine capabilities used
        # For now, return all available capabilities
        return self.capabilities
    
    async def send_message(self, recipient: str, message: AgentMessage):
        """Send message to another agent"""
        # In a real implementation, this would use Ray's messaging
        # or a message broker like Redis pub/sub
        try:
            recipient_actor = ray.get_actor(recipient)
            await recipient_actor.process_message.remote(message)
        except Exception as e:
            self.logger.error(f"Failed to send message to {recipient}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "capabilities": self.capabilities,
            "metrics": self.metrics,
            "working_memory_size": len(self.working_memory),
            "context_history_size": len(self.context_history)
        }
    
    async def update_memory(self, key: str, value: Any):
        """Update working memory"""
        self.working_memory[key] = value
        
        # In a real implementation, this might also update persistent memory
        # via Redis, vector DB, etc.
    
    async def retrieve_memory(self, key: str) -> Any:
        """Retrieve from working memory"""
        return self.working_memory.get(key)
    
    async def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search context history and memory"""
        # Simple text search implementation
        # In production, this would use vector similarity search
        results = []
        for item in self.context_history:
            if query.lower() in str(item).lower():
                results.append(item)
                if len(results) >= limit:
                    break
        return results
    
    def reset(self):
        """Reset agent state for new session"""
        self.status = AgentStatus.IDLE
        self.current_task_id = None
        self.working_memory.clear()
        self.context_history.clear()
        self.message_queue.clear()
        self.pending_responses.clear()
        
        self.logger.info(f"Reset {self.role} agent {self.agent_id}")