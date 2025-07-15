"""
Planner Agent (Orchestrator) for SPARC Multi-Agent Framework

The Planner agent is responsible for task decomposition, delegation, and orchestration.
It analyzes high-level objectives, breaks them into concrete subtasks, assigns them to 
appropriate specialist agents, and coordinates the overall workflow execution.

Following SPARC methodology: Specification → Pseudocode → Architecture → Refinement → Completion
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

import ray
from .base_agent import BaseAgent, AgentMessage, MessageType, AgentStatus


class TaskStatus:
    """Track task execution status and dependencies"""
    
    def __init__(self, task_id: str, description: str, assigned_agent: str, dependencies: List[str] = None):
        self.task_id = task_id
        self.description = description
        self.assigned_agent = assigned_agent
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.error = None


@ray.remote
class PlannerAgent(BaseAgent):
    """
    Planner Agent - The Orchestrator
    
    Core Responsibilities:
    - Break down high-level objectives into concrete tasks
    - Analyze task dependencies and execution order
    - Assign tasks to appropriate specialist agents
    - Monitor task execution and coordinate workflow
    - Integrate results and ensure objective completion
    - Handle task routing and boomerang pattern implementation
    """
    
    def __init__(self, agent_id: str, **kwargs):
        super().__init__(
            agent_id=agent_id,
            role="planner",
            capabilities=[
                "task_decomposition",
                "dependency_analysis", 
                "agent_assignment",
                "workflow_orchestration",
                "result_integration",
                "progress_monitoring"
            ],
            model_config=kwargs.get("model_config", {"model": "gemini", "temperature": 0.3}),
            memory_config=kwargs.get("memory_config", {}),
            **kwargs
        )
        
        # Planner-specific state
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.task_registry: Dict[str, TaskStatus] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self.workflow_templates: Dict[str, Dict[str, Any]] = {}
        
        # Load default workflow templates
        self._load_workflow_templates()
    
    def _load_system_prompt(self) -> str:
        """Load Planner agent system prompt following SPARC methodology"""
        return """
You are the Planner Agent, the primary orchestrator in a SPARC-aligned multi-agent system.

CORE ROLE: Task decomposition, delegation, and workflow coordination

RESPONSIBILITIES:
1. ANALYZE incoming objectives and break them into concrete, actionable subtasks
2. IDENTIFY dependencies between tasks and determine optimal execution order
3. ASSIGN tasks to appropriate specialist agents based on capabilities
4. MONITOR task execution and coordinate handoffs between agents
5. INTEGRATE results from multiple agents into coherent outcomes
6. ENSURE all requirements are met before marking objectives complete

SPARC METHODOLOGY ALIGNMENT:
- Specification: Clarify and structure the user's objective
- Pseudocode: Create high-level execution plan with task breakdown
- Architecture: Design agent interaction patterns and data flow
- Refinement: Iterate based on agent feedback and results
- Completion: Validate and integrate final deliverables

AGENT ASSIGNMENT STRATEGY:
- Researcher: Information gathering, documentation analysis, evidence synthesis
- Coder: Code generation, implementation, technical development
- QA: Testing, validation, quality assurance, error checking
- Critic: Code review, improvement suggestions, alternative approaches
- Judge: Final evaluation, completion approval, quality gating

TASK DEFINITION TEMPLATE:
For each subtask, provide:
- Task ID and clear description
- Expected deliverables and success criteria
- Relevant context and constraints
- Dependencies on other tasks
- Assigned agent and rationale
- Return instructions and format requirements

COMMUNICATION PROTOCOL:
- Use structured message formats for all agent interactions
- Implement boomerang pattern: delegate → specialist work → return to planner
- Maintain task context and progress tracking
- Coordinate parallel execution where possible
- Handle error recovery and task reassignment

DECISION CRITERIA:
- Prefer parallel execution when tasks are independent
- Sequence dependent tasks appropriately
- Consider agent workload and capabilities
- Minimize redundant work across agents
- Ensure comprehensive coverage of all requirements

QUALITY STANDARDS:
- All outputs must be reviewed by appropriate agents (QA/Critic)
- Complex tasks require multiple validation passes
- Final approval only after Judge agent evaluation
- Document all decisions and rationale
- Maintain audit trail of task execution

Think step-by-step and be systematic in your approach. Focus on creating clear, 
unambiguous task assignments with defined scope and deliverables.
"""
    
    def _initialize_tools(self):
        """Initialize Planner-specific tools"""
        self.available_tools = {
            "task_decomposer": self._decompose_task,
            "dependency_analyzer": self._analyze_dependencies,
            "agent_selector": self._select_agent_for_task,
            "workflow_coordinator": self._coordinate_workflow,
            "result_integrator": self._integrate_results,
            "progress_tracker": self._track_progress
        }
    
    def _load_workflow_templates(self):
        """Load predefined workflow templates for common task patterns"""
        self.workflow_templates = {
            "code_development": {
                "phases": ["specification", "research", "coding", "testing", "review", "judgment"],
                "agents": ["researcher", "coder", "qa", "critic", "judge"],
                "parallel_phases": ["research", "coding"],
                "validation_gates": ["testing", "review"]
            },
            "research_analysis": {
                "phases": ["specification", "research", "analysis", "synthesis", "review", "judgment"],
                "agents": ["researcher", "critic", "judge"],
                "parallel_phases": ["research"],
                "validation_gates": ["review"]
            },
            "system_improvement": {
                "phases": ["analysis", "proposal", "validation", "implementation", "testing", "judgment"],
                "agents": ["critic", "researcher", "coder", "qa", "judge"],
                "parallel_phases": ["analysis", "proposal"],
                "validation_gates": ["validation", "testing"]
            }
        }
    
    async def _execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute planning task - main orchestration logic
        
        Args:
            task_data: Contains objective, requirements, constraints, etc.
            
        Returns:
            Orchestration result with integrated deliverables
        """
        try:
            objective = task_data.get("objective", "")
            requirements = task_data.get("requirements", [])
            constraints = task_data.get("constraints", {})
            workflow_type = task_data.get("workflow_type", "code_development")
            
            self.logger.info(f"Starting orchestration for objective: {objective}")
            
            # Phase 1: Specification Analysis
            specification = await self._analyze_specification(objective, requirements, constraints)
            
            # Phase 2: Task Decomposition
            subtasks = await self._decompose_objective(specification, workflow_type)
            
            # Phase 3: Dependency Analysis and Scheduling
            execution_plan = await self._create_execution_plan(subtasks)
            
            # Phase 4: Workflow Execution
            workflow_id = str(uuid.uuid4())
            results = await self._execute_workflow(workflow_id, execution_plan)
            
            # Phase 5: Result Integration
            final_result = await self._integrate_workflow_results(workflow_id, results)
            
            return {
                "status": "completed",
                "objective": objective,
                "workflow_id": workflow_id,
                "final_result": final_result,
                "execution_summary": {
                    "tasks_executed": len(subtasks),
                    "agents_involved": list(set([task.assigned_agent for task in subtasks])),
                    "total_time": (datetime.utcnow() - self.task_registry[subtasks[0].task_id].created_at).total_seconds()
                },
                "tokens_used": final_result.get("total_tokens", 0),
                "processing_time": final_result.get("processing_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error in orchestration: {e}")
            return {
                "status": "error",
                "error": str(e),
                "partial_results": getattr(self, '_partial_results', {})
            }
    
    async def _analyze_specification(self, objective: str, requirements: List[str], constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze and clarify the specification (SPARC Phase 1)"""
        # Use LLM to analyze and structure the specification
        analysis_prompt = f"""
        Analyze this objective and provide structured specification:
        
        OBJECTIVE: {objective}
        REQUIREMENTS: {requirements}
        CONSTRAINTS: {constraints}
        
        Provide:
        1. Clarified objective statement
        2. Success criteria 
        3. Scope boundaries
        4. Key deliverables
        5. Assumptions and dependencies
        6. Risk factors
        """
        
        # TODO: Replace with actual LLM call
        specification = {
            "clarified_objective": objective,
            "success_criteria": requirements,
            "scope": {"included": [], "excluded": []},
            "deliverables": [],
            "assumptions": [],
            "risks": []
        }
        
        await self.update_memory("current_specification", specification)
        return specification
    
    async def _decompose_objective(self, specification: Dict[str, Any], workflow_type: str) -> List[TaskStatus]:
        """Decompose objective into concrete subtasks (SPARC Phase 2)"""
        template = self.workflow_templates.get(workflow_type, self.workflow_templates["code_development"])
        
        # Generate subtasks based on workflow template and specification
        subtasks = []
        
        # Example decomposition logic (would be enhanced with LLM)
        if workflow_type == "code_development":
            subtasks = [
                TaskStatus(
                    task_id=str(uuid.uuid4()),
                    description="Research technical requirements and best practices",
                    assigned_agent="researcher"
                ),
                TaskStatus(
                    task_id=str(uuid.uuid4()),
                    description="Implement core functionality",
                    assigned_agent="coder",
                    dependencies=[subtasks[0].task_id] if subtasks else []
                ),
                TaskStatus(
                    task_id=str(uuid.uuid4()),
                    description="Write and execute tests",
                    assigned_agent="qa",
                    dependencies=[subtasks[1].task_id] if len(subtasks) > 1 else []
                ),
                TaskStatus(
                    task_id=str(uuid.uuid4()),
                    description="Review code and suggest improvements",
                    assigned_agent="critic",
                    dependencies=[subtasks[1].task_id] if len(subtasks) > 1 else []
                ),
                TaskStatus(
                    task_id=str(uuid.uuid4()),
                    description="Final evaluation and approval",
                    assigned_agent="judge",
                    dependencies=[task.task_id for task in subtasks[-2:]]
                )
            ]
        
        # Register tasks
        for task in subtasks:
            self.task_registry[task.task_id] = task
        
        return subtasks
    
    async def _create_execution_plan(self, subtasks: List[TaskStatus]) -> Dict[str, Any]:
        """Create optimized execution plan with dependency resolution"""
        # Analyze dependencies and create execution phases
        phases = []
        remaining_tasks = subtasks.copy()
        
        while remaining_tasks:
            # Find tasks with no unresolved dependencies
            ready_tasks = [
                task for task in remaining_tasks
                if all(dep_id not in [t.task_id for t in remaining_tasks] for dep_id in task.dependencies)
            ]
            
            if not ready_tasks:
                # Circular dependency - break by taking first task
                ready_tasks = [remaining_tasks[0]]
            
            phases.append(ready_tasks)
            
            # Remove ready tasks from remaining
            for task in ready_tasks:
                remaining_tasks.remove(task)
        
        return {
            "phases": phases,
            "parallel_execution": True,
            "error_handling": "retry_with_feedback",
            "max_iterations": 3
        }
    
    async def _execute_workflow(self, workflow_id: str, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow according to execution plan"""
        self.active_workflows[workflow_id] = {
            "status": "running",
            "start_time": datetime.utcnow(),
            "phases_completed": 0,
            "total_phases": len(execution_plan["phases"])
        }
        
        phase_results = {}
        
        try:
            for phase_idx, phase_tasks in enumerate(execution_plan["phases"]):
                self.logger.info(f"Executing phase {phase_idx + 1} with {len(phase_tasks)} tasks")
                
                # Execute tasks in parallel within phase
                if execution_plan.get("parallel_execution", True) and len(phase_tasks) > 1:
                    phase_result = await self._execute_parallel_tasks(phase_tasks)
                else:
                    phase_result = await self._execute_sequential_tasks(phase_tasks)
                
                phase_results[f"phase_{phase_idx}"] = phase_result
                
                # Update workflow status
                self.active_workflows[workflow_id]["phases_completed"] = phase_idx + 1
                
                # Check for errors and handle according to policy
                if any(result.get("status") == "error" for result in phase_result.values()):
                    if execution_plan.get("error_handling") == "retry_with_feedback":
                        await self._handle_phase_errors(phase_tasks, phase_result)
                    else:
                        raise Exception(f"Phase {phase_idx} failed")
            
            self.active_workflows[workflow_id]["status"] = "completed"
            return phase_results
            
        except Exception as e:
            self.active_workflows[workflow_id]["status"] = "error"
            self.active_workflows[workflow_id]["error"] = str(e)
            raise
    
    async def _execute_parallel_tasks(self, tasks: List[TaskStatus]) -> Dict[str, Any]:
        """Execute tasks in parallel using Ray"""
        task_futures = {}
        
        for task in tasks:
            # Get agent actor
            agent_actor = await self._get_agent_actor(task.assigned_agent)
            
            # Create task message
            task_message = AgentMessage(
                message_type=MessageType.TASK_ASSIGNMENT,
                sender=self.agent_id,
                recipient=task.assigned_agent,
                payload={
                    "task_id": task.task_id,
                    "description": task.description,
                    "context": await self.retrieve_memory("current_specification"),
                    "dependencies": task.dependencies,
                    "expected_format": self._get_expected_format(task.assigned_agent)
                },
                task_id=task.task_id
            )
            
            # Submit task
            task.status = "running"
            task.started_at = datetime.utcnow()
            task_futures[task.task_id] = agent_actor.process_message.remote(task_message)
        
        # Wait for all tasks to complete
        results = {}
        for task_id, future in task_futures.items():
            try:
                result_message = await future
                results[task_id] = result_message.payload
                self.task_registry[task_id].status = "completed"
                self.task_registry[task_id].completed_at = datetime.utcnow()
                self.task_registry[task_id].result = result_message.payload
            except Exception as e:
                results[task_id] = {"status": "error", "error": str(e)}
                self.task_registry[task_id].status = "error"
                self.task_registry[task_id].error = str(e)
        
        return results
    
    async def _execute_sequential_tasks(self, tasks: List[TaskStatus]) -> Dict[str, Any]:
        """Execute tasks sequentially"""
        results = {}
        
        for task in tasks:
            try:
                agent_actor = await self._get_agent_actor(task.assigned_agent)
                
                task_message = AgentMessage(
                    message_type=MessageType.TASK_ASSIGNMENT,
                    sender=self.agent_id,
                    recipient=task.assigned_agent,
                    payload={
                        "task_id": task.task_id,
                        "description": task.description,
                        "context": await self.retrieve_memory("current_specification"),
                        "dependencies": task.dependencies,
                        "previous_results": {dep_id: self.task_registry[dep_id].result 
                                           for dep_id in task.dependencies 
                                           if dep_id in self.task_registry},
                        "expected_format": self._get_expected_format(task.assigned_agent)
                    },
                    task_id=task.task_id
                )
                
                task.status = "running"
                task.started_at = datetime.utcnow()
                
                result_message = await agent_actor.process_message.remote(task_message)
                results[task.task_id] = result_message.payload
                
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result = result_message.payload
                
            except Exception as e:
                results[task.task_id] = {"status": "error", "error": str(e)}
                task.status = "error"
                task.error = str(e)
        
        return results
    
    async def _get_agent_actor(self, agent_role: str):
        """Get Ray actor reference for specified agent"""
        try:
            return ray.get_actor(f"{agent_role}_agent")
        except ValueError:
            # Agent not found - would need to spawn or handle gracefully
            self.logger.error(f"Agent {agent_role} not found")
            raise Exception(f"Agent {agent_role} is not available")
    
    def _get_expected_format(self, agent_role: str) -> Dict[str, Any]:
        """Get expected output format for specific agent role"""
        formats = {
            "researcher": {
                "sections": ["summary", "findings", "sources", "recommendations"],
                "required_fields": ["sources", "confidence_level"]
            },
            "coder": {
                "sections": ["code", "documentation", "tests", "usage_examples"],
                "required_fields": ["code", "test_results"]
            },
            "qa": {
                "sections": ["test_results", "issues_found", "recommendations"],
                "required_fields": ["test_status", "issues_found"]
            },
            "critic": {
                "sections": ["evaluation", "improvements", "alternatives", "score"],
                "required_fields": ["evaluation", "score"]
            },
            "judge": {
                "sections": ["decision", "rationale", "final_score"],
                "required_fields": ["decision", "final_score"]
            }
        }
        return formats.get(agent_role, {"sections": ["result"], "required_fields": ["result"]})
    
    async def _handle_phase_errors(self, tasks: List[TaskStatus], phase_result: Dict[str, Any]):
        """Handle errors in phase execution with feedback loop"""
        failed_tasks = [task for task in tasks if phase_result[task.task_id].get("status") == "error"]
        
        for task in failed_tasks:
            error_info = phase_result[task.task_id]
            
            # Get feedback from Critic agent if available
            feedback = await self._get_error_feedback(task, error_info)
            
            # Retry task with feedback
            await self._retry_task_with_feedback(task, feedback)
    
    async def _get_error_feedback(self, task: TaskStatus, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get feedback from Critic agent for error resolution"""
        try:
            critic_actor = await self._get_agent_actor("critic")
            
            feedback_message = AgentMessage(
                message_type=MessageType.QUERY,
                sender=self.agent_id,
                recipient="critic",
                payload={
                    "query_type": "error_analysis",
                    "task": task.description,
                    "error": error_info,
                    "context": await self.retrieve_memory("current_specification")
                }
            )
            
            response = await critic_actor.process_message.remote(feedback_message)
            return response.payload
            
        except Exception as e:
            self.logger.warning(f"Could not get error feedback: {e}")
            return {"suggestions": ["Retry with original parameters"]}
    
    async def _retry_task_with_feedback(self, task: TaskStatus, feedback: Dict[str, Any]):
        """Retry failed task with feedback incorporated"""
        # This would implement retry logic with feedback
        # For now, just mark as needing attention
        task.status = "needs_attention"
        await self.update_memory(f"feedback_{task.task_id}", feedback)
    
    async def _integrate_workflow_results(self, workflow_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate results from all workflow phases"""
        integration_summary = {
            "workflow_id": workflow_id,
            "status": "completed",
            "deliverables": {},
            "metrics": {
                "total_phases": len(results),
                "successful_tasks": 0,
                "failed_tasks": 0,
                "total_tokens": 0
            }
        }
        
        # Extract and organize deliverables by type
        for phase_key, phase_result in results.items():
            for task_id, task_result in phase_result.items():
                if task_result.get("status") == "completed":
                    integration_summary["metrics"]["successful_tasks"] += 1
                    
                    # Extract deliverables based on agent type
                    task = self.task_registry.get(task_id)
                    if task:
                        agent_role = task.assigned_agent
                        deliverable_key = f"{agent_role}_output"
                        
                        if deliverable_key not in integration_summary["deliverables"]:
                            integration_summary["deliverables"][deliverable_key] = []
                        
                        integration_summary["deliverables"][deliverable_key].append({
                            "task_id": task_id,
                            "description": task.description,
                            "result": task_result.get("result", {}),
                            "metadata": task_result.get("agent_metadata", {})
                        })
                        
                        # Accumulate metrics
                        if "tokens_used" in task_result.get("agent_metadata", {}):
                            integration_summary["metrics"]["total_tokens"] += task_result["agent_metadata"]["tokens_used"]
                else:
                    integration_summary["metrics"]["failed_tasks"] += 1
        
        # Store integrated results in memory
        await self.update_memory(f"workflow_result_{workflow_id}", integration_summary)
        
        return integration_summary
    
    async def _process_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process queries about workflow status, task progress, etc."""
        query_type = query_data.get("type", "status")
        
        if query_type == "status":
            workflow_id = query_data.get("workflow_id")
            if workflow_id and workflow_id in self.active_workflows:
                return {
                    "workflow_status": self.active_workflows[workflow_id],
                    "task_statuses": {tid: {"status": task.status, "description": task.description} 
                                    for tid, task in self.task_registry.items()}
                }
        
        elif query_type == "progress":
            return {
                "active_workflows": len(self.active_workflows),
                "total_tasks": len(self.task_registry),
                "completed_tasks": len([t for t in self.task_registry.values() if t.status == "completed"]),
                "failed_tasks": len([t for t in self.task_registry.values() if t.status == "error"])
            }
        
        return {"result": "Query processed", "query_type": query_type}
    
    def _decompose_task(self, task: str) -> List[Dict[str, Any]]:
        """Tool: Decompose high-level task into subtasks"""
        # Implementation would use LLM to intelligently decompose
        return []
    
    def _analyze_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Tool: Analyze dependencies between tasks"""
        # Implementation would analyze task dependencies
        return {}
    
    def _select_agent_for_task(self, task: Dict[str, Any]) -> str:
        """Tool: Select best agent for a given task"""
        # Implementation would match task requirements to agent capabilities
        task_type = task.get("type", "")
        
        if "research" in task_type.lower() or "information" in task_type.lower():
            return "researcher"
        elif "code" in task_type.lower() or "implement" in task_type.lower():
            return "coder"
        elif "test" in task_type.lower() or "validation" in task_type.lower():
            return "qa"
        elif "review" in task_type.lower() or "improve" in task_type.lower():
            return "critic"
        elif "evaluate" in task_type.lower() or "decide" in task_type.lower():
            return "judge"
        else:
            return "researcher"  # Default
    
    def _coordinate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Tool: Coordinate workflow execution"""
        return self.active_workflows.get(workflow_id, {})
    
    def _integrate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tool: Integrate multiple agent results"""
        # Implementation would intelligently merge and synthesize results
        return {"integrated_result": results}
    
    def _track_progress(self, workflow_id: str) -> Dict[str, Any]:
        """Tool: Track and report workflow progress"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            return {
                "status": workflow["status"],
                "progress": f"{workflow['phases_completed']}/{workflow['total_phases']}",
                "running_time": (datetime.utcnow() - workflow["start_time"]).total_seconds()
            }
        return {"status": "not_found"}