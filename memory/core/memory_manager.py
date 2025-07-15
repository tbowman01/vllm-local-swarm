"""
Memory Manager - Central coordinator for all memory systems

This is the main entry point for memory operations, coordinating between
session memory, semantic memory, and observability systems.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

from .config import MemoryConfig
from .session_memory import SessionMemory
from .semantic_memory import SemanticMemory
from .observability import ObservabilityManager

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory storage."""
    SESSION = "session"       # Short-term context within a task/conversation
    SEMANTIC = "semantic"     # Long-term knowledge and embeddings
    AGENT = "agent"          # Agent-specific persistent state
    TRACE = "trace"          # Observability traces and logs


@dataclass
class MemoryEntry:
    """Standard memory entry structure."""
    id: str
    type: MemoryType
    content: Any
    metadata: Dict[str, Any]
    timestamp: datetime
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.id is None:
            self.id = str(uuid.uuid4())


@dataclass
class MemoryQuery:
    """Memory query structure."""
    query: str
    type: Optional[MemoryType] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    tags: List[str] = None
    limit: int = 10
    similarity_threshold: float = 0.7
    time_range: Optional[tuple] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryManager:
    """
    Central memory management system coordinating all memory types.
    
    Responsibilities:
    - Coordinate between session, semantic, and observability systems
    - Provide unified memory API for agents
    - Handle memory lifecycle and cleanup
    - Implement cross-memory search and retrieval
    """
    
    def __init__(self, config: MemoryConfig):
        """Initialize memory manager with configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.MemoryManager")
        
        # Initialize subsystems
        self.session_memory = None
        self.semantic_memory = None
        self.observability = None
        
        # Internal state
        self._initialized = False
        self._cleanup_task = None
        
    async def initialize(self) -> None:
        """Initialize all memory subsystems."""
        try:
            self.logger.info("Initializing memory management system...")
            
            # Initialize session memory (Redis)
            if self.config.session_memory_enabled:
                self.session_memory = SessionMemory(self.config.redis)
                await self.session_memory.initialize()
                self.logger.info("Session memory initialized")
            
            # Initialize semantic memory (Vector DB)
            if self.config.semantic_memory_enabled:
                self.semantic_memory = SemanticMemory(
                    self.config.qdrant, 
                    self.config.embedding
                )
                await self.semantic_memory.initialize()
                self.logger.info("Semantic memory initialized")
            
            # Initialize observability (Langfuse + ClickHouse)
            if self.config.observability_enabled:
                self.observability = ObservabilityManager(
                    self.config.langfuse,
                    self.config.clickhouse
                )
                await self.observability.initialize()
                self.logger.info("Observability system initialized")
            
            # Start background cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._initialized = True
            self.logger.info("Memory management system fully initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory system: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown all memory subsystems."""
        self.logger.info("Shutting down memory management system...")
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown subsystems
        if self.observability:
            await self.observability.shutdown()
        if self.semantic_memory:
            await self.semantic_memory.shutdown()
        if self.session_memory:
            await self.session_memory.shutdown()
        
        self._initialized = False
        self.logger.info("Memory management system shutdown complete")
    
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store memory entry in appropriate subsystem(s).
        
        Args:
            entry: Memory entry to store
            
        Returns:
            str: Entry ID
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        entry_id = entry.id or str(uuid.uuid4())
        entry.id = entry_id
        
        try:
            # Store in appropriate subsystem based on type
            if entry.type == MemoryType.SESSION and self.session_memory:
                await self.session_memory.store(entry)
                
            elif entry.type == MemoryType.SEMANTIC and self.semantic_memory:
                await self.semantic_memory.store(entry)
                
            elif entry.type == MemoryType.AGENT:
                # Agent memory goes to both session (current state) and semantic (history)
                if self.session_memory:
                    await self.session_memory.store(entry)
                if self.semantic_memory:
                    await self.semantic_memory.store(entry)
                    
            elif entry.type == MemoryType.TRACE and self.observability:
                await self.observability.log_trace(entry)
            
            # Always log to observability for analytics
            if self.observability and entry.type != MemoryType.TRACE:
                trace_entry = MemoryEntry(
                    id=f"trace_{entry_id}",
                    type=MemoryType.TRACE,
                    content={"memory_operation": "store", "original_entry": asdict(entry)},
                    metadata={"operation": "memory_store", "entry_type": entry.type.value},
                    timestamp=datetime.utcnow(),
                    agent_id=entry.agent_id,
                    session_id=entry.session_id,
                    tags=["memory_operation"] + entry.tags
                )
                await self.observability.log_trace(trace_entry)
            
            self.logger.debug(f"Stored memory entry {entry_id} of type {entry.type.value}")
            return entry_id
            
        except Exception as e:
            self.logger.error(f"Failed to store memory entry {entry_id}: {e}")
            raise
    
    async def retrieve(self, entry_id: str, memory_type: Optional[MemoryType] = None) -> Optional[MemoryEntry]:
        """
        Retrieve memory entry by ID.
        
        Args:
            entry_id: Entry ID to retrieve
            memory_type: Optional type hint for faster lookup
            
        Returns:
            MemoryEntry or None if not found
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        try:
            # Try specified type first, then all types
            types_to_search = [memory_type] if memory_type else [
                MemoryType.SESSION, MemoryType.SEMANTIC, MemoryType.AGENT
            ]
            
            for mem_type in types_to_search:
                if mem_type == MemoryType.SESSION and self.session_memory:
                    entry = await self.session_memory.retrieve(entry_id)
                    if entry:
                        return entry
                        
                elif mem_type == MemoryType.SEMANTIC and self.semantic_memory:
                    entry = await self.semantic_memory.retrieve(entry_id)
                    if entry:
                        return entry
                        
                elif mem_type == MemoryType.AGENT:
                    # Try session first for agent memory (current state)
                    if self.session_memory:
                        entry = await self.session_memory.retrieve(entry_id)
                        if entry:
                            return entry
                    # Then semantic (historical state)
                    if self.semantic_memory:
                        entry = await self.semantic_memory.retrieve(entry_id)
                        if entry:
                            return entry
            
            self.logger.debug(f"Memory entry {entry_id} not found")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve memory entry {entry_id}: {e}")
            raise
    
    async def search(self, query: MemoryQuery) -> List[MemoryEntry]:
        """
        Search memory entries across all systems.
        
        Args:
            query: Memory query parameters
            
        Returns:
            List of matching memory entries
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        results = []
        
        try:
            # Search session memory if enabled and relevant
            if (self.session_memory and 
                (query.type is None or query.type == MemoryType.SESSION)):
                session_results = await self.session_memory.search(query)
                results.extend(session_results)
            
            # Search semantic memory for similarity-based search
            if (self.semantic_memory and 
                (query.type is None or query.type in [MemoryType.SEMANTIC, MemoryType.AGENT])):
                semantic_results = await self.semantic_memory.search(query)
                results.extend(semantic_results)
            
            # Remove duplicates and sort by relevance/timestamp
            unique_results = {entry.id: entry for entry in results}
            sorted_results = list(unique_results.values())
            
            # Sort by timestamp (newest first)
            sorted_results.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Limit results
            limited_results = sorted_results[:query.limit]
            
            # Log search operation
            if self.observability:
                trace_entry = MemoryEntry(
                    id=str(uuid.uuid4()),
                    type=MemoryType.TRACE,
                    content={
                        "memory_operation": "search",
                        "query": asdict(query),
                        "results_count": len(limited_results)
                    },
                    metadata={"operation": "memory_search"},
                    timestamp=datetime.utcnow(),
                    session_id=query.session_id,
                    tags=["memory_operation", "search"]
                )
                await self.observability.log_trace(trace_entry)
            
            self.logger.debug(f"Memory search returned {len(limited_results)} results")
            return limited_results
            
        except Exception as e:
            self.logger.error(f"Failed to search memory: {e}")
            raise
    
    async def delete(self, entry_id: str, memory_type: Optional[MemoryType] = None) -> bool:
        """
        Delete memory entry.
        
        Args:
            entry_id: Entry ID to delete
            memory_type: Optional type hint for faster deletion
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not self._initialized:
            raise RuntimeError("Memory manager not initialized")
        
        deleted = False
        
        try:
            # Delete from all relevant subsystems
            if memory_type is None or memory_type == MemoryType.SESSION:
                if self.session_memory:
                    session_deleted = await self.session_memory.delete(entry_id)
                    deleted = deleted or session_deleted
            
            if memory_type is None or memory_type == MemoryType.SEMANTIC:
                if self.semantic_memory:
                    semantic_deleted = await self.semantic_memory.delete(entry_id)
                    deleted = deleted or semantic_deleted
            
            if memory_type is None or memory_type == MemoryType.AGENT:
                # Agent entries might be in both systems
                if self.session_memory:
                    session_deleted = await self.session_memory.delete(entry_id)
                    deleted = deleted or session_deleted
                if self.semantic_memory:
                    semantic_deleted = await self.semantic_memory.delete(entry_id)
                    deleted = deleted or semantic_deleted
            
            if deleted:
                self.logger.debug(f"Deleted memory entry {entry_id}")
            else:
                self.logger.debug(f"Memory entry {entry_id} not found for deletion")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete memory entry {entry_id}: {e}")
            raise
    
    async def get_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """
        Get all memory for a specific agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict containing session and semantic memory for the agent
        """
        query = MemoryQuery(
            query="*",
            agent_id=agent_id,
            limit=1000
        )
        
        entries = await self.search(query)
        
        return {
            "agent_id": agent_id,
            "total_entries": len(entries),
            "session_entries": [e for e in entries if e.type == MemoryType.SESSION],
            "semantic_entries": [e for e in entries if e.type == MemoryType.SEMANTIC],
            "agent_entries": [e for e in entries if e.type == MemoryType.AGENT],
            "latest_activity": max([e.timestamp for e in entries]) if entries else None
        }
    
    async def get_session_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Get all memory for a specific session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict containing all memory for the session
        """
        query = MemoryQuery(
            query="*",
            session_id=session_id,
            limit=1000
        )
        
        entries = await self.search(query)
        
        return {
            "session_id": session_id,
            "total_entries": len(entries),
            "entries": entries,
            "agents_involved": list(set([e.agent_id for e in entries if e.agent_id])),
            "start_time": min([e.timestamp for e in entries]) if entries else None,
            "end_time": max([e.timestamp for e in entries]) if entries else None
        }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get overall memory system statistics.
        
        Returns:
            Dict containing system statistics
        """
        stats = {
            "initialized": self._initialized,
            "timestamp": datetime.utcnow(),
            "subsystems": {}
        }
        
        if self.session_memory:
            stats["subsystems"]["session"] = await self.session_memory.get_stats()
        
        if self.semantic_memory:
            stats["subsystems"]["semantic"] = await self.semantic_memory.get_stats()
        
        if self.observability:
            stats["subsystems"]["observability"] = await self.observability.get_stats()
        
        return stats
    
    async def _cleanup_loop(self):
        """Background cleanup task."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self._cleanup_old_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data based on retention policy."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.data_retention_days)
        
        # Cleanup session memory
        if self.session_memory:
            await self.session_memory.cleanup_old_data(cutoff_date)
        
        # Cleanup semantic memory (optional - might want to keep for learning)
        # if self.semantic_memory:
        #     await self.semantic_memory.cleanup_old_data(cutoff_date)
        
        self.logger.info(f"Completed memory cleanup for data older than {cutoff_date}")