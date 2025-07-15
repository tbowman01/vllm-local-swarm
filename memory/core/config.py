"""
Memory System Configuration

Centralized configuration for all memory and observability components.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class RedisConfig:
    """Configuration for Redis session memory."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 100
    socket_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "100")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "30"))
        )


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database."""
    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection_name: str = "agent_memory"
    vector_size: int = 1536  # OpenAI embedding size
    distance_metric: str = "cosine"
    api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'QdrantConfig':
        return cls(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333")),
            grpc_port=int(os.getenv("QDRANT_GRPC_PORT", "6334")),
            collection_name=os.getenv("QDRANT_COLLECTION", "agent_memory"),
            vector_size=int(os.getenv("QDRANT_VECTOR_SIZE", "1536")),
            distance_metric=os.getenv("QDRANT_DISTANCE", "cosine"),
            api_key=os.getenv("QDRANT_API_KEY")
        )


@dataclass
class LangfuseConfig:
    """Configuration for Langfuse observability."""
    host: str = "localhost"
    port: int = 3000
    public_key: Optional[str] = None
    secret_key: Optional[str] = None
    enabled: bool = True
    flush_interval: int = 1  # seconds
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> 'LangfuseConfig':
        return cls(
            host=os.getenv("LANGFUSE_HOST", "localhost"),
            port=int(os.getenv("LANGFUSE_PORT", "3000")),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            enabled=os.getenv("LANGFUSE_ENABLED", "true").lower() == "true",
            flush_interval=int(os.getenv("LANGFUSE_FLUSH_INTERVAL", "1")),
            max_retries=int(os.getenv("LANGFUSE_MAX_RETRIES", "3"))
        )


@dataclass
class ClickHouseConfig:
    """Configuration for ClickHouse analytics storage."""
    host: str = "localhost"
    port: int = 8123
    database: str = "langfuse"
    username: str = "default"
    password: str = ""
    secure: bool = False
    
    @classmethod
    def from_env(cls) -> 'ClickHouseConfig':
        return cls(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            database=os.getenv("CLICKHOUSE_DATABASE", "langfuse"),
            username=os.getenv("CLICKHOUSE_USERNAME", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            secure=os.getenv("CLICKHOUSE_SECURE", "false").lower() == "true"
        )


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"  # or "cuda" if available
    batch_size: int = 32
    normalize_embeddings: bool = True
    
    @classmethod
    def from_env(cls) -> 'EmbeddingConfig':
        return cls(
            model_name=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            device=os.getenv("EMBEDDING_DEVICE", "cpu"),
            batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
            normalize_embeddings=os.getenv("EMBEDDING_NORMALIZE", "true").lower() == "true"
        )


@dataclass
class MemoryConfig:
    """Complete memory system configuration."""
    redis: RedisConfig
    qdrant: QdrantConfig  
    langfuse: LangfuseConfig
    clickhouse: ClickHouseConfig
    embedding: EmbeddingConfig
    
    # General settings
    data_retention_days: int = 30
    max_session_memory_mb: int = 100
    semantic_memory_enabled: bool = True
    session_memory_enabled: bool = True
    observability_enabled: bool = True
    
    # File paths
    memory_base_path: Path = Path("./memory")
    logs_path: Path = Path("./logs")
    
    def __post_init__(self):
        """Ensure directories exist."""
        self.memory_base_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        """Create configuration from environment variables."""
        return cls(
            redis=RedisConfig.from_env(),
            qdrant=QdrantConfig.from_env(),
            langfuse=LangfuseConfig.from_env(),
            clickhouse=ClickHouseConfig.from_env(),
            embedding=EmbeddingConfig.from_env(),
            data_retention_days=int(os.getenv("MEMORY_RETENTION_DAYS", "30")),
            max_session_memory_mb=int(os.getenv("MAX_SESSION_MEMORY_MB", "100")),
            semantic_memory_enabled=os.getenv("SEMANTIC_MEMORY_ENABLED", "true").lower() == "true",
            session_memory_enabled=os.getenv("SESSION_MEMORY_ENABLED", "true").lower() == "true",
            observability_enabled=os.getenv("OBSERVABILITY_ENABLED", "true").lower() == "true",
            memory_base_path=Path(os.getenv("MEMORY_BASE_PATH", "./memory")),
            logs_path=Path(os.getenv("LOGS_PATH", "./logs"))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "redis": self.redis.__dict__,
            "qdrant": self.qdrant.__dict__,
            "langfuse": self.langfuse.__dict__,
            "clickhouse": self.clickhouse.__dict__,
            "embedding": self.embedding.__dict__,
            "data_retention_days": self.data_retention_days,
            "max_session_memory_mb": self.max_session_memory_mb,
            "semantic_memory_enabled": self.semantic_memory_enabled,
            "session_memory_enabled": self.session_memory_enabled,
            "observability_enabled": self.observability_enabled,
            "memory_base_path": str(self.memory_base_path),
            "logs_path": str(self.logs_path)
        }