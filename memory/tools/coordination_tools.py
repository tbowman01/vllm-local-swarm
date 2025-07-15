"""
Coordination Tools for Agent Communication

Provides tools for agent-to-agent coordination and handoffs.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..core import MemoryManager, MemoryEntry, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


class CoordinationTool:
    """
    Tool for agent coordination and communication.
    
    Handles agent handoffs, shared context, and coordination protocols.
    """
    
    def __init__(self, memory_manager: MemoryManager, agent_id: str):
        """
        Initialize coordination tool for a specific agent.
        
        Args:
            memory_manager: Initialized memory manager instance
            agent_id: ID of the agent using this tool
        """
        self.memory_manager = memory_manager
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"{__name__}.CoordinationTool.{agent_id}")
        
        # Current session and coordination state
        self.current_session_id: Optional[str] = None
        self.coordination_context: Dict[str, Any] = {}
    
    def set_session(self, session_id: str) -> None:
        """Set the current session ID."""
        self.current_session_id = session_id
        self.logger.debug(f"Set session ID to: {session_id}")
    
    async def handoff_to_agent(self, target_agent_id: str, task_data: Dict[str, Any],
                              handoff_type: str = "task_delegation",
                              priority: str = "normal",
                              expected_completion: Optional[datetime] = None) -> str:
        """
        Hand off a task to another agent.
        
        Args:
            target_agent_id: ID of the target agent
            task_data: Data and context for the task
            handoff_type: Type of handoff (task_delegation, consultation, etc.)
            priority: Priority level (low, normal, high, urgent)
            expected_completion: Optional expected completion time
            
        Returns:
            str: Handoff ID
        """
        handoff_data = {
            "task_data": task_data,
            "handoff_type": handoff_type,
            "priority": priority,
            "expected_completion": expected_completion.isoformat() if expected_completion else None,
            "handoff_time": datetime.utcnow().isoformat(),
            "from_agent": self.agent_id,
            "to_agent": target_agent_id,
            "status": "pending"
        }
        
        # Store handoff in session memory
        handoff_entry = MemoryEntry(
            id=None,
            type=MemoryType.SESSION,
            content=handoff_data,
            metadata={
                "operation": "agent_handoff",
                "from_agent": self.agent_id,
                "to_agent": target_agent_id,
                "handoff_type": handoff_type,
                "priority": priority
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["handoff", "coordination", handoff_type, priority]
        )
        
        handoff_id = await self.memory_manager.store(handoff_entry)
        
        # Also notify in shared coordination space
        await self._update_coordination_board(
            "handoff_created",
            {
                "handoff_id": handoff_id,
                "from_agent": self.agent_id,
                "to_agent": target_agent_id,
                "task_summary": task_data.get("summary", "Task handoff"),
                "priority": priority
            }
        )
        
        self.logger.info(f"Created handoff {handoff_id} to agent {target_agent_id}")
        return handoff_id
    
    async def get_pending_handoffs(self) -> List[Dict[str, Any]]:
        """
        Get handoffs pending for this agent.
        
        Returns:
            List of pending handoff tasks
        """
        # Search for handoffs directed to this agent
        query = MemoryQuery(
            query="handoff",
            type=MemoryType.SESSION,
            session_id=self.current_session_id,
            tags=["handoff"],
            limit=50
        )
        
        handoffs = await self.memory_manager.search(query)
        
        pending_handoffs = []
        for handoff in handoffs:
            content = handoff.content
            if (content.get("to_agent") == self.agent_id and 
                content.get("status") == "pending"):
                
                pending_handoffs.append({
                    "handoff_id": handoff.id,
                    "from_agent": content.get("from_agent"),
                    "task_data": content.get("task_data"),
                    "handoff_type": content.get("handoff_type"),
                    "priority": content.get("priority", "normal"),
                    "handoff_time": content.get("handoff_time"),
                    "expected_completion": content.get("expected_completion"),
                    "metadata": handoff.metadata
                })
        
        # Sort by priority and handoff time
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        pending_handoffs.sort(
            key=lambda x: (priority_order.get(x["priority"], 2), x["handoff_time"])
        )
        
        self.logger.debug(f"Found {len(pending_handoffs)} pending handoffs")
        return pending_handoffs
    
    async def accept_handoff(self, handoff_id: str, acceptance_note: str = "") -> bool:
        """
        Accept a handoff task.
        
        Args:
            handoff_id: ID of the handoff to accept
            acceptance_note: Optional note about acceptance
            
        Returns:
            bool: True if accepted successfully
        """
        # Retrieve the handoff
        handoff_entry = await self.memory_manager.retrieve(handoff_id, MemoryType.SESSION)
        
        if not handoff_entry:
            self.logger.error(f"Handoff {handoff_id} not found")
            return False
        
        content = handoff_entry.content
        if content.get("to_agent") != self.agent_id:
            self.logger.error(f"Handoff {handoff_id} not directed to this agent")
            return False
        
        if content.get("status") != "pending":
            self.logger.error(f"Handoff {handoff_id} is not pending")
            return False
        
        # Update handoff status
        content["status"] = "accepted"
        content["accepted_time"] = datetime.utcnow().isoformat()
        content["acceptance_note"] = acceptance_note
        
        updated_entry = MemoryEntry(
            id=handoff_id,
            type=MemoryType.SESSION,
            content=content,
            metadata=handoff_entry.metadata,
            timestamp=handoff_entry.timestamp,
            agent_id=handoff_entry.agent_id,
            session_id=handoff_entry.session_id,
            tags=handoff_entry.tags
        )
        
        await self.memory_manager.store(updated_entry)
        
        # Update coordination board
        await self._update_coordination_board(
            "handoff_accepted",
            {
                "handoff_id": handoff_id,
                "by_agent": self.agent_id,
                "acceptance_note": acceptance_note
            }
        )
        
        self.logger.info(f"Accepted handoff {handoff_id}")
        return True
    
    async def complete_handoff(self, handoff_id: str, result: Dict[str, Any],
                              completion_note: str = "") -> bool:
        """
        Complete a handoff task.
        
        Args:
            handoff_id: ID of the handoff to complete
            result: Results/output from the task
            completion_note: Optional completion notes
            
        Returns:
            bool: True if completed successfully
        """
        # Retrieve the handoff
        handoff_entry = await self.memory_manager.retrieve(handoff_id, MemoryType.SESSION)
        
        if not handoff_entry:
            self.logger.error(f"Handoff {handoff_id} not found")
            return False
        
        content = handoff_entry.content
        if content.get("to_agent") != self.agent_id:
            self.logger.error(f"Handoff {handoff_id} not assigned to this agent")
            return False
        
        # Update handoff status
        content["status"] = "completed"
        content["completed_time"] = datetime.utcnow().isoformat()
        content["result"] = result
        content["completion_note"] = completion_note
        
        updated_entry = MemoryEntry(
            id=handoff_id,
            type=MemoryType.SESSION,
            content=content,
            metadata=handoff_entry.metadata,
            timestamp=handoff_entry.timestamp,
            agent_id=handoff_entry.agent_id,
            session_id=handoff_entry.session_id,
            tags=handoff_entry.tags + ["completed"]
        )
        
        await self.memory_manager.store(updated_entry)
        
        # Update coordination board
        await self._update_coordination_board(
            "handoff_completed",
            {
                "handoff_id": handoff_id,
                "by_agent": self.agent_id,
                "result_summary": str(result)[:200],  # Truncated summary
                "completion_note": completion_note
            }
        )
        
        self.logger.info(f"Completed handoff {handoff_id}")
        return True
    
    async def share_context(self, context_key: str, context_data: Any,
                           visibility: str = "session",
                           expiry_hours: Optional[int] = None) -> str:
        """
        Share context with other agents.
        
        Args:
            context_key: Key to identify the shared context
            context_data: Context data to share
            visibility: "session", "global", or specific agent IDs
            expiry_hours: Optional expiry time in hours
            
        Returns:
            str: Shared context ID
        """
        shared_context = {
            "context_key": context_key,
            "context_data": context_data,
            "shared_by": self.agent_id,
            "visibility": visibility,
            "shared_time": datetime.utcnow().isoformat(),
            "expiry_hours": expiry_hours
        }
        
        context_entry = MemoryEntry(
            id=f"shared_context_{context_key}_{self.agent_id}",
            type=MemoryType.SESSION,
            content=shared_context,
            metadata={
                "operation": "context_sharing",
                "shared_by": self.agent_id,
                "visibility": visibility,
                "context_key": context_key
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["shared_context", "coordination", visibility]
        )
        
        context_id = await self.memory_manager.store(context_entry)
        
        self.logger.debug(f"Shared context '{context_key}' with visibility '{visibility}'")
        return context_id
    
    async def get_shared_context(self, context_key: Optional[str] = None,
                                from_agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get shared context from other agents.
        
        Args:
            context_key: Optional specific context key to retrieve
            from_agent: Optional specific agent to get context from
            
        Returns:
            List of shared context entries
        """
        # Build query
        if context_key:
            query_str = context_key
        else:
            query_str = "shared_context"
        
        query = MemoryQuery(
            query=query_str,
            type=MemoryType.SESSION,
            session_id=self.current_session_id,
            tags=["shared_context"],
            limit=50
        )
        
        results = await self.memory_manager.search(query)
        
        shared_contexts = []
        for entry in results:
            content = entry.content
            
            # Check visibility rules
            visibility = content.get("visibility", "session")
            if visibility == "session" or visibility == "global":
                # Can access
                pass
            elif isinstance(visibility, list) and self.agent_id in visibility:
                # Specifically granted access
                pass
            else:
                # No access
                continue
            
            # Filter by from_agent if specified
            if from_agent and content.get("shared_by") != from_agent:
                continue
            
            # Filter by context_key if specified
            if context_key and content.get("context_key") != context_key:
                continue
            
            # Check expiry
            if content.get("expiry_hours"):
                shared_time = datetime.fromisoformat(content.get("shared_time"))
                expiry_time = shared_time + timedelta(hours=content.get("expiry_hours"))
                if datetime.utcnow() > expiry_time:
                    continue
            
            shared_contexts.append({
                "context_id": entry.id,
                "context_key": content.get("context_key"),
                "context_data": content.get("context_data"),
                "shared_by": content.get("shared_by"),
                "shared_time": content.get("shared_time"),
                "visibility": content.get("visibility"),
                "expiry_hours": content.get("expiry_hours")
            })
        
        self.logger.debug(f"Retrieved {len(shared_contexts)} shared context entries")
        return shared_contexts
    
    async def broadcast_status(self, status: str, details: Dict[str, Any] = None) -> str:
        """
        Broadcast current status to other agents.
        
        Args:
            status: Current status (e.g., "working", "available", "blocked")
            details: Optional additional status details
            
        Returns:
            str: Status broadcast ID
        """
        status_data = {
            "agent_id": self.agent_id,
            "status": status,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        status_entry = MemoryEntry(
            id=f"status_{self.agent_id}_{int(datetime.utcnow().timestamp())}",
            type=MemoryType.SESSION,
            content=status_data,
            metadata={
                "operation": "status_broadcast",
                "agent_id": self.agent_id,
                "status": status
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["status", "broadcast", status]
        )
        
        status_id = await self.memory_manager.store(status_entry)
        
        # Update coordination board
        await self._update_coordination_board(
            "status_update",
            {
                "agent_id": self.agent_id,
                "status": status,
                "details": details
            }
        )
        
        self.logger.debug(f"Broadcast status: {status}")
        return status_id
    
    async def get_agent_status(self, target_agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get status of other agents.
        
        Args:
            target_agent_id: Optional specific agent to get status for
            
        Returns:
            List of agent status entries
        """
        query = MemoryQuery(
            query="status",
            type=MemoryType.SESSION,
            session_id=self.current_session_id,
            tags=["status", "broadcast"],
            limit=100
        )
        
        results = await self.memory_manager.search(query)
        
        # Get latest status for each agent
        agent_statuses = {}
        for entry in results:
            content = entry.content
            agent_id = content.get("agent_id")
            
            if target_agent_id and agent_id != target_agent_id:
                continue
            
            if agent_id == self.agent_id:
                continue  # Skip own status
            
            # Keep only latest status per agent
            if (agent_id not in agent_statuses or 
                entry.timestamp > agent_statuses[agent_id]["timestamp"]):
                agent_statuses[agent_id] = {
                    "agent_id": agent_id,
                    "status": content.get("status"),
                    "details": content.get("details", {}),
                    "timestamp": entry.timestamp,
                    "last_seen": content.get("timestamp")
                }
        
        status_list = list(agent_statuses.values())
        status_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        self.logger.debug(f"Retrieved status for {len(status_list)} agents")
        return status_list
    
    async def request_assistance(self, request_type: str, details: Dict[str, Any],
                                urgency: str = "normal") -> str:
        """
        Request assistance from other agents.
        
        Args:
            request_type: Type of assistance needed
            details: Details about what's needed
            urgency: Urgency level (low, normal, high, urgent)
            
        Returns:
            str: Assistance request ID
        """
        request_data = {
            "requesting_agent": self.agent_id,
            "request_type": request_type,
            "details": details,
            "urgency": urgency,
            "status": "open",
            "request_time": datetime.utcnow().isoformat()
        }
        
        request_entry = MemoryEntry(
            id=None,
            type=MemoryType.SESSION,
            content=request_data,
            metadata={
                "operation": "assistance_request",
                "requesting_agent": self.agent_id,
                "request_type": request_type,
                "urgency": urgency
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["assistance_request", "coordination", request_type, urgency]
        )
        
        request_id = await self.memory_manager.store(request_entry)
        
        # Update coordination board
        await self._update_coordination_board(
            "assistance_requested",
            {
                "request_id": request_id,
                "requesting_agent": self.agent_id,
                "request_type": request_type,
                "urgency": urgency,
                "details_summary": str(details)[:200]
            }
        )
        
        self.logger.info(f"Requested assistance: {request_type} (urgency: {urgency})")
        return request_id
    
    async def get_assistance_requests(self) -> List[Dict[str, Any]]:
        """
        Get open assistance requests from other agents.
        
        Returns:
            List of assistance requests
        """
        query = MemoryQuery(
            query="assistance_request",
            type=MemoryType.SESSION,
            session_id=self.current_session_id,
            tags=["assistance_request"],
            limit=50
        )
        
        results = await self.memory_manager.search(query)
        
        open_requests = []
        for entry in results:
            content = entry.content
            
            # Skip own requests and closed requests
            if (content.get("requesting_agent") == self.agent_id or
                content.get("status") != "open"):
                continue
            
            open_requests.append({
                "request_id": entry.id,
                "requesting_agent": content.get("requesting_agent"),
                "request_type": content.get("request_type"),
                "details": content.get("details"),
                "urgency": content.get("urgency", "normal"),
                "request_time": content.get("request_time")
            })
        
        # Sort by urgency and time
        urgency_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        open_requests.sort(
            key=lambda x: (urgency_order.get(x["urgency"], 2), x["request_time"])
        )
        
        self.logger.debug(f"Found {len(open_requests)} open assistance requests")
        return open_requests
    
    async def respond_to_assistance(self, request_id: str, response: Dict[str, Any]) -> bool:
        """
        Respond to an assistance request.
        
        Args:
            request_id: ID of the assistance request
            response: Response data
            
        Returns:
            bool: True if response was recorded
        """
        # Retrieve the request
        request_entry = await self.memory_manager.retrieve(request_id, MemoryType.SESSION)
        
        if not request_entry:
            self.logger.error(f"Assistance request {request_id} not found")
            return False
        
        # Create response entry
        response_data = {
            "request_id": request_id,
            "responding_agent": self.agent_id,
            "response": response,
            "response_time": datetime.utcnow().isoformat()
        }
        
        response_entry = MemoryEntry(
            id=f"assistance_response_{request_id}_{self.agent_id}",
            type=MemoryType.SESSION,
            content=response_data,
            metadata={
                "operation": "assistance_response",
                "request_id": request_id,
                "responding_agent": self.agent_id
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["assistance_response", "coordination"]
        )
        
        await self.memory_manager.store(response_entry)
        
        self.logger.info(f"Responded to assistance request {request_id}")
        return True
    
    async def get_coordination_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current coordination activities.
        
        Returns:
            Dict containing coordination summary
        """
        # Get pending handoffs
        pending_handoffs = await self.get_pending_handoffs()
        
        # Get agent statuses
        agent_statuses = await self.get_agent_status()
        
        # Get assistance requests
        assistance_requests = await self.get_assistance_requests()
        
        # Get shared contexts
        shared_contexts = await self.get_shared_context()
        
        summary = {
            "agent_id": self.agent_id,
            "session_id": self.current_session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "pending_handoffs": len(pending_handoffs),
            "active_agents": len(agent_statuses),
            "open_assistance_requests": len(assistance_requests),
            "shared_contexts": len(shared_contexts),
            "coordination_details": {
                "handoffs": pending_handoffs[:5],  # Top 5
                "agent_statuses": agent_statuses[:10],  # Top 10
                "assistance_requests": assistance_requests[:5],  # Top 5
                "shared_contexts": [ctx["context_key"] for ctx in shared_contexts[:10]]
            }
        }
        
        return summary
    
    async def _update_coordination_board(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Update the coordination board with an event."""
        coordination_event = {
            "event_type": event_type,
            "event_data": event_data,
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        event_entry = MemoryEntry(
            id=None,
            type=MemoryType.SESSION,
            content=coordination_event,
            metadata={
                "operation": "coordination_event",
                "event_type": event_type,
                "agent_id": self.agent_id
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["coordination_board", event_type]
        )
        
        await self.memory_manager.store(event_entry)