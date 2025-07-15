"""
SwarmCoordinator: Main orchestration engine for the vLLM Local Swarm.

This module implements the central coordination system that manages
all agents, routes tasks, and executes SPARC workflows using Ray.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

import ray

from .messaging import (
    Message, MessageType, TaskRequest, TaskResponse, TaskStatus,
    CoordinationMessage, Priority, create_task_request
)
from .agents import (
    AgentType, AgentBase, AgentConfiguration, create_agent,
    PlannerAgent, ResearcherAgent, CoderAgent, QAAgent, CriticAgent, JudgeAgent
)
from .routing import TaskRouter, DAGExecutor, RoutingStrategy


class SwarmState(Enum):
    """Current operational state of the swarm."""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    SCALING = "scaling"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class SwarmConfiguration:
    """Configuration for the SwarmCoordinator."""
    # Agent configuration
    default_agents_per_type: Dict[AgentType, int] = field(default_factory=lambda: {
        AgentType.PLANNER: 1,
        AgentType.RESEARCHER: 2,
        AgentType.CODER: 2,
        AgentType.QA: 1,
        AgentType.CRITIC: 1,
        AgentType.JUDGE: 1
    })
    
    # Model configuration
    primary_model: str = "phi-3.5"
    fallback_model: str = "gpt-4.1"
    
    # Orchestration settings
    max_concurrent_workflows: int = 10
    default_routing_strategy: RoutingStrategy = RoutingStrategy.SPARC_WORKFLOW
    enable_auto_scaling: bool = True
    
    # Performance settings
    task_timeout_seconds: int = 300
    heartbeat_interval_seconds: int = 30
    performance_monitoring_enabled: bool = True
    
    # Memory and storage
    enable_session_memory: bool = True
    enable_semantic_memory: bool = True
    memory_retention_days: int = 30


@dataclass
class SwarmMetrics:
    """Performance and operational metrics for the swarm."""
    # Task metrics
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_task_duration: float = 0.0
    current_active_tasks: int = 0
    
    # Agent metrics
    total_agents: int = 0
    active_agents: int = 0
    agent_utilization: float = 0.0
    
    # Resource metrics
    total_tokens_consumed: int = 0
    average_tokens_per_task: float = 0.0
    
    # Performance metrics
    success_rate: float = 1.0
    average_response_time: float = 0.0
    
    # System metrics
    uptime_seconds: float = 0.0
    last_updated: float = field(default_factory=time.time)


@ray.remote
class SwarmCoordinator:
    """
    Central orchestration engine for the vLLM Local Swarm.
    
    The SwarmCoordinator implements the SPARC framework's orchestration layer,
    managing specialized agents, routing tasks, and executing complex workflows
    through a Ray-distributed architecture.
    
    Key Responsibilities:
    - Agent lifecycle management (creation, monitoring, scaling)
    - Task routing and load balancing
    - Workflow orchestration via DAG execution
    - Performance monitoring and optimization
    - Memory and context management
    - Self-improvement and adaptation
    """
    
    def __init__(self, config: SwarmConfiguration):
        self.config = config
        self.state = SwarmState.INITIALIZING
        self.metrics = SwarmMetrics()
        
        # Core components
        self.task_router = TaskRouter()
        self.dag_executor = DAGExecutor(self.task_router)
        
        # Agent management
        self.agents: Dict[str, AgentBase] = {}
        self.agent_types: Dict[AgentType, List[str]] = {}
        
        # Task and workflow management
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Performance monitoring
        self.performance_history: List[SwarmMetrics] = []
        self.last_heartbeat = time.time()
        
        # Initialize logger
        self.logger = logging.getLogger("orchestrator.SwarmCoordinator")
        
        self.logger.info("SwarmCoordinator initializing...")
    
    async def initialize(self):
        """Initialize the swarm coordinator and create initial agents."""
        try:
            self.logger.info("Starting swarm initialization")
            
            # Initialize Ray if not already initialized
            if not ray.is_initialized():
                ray.init(address="auto", ignore_reinit_error=True)
            
            # Create initial agent pool
            await self._create_initial_agents()
            
            # Setup monitoring
            if self.config.performance_monitoring_enabled:
                await self._start_monitoring()
            
            # Mark as ready
            self.state = SwarmState.READY
            self.metrics.total_agents = len(self.agents)
            self.metrics.active_agents = len(self.agents)
            
            self.logger.info(f"SwarmCoordinator initialized with {len(self.agents)} agents")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SwarmCoordinator: {str(e)}")
            self.state = SwarmState.ERROR
            raise
    
    async def create_task(
        self, 
        task_definition: str, 
        objective: str,
        priority: Priority = Priority.MEDIUM,
        workflow_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Create and execute a new task.
        
        Args:
            task_definition: Description of what needs to be done
            objective: High-level goal and success criteria
            priority: Task priority level
            workflow_id: Optional workflow to use (defaults to SPARC)
            **kwargs: Additional task parameters
            
        Returns:
            Task ID for tracking progress
        """
        if self.state != SwarmState.READY:
            raise RuntimeError(f"Swarm not ready (current state: {self.state.value})")
        
        # Create task request
        task_request = create_task_request(
            sender_id="swarm_coordinator",
            recipient_id="",  # Will be determined by routing
            task_definition=task_definition,
            objective=objective,
            priority=priority,
            **kwargs
        )
        
        self.logger.info(f"Creating task {task_request.task_id}: {objective}")
        
        # Store task
        self.active_tasks[task_request.task_id] = task_request
        self.metrics.current_active_tasks += 1
        
        # Execute task (workflow or direct routing)
        if workflow_id or self._should_use_workflow(task_request):
            # Use workflow execution
            workflow_id = workflow_id or "sparc_default"
            asyncio.create_task(
                self._execute_workflow_task(task_request, workflow_id)
            )
        else:
            # Direct agent routing
            asyncio.create_task(
                self._execute_direct_task(task_request)
            )
        
        return task_request.task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get current status of a task."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "active",
                "definition": task.task_definition,
                "objective": task.objective,
                "priority": task.priority.value,
                "created_time": task.timestamp.isoformat()
            }
        
        # Check completed tasks
        for task_record in self.task_history:
            if task_record.get("task_id") == task_id:
                return task_record
        
        return {"task_id": task_id, "status": "not_found"}
    
    async def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks with optional status filter."""
        tasks = []
        
        # Active tasks
        if not status or status == "active":
            for task_id, task in self.active_tasks.items():
                tasks.append({
                    "task_id": task_id,
                    "status": "active",
                    "definition": task.task_definition,
                    "objective": task.objective,
                    "priority": task.priority.value,
                    "created_time": task.timestamp.isoformat()
                })
        
        # Historical tasks
        if not status or status in ["completed", "failed"]:
            for task_record in self.task_history[-50:]:  # Last 50 tasks
                if not status or task_record.get("status") == status:
                    tasks.append(task_record)
        
        return tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            self.metrics.current_active_tasks -= 1
            
            # Add to history as cancelled
            self.task_history.append({
                "task_id": task_id,
                "status": "cancelled",
                "definition": task.task_definition,
                "objective": task.objective,
                "cancelled_time": time.time()
            })
            
            self.logger.info(f"Cancelled task {task_id}")
            return True
        
        return False
    
    async def get_swarm_status(self) -> Dict[str, Any]:
        """Get comprehensive swarm status and metrics."""
        # Update current metrics
        await self._update_metrics()
        
        return {
            "state": self.state.value,
            "metrics": {
                "total_tasks_completed": self.metrics.total_tasks_completed,
                "total_tasks_failed": self.metrics.total_tasks_failed,
                "current_active_tasks": self.metrics.current_active_tasks,
                "success_rate": self.metrics.success_rate,
                "average_task_duration": self.metrics.average_task_duration,
                "total_agents": self.metrics.total_agents,
                "active_agents": self.metrics.active_agents,
                "agent_utilization": self.metrics.agent_utilization,
                "uptime_seconds": time.time() - (self.metrics.last_updated - self.metrics.uptime_seconds)
            },
            "agents": await self._get_agent_status(),
            "workflows": {
                "active_count": len(self.active_workflows),
                "available_workflows": list(self.dag_executor.workflow_definitions.keys())
            }
        }
    
    async def scale_agents(self, agent_type: AgentType, target_count: int) -> bool:
        """Scale the number of agents of a specific type."""
        self.logger.info(f"Scaling {agent_type.value} agents to {target_count}")
        
        current_count = len(self.agent_types.get(agent_type, []))
        
        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                agent_id = f"{agent_type.value}_{len(self.agents) + 1}"
                await self._create_agent(agent_type, agent_id)
        
        elif target_count < current_count:
            # Scale down
            agents_to_remove = self.agent_types[agent_type][target_count:]
            for agent_id in agents_to_remove:
                await self._remove_agent(agent_id)
        
        await self._update_metrics()
        return True
    
    async def shutdown(self):
        """Gracefully shutdown the swarm coordinator."""
        self.logger.info("Shutting down SwarmCoordinator")
        self.state = SwarmState.SHUTDOWN
        
        # Cancel active tasks
        for task_id in list(self.active_tasks.keys()):
            await self.cancel_task(task_id)
        
        # Shutdown agents
        for agent_id in list(self.agents.keys()):
            await self._remove_agent(agent_id)
        
        self.logger.info("SwarmCoordinator shutdown complete")
    
    # Private methods
    
    async def _create_initial_agents(self):
        """Create the initial pool of agents."""
        for agent_type, count in self.config.default_agents_per_type.items():
            for i in range(count):
                agent_id = f"{agent_type.value}_{i + 1}"
                await self._create_agent(agent_type, agent_id)
    
    async def _create_agent(self, agent_type: AgentType, agent_id: str) -> str:
        """Create a new agent of the specified type."""
        try:
            # Create agent configuration
            config = AgentConfiguration(
                agent_id=agent_id,
                agent_type=agent_type,
                capabilities=self._get_default_capabilities(agent_type),
                primary_model=self.config.primary_model,
                fallback_model=self.config.fallback_model
            )
            
            # Create and initialize agent
            agent = await create_agent(agent_type, agent_id, **config.__dict__)
            
            # Register with coordinator
            self.agents[agent_id] = agent
            
            if agent_type not in self.agent_types:
                self.agent_types[agent_type] = []
            self.agent_types[agent_type].append(agent_id)
            
            # Register with router
            self.task_router.register_agent(agent_id, agent, agent_type)
            
            self.logger.info(f"Created agent {agent_id} ({agent_type.value})")
            return agent_id
            
        except Exception as e:
            self.logger.error(f"Failed to create agent {agent_id}: {str(e)}")
            raise
    
    async def _remove_agent(self, agent_id: str):
        """Remove an agent from the swarm."""
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)
            
            # Remove from type registry
            for agent_type, agent_list in self.agent_types.items():
                if agent_id in agent_list:
                    agent_list.remove(agent_id)
                    break
            
            # Unregister from router
            self.task_router.unregister_agent(agent_id)
            
            self.logger.info(f"Removed agent {agent_id}")
    
    def _get_default_capabilities(self, agent_type: AgentType):
        """Get default capabilities for an agent type."""
        # This would be expanded with actual capability definitions
        from .agents import AgentCapabilities
        return AgentCapabilities()
    
    async def _execute_workflow_task(self, task_request: TaskRequest, workflow_id: str):
        """Execute a task using workflow orchestration."""
        try:
            self.logger.info(f"Executing task {task_request.task_id} using workflow {workflow_id}")
            
            # Track workflow
            execution_id = f"{workflow_id}_{task_request.task_id}"
            self.active_workflows[execution_id] = {
                "task_id": task_request.task_id,
                "workflow_id": workflow_id,
                "start_time": time.time(),
                "status": "running"
            }
            
            # Execute workflow
            result = await self.dag_executor.execute_workflow(
                workflow_id, task_request, execution_id
            )
            
            # Process result
            await self._complete_task(task_request.task_id, result, workflow_execution=True)
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed for task {task_request.task_id}: {str(e)}")
            await self._fail_task(task_request.task_id, str(e))
        
        finally:
            if execution_id in self.active_workflows:
                self.active_workflows.pop(execution_id)
    
    async def _execute_direct_task(self, task_request: TaskRequest):
        """Execute a task via direct agent routing."""
        try:
            self.logger.info(f"Executing task {task_request.task_id} via direct routing")
            
            # Route to appropriate agent
            agent_id = await self.task_router.route_task(
                task_request, self.config.default_routing_strategy
            )
            
            if not agent_id:
                raise RuntimeError("No suitable agent found for task")
            
            # Execute task
            agent = self.agents[agent_id]
            response = await agent.handle_message.remote(task_request)
            
            # Process response
            if response and hasattr(response, 'status'):
                if response.status == TaskStatus.COMPLETED:
                    await self._complete_task(task_request.task_id, response.deliverables)
                else:
                    await self._fail_task(task_request.task_id, response.task_completion_summary)
            else:
                await self._fail_task(task_request.task_id, "No response from agent")
            
        except Exception as e:
            self.logger.error(f"Direct task execution failed for {task_request.task_id}: {str(e)}")
            await self._fail_task(task_request.task_id, str(e))
    
    async def _complete_task(self, task_id: str, result: Any, workflow_execution: bool = False):
        """Mark a task as completed and update metrics."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            
            # Update metrics
            self.metrics.total_tasks_completed += 1
            self.metrics.current_active_tasks -= 1
            
            # Add to history
            completion_record = {
                "task_id": task_id,
                "status": "completed",
                "definition": task.task_definition,
                "objective": task.objective,
                "result": result,
                "workflow_execution": workflow_execution,
                "completed_time": time.time(),
                "duration": time.time() - task.timestamp.timestamp()
            }
            
            self.task_history.append(completion_record)
            
            # Update performance metrics
            await self._update_task_performance_metrics(completion_record["duration"], True)
            
            self.logger.info(f"Task {task_id} completed successfully")
    
    async def _fail_task(self, task_id: str, error_message: str):
        """Mark a task as failed and update metrics."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            
            # Update metrics
            self.metrics.total_tasks_failed += 1
            self.metrics.current_active_tasks -= 1
            
            # Add to history
            failure_record = {
                "task_id": task_id,
                "status": "failed",
                "definition": task.task_definition,
                "objective": task.objective,
                "error": error_message,
                "failed_time": time.time(),
                "duration": time.time() - task.timestamp.timestamp()
            }
            
            self.task_history.append(failure_record)
            
            # Update performance metrics
            await self._update_task_performance_metrics(failure_record["duration"], False)
            
            self.logger.error(f"Task {task_id} failed: {error_message}")
    
    def _should_use_workflow(self, task_request: TaskRequest) -> bool:
        """Determine if a task should use workflow execution."""
        # Use workflow for complex tasks or when explicitly requested
        complex_keywords = ['complex', 'multi-step', 'workflow', 'pipeline', 'comprehensive']
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        
        return any(keyword in task_text for keyword in complex_keywords)
    
    async def _start_monitoring(self):
        """Start performance monitoring background task."""
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.state != SwarmState.SHUTDOWN:
            try:
                await self._update_metrics()
                await self._check_agent_health()
                
                # Auto-scaling if enabled
                if self.config.enable_auto_scaling:
                    await self._evaluate_auto_scaling()
                
                await asyncio.sleep(self.config.heartbeat_interval_seconds)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _update_metrics(self):
        """Update performance metrics."""
        # Calculate success rate
        total_tasks = self.metrics.total_tasks_completed + self.metrics.total_tasks_failed
        if total_tasks > 0:
            self.metrics.success_rate = self.metrics.total_tasks_completed / total_tasks
        
        # Update agent metrics
        self.metrics.total_agents = len(self.agents)
        
        # Calculate agent utilization
        if self.metrics.total_agents > 0:
            busy_agents = 0
            for agent_id, agent in self.agents.items():
                try:
                    metrics = await agent.get_performance_metrics.remote()
                    if metrics.get('current_task_count', 0) > 0:
                        busy_agents += 1
                except:
                    pass  # Skip if agent unavailable
            
            self.metrics.agent_utilization = busy_agents / self.metrics.total_agents
        
        # Update timestamp
        self.metrics.last_updated = time.time()
    
    async def _update_task_performance_metrics(self, duration: float, success: bool):
        """Update task-specific performance metrics."""
        # Update average task duration
        total_tasks = self.metrics.total_tasks_completed + self.metrics.total_tasks_failed
        if total_tasks == 1:
            self.metrics.average_task_duration = duration
        else:
            self.metrics.average_task_duration = (
                (self.metrics.average_task_duration * (total_tasks - 1) + duration) / total_tasks
            )
    
    async def _check_agent_health(self):
        """Check health status of all agents."""
        unhealthy_agents = []
        
        for agent_id, agent in self.agents.items():
            try:
                # Try to get agent status
                metrics = await asyncio.wait_for(
                    agent.get_performance_metrics.remote(), 
                    timeout=5.0
                )
                # Agent responded successfully
            except (asyncio.TimeoutError, Exception):
                unhealthy_agents.append(agent_id)
        
        # Handle unhealthy agents
        for agent_id in unhealthy_agents:
            self.logger.warning(f"Agent {agent_id} appears unhealthy")
            # In a full implementation, we might restart or replace the agent
    
    async def _evaluate_auto_scaling(self):
        """Evaluate whether auto-scaling is needed."""
        # Simple auto-scaling logic based on agent utilization
        if self.metrics.agent_utilization > 0.8:
            # High utilization - consider scaling up
            self.logger.info("High agent utilization detected - consider scaling up")
        elif self.metrics.agent_utilization < 0.3 and self.metrics.total_agents > 3:
            # Low utilization - consider scaling down
            self.logger.info("Low agent utilization detected - consider scaling down")
    
    async def _get_agent_status(self) -> Dict[str, Any]:
        """Get detailed status of all agents."""
        agent_status = {}
        
        for agent_id, agent in self.agents.items():
            try:
                metrics = await agent.get_performance_metrics.remote()
                agent_status[agent_id] = metrics
            except Exception as e:
                agent_status[agent_id] = {"error": str(e), "status": "unreachable"}
        
        return agent_status


# Utility functions for creating and managing swarm coordinators

async def create_swarm_coordinator(config: Optional[SwarmConfiguration] = None) -> SwarmCoordinator:
    """
    Create and initialize a SwarmCoordinator.
    
    Args:
        config: Optional configuration. Uses defaults if not provided.
        
    Returns:
        Initialized SwarmCoordinator
    """
    if config is None:
        config = SwarmConfiguration()
    
    coordinator = SwarmCoordinator.remote(config)
    await coordinator.initialize.remote()
    
    return coordinator


def get_default_swarm_config() -> SwarmConfiguration:
    """Get a default SwarmConfiguration."""
    return SwarmConfiguration()