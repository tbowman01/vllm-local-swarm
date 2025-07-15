"""
Base agent classes and specialized agent types for the SPARC framework.

This module implements the core agent architecture with specialized roles:
Planner, Researcher, Coder, QA, Critic, and Judge.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import ray

from .messaging import (
    Message, MessageType, TaskRequest, TaskResponse, TaskStatus,
    Priority, MessageValidator, create_task_response
)


class AgentType(Enum):
    """Specialized agent types following SPARC methodology."""
    PLANNER = "planner"          # Orchestrator - breaks down tasks, coordinates
    RESEARCHER = "researcher"     # Information Specialist - knowledge gathering
    CODER = "coder"              # Developer - code generation and implementation
    QA = "qa"                    # Tester/Validator - quality assurance
    CRITIC = "critic"            # Reviewer - critical evaluation and feedback
    JUDGE = "judge"              # Evaluator/Decider - final decisions and approvals


class AgentState(Enum):
    """Current operational state of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentCapabilities:
    """Defines what an agent can do and its resource requirements."""
    supported_tasks: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    requires_internet: bool = False
    requires_code_execution: bool = False
    requires_file_access: bool = False
    model_preferences: List[str] = field(default_factory=list)
    max_context_tokens: int = 4096


@dataclass
class AgentConfiguration:
    """Agent configuration and behavior settings."""
    agent_id: str
    agent_type: AgentType
    capabilities: AgentCapabilities
    
    # Prompt configuration
    system_prompt_template: str = ""
    cognitive_framework: str = ""  # e.g., "Define→Infer→Synthesize"
    output_format_template: str = ""
    
    # Model configuration
    primary_model: str = "phi-3.5"
    fallback_model: str = "gpt-4.1"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    # Behavioral settings
    max_retries: int = 3
    timeout_seconds: int = 300
    auto_escalate_threshold: float = 0.6  # Confidence threshold for escalation
    
    # Memory and context settings
    use_memory: bool = True
    memory_retention_days: int = 30
    context_compression_enabled: bool = True


@ray.remote
class AgentBase(ABC):
    """
    Base class for all SPARC-aligned agents.
    
    Implements core agent functionality including:
    - Structured message handling
    - Memory integration
    - Model interaction
    - Performance tracking
    - Error handling and recovery
    """
    
    def __init__(self, config: AgentConfiguration):
        self.config = config
        self.state = AgentState.IDLE
        self.current_tasks: Dict[str, TaskRequest] = {}
        self.task_history: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.total_tasks_completed = 0
        self.total_tokens_consumed = 0
        self.average_response_time = 0.0
        self.success_rate = 1.0
        
        # Initialize logger
        self.logger = logging.getLogger(f"agent.{config.agent_type.value}.{config.agent_id}")
        
        # Initialize connections (to be implemented by subclasses)
        self._llm_client = None
        self._memory_store = None
        self._vector_store = None
        
        self.logger.info(f"Agent {self.config.agent_id} ({self.config.agent_type.value}) initialized")
    
    async def initialize(self):
        """Initialize agent resources and connections."""
        await self._setup_llm_client()
        await self._setup_memory_connections()
        self.state = AgentState.IDLE
        self.logger.info(f"Agent {self.config.agent_id} ready")
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """
        Main message handling entry point.
        
        Routes messages to appropriate handlers based on message type.
        """
        # Validate message
        is_valid, errors = MessageValidator.validate_message(message)
        if not is_valid:
            self.logger.error(f"Invalid message received: {errors}")
            return self._create_error_response(message, f"Message validation failed: {errors}")
        
        try:
            self.logger.debug(f"Handling message {message.message_id} of type {message.message_type}")
            
            # Route based on message type
            if message.message_type == MessageType.TASK_REQUEST:
                return await self._handle_task_request(message)
            elif message.message_type == MessageType.COORDINATION:
                return await self._handle_coordination(message)
            elif message.message_type == MessageType.MEMORY_STORE:
                return await self._handle_memory_store(message)
            elif message.message_type == MessageType.MEMORY_RETRIEVE:
                return await self._handle_memory_retrieve(message)
            else:
                self.logger.warning(f"Unhandled message type: {message.message_type}")
                return self._create_error_response(message, f"Unsupported message type: {message.message_type}")
        
        except Exception as e:
            self.logger.error(f"Error handling message {message.message_id}: {str(e)}")
            return self._create_error_response(message, str(e))
    
    async def _handle_task_request(self, message: Message) -> TaskResponse:
        """Handle incoming task requests."""
        task_request = TaskRequest.from_dict(message.to_dict())
        
        # Check if we can handle this task
        if not self._can_handle_task(task_request):
            return self._create_task_response(
                task_request,
                status=TaskStatus.FAILED,
                summary="Agent cannot handle this task type",
                issues=["Task type not supported by this agent"]
            )
        
        # Check capacity
        if len(self.current_tasks) >= self.config.capabilities.max_concurrent_tasks:
            return self._create_task_response(
                task_request,
                status=TaskStatus.FAILED,
                summary="Agent at capacity",
                issues=["Maximum concurrent tasks reached"]
            )
        
        # Execute task
        self.state = AgentState.BUSY
        self.current_tasks[task_request.task_id] = task_request
        
        try:
            start_time = time.time()
            response = await self._execute_task(task_request)
            execution_time = time.time() - start_time
            
            # Update performance metrics
            self._update_performance_metrics(execution_time, response.status == TaskStatus.COMPLETED)
            
            return response
        
        finally:
            self.current_tasks.pop(task_request.task_id, None)
            self.state = AgentState.IDLE if not self.current_tasks else AgentState.BUSY
    
    @abstractmethod
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """
        Execute the actual task logic.
        
        Must be implemented by specialized agent subclasses.
        """
        pass
    
    @abstractmethod
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """
        Determine if this agent can handle the given task.
        
        Must be implemented by specialized agent subclasses.
        """
        pass
    
    async def _handle_coordination(self, message: Message) -> Optional[Message]:
        """Handle coordination messages from other agents."""
        coordination_type = message.content.get("coordination_type", "")
        
        if coordination_type == "status_check":
            return self._create_status_response(message)
        elif coordination_type == "resource_request":
            return await self._handle_resource_request(message)
        else:
            self.logger.debug(f"Unhandled coordination type: {coordination_type}")
            return None
    
    async def _handle_memory_store(self, message: Message) -> Optional[Message]:
        """Store information in agent memory."""
        # Implementation depends on memory backend
        pass
    
    async def _handle_memory_retrieve(self, message: Message) -> Optional[Message]:
        """Retrieve information from agent memory."""
        # Implementation depends on memory backend
        pass
    
    def _create_task_response(
        self,
        task_request: TaskRequest,
        status: TaskStatus,
        summary: str,
        deliverables: Optional[Dict[str, Any]] = None,
        issues: Optional[List[str]] = None,
        **kwargs
    ) -> TaskResponse:
        """Create a standardized task response."""
        return create_task_response(
            sender_id=self.config.agent_id,
            recipient_id=task_request.sender_id,
            task_completion_summary=summary,
            deliverables=deliverables or {},
            task_id=task_request.task_id,
            status=status,
            issues_encountered=issues or [],
            model_used=self.config.primary_model,
            **kwargs
        )
    
    def _create_error_response(self, original_message: Message, error_message: str) -> Message:
        """Create an error response message."""
        return Message(
            message_type=MessageType.ERROR,
            sender_id=self.config.agent_id,
            recipient_id=original_message.sender_id,
            content={"error": error_message, "original_message_id": original_message.message_id},
            task_id=original_message.task_id,
            session_id=original_message.session_id
        )
    
    def _create_status_response(self, message: Message) -> Message:
        """Create a status response for coordination."""
        return Message(
            message_type=MessageType.STATUS_UPDATE,
            sender_id=self.config.agent_id,
            recipient_id=message.sender_id,
            content={
                "state": self.state.value,
                "current_tasks": len(self.current_tasks),
                "max_capacity": self.config.capabilities.max_concurrent_tasks,
                "total_completed": self.total_tasks_completed,
                "success_rate": self.success_rate
            }
        )
    
    async def _handle_resource_request(self, message: Message) -> Optional[Message]:
        """Handle requests for agent resources or capabilities."""
        # Default implementation - can be overridden by subclasses
        return Message(
            message_type=MessageType.COORDINATION,
            sender_id=self.config.agent_id,
            recipient_id=message.sender_id,
            content={
                "coordination_type": "resource_response",
                "capabilities": {
                    "supported_tasks": self.config.capabilities.supported_tasks,
                    "max_concurrent_tasks": self.config.capabilities.max_concurrent_tasks,
                    "available_capacity": (
                        self.config.capabilities.max_concurrent_tasks - len(self.current_tasks)
                    )
                }
            }
        )
    
    def _update_performance_metrics(self, execution_time: float, success: bool):
        """Update agent performance tracking metrics."""
        self.total_tasks_completed += 1
        
        # Update average response time
        if self.average_response_time == 0.0:
            self.average_response_time = execution_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_tasks_completed - 1) + execution_time)
                / self.total_tasks_completed
            )
        
        # Update success rate
        if success:
            success_count = int(self.success_rate * (self.total_tasks_completed - 1)) + 1
        else:
            success_count = int(self.success_rate * (self.total_tasks_completed - 1))
        
        self.success_rate = success_count / self.total_tasks_completed
    
    async def _setup_llm_client(self):
        """Setup LLM client connections."""
        # To be implemented with actual LLM clients
        pass
    
    async def _setup_memory_connections(self):
        """Setup memory store connections."""
        # To be implemented with actual memory backends
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return {
            "agent_id": self.config.agent_id,
            "agent_type": self.config.agent_type.value,
            "state": self.state.value,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tokens_consumed": self.total_tokens_consumed,
            "average_response_time": self.average_response_time,
            "success_rate": self.success_rate,
            "current_task_count": len(self.current_tasks),
            "max_capacity": self.config.capabilities.max_concurrent_tasks
        }


# Specialized Agent Classes for SPARC Roles

@ray.remote
class PlannerAgent(AgentBase):
    """
    Planner (Orchestrator) Agent - SPARC Framework
    
    Responsibilities:
    - Breaks down high-level objectives into concrete tasks
    - Assigns tasks to specialized agents
    - Coordinates workflow and manages dependencies
    - Integrates results from multiple agents
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.PLANNER
        config.capabilities.supported_tasks = [
            "task_decomposition", "workflow_planning", "agent_coordination",
            "result_integration", "dependency_analysis"
        ]
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """Planner can handle orchestration and coordination tasks."""
        task_keywords = ["plan", "coordinate", "orchestrate", "breakdown", "manage"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute planning and orchestration logic."""
        # TODO: Implement actual planning logic with LLM
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="Planning task completed",
            deliverables={"plan": "Generated task breakdown"}
        )


@ray.remote
class ResearcherAgent(AgentBase):
    """
    Researcher (Information Specialist) Agent - SPARC Framework
    
    Responsibilities:
    - Knowledge gathering and information synthesis
    - Web searches and documentation analysis
    - Evidence collection with proper citations
    - Cross-verification of facts
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.RESEARCHER
        config.capabilities.supported_tasks = [
            "information_gathering", "web_search", "document_analysis",
            "fact_verification", "citation_formatting"
        ]
        config.capabilities.requires_internet = True
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """Researcher can handle information gathering tasks."""
        task_keywords = ["research", "search", "analyze", "investigate", "gather", "find"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute research and information gathering."""
        # TODO: Implement actual research logic with LLM and tools
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="Research task completed",
            deliverables={"research_report": "Gathered information with citations"}
        )


@ray.remote
class CoderAgent(AgentBase):
    """
    Coder (Developer) Agent - SPARC Framework
    
    Responsibilities:
    - Code generation and implementation
    - Following architectural constraints
    - Code optimization and refactoring
    - Integration with existing codebases
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.CODER
        config.capabilities.supported_tasks = [
            "code_generation", "code_optimization", "debugging",
            "refactoring", "integration", "documentation"
        ]
        config.capabilities.requires_code_execution = True
        config.capabilities.requires_file_access = True
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """Coder can handle programming and development tasks."""
        task_keywords = ["code", "implement", "develop", "program", "build", "create", "write"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute coding and development tasks."""
        # TODO: Implement actual coding logic with LLM and tools
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="Coding task completed",
            deliverables={"code": "Generated code implementation"}
        )


@ray.remote
class QAAgent(AgentBase):
    """
    QA (Tester/Validator) Agent - SPARC Framework
    
    Responsibilities:
    - Quality assurance and testing
    - Code validation and correctness checking
    - Security policy compliance
    - Performance verification
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.QA
        config.capabilities.supported_tasks = [
            "testing", "validation", "quality_assurance",
            "security_check", "performance_testing"
        ]
        config.capabilities.requires_code_execution = True
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """QA can handle testing and validation tasks."""
        task_keywords = ["test", "validate", "verify", "check", "ensure", "quality"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute testing and validation tasks."""
        # TODO: Implement actual QA logic with LLM and testing tools
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="QA task completed",
            deliverables={"test_results": "Validation and testing results"}
        )


@ray.remote
class CriticAgent(AgentBase):
    """
    Critic (Reviewer) Agent - SPARC Framework
    
    Responsibilities:
    - Critical evaluation of outputs
    - Identifying flaws and improvements
    - Suggesting alternative approaches
    - Constructive feedback generation
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.CRITIC
        config.capabilities.supported_tasks = [
            "code_review", "critical_analysis", "improvement_suggestions",
            "alternative_solutions", "feedback_generation"
        ]
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """Critic can handle review and evaluation tasks."""
        task_keywords = ["review", "critique", "evaluate", "analyze", "assess", "improve"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute critical review and evaluation."""
        # TODO: Implement actual critique logic with LLM
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="Critique task completed",
            deliverables={"critique": "Critical evaluation and improvement suggestions"}
        )


@ray.remote
class JudgeAgent(AgentBase):
    """
    Judge (Evaluator/Decider) Agent - SPARC Framework
    
    Responsibilities:
    - Final decision making on task completion
    - Scoring and approval processes
    - Integration of multiple evaluations
    - Determining need for additional iterations
    """
    
    def __init__(self, config: AgentConfiguration):
        config.agent_type = AgentType.JUDGE
        config.capabilities.supported_tasks = [
            "final_evaluation", "decision_making", "scoring",
            "approval_process", "iteration_assessment"
        ]
        super().__init__(config)
    
    def _can_handle_task(self, task_request: TaskRequest) -> bool:
        """Judge can handle evaluation and decision tasks."""
        task_keywords = ["judge", "evaluate", "decide", "approve", "score", "assess"]
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        return any(keyword in task_text for keyword in task_keywords)
    
    async def _execute_task(self, task_request: TaskRequest) -> TaskResponse:
        """Execute final evaluation and decision making."""
        # TODO: Implement actual judging logic with LLM
        return self._create_task_response(
            task_request,
            status=TaskStatus.COMPLETED,
            summary="Evaluation task completed",
            deliverables={"evaluation": "Final evaluation and decision"}
        )


# Agent Factory Functions

def create_agent_config(
    agent_id: str,
    agent_type: AgentType,
    primary_model: str = "phi-3.5",
    **kwargs
) -> AgentConfiguration:
    """Create a standardized agent configuration."""
    capabilities = AgentCapabilities()
    
    return AgentConfiguration(
        agent_id=agent_id,
        agent_type=agent_type,
        capabilities=capabilities,
        primary_model=primary_model,
        **kwargs
    )


async def create_agent(agent_type: AgentType, agent_id: str, **config_kwargs) -> AgentBase:
    """
    Factory function to create specialized agents.
    
    Args:
        agent_type: Type of agent to create
        agent_id: Unique identifier for the agent
        **config_kwargs: Additional configuration options
    
    Returns:
        Initialized agent instance
    """
    config = create_agent_config(agent_id, agent_type, **config_kwargs)
    
    # Map agent types to classes
    agent_classes = {
        AgentType.PLANNER: PlannerAgent,
        AgentType.RESEARCHER: ResearcherAgent,
        AgentType.CODER: CoderAgent,
        AgentType.QA: QAAgent,
        AgentType.CRITIC: CriticAgent,
        AgentType.JUDGE: JudgeAgent
    }
    
    agent_class = agent_classes.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    # Create and initialize agent
    agent = agent_class.remote(config)
    await agent.initialize.remote()
    
    return agent