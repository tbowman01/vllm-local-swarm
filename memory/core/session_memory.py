"""
Session Memory - Redis-based short-term context storage

Handles session-level memory for agent coordination and task context.
Optimized for fast read/write operations and agent handoffs.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import asdict

import redis.asyncio as aioredis
from redis.asyncio import Redis

from .config import RedisConfig
from .models import MemoryEntry, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


class SessionMemory:
    """
    Redis-based session memory for short-term context and agent coordination.
    
    Features:
    - Fast key-value storage for session context
    - Agent handoff coordination
    - Task state management
    - Session-based isolation
    - Automatic expiration
    """
    
    def __init__(self, config: RedisConfig):
        """Initialize session memory with Redis configuration."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.SessionMemory")
        
        # Redis client
        self.redis: Optional[Redis] = None
        
        # Key prefixes for organization
        self.PREFIXES = {
            "session": "session:",
            "agent": "agent:",
            "task": "task:",
            "handoff": "handoff:",
            "context": "context:",
            "coordination": "coord:",
            "index": "index:"
        }
        
        # Default TTL for different data types (seconds)
        self.TTL = {
            "session": 24 * 3600,      # 24 hours
            "agent": 12 * 3600,        # 12 hours
            "task": 8 * 3600,          # 8 hours
            "handoff": 1 * 3600,       # 1 hour
            "context": 6 * 3600,       # 6 hours
            "coordination": 2 * 3600,  # 2 hours
        }
    
    async def initialize(self) -> None:
        """Initialize Redis connection and setup."""
        try:
            self.logger.info("Initializing Redis session memory...")
            
            # Create Redis connection
            self.redis = aioredis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                decode_responses=True
            )
            
            # Test connection
            await self.redis.ping()
            
            # Setup indexes for efficient queries
            await self._setup_indexes()
            
            self.logger.info("Redis session memory initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis session memory: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown Redis connection."""
        if self.redis:
            await self.redis.close()
            self.logger.info("Redis session memory connection closed")
    
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store memory entry in Redis.
        
        Args:
            entry: Memory entry to store
            
        Returns:
            str: Entry ID
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Generate key based on entry type and ID
            key = self._generate_key(entry)
            
            # Prepare data for storage
            data = {
                "id": entry.id,
                "type": entry.type.value,
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp.isoformat(),
                "agent_id": entry.agent_id,
                "session_id": entry.session_id,
                "tags": entry.tags
            }
            
            # Store entry
            await self.redis.hset(key, mapping={
                k: json.dumps(v) if v is not None else ""
                for k, v in data.items()
            })
            
            # Set expiration based on type
            ttl = self._get_ttl(entry)
            if ttl:
                await self.redis.expire(key, ttl)
            
            # Update indexes
            await self._update_indexes(entry)
            
            self.logger.debug(f"Stored session memory entry: {key}")
            return entry.id
            
        except Exception as e:
            self.logger.error(f"Failed to store session memory entry {entry.id}: {e}")
            raise
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve memory entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            MemoryEntry or None if not found
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Try different key patterns to find the entry
            patterns = [
                f"{prefix}{entry_id}" for prefix in self.PREFIXES.values()
            ]
            
            for pattern in patterns:
                data = await self.redis.hgetall(pattern)
                if data:
                    return self._deserialize_entry(data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve session memory entry {entry_id}: {e}")
            raise
    
    async def search(self, query: MemoryQuery) -> List[MemoryEntry]:
        """
        Search memory entries based on query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching entries
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            results = []
            
            # Get relevant keys based on query filters
            keys = await self._get_keys_for_query(query)
            
            # Retrieve and filter entries
            for key in keys:
                data = await self.redis.hgetall(key)
                if data:
                    entry = self._deserialize_entry(data)
                    if self._matches_query(entry, query):
                        results.append(entry)
            
            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            return results[:query.limit]
            
        except Exception as e:
            self.logger.error(f"Failed to search session memory: {e}")
            raise
    
    async def delete(self, entry_id: str) -> bool:
        """
        Delete memory entry.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Find and delete the entry
            patterns = [
                f"{prefix}{entry_id}" for prefix in self.PREFIXES.values()
            ]
            
            deleted = False
            for pattern in patterns:
                if await self.redis.exists(pattern):
                    # Remove from indexes first
                    data = await self.redis.hgetall(pattern)
                    if data:
                        entry = self._deserialize_entry(data)
                        await self._remove_from_indexes(entry)
                    
                    # Delete the entry
                    await self.redis.delete(pattern)
                    deleted = True
                    break
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete session memory entry {entry_id}: {e}")
            raise
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get complete context for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict containing session context
        """
        if not self.redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Get session index
            session_index_key = f"{self.PREFIXES['index']}session:{session_id}"
            entry_ids = await self.redis.smembers(session_index_key)
            
            # Retrieve all entries for the session
            entries = []
            for entry_id in entry_ids:
                entry = await self.retrieve(entry_id)
                if entry:
                    entries.append(entry)
            
            # Organize by type
            context = {
                "session_id": session_id,
                "entries": entries,
                "agents": {},
                "tasks": {},
                "coordination": {},
                "handoffs": []
            }
            
            for entry in entries:
                if entry.agent_id:
                    if entry.agent_id not in context["agents"]:
                        context["agents"][entry.agent_id] = []
                    context["agents"][entry.agent_id].append(entry)
                
                if "task" in entry.tags:
                    task_id = entry.metadata.get("task_id", "unknown")
                    if task_id not in context["tasks"]:
                        context["tasks"][task_id] = []
                    context["tasks"][task_id].append(entry)
                
                if "coordination" in entry.tags:
                    context["coordination"][entry.id] = entry
                
                if "handoff" in entry.tags:
                    context["handoffs"].append(entry)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get session context for {session_id}: {e}")
            raise
    
    async def store_agent_handoff(self, from_agent: str, to_agent: str, 
                                 session_id: str, handoff_data: Dict[str, Any]) -> str:
        """
        Store agent handoff information for coordination.
        
        Args:
            from_agent: Source agent ID
            to_agent: Target agent ID  
            session_id: Session ID
            handoff_data: Data being passed between agents
            
        Returns:
            str: Handoff entry ID
        """
        handoff_entry = MemoryEntry(
            id=f"handoff_{from_agent}_{to_agent}_{int(datetime.utcnow().timestamp())}",
            type=MemoryType.SESSION,
            content={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "handoff_data": handoff_data,
                "handoff_type": "agent_coordination"
            },
            metadata={
                "operation": "agent_handoff",
                "from_agent": from_agent,
                "to_agent": to_agent
            },
            timestamp=datetime.utcnow(),
            session_id=session_id,
            tags=["handoff", "coordination"]
        )
        
        return await self.store(handoff_entry)
    
    async def get_agent_handoffs(self, agent_id: str, session_id: str) -> List[MemoryEntry]:
        """
        Get handoffs for a specific agent in a session.
        
        Args:
            agent_id: Agent ID
            session_id: Session ID
            
        Returns:
            List of handoff entries
        """
        query = MemoryQuery(
            query="handoff",
            session_id=session_id,
            tags=["handoff"],
            limit=100
        )
        
        handoffs = await self.search(query)
        
        # Filter for this agent
        agent_handoffs = []
        for handoff in handoffs:
            content = handoff.content
            if (content.get("from_agent") == agent_id or 
                content.get("to_agent") == agent_id):
                agent_handoffs.append(handoff)
        
        return agent_handoffs
    
    async def cleanup_old_data(self, cutoff_date: datetime) -> int:
        """
        Clean up old session data.
        
        Args:
            cutoff_date: Delete data older than this date
            
        Returns:
            int: Number of entries deleted
        """
        if not self.redis:
            return 0
        
        deleted_count = 0
        
        try:
            # Get all keys
            all_keys = []
            for prefix in self.PREFIXES.values():
                pattern_keys = await self.redis.keys(f"{prefix}*")
                all_keys.extend(pattern_keys)
            
            # Check each key and delete if too old
            for key in all_keys:
                try:
                    data = await self.redis.hgetall(key)
                    if data and "timestamp" in data:
                        entry_time = datetime.fromisoformat(data["timestamp"])
                        if entry_time < cutoff_date:
                            await self.redis.delete(key)
                            deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Error checking key {key} for cleanup: {e}")
            
            self.logger.info(f"Cleaned up {deleted_count} old session memory entries")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error during session memory cleanup: {e}")
            return deleted_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get session memory statistics.
        
        Returns:
            Dict containing statistics
        """
        if not self.redis:
            return {"error": "Redis not initialized"}
        
        try:
            stats = {
                "total_keys": 0,
                "keys_by_type": {},
                "memory_usage": await self.redis.memory_usage() if hasattr(self.redis, 'memory_usage') else "unknown",
                "connection_info": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db
                }
            }
            
            # Count keys by type
            for prefix_name, prefix in self.PREFIXES.items():
                keys = await self.redis.keys(f"{prefix}*")
                count = len(keys)
                stats["keys_by_type"][prefix_name] = count
                stats["total_keys"] += count
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting session memory stats: {e}")
            return {"error": str(e)}
    
    def _generate_key(self, entry: MemoryEntry) -> str:
        """Generate Redis key for entry."""
        if entry.agent_id and "agent" in entry.tags:
            return f"{self.PREFIXES['agent']}{entry.id}"
        elif "task" in entry.tags:
            return f"{self.PREFIXES['task']}{entry.id}"
        elif "handoff" in entry.tags:
            return f"{self.PREFIXES['handoff']}{entry.id}"
        elif "coordination" in entry.tags:
            return f"{self.PREFIXES['coordination']}{entry.id}"
        elif "context" in entry.tags:
            return f"{self.PREFIXES['context']}{entry.id}"
        else:
            return f"{self.PREFIXES['session']}{entry.id}"
    
    def _get_ttl(self, entry: MemoryEntry) -> Optional[int]:
        """Get TTL for entry based on type and tags."""
        if "handoff" in entry.tags:
            return self.TTL["handoff"]
        elif "coordination" in entry.tags:
            return self.TTL["coordination"]
        elif "task" in entry.tags:
            return self.TTL["task"]
        elif "context" in entry.tags:
            return self.TTL["context"]
        elif entry.agent_id:
            return self.TTL["agent"]
        else:
            return self.TTL["session"]
    
    def _deserialize_entry(self, data: Dict[str, str]) -> MemoryEntry:
        """Convert Redis hash data back to MemoryEntry."""
        return MemoryEntry(
            id=data.get("id", ""),
            type=MemoryType(data.get("type", "session")),
            content=json.loads(data.get("content", "null")),
            metadata=json.loads(data.get("metadata", "{}")),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat())),
            agent_id=data.get("agent_id") or None,
            session_id=data.get("session_id") or None,
            tags=json.loads(data.get("tags", "[]"))
        )
    
    async def _setup_indexes(self) -> None:
        """Setup Redis indexes for efficient queries."""
        # Indexes are created dynamically as entries are added
        pass
    
    async def _update_indexes(self, entry: MemoryEntry) -> None:
        """Update indexes when entry is added."""
        try:
            # Session index
            if entry.session_id:
                session_index = f"{self.PREFIXES['index']}session:{entry.session_id}"
                await self.redis.sadd(session_index, entry.id)
                await self.redis.expire(session_index, self.TTL["session"])
            
            # Agent index
            if entry.agent_id:
                agent_index = f"{self.PREFIXES['index']}agent:{entry.agent_id}"
                await self.redis.sadd(agent_index, entry.id)
                await self.redis.expire(agent_index, self.TTL["agent"])
            
            # Tag indexes
            for tag in entry.tags:
                tag_index = f"{self.PREFIXES['index']}tag:{tag}"
                await self.redis.sadd(tag_index, entry.id)
                await self.redis.expire(tag_index, self.TTL["session"])
                
        except Exception as e:
            self.logger.warning(f"Failed to update indexes for entry {entry.id}: {e}")
    
    async def _remove_from_indexes(self, entry: MemoryEntry) -> None:
        """Remove entry from indexes."""
        try:
            # Session index
            if entry.session_id:
                session_index = f"{self.PREFIXES['index']}session:{entry.session_id}"
                await self.redis.srem(session_index, entry.id)
            
            # Agent index
            if entry.agent_id:
                agent_index = f"{self.PREFIXES['index']}agent:{entry.agent_id}"
                await self.redis.srem(agent_index, entry.id)
            
            # Tag indexes
            for tag in entry.tags:
                tag_index = f"{self.PREFIXES['index']}tag:{tag}"
                await self.redis.srem(tag_index, entry.id)
                
        except Exception as e:
            self.logger.warning(f"Failed to remove from indexes for entry {entry.id}: {e}")
    
    async def _get_keys_for_query(self, query: MemoryQuery) -> List[str]:
        """Get relevant keys for a query."""
        keys = set()
        
        # Session-based keys
        if query.session_id:
            session_index = f"{self.PREFIXES['index']}session:{query.session_id}"
            session_keys = await self.redis.smembers(session_index)
            for entry_id in session_keys:
                for prefix in self.PREFIXES.values():
                    key = f"{prefix}{entry_id}"
                    if await self.redis.exists(key):
                        keys.add(key)
        
        # Agent-based keys
        if query.agent_id:
            agent_index = f"{self.PREFIXES['index']}agent:{query.agent_id}"
            agent_keys = await self.redis.smembers(agent_index)
            for entry_id in agent_keys:
                for prefix in self.PREFIXES.values():
                    key = f"{prefix}{entry_id}"
                    if await self.redis.exists(key):
                        keys.add(key)
        
        # Tag-based keys
        for tag in query.tags:
            tag_index = f"{self.PREFIXES['index']}tag:{tag}"
            tag_keys = await self.redis.smembers(tag_index)
            for entry_id in tag_keys:
                for prefix in self.PREFIXES.values():
                    key = f"{prefix}{entry_id}"
                    if await self.redis.exists(key):
                        keys.add(key)
        
        # If no specific filters, get all keys
        if not keys and not query.session_id and not query.agent_id and not query.tags:
            for prefix in self.PREFIXES.values():
                pattern_keys = await self.redis.keys(f"{prefix}*")
                keys.update(pattern_keys)
        
        return list(keys)
    
    def _matches_query(self, entry: MemoryEntry, query: MemoryQuery) -> bool:
        """Check if entry matches query criteria."""
        # Type filter
        if query.type and entry.type != query.type:
            return False
        
        # Session filter
        if query.session_id and entry.session_id != query.session_id:
            return False
        
        # Agent filter
        if query.agent_id and entry.agent_id != query.agent_id:
            return False
        
        # Tag filter
        if query.tags:
            if not any(tag in entry.tags for tag in query.tags):
                return False
        
        # Time range filter
        if query.time_range:
            start_time, end_time = query.time_range
            if entry.timestamp < start_time or entry.timestamp > end_time:
                return False
        
        # Text search in content and metadata
        if query.query and query.query != "*":
            search_text = query.query.lower()
            content_str = json.dumps(entry.content).lower()
            metadata_str = json.dumps(entry.metadata).lower()
            tags_str = " ".join(entry.tags).lower()
            
            if (search_text not in content_str and 
                search_text not in metadata_str and 
                search_text not in tags_str):
                return False
        
        return True