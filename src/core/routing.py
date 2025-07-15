"""
Task routing and DAG execution system for SPARC workflow orchestration.

This module implements the intelligent routing of tasks to appropriate agents
and manages the directed acyclic graph (DAG) execution of complex workflows.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

import ray

from .messaging import (
    Message, TaskRequest, TaskResponse, TaskStatus, 
    CoordinationMessage, Priority
)
from .agents import AgentType, AgentBase


class RoutingStrategy(Enum):
    """Task routing strategies."""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    CAPABILITY_MATCHED = "capability_matched"
    PRIORITY_BASED = "priority_based"
    SPARC_WORKFLOW = "sparc_workflow"


class WorkflowStage(Enum):
    """SPARC workflow stages."""
    SPECIFICATION = "specification"
    PSEUDOCODE = "pseudocode"
    ARCHITECTURE = "architecture"
    REFINEMENT = "refinement"
    COMPLETION = "completion"


@dataclass
class RoutingRule:
    """Defines how tasks should be routed to agents."""
    rule_id: str
    condition: str  # Task matching condition (e.g., "task_type == 'research'")
    target_agent_type: AgentType
    priority: int = 0  # Higher priority rules are checked first
    max_parallel_tasks: int = 1
    requires_capabilities: List[str] = field(default_factory=list)


@dataclass
class WorkflowNode:
    """Node in a workflow DAG."""
    node_id: str
    agent_type: AgentType
    task_template: str
    dependencies: List[str] = field(default_factory=list)
    parallel_execution: bool = False
    conditional_execution: Optional[str] = None  # Condition for execution
    output_mapping: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Complete workflow definition with nodes and execution rules."""
    workflow_id: str
    name: str
    description: str
    nodes: List[WorkflowNode]
    initial_node: str
    final_nodes: List[str]
    timeout_seconds: int = 3600
    max_iterations: int = 5


class TaskRouter:
    """
    Intelligent task router for SPARC-aligned agent coordination.
    
    Routes tasks to appropriate agents based on:
    - Task type and content analysis
    - Agent capabilities and availability
    - SPARC workflow stage requirements
    - Load balancing and performance optimization
    """
    
    def __init__(self):
        self.routing_rules: List[RoutingRule] = []
        self.agent_registry: Dict[str, AgentBase] = {}
        self.agent_types: Dict[AgentType, List[str]] = {}
        self.routing_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("routing.TaskRouter")
        
        # Initialize default SPARC routing rules
        self._setup_default_routing_rules()
    
    def register_agent(self, agent_id: str, agent: AgentBase, agent_type: AgentType):
        """Register an agent with the router."""
        self.agent_registry[agent_id] = agent
        
        if agent_type not in self.agent_types:
            self.agent_types[agent_type] = []
        self.agent_types[agent_type].append(agent_id)
        
        self.logger.info(f"Registered agent {agent_id} of type {agent_type.value}")
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent from the router."""
        if agent_id in self.agent_registry:
            agent = self.agent_registry.pop(agent_id)
            
            # Remove from type registry
            for agent_type, agent_list in self.agent_types.items():
                if agent_id in agent_list:
                    agent_list.remove(agent_id)
                    break
            
            self.logger.info(f"Unregistered agent {agent_id}")
    
    async def route_task(
        self, 
        task_request: TaskRequest, 
        strategy: RoutingStrategy = RoutingStrategy.SPARC_WORKFLOW
    ) -> Optional[str]:
        """
        Route a task to the most appropriate agent.
        
        Args:
            task_request: Task to be routed
            strategy: Routing strategy to use
            
        Returns:
            Agent ID to handle the task, or None if no suitable agent found
        """
        self.logger.debug(f"Routing task {task_request.task_id} using strategy {strategy.value}")
        
        if strategy == RoutingStrategy.SPARC_WORKFLOW:
            return await self._route_sparc_workflow(task_request)
        elif strategy == RoutingStrategy.CAPABILITY_MATCHED:
            return await self._route_by_capability(task_request)
        elif strategy == RoutingStrategy.LOAD_BALANCED:
            return await self._route_load_balanced(task_request)
        elif strategy == RoutingStrategy.PRIORITY_BASED:
            return await self._route_by_priority(task_request)
        else:
            return await self._route_round_robin(task_request)
    
    async def _route_sparc_workflow(self, task_request: TaskRequest) -> Optional[str]:
        """Route based on SPARC workflow methodology."""
        # Analyze task to determine workflow stage and appropriate agent type
        agent_type = self._analyze_task_for_agent_type(task_request)
        
        if agent_type and agent_type in self.agent_types:
            # Find best agent of the determined type
            return await self._select_best_agent(agent_type, task_request)
        
        return None
    
    async def _route_by_capability(self, task_request: TaskRequest) -> Optional[str]:
        """Route based on agent capabilities matching."""
        suitable_agents = []
        
        for agent_id, agent in self.agent_registry.items():
            # Check if agent can handle the task
            can_handle = await agent._can_handle_task.remote(task_request)
            if can_handle:
                # Get agent metrics for ranking
                metrics = await agent.get_performance_metrics.remote()
                suitable_agents.append((agent_id, metrics))
        
        if suitable_agents:
            # Rank by success rate and availability
            suitable_agents.sort(
                key=lambda x: (x[1]['success_rate'], -x[1]['current_task_count']),
                reverse=True
            )
            return suitable_agents[0][0]
        
        return None
    
    async def _route_load_balanced(self, task_request: TaskRequest) -> Optional[str]:
        """Route to agent with lowest current load."""
        agent_loads = []
        
        for agent_id, agent in self.agent_registry.items():
            metrics = await agent.get_performance_metrics.remote()
            load_factor = metrics['current_task_count'] / metrics.get('max_capacity', 1)
            agent_loads.append((agent_id, load_factor))
        
        if agent_loads:
            agent_loads.sort(key=lambda x: x[1])  # Sort by load factor
            return agent_loads[0][0]
        
        return None
    
    async def _route_by_priority(self, task_request: TaskRequest) -> Optional[str]:
        """Route based on task priority and agent availability."""
        # For high priority tasks, prefer agents with best success rates
        if task_request.priority == Priority.HIGH or task_request.priority == Priority.CRITICAL:
            return await self._route_by_capability(task_request)
        else:
            return await self._route_load_balanced(task_request)
    
    async def _route_round_robin(self, task_request: TaskRequest) -> Optional[str]:
        """Simple round-robin routing."""
        if self.agent_registry:
            agent_ids = list(self.agent_registry.keys())
            # Use task ID hash for consistent but distributed routing
            index = hash(task_request.task_id) % len(agent_ids)
            return agent_ids[index]
        
        return None
    
    def _analyze_task_for_agent_type(self, task_request: TaskRequest) -> Optional[AgentType]:
        """
        Analyze task content to determine appropriate agent type.
        
        Uses keyword analysis and heuristics to map tasks to SPARC agent roles.
        """
        task_text = f"{task_request.task_definition} {task_request.objective}".lower()
        
        # Define keywords for each agent type
        agent_keywords = {
            AgentType.PLANNER: ['plan', 'coordinate', 'organize', 'breakdown', 'manage', 'orchestrate'],
            AgentType.RESEARCHER: ['research', 'search', 'investigate', 'analyze', 'gather', 'find'],
            AgentType.CODER: ['code', 'implement', 'develop', 'program', 'build', 'create', 'write'],
            AgentType.QA: ['test', 'validate', 'verify', 'check', 'ensure', 'quality'],
            AgentType.CRITIC: ['review', 'critique', 'evaluate', 'assess', 'improve', 'analyze'],
            AgentType.JUDGE: ['judge', 'decide', 'approve', 'evaluate', 'score', 'final']
        }
        
        # Score each agent type based on keyword matches
        scores = {}
        for agent_type, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in task_text)
            if score > 0:
                scores[agent_type] = score
        
        # Return agent type with highest score
        if scores:
            return max(scores, key=scores.get)
        
        # Default to Planner for complex coordination tasks
        return AgentType.PLANNER
    
    async def _select_best_agent(self, agent_type: AgentType, task_request: TaskRequest) -> Optional[str]:
        """Select the best agent of a given type for the task."""
        if agent_type not in self.agent_types or not self.agent_types[agent_type]:
            return None
        
        agent_candidates = []
        
        for agent_id in self.agent_types[agent_type]:
            agent = self.agent_registry[agent_id]
            metrics = await agent.get_performance_metrics.remote()
            
            # Skip agents that are at capacity
            if metrics['current_task_count'] >= metrics.get('max_capacity', 1):
                continue
            
            # Score based on performance and availability
            score = (
                metrics['success_rate'] * 0.4 +
                (1 - metrics['current_task_count'] / metrics.get('max_capacity', 1)) * 0.3 +
                (1 / (1 + metrics['average_response_time'])) * 0.3
            )
            
            agent_candidates.append((agent_id, score))
        
        if agent_candidates:
            agent_candidates.sort(key=lambda x: x[1], reverse=True)
            return agent_candidates[0][0]
        
        return None
    
    def _setup_default_routing_rules(self):
        """Setup default routing rules for SPARC methodology."""
        default_rules = [
            RoutingRule(
                rule_id="research_tasks",
                condition="contains_keywords(['research', 'search', 'investigate'])",
                target_agent_type=AgentType.RESEARCHER,
                priority=10
            ),
            RoutingRule(
                rule_id="coding_tasks",
                condition="contains_keywords(['code', 'implement', 'develop'])",
                target_agent_type=AgentType.CODER,
                priority=10
            ),
            RoutingRule(
                rule_id="testing_tasks",
                condition="contains_keywords(['test', 'validate', 'verify'])",
                target_agent_type=AgentType.QA,
                priority=10
            ),
            RoutingRule(
                rule_id="review_tasks",
                condition="contains_keywords(['review', 'critique', 'evaluate'])",
                target_agent_type=AgentType.CRITIC,
                priority=10
            ),
            RoutingRule(
                rule_id="planning_tasks",
                condition="contains_keywords(['plan', 'coordinate', 'organize'])",
                target_agent_type=AgentType.PLANNER,
                priority=8
            ),
            RoutingRule(
                rule_id="evaluation_tasks",
                condition="contains_keywords(['judge', 'decide', 'approve'])",
                target_agent_type=AgentType.JUDGE,
                priority=10
            )
        ]
        
        self.routing_rules.extend(default_rules)
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing performance statistics."""
        return {
            "total_routes": len(self.routing_history),
            "agent_count": len(self.agent_registry),
            "agent_types": {
                agent_type.value: len(agents) 
                for agent_type, agents in self.agent_types.items()
            }
        }


class DAGExecutor:
    """
    Directed Acyclic Graph executor for complex SPARC workflows.
    
    Manages execution of multi-step workflows with dependencies,
    parallel execution, and conditional logic.
    """
    
    def __init__(self, task_router: TaskRouter):
        self.task_router = task_router
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("routing.DAGExecutor")
        
        # Setup default SPARC workflow
        self._setup_default_sparc_workflow()
    
    def register_workflow(self, workflow: WorkflowDefinition):
        """Register a workflow definition."""
        self.workflow_definitions[workflow.workflow_id] = workflow
        self.logger.info(f"Registered workflow: {workflow.name}")
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        initial_task: TaskRequest,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow DAG.
        
        Args:
            workflow_id: ID of workflow to execute
            initial_task: Initial task to start the workflow
            execution_id: Unique execution ID (generated if not provided)
            
        Returns:
            Dictionary containing execution results and metadata
        """
        if workflow_id not in self.workflow_definitions:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        workflow = self.workflow_definitions[workflow_id]
        execution_id = execution_id or f"{workflow_id}_{initial_task.task_id}"
        
        self.logger.info(f"Starting workflow execution {execution_id}")
        
        # Initialize execution context
        execution_context = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "initial_task": initial_task,
            "status": "running",
            "start_time": asyncio.get_event_loop().time(),
            "results": {},
            "errors": [],
            "completed_nodes": set(),
            "running_nodes": set()
        }
        
        self.active_executions[execution_id] = execution_context
        
        try:
            # Build execution graph
            graph = self._build_execution_graph(workflow)
            
            # Execute workflow
            results = await self._execute_graph(graph, workflow, execution_context)
            
            execution_context["status"] = "completed"
            execution_context["results"] = results
            
            return execution_context
        
        except Exception as e:
            self.logger.error(f"Workflow execution {execution_id} failed: {str(e)}")
            execution_context["status"] = "failed"
            execution_context["errors"].append(str(e))
            return execution_context
        
        finally:
            execution_context["end_time"] = asyncio.get_event_loop().time()
            execution_context["duration"] = (
                execution_context["end_time"] - execution_context["start_time"]
            )
    
    def _build_execution_graph(self, workflow: WorkflowDefinition) -> nx.DiGraph:
        """Build a NetworkX graph from workflow definition."""
        graph = nx.DiGraph()
        
        # Add nodes
        for node in workflow.nodes:
            graph.add_node(node.node_id, node_data=node)
        
        # Add edges based on dependencies
        for node in workflow.nodes:
            for dependency in node.dependencies:
                graph.add_edge(dependency, node.node_id)
        
        # Validate DAG
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("Workflow contains cycles")
        
        return graph
    
    async def _execute_graph(
        self, 
        graph: nx.DiGraph, 
        workflow: WorkflowDefinition,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the workflow graph."""
        results = {}
        completed = execution_context["completed_nodes"]
        running = execution_context["running_nodes"]
        
        # Get topological order for execution
        execution_order = list(nx.topological_sort(graph))
        
        # Execute nodes in dependency order
        while len(completed) < len(graph.nodes):
            # Find nodes ready to execute
            ready_nodes = []
            
            for node_id in execution_order:
                if (node_id not in completed and 
                    node_id not in running and
                    all(dep in completed for dep in graph.predecessors(node_id))):
                    ready_nodes.append(node_id)
            
            if not ready_nodes:
                # Check if we're waiting for running nodes
                if running:
                    await asyncio.sleep(0.1)  # Wait briefly
                    continue
                else:
                    # No ready nodes and none running - deadlock
                    raise RuntimeError("Workflow execution deadlock detected")
            
            # Execute ready nodes (potentially in parallel)
            tasks = []
            for node_id in ready_nodes:
                node_data = graph.nodes[node_id]["node_data"]
                
                # Check conditional execution
                if node_data.conditional_execution:
                    if not self._evaluate_condition(node_data.conditional_execution, results):
                        completed.add(node_id)
                        continue
                
                running.add(node_id)
                task = asyncio.create_task(
                    self._execute_node(node_data, execution_context, results)
                )
                tasks.append((node_id, task))
            
            # Wait for tasks to complete
            if tasks:
                for node_id, task in tasks:
                    try:
                        result = await task
                        results[node_id] = result
                        completed.add(node_id)
                        self.logger.debug(f"Node {node_id} completed successfully")
                    except Exception as e:
                        self.logger.error(f"Node {node_id} failed: {str(e)}")
                        execution_context["errors"].append(f"Node {node_id}: {str(e)}")
                        completed.add(node_id)  # Mark as completed even if failed
                    finally:
                        running.discard(node_id)
        
        return results
    
    async def _execute_node(
        self, 
        node: WorkflowNode, 
        execution_context: Dict[str, Any],
        current_results: Dict[str, Any]
    ) -> Any:
        """Execute a single workflow node."""
        self.logger.debug(f"Executing node {node.node_id}")
        
        # Create task request from node template
        task_request = self._create_task_from_node(node, execution_context, current_results)
        
        # Route task to appropriate agent
        agent_id = await self.task_router.route_task(task_request)
        if not agent_id:
            raise RuntimeError(f"No suitable agent found for node {node.node_id}")
        
        # Execute task
        agent = self.task_router.agent_registry[agent_id]
        response = await agent.handle_message.remote(task_request)
        
        # Process response
        if response and hasattr(response, 'status'):
            if response.status == TaskStatus.COMPLETED:
                return response.deliverables
            else:
                raise RuntimeError(f"Task failed: {response.task_completion_summary}")
        
        return None
    
    def _create_task_from_node(
        self, 
        node: WorkflowNode, 
        execution_context: Dict[str, Any],
        current_results: Dict[str, Any]
    ) -> TaskRequest:
        """Create a task request from a workflow node."""
        # Substitute variables in task template
        task_definition = self._substitute_variables(
            node.task_template, 
            execution_context, 
            current_results
        )
        
        return TaskRequest(
            sender_id="dag_executor",
            recipient_id="",  # Will be determined by routing
            task_definition=task_definition,
            objective=f"Execute workflow node: {node.node_id}",
            task_id=f"{execution_context['execution_id']}_{node.node_id}",
            session_id=execution_context["execution_id"]
        )
    
    def _substitute_variables(
        self, 
        template: str, 
        execution_context: Dict[str, Any],
        current_results: Dict[str, Any]
    ) -> str:
        """Substitute variables in task templates."""
        # Simple variable substitution
        # In a full implementation, this would use a proper template engine
        substituted = template
        
        # Substitute execution context variables
        for key, value in execution_context.items():
            substituted = substituted.replace(f"{{{key}}}", str(value))
        
        # Substitute result variables
        for node_id, result in current_results.items():
            substituted = substituted.replace(f"{{results.{node_id}}}", str(result))
        
        return substituted
    
    def _evaluate_condition(self, condition: str, results: Dict[str, Any]) -> bool:
        """Evaluate conditional execution logic."""
        # Simple condition evaluation
        # In a full implementation, this would use a safe expression evaluator
        try:
            # Replace result references with actual values
            eval_condition = condition
            for node_id, result in results.items():
                eval_condition = eval_condition.replace(
                    f"results.{node_id}", 
                    f"'{result}'" if isinstance(result, str) else str(result)
                )
            
            # Basic safety check - only allow simple comparisons
            allowed_operators = ['==', '!=', '>', '<', '>=', '<=', 'and', 'or', 'not']
            if any(op in eval_condition for op in ['import', 'exec', 'eval', '__']):
                return False
            
            return eval(eval_condition)
        except:
            return False
    
    def _setup_default_sparc_workflow(self):
        """Setup the default SPARC workflow."""
        sparc_workflow = WorkflowDefinition(
            workflow_id="sparc_default",
            name="SPARC Default Workflow",
            description="Standard SPARC methodology workflow",
            nodes=[
                WorkflowNode(
                    node_id="specification",
                    agent_type=AgentType.PLANNER,
                    task_template="Analyze and create specification for: {initial_task.objective}",
                    dependencies=[]
                ),
                WorkflowNode(
                    node_id="research",
                    agent_type=AgentType.RESEARCHER,
                    task_template="Research requirements for: {results.specification}",
                    dependencies=["specification"],
                    parallel_execution=True
                ),
                WorkflowNode(
                    node_id="pseudocode",
                    agent_type=AgentType.PLANNER,
                    task_template="Create pseudocode based on: {results.specification} and {results.research}",
                    dependencies=["specification", "research"]
                ),
                WorkflowNode(
                    node_id="implementation",
                    agent_type=AgentType.CODER,
                    task_template="Implement solution based on: {results.pseudocode}",
                    dependencies=["pseudocode"]
                ),
                WorkflowNode(
                    node_id="testing",
                    agent_type=AgentType.QA,
                    task_template="Test and validate: {results.implementation}",
                    dependencies=["implementation"],
                    parallel_execution=True
                ),
                WorkflowNode(
                    node_id="review",
                    agent_type=AgentType.CRITIC,
                    task_template="Review and critique: {results.implementation}",
                    dependencies=["implementation"],
                    parallel_execution=True
                ),
                WorkflowNode(
                    node_id="refinement",
                    agent_type=AgentType.CODER,
                    task_template="Refine implementation based on: {results.testing} and {results.review}",
                    dependencies=["testing", "review"],
                    conditional_execution="results.testing != 'passed' or results.review != 'approved'"
                ),
                WorkflowNode(
                    node_id="final_evaluation",
                    agent_type=AgentType.JUDGE,
                    task_template="Final evaluation of: {results.implementation} or {results.refinement}",
                    dependencies=["testing", "review"]
                )
            ],
            initial_node="specification",
            final_nodes=["final_evaluation"]
        )
        
        self.register_workflow(sparc_workflow)