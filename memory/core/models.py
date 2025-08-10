"""
Memory Models - Shared data structures for memory system

This module contains data classes and enums used across the memory system,
extracted to prevent circular imports.
"""

from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class MemoryType(Enum):
    """Types of memory storage."""
    SESSION = "session"       # Short-term context within a task/conversation
    SEMANTIC = "semantic"     # Long-term knowledge and embeddings
    AGENT = "agent"          # Agent-specific persistent state
    TRACE = "trace"          # Observability traces and logs


@dataclass
class MemoryEntry:
    """
    Universal memory entry structure for all memory types.
    
    This structure supports all memory systems with optional fields
    for type-specific metadata.
    """
    id: str
    type: MemoryType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Semantic memory specific fields
    embedding: Optional[List[float]] = None
    similarity_score: Optional[float] = None
    
    # Session memory specific fields
    ttl: Optional[int] = None  # TTL in seconds
    
    # Trace memory specific fields
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            'id': self.id,
            'type': self.type.value,
            'content': self.content,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'agent_id': self.agent_id,
            'tags': self.tags
        }
        
        # Add optional fields if present
        if self.embedding is not None:
            data['embedding'] = self.embedding
        if self.similarity_score is not None:
            data['similarity_score'] = self.similarity_score
        if self.ttl is not None:
            data['ttl'] = self.ttl
        if self.trace_id is not None:
            data['trace_id'] = self.trace_id
        if self.span_id is not None:
            data['span_id'] = self.span_id
        if self.parent_span_id is not None:
            data['parent_span_id'] = self.parent_span_id
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            type=MemoryType(data['type']),
            content=data['content'],
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            session_id=data.get('session_id'),
            agent_id=data.get('agent_id'),
            tags=data.get('tags', []),
            embedding=data.get('embedding'),
            similarity_score=data.get('similarity_score'),
            ttl=data.get('ttl'),
            trace_id=data.get('trace_id'),
            span_id=data.get('span_id'),
            parent_span_id=data.get('parent_span_id')
        )


@dataclass
class MemoryQuery:
    """
    Query structure for searching memory entries.
    
    Supports flexible queries across all memory types with filtering
    and similarity search capabilities.
    """
    query: str
    type: Optional[MemoryType] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    limit: int = 10
    offset: int = 0
    
    # Semantic search specific fields
    similarity_threshold: float = 0.7
    include_embeddings: bool = False
    
    # Time-based filtering
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Advanced filtering
    metadata_filters: Dict[str, Any] = field(default_factory=dict)
    exclude_tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        data = {
            'query': self.query,
            'type': self.type.value if self.type else None,
            'session_id': self.session_id,
            'agent_id': self.agent_id,
            'tags': self.tags,
            'limit': self.limit,
            'offset': self.offset,
            'similarity_threshold': self.similarity_threshold,
            'include_embeddings': self.include_embeddings,
            'metadata_filters': self.metadata_filters,
            'exclude_tags': self.exclude_tags
        }
        
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
            
        return data


@dataclass
class MemoryStats:
    """Memory system statistics and metrics."""
    total_entries: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    memory_usage_mb: float = 0.0
    cache_hit_rate: float = 0.0
    avg_query_time_ms: float = 0.0
    active_sessions: int = 0
    
    # Service-specific stats
    redis_memory_mb: float = 0.0
    qdrant_collections: int = 0
    qdrant_vectors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_entries': self.total_entries,
            'entries_by_type': self.entries_by_type,
            'memory_usage_mb': self.memory_usage_mb,
            'cache_hit_rate': self.cache_hit_rate,
            'avg_query_time_ms': self.avg_query_time_ms,
            'active_sessions': self.active_sessions,
            'redis_memory_mb': self.redis_memory_mb,
            'qdrant_collections': self.qdrant_collections,
            'qdrant_vectors': self.qdrant_vectors
        }


@dataclass 
class AgentMemoryContext:
    """Context structure for agent memory operations."""
    agent_id: str
    session_id: str
    task_context: Dict[str, Any] = field(default_factory=dict)
    previous_interactions: List[MemoryEntry] = field(default_factory=list)
    relevant_knowledge: List[MemoryEntry] = field(default_factory=list)
    memory_budget: int = 1000  # Max entries to consider
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_id': self.agent_id,
            'session_id': self.session_id, 
            'task_context': self.task_context,
            'previous_interactions': [entry.to_dict() for entry in self.previous_interactions],
            'relevant_knowledge': [entry.to_dict() for entry in self.relevant_knowledge],
            'memory_budget': self.memory_budget
        }