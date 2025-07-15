"""
Memory Tools for Agent Integration

Provides high-level tools for agents to interact with the memory system.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..core import MemoryManager, MemoryEntry, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


class MemoryTool:
    """
    High-level memory tool for agent integration.
    
    Provides simplified interfaces for agents to store, retrieve, and search memory.
    """
    
    def __init__(self, memory_manager: MemoryManager, agent_id: str):
        """
        Initialize memory tool for a specific agent.
        
        Args:
            memory_manager: Initialized memory manager instance
            agent_id: ID of the agent using this tool
        """
        self.memory_manager = memory_manager
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"{__name__}.MemoryTool.{agent_id}")
        
        # Default session ID (can be overridden)
        self.current_session_id: Optional[str] = None
    
    def set_session(self, session_id: str) -> None:
        """
        Set the current session ID for this agent.
        
        Args:
            session_id: Session ID to use for subsequent operations
        """
        self.current_session_id = session_id
        self.logger.debug(f"Set session ID to: {session_id}")
    
    async def store_knowledge(self, content: Any, description: str, 
                             tags: Optional[List[str]] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store knowledge in semantic memory for long-term retention.
        
        Args:
            content: Content to store
            description: Human-readable description
            tags: Optional tags for categorization
            metadata: Optional additional metadata
            
        Returns:
            str: Entry ID
        """
        entry = MemoryEntry(
            id=None,  # Will be generated
            type=MemoryType.SEMANTIC,
            content=content,
            metadata={
                "description": description,
                "stored_by": self.agent_id,
                **(metadata or {})
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=tags or []
        )
        
        entry_id = await self.memory_manager.store(entry)
        self.logger.info(f"Stored knowledge: {description} ({entry_id})")
        return entry_id
    
    async def store_context(self, content: Any, context_type: str,
                           ttl_hours: Optional[int] = None,
                           tags: Optional[List[str]] = None) -> str:
        """
        Store context in session memory for short-term use.
        
        Args:
            content: Content to store
            context_type: Type of context (e.g., "task_state", "conversation")
            ttl_hours: Optional TTL in hours
            tags: Optional tags
            
        Returns:
            str: Entry ID
        """
        entry = MemoryEntry(
            id=None,
            type=MemoryType.SESSION,
            content=content,
            metadata={
                "context_type": context_type,
                "stored_by": self.agent_id,
                "ttl_hours": ttl_hours
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["context", context_type] + (tags or [])
        )
        
        entry_id = await self.memory_manager.store(entry)
        self.logger.debug(f"Stored context: {context_type} ({entry_id})")
        return entry_id
    
    async def store_agent_state(self, state: Dict[str, Any], 
                               state_type: str = "current") -> str:
        """
        Store agent state for persistence.
        
        Args:
            state: Agent state data
            state_type: Type of state (e.g., "current", "checkpoint")
            
        Returns:
            str: Entry ID
        """
        entry = MemoryEntry(
            id=f"agent_state_{self.agent_id}_{state_type}",
            type=MemoryType.AGENT,
            content=state,
            metadata={
                "state_type": state_type,
                "agent_id": self.agent_id
            },
            timestamp=datetime.utcnow(),
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["agent_state", state_type]
        )
        
        entry_id = await self.memory_manager.store(entry)
        self.logger.debug(f"Stored agent state: {state_type}")
        return entry_id
    
    async def retrieve_knowledge(self, query: str, limit: int = 5,
                                similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Search semantic memory for relevant knowledge.
        
        Args:
            query: Search query
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of knowledge entries with similarity scores
        """
        memory_query = MemoryQuery(
            query=query,
            type=MemoryType.SEMANTIC,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        results = await self.memory_manager.search(memory_query)
        
        formatted_results = []
        for entry in results:
            formatted_results.append({
                "id": entry.id,
                "content": entry.content,
                "description": entry.metadata.get("description", ""),
                "similarity_score": entry.metadata.get("similarity_score", 0),
                "timestamp": entry.timestamp.isoformat(),
                "tags": entry.tags,
                "stored_by": entry.metadata.get("stored_by")
            })
        
        self.logger.debug(f"Retrieved {len(formatted_results)} knowledge entries for query: {query}")
        return formatted_results
    
    async def retrieve_context(self, context_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve context from session memory.
        
        Args:
            context_type: Optional filter by context type
            
        Returns:
            List of context entries
        """
        query_tags = ["context"]
        if context_type:
            query_tags.append(context_type)
        
        memory_query = MemoryQuery(
            query="*",
            type=MemoryType.SESSION,
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=query_tags,
            limit=50
        )
        
        results = await self.memory_manager.search(memory_query)
        
        formatted_results = []
        for entry in results:
            formatted_results.append({
                "id": entry.id,
                "content": entry.content,
                "context_type": entry.metadata.get("context_type"),
                "timestamp": entry.timestamp.isoformat(),
                "tags": entry.tags
            })
        
        self.logger.debug(f"Retrieved {len(formatted_results)} context entries")
        return formatted_results
    
    async def retrieve_agent_state(self, state_type: str = "current") -> Optional[Dict[str, Any]]:
        """
        Retrieve agent state.
        
        Args:
            state_type: Type of state to retrieve
            
        Returns:
            Agent state data or None if not found
        """
        entry_id = f"agent_state_{self.agent_id}_{state_type}"
        entry = await self.memory_manager.retrieve(entry_id, MemoryType.AGENT)
        
        if entry:
            self.logger.debug(f"Retrieved agent state: {state_type}")
            return entry.content
        else:
            self.logger.debug(f"No agent state found: {state_type}")
            return None
    
    async def search_memory(self, query: str, memory_types: Optional[List[MemoryType]] = None,
                           tags: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search across all memory types.
        
        Args:
            query: Search query
            memory_types: Optional filter by memory types
            tags: Optional tag filters
            limit: Maximum number of results
            
        Returns:
            List of memory entries from all systems
        """
        all_results = []
        
        # Search each memory type if not filtered
        types_to_search = memory_types or [MemoryType.SESSION, MemoryType.SEMANTIC, MemoryType.AGENT]
        
        for memory_type in types_to_search:
            memory_query = MemoryQuery(
                query=query,
                type=memory_type,
                agent_id=self.agent_id,
                session_id=self.current_session_id,
                tags=tags,
                limit=limit
            )
            
            results = await self.memory_manager.search(memory_query)
            
            for entry in results:
                all_results.append({
                    "id": entry.id,
                    "type": entry.type.value,
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_id": entry.agent_id,
                    "session_id": entry.session_id,
                    "tags": entry.tags,
                    "similarity_score": entry.metadata.get("similarity_score", 1.0)
                })
        
        # Sort by relevance (similarity score, then timestamp)
        all_results.sort(key=lambda x: (-x["similarity_score"], x["timestamp"]), reverse=True)
        
        # Limit results
        limited_results = all_results[:limit]
        
        self.logger.debug(f"Search returned {len(limited_results)} total results")
        return limited_results
    
    async def delete_memory(self, entry_id: str, memory_type: Optional[MemoryType] = None) -> bool:
        """
        Delete a memory entry.
        
        Args:
            entry_id: ID of entry to delete
            memory_type: Optional type hint
            
        Returns:
            bool: True if deleted, False if not found
        """
        deleted = await self.memory_manager.delete(entry_id, memory_type)
        
        if deleted:
            self.logger.info(f"Deleted memory entry: {entry_id}")
        else:
            self.logger.warning(f"Memory entry not found: {entry_id}")
        
        return deleted
    
    async def get_my_memory_summary(self) -> Dict[str, Any]:
        """
        Get a summary of this agent's memory usage.
        
        Returns:
            Dict containing memory summary
        """
        summary = await self.memory_manager.get_agent_memory(self.agent_id)
        
        # Add some derived metrics
        summary["session_context_count"] = len([
            e for e in summary["session_entries"] 
            if "context" in e.tags
        ])
        
        summary["knowledge_count"] = len(summary["semantic_entries"])
        
        return summary
    
    async def clear_session_context(self) -> int:
        """
        Clear all context for the current session.
        
        Returns:
            int: Number of entries deleted
        """
        if not self.current_session_id:
            return 0
        
        # Search for session context entries
        memory_query = MemoryQuery(
            query="*",
            type=MemoryType.SESSION,
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["context"],
            limit=1000
        )
        
        entries = await self.memory_manager.search(memory_query)
        
        # Delete each entry
        deleted_count = 0
        for entry in entries:
            if await self.memory_manager.delete(entry.id, MemoryType.SESSION):
                deleted_count += 1
        
        self.logger.info(f"Cleared {deleted_count} session context entries")
        return deleted_count
    
    # Convenience methods for common operations
    
    async def remember(self, key: str, value: Any, permanent: bool = False) -> str:
        """
        Simple key-value storage.
        
        Args:
            key: Key to store under
            value: Value to store
            permanent: If True, store in semantic memory, else session memory
            
        Returns:
            str: Entry ID
        """
        if permanent:
            return await self.store_knowledge(
                content={"key": key, "value": value},
                description=f"Remembered: {key}",
                tags=["key_value", "remembered"]
            )
        else:
            return await self.store_context(
                content={"key": key, "value": value},
                context_type="key_value",
                tags=["remembered"]
            )
    
    async def recall(self, key: str, permanent: bool = False) -> Any:
        """
        Simple key-value retrieval.
        
        Args:
            key: Key to retrieve
            permanent: If True, search semantic memory, else session memory
            
        Returns:
            Value associated with key, or None if not found
        """
        memory_type = MemoryType.SEMANTIC if permanent else MemoryType.SESSION
        
        memory_query = MemoryQuery(
            query=key,
            type=memory_type,
            agent_id=self.agent_id,
            session_id=self.current_session_id,
            tags=["key_value", "remembered"],
            limit=1
        )
        
        results = await self.memory_manager.search(memory_query)
        
        for entry in results:
            content = entry.content
            if isinstance(content, dict) and content.get("key") == key:
                return content.get("value")
        
        return None
    
    async def learn_from_interaction(self, interaction_data: Dict[str, Any],
                                    outcome: str, effectiveness_score: float) -> str:
        """
        Store learning from an interaction for future reference.
        
        Args:
            interaction_data: Data about the interaction
            outcome: What happened
            effectiveness_score: How effective it was (0.0 to 1.0)
            
        Returns:
            str: Entry ID
        """
        learning_content = {
            "interaction": interaction_data,
            "outcome": outcome,
            "effectiveness_score": effectiveness_score,
            "learned_by": self.agent_id,
            "learning_type": "interaction"
        }
        
        return await self.store_knowledge(
            content=learning_content,
            description=f"Learning from interaction: {outcome}",
            tags=["learning", "interaction", f"effectiveness_{int(effectiveness_score * 10)}"],
            metadata={
                "effectiveness_score": effectiveness_score,
                "outcome": outcome
            }
        )
    
    async def get_relevant_learnings(self, context: str, min_effectiveness: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get relevant past learnings for current context.
        
        Args:
            context: Current context or situation
            min_effectiveness: Minimum effectiveness score to include
            
        Returns:
            List of relevant learning entries
        """
        results = await self.retrieve_knowledge(
            query=context,
            limit=10,
            similarity_threshold=0.6
        )
        
        # Filter for learnings with minimum effectiveness
        relevant_learnings = []
        for result in results:
            if "learning" in result.get("tags", []):
                content = result["content"]
                if isinstance(content, dict):
                    effectiveness = content.get("effectiveness_score", 0)
                    if effectiveness >= min_effectiveness:
                        relevant_learnings.append(result)
        
        return relevant_learnings