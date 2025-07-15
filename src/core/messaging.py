"""
Structured messaging and communication protocols for agent interactions.

This module implements the SPARC framework's boomerang routing pattern
and structured message formats for reliable agent-to-agent communication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class MessageType(Enum):
    """Types of messages in the system."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    COORDINATION = "coordination"
    FEEDBACK = "feedback"
    STATUS_UPDATE = "status_update"
    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    ERROR = "error"


class Priority(Enum):
    """Task and message priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Message:
    """
    Base structured message for agent communication.
    
    Implements the SPARC framework's structured template approach
    for consistent and complete information exchange.
    """
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.COORDINATION
    sender_id: str = ""
    recipient_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: Priority = Priority.MEDIUM
    
    # Core message content
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Routing information for boomerang pattern
    return_to: Optional[str] = None
    task_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "content": self.content,
            "context": self.context,
            "metadata": self.metadata,
            "return_to": self.return_to,
            "task_id": self.task_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=MessageType(data.get("message_type", "coordination")),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            priority=Priority(data.get("priority", 2)),
            content=data.get("content", {}),
            context=data.get("context", {}),
            metadata=data.get("metadata", {}),
            return_to=data.get("return_to"),
            task_id=data.get("task_id"),
            session_id=data.get("session_id")
        )


@dataclass
class TaskRequest(Message):
    """
    Structured task request following SPARC methodology.
    
    Implements the Define→Infer→Synthesize cognitive pattern
    with clear task definition, context, and expected outputs.
    """
    message_type: MessageType = field(default=MessageType.TASK_REQUEST, init=False)
    
    # SPARC-aligned task structure
    task_definition: str = ""
    objective: str = ""
    constraints: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    expected_output_format: str = ""
    success_criteria: List[str] = field(default_factory=list)
    
    # Context tiers for token efficiency
    tier1_context: Dict[str, Any] = field(default_factory=dict)  # Essential context
    tier2_context: Dict[str, Any] = field(default_factory=dict)  # Additional context on request
    tier3_context: Dict[str, Any] = field(default_factory=dict)  # Extended context if needed
    
    # Execution parameters
    max_iterations: int = 3
    timeout_seconds: int = 300
    use_fallback_model: bool = False
    
    def __post_init__(self):
        """Populate content with task-specific fields."""
        self.content.update({
            "task_definition": self.task_definition,
            "objective": self.objective,
            "constraints": self.constraints,
            "dependencies": self.dependencies,
            "expected_output_format": self.expected_output_format,
            "success_criteria": self.success_criteria,
            "tier1_context": self.tier1_context,
            "tier2_context": self.tier2_context,
            "tier3_context": self.tier3_context,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "use_fallback_model": self.use_fallback_model
        })


@dataclass
class TaskResponse(Message):
    """
    Structured task response with comprehensive feedback.
    
    Follows SPARC's structured output template to ensure
    complete and parseable results.
    """
    message_type: MessageType = field(default=MessageType.TASK_RESPONSE, init=False)
    
    # Core response sections
    task_completion_summary: str = ""
    deliverables: Dict[str, Any] = field(default_factory=dict)
    issues_encountered: List[str] = field(default_factory=list)
    next_steps_recommendation: List[str] = field(default_factory=list)
    
    # Execution metrics
    status: TaskStatus = TaskStatus.COMPLETED
    execution_time_seconds: float = 0.0
    iterations_used: int = 1
    tokens_consumed: int = 0
    model_used: str = ""
    
    # Quality indicators
    confidence_score: float = 0.8  # 0.0 to 1.0
    needs_review: bool = False
    requires_human_input: bool = False
    
    # Feedback for improvement
    performance_notes: List[str] = field(default_factory=list)
    suggested_improvements: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Populate content with response-specific fields."""
        self.content.update({
            "task_completion_summary": self.task_completion_summary,
            "deliverables": self.deliverables,
            "issues_encountered": self.issues_encountered,
            "next_steps_recommendation": self.next_steps_recommendation,
            "status": self.status.value,
            "execution_time_seconds": self.execution_time_seconds,
            "iterations_used": self.iterations_used,
            "tokens_consumed": self.tokens_consumed,
            "model_used": self.model_used,
            "confidence_score": self.confidence_score,
            "needs_review": self.needs_review,
            "requires_human_input": self.requires_human_input,
            "performance_notes": self.performance_notes,
            "suggested_improvements": self.suggested_improvements
        })


@dataclass
class CoordinationMessage(Message):
    """
    Messages for agent coordination and workflow management.
    """
    message_type: MessageType = field(default=MessageType.COORDINATION, init=False)
    
    coordination_type: str = ""  # "handoff", "status_check", "resource_request", etc.
    workflow_stage: str = ""     # Current SPARC stage
    agent_assignments: Dict[str, str] = field(default_factory=dict)
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Populate content with coordination-specific fields."""
        self.content.update({
            "coordination_type": self.coordination_type,
            "workflow_stage": self.workflow_stage,
            "agent_assignments": self.agent_assignments,
            "resource_requirements": self.resource_requirements
        })


class MessageValidator:
    """
    Validates message structure and content for reliability.
    """
    
    @staticmethod
    def validate_message(message: Message) -> tuple[bool, List[str]]:
        """
        Validate a message structure and content.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        if not message.sender_id:
            errors.append("sender_id is required")
        if not message.recipient_id:
            errors.append("recipient_id is required")
        
        # Message type specific validation
        if isinstance(message, TaskRequest):
            if not message.task_definition:
                errors.append("task_definition is required for TaskRequest")
            if not message.objective:
                errors.append("objective is required for TaskRequest")
        
        elif isinstance(message, TaskResponse):
            if not message.task_completion_summary:
                errors.append("task_completion_summary is required for TaskResponse")
            if message.confidence_score < 0.0 or message.confidence_score > 1.0:
                errors.append("confidence_score must be between 0.0 and 1.0")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_task_dependencies(task: TaskRequest, available_tasks: List[str]) -> tuple[bool, List[str]]:
        """
        Validate that task dependencies are satisfiable.
        """
        errors = []
        
        for dep in task.dependencies:
            if dep not in available_tasks:
                errors.append(f"Dependency '{dep}' is not available")
        
        return len(errors) == 0, errors


# Utility functions for message handling
def create_task_request(
    sender_id: str,
    recipient_id: str,
    task_definition: str,
    objective: str,
    task_id: Optional[str] = None,
    **kwargs
) -> TaskRequest:
    """Create a standardized task request message."""
    return TaskRequest(
        sender_id=sender_id,
        recipient_id=recipient_id,
        task_definition=task_definition,
        objective=objective,
        task_id=task_id or str(uuid.uuid4()),
        **kwargs
    )


def create_task_response(
    sender_id: str,
    recipient_id: str,
    task_completion_summary: str,
    deliverables: Dict[str, Any],
    task_id: Optional[str] = None,
    **kwargs
) -> TaskResponse:
    """Create a standardized task response message."""
    return TaskResponse(
        sender_id=sender_id,
        recipient_id=recipient_id,
        task_completion_summary=task_completion_summary,
        deliverables=deliverables,
        task_id=task_id,
        **kwargs
    )


def create_coordination_message(
    sender_id: str,
    recipient_id: str,
    coordination_type: str,
    workflow_stage: str,
    **kwargs
) -> CoordinationMessage:
    """Create a standardized coordination message."""
    return CoordinationMessage(
        sender_id=sender_id,
        recipient_id=recipient_id,
        coordination_type=coordination_type,
        workflow_stage=workflow_stage,
        **kwargs
    )