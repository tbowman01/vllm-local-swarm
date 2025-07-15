"""
Orchestration utilities for coordinating agents in the swarm.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class TaskConfig:
    """Configuration for a swarm task."""
    task_id: str
    task_type: str
    priority: int = 1
    max_retries: int = 3
    timeout: int = 300
    agents_required: int = 1

class TaskOrchestrator:
    """Orchestrates tasks across the swarm."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_tasks: Dict[str, TaskConfig] = {}
        self.task_results: Dict[str, Any] = {}
        
    async def submit_task(self, task_config: TaskConfig) -> str:
        """Submit a task to the orchestrator."""
        self.logger.info(f"Submitting task: {task_config.task_id}")
        self.active_tasks[task_config.task_id] = task_config
        return task_config.task_id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        if task_id in self.active_tasks:
            return {
                "task_id": task_id,
                "status": "active",
                "config": self.active_tasks[task_id]
            }
        elif task_id in self.task_results:
            return {
                "task_id": task_id,
                "status": "completed",
                "result": self.task_results[task_id]
            }
        return None
    
    async def complete_task(self, task_id: str, result: Any):
        """Mark a task as completed."""
        if task_id in self.active_tasks:
            self.task_results[task_id] = result
            del self.active_tasks[task_id]
            self.logger.info(f"Task completed: {task_id}")
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get the current orchestrator status."""
        return {
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.task_results),
            "total_tasks": len(self.active_tasks) + len(self.task_results)
        }

# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> TaskOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator()
    return _orchestrator