#!/usr/bin/env python3
"""
Advanced Task Router for vLLM Local Swarm
==========================================

Intelligent task routing system that:
- Analyzes task requirements and complexity
- Routes tasks to most suitable agents
- Implements load balancing across agents
- Provides task priority and scheduling
- Tracks agent performance and specialization
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentCapability(Enum):
    """Agent capability types"""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CODING = "coding"
    MATH = "math"
    REASONING = "reasoning"
    MEMORY = "memory"
    COORDINATION = "coordination"
    SPECIALIZED = "specialized"


@dataclass
class TaskRequirements:
    """Task requirements and constraints"""
    capabilities: List[AgentCapability]
    min_memory_mb: int = 512
    max_execution_time: int = 300  # seconds
    requires_gpu: bool = False
    requires_network: bool = True
    complexity_score: float = 0.5  # 0.0 to 1.0
    expected_tokens: int = 1000


@dataclass
class AgentProfile:
    """Agent profile and capabilities"""
    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    max_concurrent_tasks: int = 3
    memory_capacity_mb: int = 1024
    average_response_time: float = 5.0  # seconds
    success_rate: float = 0.95
    specialization_score: Dict[AgentCapability, float] = field(default_factory=dict)
    current_load: int = 0
    last_seen: datetime = field(default_factory=datetime.now)
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0


@dataclass
class Task:
    """Task definition with routing metadata"""
    task_id: str
    description: str
    requirements: TaskRequirements
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    # Routing metadata
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TaskRouter:
    """
    Advanced task routing system with intelligent agent selection
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self.tasks: Dict[str, Task] = {}
        self.task_queue: Dict[TaskPriority, List[str]] = {
            priority: [] for priority in TaskPriority
        }
        
        # Performance tracking
        self.routing_stats = defaultdict(int)
        self.agent_performance = defaultdict(lambda: {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'avg_completion_time': 0.0,
            'last_updated': datetime.now()
        })
        
        # Task assignment history for learning
        self.assignment_history: List[Dict[str, Any]] = []
        
        self._running = False
        self._router_task = None
        
    async def start(self):
        """Start the task router"""
        if self._running:
            return
            
        self._running = True
        self._router_task = asyncio.create_task(self._routing_loop())
        logger.info("Task router started")
        
    async def stop(self):
        """Stop the task router"""
        self._running = False
        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass
        logger.info("Task router stopped")
        
    async def register_agent(self, agent_profile: AgentProfile):
        """Register a new agent with the router"""
        self.agents[agent_profile.agent_id] = agent_profile
        logger.info(f"Registered agent {agent_profile.agent_id} with capabilities: {agent_profile.capabilities}")
        
    async def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self.agents:
            # Reassign any pending tasks from this agent
            await self._reassign_agent_tasks(agent_id)
            del self.agents[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
            
    async def submit_task(self, task: Task) -> str:
        """Submit a new task for routing"""
        self.tasks[task.task_id] = task
        
        # Add to priority queue
        self.task_queue[task.priority].append(task.task_id)
        
        # Sort by priority and deadline
        self._sort_task_queue(task.priority)
        
        logger.info(f"Task {task.task_id} submitted with priority {task.priority.value}")
        return task.task_id
        
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task"""
        if task_id not in self.tasks:
            return None
            
        task = self.tasks[task_id]
        return {
            'task_id': task_id,
            'status': task.status.value,
            'assigned_agent': task.assigned_agent,
            'created_at': task.created_at.isoformat(),
            'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'retry_count': task.retry_count,
            'result': task.result,
            'error': task.error
        }
        
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
            
        # Remove from queue if pending
        if task.status == TaskStatus.PENDING:
            for priority_queue in self.task_queue.values():
                if task_id in priority_queue:
                    priority_queue.remove(task_id)
                    
        # Update agent load if assigned
        if task.assigned_agent and task.assigned_agent in self.agents:
            self.agents[task.assigned_agent].current_load -= 1
            
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        
        logger.info(f"Task {task_id} cancelled")
        return True
        
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an agent"""
        if agent_id not in self.agents:
            return None
            
        agent = self.agents[agent_id]
        perf = self.agent_performance[agent_id]
        
        return {
            'agent_id': agent_id,
            'name': agent.name,
            'capabilities': [cap.value for cap in agent.capabilities],
            'current_load': agent.current_load,
            'max_concurrent_tasks': agent.max_concurrent_tasks,
            'success_rate': agent.success_rate,
            'average_response_time': agent.average_response_time,
            'total_tasks_completed': perf['tasks_completed'],
            'total_tasks_failed': perf['tasks_failed'],
            'last_seen': agent.last_seen.isoformat(),
            'specialization_scores': {cap.value: score for cap, score in agent.specialization_score.items()}
        }
        
    async def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing system statistics"""
        total_tasks = len(self.tasks)
        pending_tasks = sum(len(queue) for queue in self.task_queue.values())
        
        status_counts = defaultdict(int)
        for task in self.tasks.values():
            status_counts[task.status.value] += 1
            
        return {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'active_agents': len(self.agents),
            'status_distribution': dict(status_counts),
            'routing_stats': dict(self.routing_stats),
            'average_assignment_time': self._calculate_avg_assignment_time(),
            'agent_utilization': self._calculate_agent_utilization()
        }
        
    async def _routing_loop(self):
        """Main routing loop"""
        while self._running:
            try:
                await self._process_pending_tasks()
                await self._update_agent_health()
                await self._cleanup_completed_tasks()
                
                # Sleep for a short time to prevent busy waiting
                await asyncio.sleep(1.0)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in routing loop: {e}")
                await asyncio.sleep(5.0)
                
    async def _process_pending_tasks(self):
        """Process pending tasks and assign to suitable agents"""
        # Process in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
            queue = self.task_queue[priority]
            
            while queue and self._has_available_agents():
                task_id = queue.pop(0)
                
                if task_id not in self.tasks:
                    continue
                    
                task = self.tasks[task_id]
                
                # Skip if task is no longer pending
                if task.status != TaskStatus.PENDING:
                    continue
                    
                # Check if task has exceeded deadline
                if task.deadline and datetime.now() > task.deadline:
                    task.status = TaskStatus.FAILED
                    task.error = "Task exceeded deadline"
                    task.completed_at = datetime.now()
                    continue
                    
                # Find best agent for this task
                best_agent = await self._find_best_agent(task)
                
                if best_agent:
                    await self._assign_task_to_agent(task_id, best_agent.agent_id)
                else:
                    # No suitable agent available, put back in queue
                    queue.insert(0, task_id)
                    break
                    
    async def _find_best_agent(self, task: Task) -> Optional[AgentProfile]:
        """Find the best agent for a given task"""
        suitable_agents = []
        
        for agent in self.agents.values():
            # Check basic availability
            if agent.current_load >= agent.max_concurrent_tasks:
                continue
                
            # Check capability requirements
            if not self._agent_has_capabilities(agent, task.requirements.capabilities):
                continue
                
            # Check resource requirements
            if agent.memory_capacity_mb < task.requirements.min_memory_mb:
                continue
                
            # Calculate suitability score
            score = await self._calculate_agent_suitability(agent, task)
            suitable_agents.append((agent, score))
            
        if not suitable_agents:
            return None
            
        # Sort by suitability score (highest first)
        suitable_agents.sort(key=lambda x: x[1], reverse=True)
        
        # Return best agent
        best_agent, best_score = suitable_agents[0]
        
        # Record routing decision for learning
        self.routing_stats[f'routed_to_{best_agent.agent_id}'] += 1
        
        logger.debug(f"Selected agent {best_agent.agent_id} for task {task.task_id} with score {best_score}")
        
        return best_agent
        
    async def _calculate_agent_suitability(self, agent: AgentProfile, task: Task) -> float:
        """Calculate how suitable an agent is for a task"""
        score = 0.0
        
        # Base score from success rate
        score += agent.success_rate * 0.3
        
        # Load balancing - prefer less loaded agents
        load_ratio = agent.current_load / agent.max_concurrent_tasks
        score += (1.0 - load_ratio) * 0.2
        
        # Response time - prefer faster agents
        response_score = max(0, 1.0 - (agent.average_response_time / 30.0))  # 30s baseline
        score += response_score * 0.2
        
        # Specialization score - prefer agents specialized in required capabilities
        specialization_score = 0.0
        for capability in task.requirements.capabilities:
            if capability in agent.specialization_score:
                specialization_score += agent.specialization_score[capability]
        
        if task.requirements.capabilities:
            specialization_score /= len(task.requirements.capabilities)
            
        score += specialization_score * 0.3
        
        # Randomization for exploration
        import random
        score += random.uniform(0, 0.1)
        
        return min(score, 1.0)  # Cap at 1.0
        
    def _agent_has_capabilities(self, agent: AgentProfile, required_capabilities: List[AgentCapability]) -> bool:
        """Check if agent has required capabilities"""
        agent_caps = set(agent.capabilities)
        required_caps = set(required_capabilities)
        
        # Agent must have all required capabilities
        return required_caps.issubset(agent_caps)
        
    async def _assign_task_to_agent(self, task_id: str, agent_id: str):
        """Assign a task to an agent"""
        task = self.tasks[task_id]
        agent = self.agents[agent_id]
        
        # Update task
        task.status = TaskStatus.ASSIGNED
        task.assigned_agent = agent_id
        task.assigned_at = datetime.now()
        
        # Update agent load
        agent.current_load += 1
        
        # Record assignment for learning
        self.assignment_history.append({
            'task_id': task_id,
            'agent_id': agent_id,
            'assigned_at': datetime.now(),
            'task_requirements': {
                'capabilities': [cap.value for cap in task.requirements.capabilities],
                'complexity_score': task.requirements.complexity_score,
                'expected_tokens': task.requirements.expected_tokens
            },
            'agent_load': agent.current_load
        })
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        
    async def _reassign_agent_tasks(self, agent_id: str):
        """Reassign tasks from a failed/removed agent"""
        for task in self.tasks.values():
            if task.assigned_agent == agent_id and task.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                # Reset task to pending
                task.status = TaskStatus.PENDING
                task.assigned_agent = None
                task.assigned_at = None
                task.retry_count += 1
                
                # Add back to queue if not exceeded max retries
                if task.retry_count <= task.max_retries:
                    self.task_queue[task.priority].append(task.task_id)
                    logger.info(f"Reassigned task {task.task_id} after agent {agent_id} failure")
                else:
                    task.status = TaskStatus.FAILED
                    task.error = "Exceeded maximum retries"
                    task.completed_at = datetime.now()
                    logger.warning(f"Task {task.task_id} failed - exceeded max retries")
                    
    def _has_available_agents(self) -> bool:
        """Check if any agents have available capacity"""
        return any(agent.current_load < agent.max_concurrent_tasks for agent in self.agents.values())
        
    def _sort_task_queue(self, priority: TaskPriority):
        """Sort task queue by deadline and creation time"""
        queue = self.task_queue[priority]
        
        def sort_key(task_id: str) -> Tuple[float, float]:
            task = self.tasks[task_id]
            # Sort by deadline first (if exists), then by creation time
            deadline_priority = task.deadline.timestamp() if task.deadline else float('inf')
            creation_priority = task.created_at.timestamp()
            return (deadline_priority, creation_priority)
            
        queue.sort(key=sort_key)
        
    async def _update_agent_health(self):
        """Update agent health and performance metrics"""
        current_time = datetime.now()
        
        for agent_id, agent in list(self.agents.items()):
            # Check if agent is stale (hasn't been seen for a while)
            if current_time - agent.last_seen > timedelta(minutes=5):
                logger.warning(f"Agent {agent_id} appears to be offline")
                # Could mark agent as offline or remove it
                
    async def _cleanup_completed_tasks(self):
        """Clean up old completed tasks"""
        current_time = datetime.now()
        cleanup_age = timedelta(hours=24)  # Keep tasks for 24 hours
        
        to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_at and current_time - task.completed_at > cleanup_age):
                to_remove.append(task_id)
                
        for task_id in to_remove:
            del self.tasks[task_id]
            logger.debug(f"Cleaned up old task {task_id}")
            
    def _calculate_avg_assignment_time(self) -> float:
        """Calculate average time from task creation to assignment"""
        assignment_times = []
        
        for task in self.tasks.values():
            if task.assigned_at:
                delta = task.assigned_at - task.created_at
                assignment_times.append(delta.total_seconds())
                
        return sum(assignment_times) / len(assignment_times) if assignment_times else 0.0
        
    def _calculate_agent_utilization(self) -> Dict[str, float]:
        """Calculate utilization rate for each agent"""
        utilization = {}
        
        for agent_id, agent in self.agents.items():
            if agent.max_concurrent_tasks > 0:
                utilization[agent_id] = agent.current_load / agent.max_concurrent_tasks
            else:
                utilization[agent_id] = 0.0
                
        return utilization


# Example usage and testing
async def main():
    """Example usage of the task router"""
    router = TaskRouter()
    await router.start()
    
    # Register some example agents
    research_agent = AgentProfile(
        agent_id="research-001",
        name="Research Specialist",
        capabilities=[AgentCapability.RESEARCH, AgentCapability.ANALYSIS],
        specialization_score={
            AgentCapability.RESEARCH: 0.9,
            AgentCapability.ANALYSIS: 0.8
        }
    )
    
    coding_agent = AgentProfile(
        agent_id="coding-001", 
        name="Code Specialist",
        capabilities=[AgentCapability.CODING, AgentCapability.REASONING],
        specialization_score={
            AgentCapability.CODING: 0.95,
            AgentCapability.REASONING: 0.7
        }
    )
    
    await router.register_agent(research_agent)
    await router.register_agent(coding_agent)
    
    # Submit some example tasks
    research_task = Task(
        task_id="task-001",
        description="Research the latest developments in AI",
        requirements=TaskRequirements(
            capabilities=[AgentCapability.RESEARCH],
            complexity_score=0.7
        ),
        priority=TaskPriority.HIGH
    )
    
    coding_task = Task(
        task_id="task-002",
        description="Implement a new API endpoint",
        requirements=TaskRequirements(
            capabilities=[AgentCapability.CODING],
            complexity_score=0.6
        ),
        priority=TaskPriority.MEDIUM
    )
    
    await router.submit_task(research_task)
    await router.submit_task(coding_task)
    
    # Let the router process for a few seconds
    await asyncio.sleep(3)
    
    # Check stats
    stats = await router.get_routing_stats()
    print("Routing Stats:", json.dumps(stats, indent=2))
    
    # Check task statuses
    for task_id in ["task-001", "task-002"]:
        status = await router.get_task_status(task_id)
        print(f"Task {task_id} Status:", json.dumps(status, indent=2))
    
    await router.stop()


if __name__ == "__main__":
    asyncio.run(main())