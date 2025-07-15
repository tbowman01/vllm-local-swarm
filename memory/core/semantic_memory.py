"""
Semantic Memory - Vector database-based long-term knowledge storage

Handles semantic memory for knowledge retrieval across sessions using
vector embeddings and similarity search.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import asdict

import numpy as np
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from .config import QdrantConfig, EmbeddingConfig
from .memory_manager import MemoryEntry, MemoryQuery, MemoryType

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Handles text embedding generation for semantic search.
    """
    
    def __init__(self, config: EmbeddingConfig):
        """Initialize embedding generator."""
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.EmbeddingGenerator")
        self.model = None
        
    async def initialize(self) -> None:
        """Initialize the embedding model."""
        try:
            self.logger.info(f"Loading embedding model: {self.config.model_name}")
            
            # Load model in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None, 
                lambda: SentenceTransformer(
                    self.config.model_name,
                    device=self.config.device
                )
            )
            
            self.logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            List of floats representing the embedding
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    [text],
                    normalize_embeddings=self.config.normalize_embeddings,
                    batch_size=1
                )[0]
            )
            
            return embedding.tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embeddings
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            # Generate embeddings in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    texts,
                    normalize_embeddings=self.config.normalize_embeddings,
                    batch_size=self.config.batch_size
                )
            )
            
            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            self.logger.error(f"Failed to generate batch embeddings: {e}")
            raise


class SemanticMemory:
    """
    Vector database-based semantic memory for long-term knowledge storage.
    
    Features:
    - Vector similarity search
    - Knowledge persistence across sessions
    - Semantic clustering and organization
    - Cross-session learning and retrieval
    """
    
    def __init__(self, qdrant_config: QdrantConfig, embedding_config: EmbeddingConfig):
        """Initialize semantic memory."""
        self.qdrant_config = qdrant_config
        self.embedding_config = embedding_config
        self.logger = logging.getLogger(f"{__name__}.SemanticMemory")
        
        # Components
        self.client: Optional[QdrantClient] = None
        self.embedding_generator: Optional[EmbeddingGenerator] = None
        
        # Collection settings
        self.collection_name = qdrant_config.collection_name
        self.vector_size = qdrant_config.vector_size
        
    async def initialize(self) -> None:
        """Initialize Qdrant client and embedding generator."""
        try:
            self.logger.info("Initializing semantic memory...")
            
            # Initialize Qdrant client
            self.client = QdrantClient(
                host=self.qdrant_config.host,
                port=self.qdrant_config.port,
                api_key=self.qdrant_config.api_key
            )
            
            # Initialize embedding generator
            self.embedding_generator = EmbeddingGenerator(self.embedding_config)
            await self.embedding_generator.initialize()
            
            # Setup collection
            await self._setup_collection()
            
            self.logger.info("Semantic memory initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize semantic memory: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Shutdown semantic memory."""
        if self.client:
            self.client.close()
        self.logger.info("Semantic memory shutdown complete")
    
    async def store(self, entry: MemoryEntry) -> str:
        """
        Store memory entry with vector embedding.
        
        Args:
            entry: Memory entry to store
            
        Returns:
            str: Entry ID
        """
        if not self.client or not self.embedding_generator:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # Generate text for embedding
            text_content = self._extract_text_content(entry)
            
            # Generate embedding
            embedding = await self.embedding_generator.generate_embedding(text_content)
            
            # Prepare point for Qdrant
            point = PointStruct(
                id=entry.id,
                vector=embedding,
                payload={
                    "id": entry.id,
                    "type": entry.type.value,
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_id": entry.agent_id,
                    "session_id": entry.session_id,
                    "tags": entry.tags,
                    "text_content": text_content,
                    "embedding_model": self.embedding_config.model_name
                }
            )
            
            # Store in Qdrant
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
            )
            
            self.logger.debug(f"Stored semantic memory entry: {entry.id}")
            return entry.id
            
        except Exception as e:
            self.logger.error(f"Failed to store semantic memory entry {entry.id}: {e}")
            raise
    
    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve memory entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            MemoryEntry or None if not found
        """
        if not self.client:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # Retrieve from Qdrant
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[entry_id]
                )
            )
            
            if not result:
                return None
            
            # Convert back to MemoryEntry
            point = result[0]
            return self._point_to_memory_entry(point)
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve semantic memory entry {entry_id}: {e}")
            raise
    
    async def search(self, query: MemoryQuery) -> List[MemoryEntry]:
        """
        Search memory entries using semantic similarity.
        
        Args:
            query: Search query
            
        Returns:
            List of similar memory entries
        """
        if not self.client or not self.embedding_generator:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_embedding(query.query)
            
            # Prepare filters
            filter_conditions = self._build_filter(query)
            
            # Search in Qdrant
            loop = asyncio.get_event_loop()
            search_result = await loop.run_in_executor(
                None,
                lambda: self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    query_filter=filter_conditions,
                    limit=query.limit,
                    score_threshold=query.similarity_threshold
                )
            )
            
            # Convert results to MemoryEntry objects
            results = []
            for scored_point in search_result:
                entry = self._point_to_memory_entry(scored_point)
                if entry:
                    # Add similarity score to metadata
                    entry.metadata["similarity_score"] = scored_point.score
                    results.append(entry)
            
            self.logger.debug(f"Semantic search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search semantic memory: {e}")
            raise
    
    async def search_similar(self, entry_id: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Find entries similar to a given entry.
        
        Args:
            entry_id: ID of the reference entry
            limit: Maximum number of results
            
        Returns:
            List of similar entries
        """
        if not self.client:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # Get the reference entry vector
            loop = asyncio.get_event_loop()
            points = await loop.run_in_executor(
                None,
                lambda: self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[entry_id],
                    with_vectors=True
                )
            )
            
            if not points:
                return []
            
            reference_vector = points[0].vector
            
            # Search for similar entries
            search_result = await loop.run_in_executor(
                None,
                lambda: self.client.search(
                    collection_name=self.collection_name,
                    query_vector=reference_vector,
                    limit=limit + 1  # +1 to exclude the reference entry itself
                )
            )
            
            # Convert results and exclude the reference entry
            results = []
            for scored_point in search_result:
                if scored_point.id != entry_id:
                    entry = self._point_to_memory_entry(scored_point)
                    if entry:
                        entry.metadata["similarity_score"] = scored_point.score
                        results.append(entry)
            
            return results[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to find similar entries for {entry_id}: {e}")
            raise
    
    async def delete(self, entry_id: str) -> bool:
        """
        Delete memory entry.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if not self.client:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # Delete from Qdrant
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=[entry_id]
                    )
                )
            )
            
            # Check if deletion was successful
            deleted = result.status == models.UpdateStatus.COMPLETED
            
            if deleted:
                self.logger.debug(f"Deleted semantic memory entry: {entry_id}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete semantic memory entry {entry_id}: {e}")
            raise
    
    async def get_knowledge_clusters(self, num_clusters: int = 10) -> List[Dict[str, Any]]:
        """
        Get knowledge clusters for visualization and analysis.
        
        Args:
            num_clusters: Number of clusters to return
            
        Returns:
            List of cluster information
        """
        if not self.client:
            raise RuntimeError("Semantic memory not initialized")
        
        try:
            # This is a simplified clustering approach
            # In a production system, you might want to use more sophisticated clustering
            
            # Get all points with vectors
            loop = asyncio.get_event_loop()
            points = await loop.run_in_executor(
                None,
                lambda: self.client.scroll(
                    collection_name=self.collection_name,
                    with_vectors=True,
                    limit=1000  # Limit for performance
                )[0]
            )
            
            if not points:
                return []
            
            # Simple clustering based on tags and content types
            clusters = {}
            for point in points:
                payload = point.payload
                tags = payload.get("tags", [])
                entry_type = payload.get("type", "unknown")
                agent_id = payload.get("agent_id", "unknown")
                
                # Create cluster key
                cluster_key = f"{entry_type}_{agent_id}"
                if tags:
                    cluster_key += f"_{'_'.join(sorted(tags[:2]))}"  # Top 2 tags
                
                if cluster_key not in clusters:
                    clusters[cluster_key] = {
                        "cluster_id": cluster_key,
                        "type": entry_type,
                        "agent_id": agent_id,
                        "tags": tags,
                        "entries": [],
                        "count": 0
                    }
                
                clusters[cluster_key]["entries"].append(point.id)
                clusters[cluster_key]["count"] += 1
            
            # Sort by count and return top clusters
            sorted_clusters = sorted(
                clusters.values(),
                key=lambda x: x["count"],
                reverse=True
            )
            
            return sorted_clusters[:num_clusters]
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge clusters: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get semantic memory statistics.
        
        Returns:
            Dict containing statistics
        """
        if not self.client:
            return {"error": "Qdrant client not initialized"}
        
        try:
            # Get collection info
            loop = asyncio.get_event_loop()
            collection_info = await loop.run_in_executor(
                None,
                lambda: self.client.get_collection(self.collection_name)
            )
            
            # Get basic stats
            stats = {
                "collection_name": self.collection_name,
                "vector_size": self.vector_size,
                "total_points": collection_info.points_count,
                "indexed_points": collection_info.indexed_vectors_count,
                "embedding_model": self.embedding_config.model_name,
                "distance_metric": self.qdrant_config.distance_metric
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting semantic memory stats: {e}")
            return {"error": str(e)}
    
    async def _setup_collection(self) -> None:
        """Setup Qdrant collection if it doesn't exist."""
        try:
            loop = asyncio.get_event_loop()
            
            # Check if collection exists
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.client.get_collection(self.collection_name)
                )
                self.logger.info(f"Collection {self.collection_name} already exists")
                return
            except Exception:
                # Collection doesn't exist, create it
                pass
            
            # Create collection
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "dot": Distance.DOT
            }
            
            distance = distance_map.get(
                self.qdrant_config.distance_metric.lower(),
                Distance.COSINE
            )
            
            await loop.run_in_executor(
                None,
                lambda: self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=distance
                    )
                )
            )
            
            self.logger.info(f"Created collection {self.collection_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to setup collection: {e}")
            raise
    
    def _extract_text_content(self, entry: MemoryEntry) -> str:
        """Extract text content from memory entry for embedding."""
        text_parts = []
        
        # Add content as text
        if isinstance(entry.content, str):
            text_parts.append(entry.content)
        elif isinstance(entry.content, dict):
            # Extract text fields from dict
            for key, value in entry.content.items():
                if isinstance(value, str):
                    text_parts.append(f"{key}: {value}")
        else:
            text_parts.append(str(entry.content))
        
        # Add metadata text
        for key, value in entry.metadata.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
        
        # Add tags
        if entry.tags:
            text_parts.append("Tags: " + ", ".join(entry.tags))
        
        # Add agent and session info
        if entry.agent_id:
            text_parts.append(f"Agent: {entry.agent_id}")
        
        if entry.session_id:
            text_parts.append(f"Session: {entry.session_id}")
        
        return " ".join(text_parts)
    
    def _point_to_memory_entry(self, point) -> Optional[MemoryEntry]:
        """Convert Qdrant point to MemoryEntry."""
        try:
            payload = point.payload
            
            return MemoryEntry(
                id=payload["id"],
                type=MemoryType(payload["type"]),
                content=payload["content"],
                metadata=payload["metadata"],
                timestamp=datetime.fromisoformat(payload["timestamp"]),
                agent_id=payload.get("agent_id"),
                session_id=payload.get("session_id"),
                tags=payload.get("tags", [])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert point to memory entry: {e}")
            return None
    
    def _build_filter(self, query: MemoryQuery) -> Optional[models.Filter]:
        """Build Qdrant filter from query."""
        conditions = []
        
        # Type filter
        if query.type:
            conditions.append(
                models.FieldCondition(
                    key="type",
                    match=models.MatchValue(value=query.type.value)
                )
            )
        
        # Agent filter
        if query.agent_id:
            conditions.append(
                models.FieldCondition(
                    key="agent_id",
                    match=models.MatchValue(value=query.agent_id)
                )
            )
        
        # Session filter
        if query.session_id:
            conditions.append(
                models.FieldCondition(
                    key="session_id",
                    match=models.MatchValue(value=query.session_id)
                )
            )
        
        # Tag filters
        for tag in query.tags:
            conditions.append(
                models.FieldCondition(
                    key="tags",
                    match=models.MatchValue(value=tag)
                )
            )
        
        # Time range filter
        if query.time_range:
            start_time, end_time = query.time_range
            conditions.append(
                models.FieldCondition(
                    key="timestamp",
                    range=models.Range(
                        gte=start_time.isoformat(),
                        lte=end_time.isoformat()
                    )
                )
            )
        
        if conditions:
            return models.Filter(must=conditions)
        
        return None