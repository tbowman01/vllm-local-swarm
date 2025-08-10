#!/usr/bin/env python3
"""
Semantic Memory Search System
============================

Advanced semantic search capabilities for the memory system using:
- Vector embeddings for semantic similarity
- Hybrid search combining semantic and keyword matching
- Context-aware memory retrieval
- Learning-based relevance scoring
"""

import asyncio
import logging
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib

try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    print("Installing semantic search dependencies...")
    import subprocess
    subprocess.run(["pip", "install", "sentence-transformers", "faiss-cpu"], check=True)
    from sentence_transformers import SentenceTransformer
    import faiss

from .models import MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class SearchMode(Enum):
    """Search modes for semantic search"""
    SEMANTIC = "semantic"          # Pure vector similarity
    KEYWORD = "keyword"            # Traditional keyword matching
    HYBRID = "hybrid"              # Combined semantic + keyword
    CONTEXTUAL = "contextual"      # Context-aware search
    LEARNING = "learning"          # Learning-based relevance


@dataclass
class SearchQuery:
    """Search query structure"""
    query: str
    mode: SearchMode = SearchMode.HYBRID
    max_results: int = 10
    min_similarity: float = 0.5
    memory_types: List[MemoryType] = field(default_factory=list)
    time_range: Optional[Tuple[datetime, datetime]] = None
    agent_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    boost_recent: bool = True
    include_metadata: bool = True


@dataclass 
class SearchResult:
    """Search result structure"""
    memory_entry: MemoryEntry
    similarity_score: float
    relevance_score: float
    search_rank: int
    match_reasons: List[str]
    snippet: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticSearchEngine:
    """
    Advanced semantic search engine for memory retrieval
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_model = None
        self.index = None
        self.memory_entries: Dict[str, MemoryEntry] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        
        # Search statistics
        self.search_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'avg_results_per_search': 0.0,
            'popular_queries': {},
            'performance_metrics': {
                'avg_search_time': 0.0,
                'index_size': 0,
                'embedding_cache_size': 0
            }
        }
        
        # Learning components
        self.query_feedback: Dict[str, List[Dict[str, Any]]] = {}
        self.relevance_learning = RelevanceLearner()
        
        self._initialized = False
        
    async def initialize(self):
        """Initialize the semantic search engine"""
        if self._initialized:
            return
            
        logger.info(f"🧠 Initializing Semantic Search Engine with model: {self.model_name}")
        
        try:
            # Load sentence transformer model
            self.embedding_model = SentenceTransformer(self.model_name)
            
            # Initialize FAISS index (will be built when entries are added)
            self.index = None
            
            self._initialized = True
            logger.info("✅ Semantic Search Engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Semantic Search Engine: {e}")
            raise
            
    async def add_memory(self, memory_entry: MemoryEntry):
        """Add memory entry to search index"""
        if not self._initialized:
            await self.initialize()
            
        try:
            # Store memory entry
            self.memory_entries[memory_entry.id] = memory_entry
            
            # Generate embedding for searchable content
            searchable_content = self._extract_searchable_content(memory_entry)
            embedding = await self._generate_embedding(searchable_content)
            self.embeddings[memory_entry.id] = embedding
            
            # Rebuild index if needed
            await self._rebuild_index_if_needed()
            
        except Exception as e:
            logger.error(f"❌ Error adding memory to search index: {e}")
            
    async def remove_memory(self, memory_id: str):
        """Remove memory entry from search index"""
        if memory_id in self.memory_entries:
            del self.memory_entries[memory_id]
            
        if memory_id in self.embeddings:
            del self.embeddings[memory_id]
            
        # Rebuild index
        await self._rebuild_index_if_needed()
        
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search"""
        if not self._initialized:
            await self.initialize()
            
        start_time = datetime.now()
        
        try:
            self.search_stats['total_searches'] += 1
            
            # Track popular queries
            query_hash = hashlib.md5(query.query.encode()).hexdigest()[:8]
            if query_hash not in self.search_stats['popular_queries']:
                self.search_stats['popular_queries'][query_hash] = {
                    'query': query.query[:50],
                    'count': 0
                }
            self.search_stats['popular_queries'][query_hash]['count'] += 1
            
            # Execute search based on mode
            if query.mode == SearchMode.SEMANTIC:
                results = await self._semantic_search(query)
            elif query.mode == SearchMode.KEYWORD:
                results = await self._keyword_search(query)
            elif query.mode == SearchMode.HYBRID:
                results = await self._hybrid_search(query)
            elif query.mode == SearchMode.CONTEXTUAL:
                results = await self._contextual_search(query)
            elif query.mode == SearchMode.LEARNING:
                results = await self._learning_search(query)
            else:
                results = await self._hybrid_search(query)
                
            # Post-process results
            results = await self._post_process_results(query, results)
            
            # Update statistics
            search_time = (datetime.now() - start_time).total_seconds()
            self._update_search_stats(len(results), search_time)
            
            if results:
                self.search_stats['successful_searches'] += 1
                
            return results
            
        except Exception as e:
            logger.error(f"❌ Error during search: {e}")
            return []
            
    async def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform pure semantic vector search"""
        if not self.index or len(self.embeddings) == 0:
            return []
            
        # Generate query embedding
        query_embedding = await self._generate_embedding(query.query)
        
        # Search in FAISS index
        k = min(query.max_results * 2, len(self.embeddings))  # Get more candidates
        similarities, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'), k
        )
        
        results = []
        memory_ids = list(self.embeddings.keys())
        
        for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
            if idx == -1 or similarity < query.min_similarity:
                continue
                
            memory_id = memory_ids[idx]
            memory_entry = self.memory_entries[memory_id]
            
            # Apply filters
            if not self._passes_filters(memory_entry, query):
                continue
                
            results.append(SearchResult(
                memory_entry=memory_entry,
                similarity_score=float(similarity),
                relevance_score=float(similarity),
                search_rank=i,
                match_reasons=["semantic_similarity"],
                snippet=self._generate_snippet(memory_entry, query.query)
            ))
            
        return results
        
    async def _keyword_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform keyword-based search"""
        query_terms = query.query.lower().split()
        results = []
        
        for i, (memory_id, memory_entry) in enumerate(self.memory_entries.items()):
            if not self._passes_filters(memory_entry, query):
                continue
                
            # Calculate keyword match score
            content = self._extract_searchable_content(memory_entry).lower()
            
            matches = 0
            matched_terms = []
            for term in query_terms:
                if term in content:
                    matches += content.count(term)
                    matched_terms.append(term)
                    
            if matches > 0:
                # Simple TF-IDF-like scoring
                score = matches / len(query_terms)
                
                results.append(SearchResult(
                    memory_entry=memory_entry,
                    similarity_score=score,
                    relevance_score=score,
                    search_rank=i,
                    match_reasons=[f"keyword_match: {', '.join(matched_terms)}"],
                    snippet=self._generate_snippet(memory_entry, query.query)
                ))
                
        # Sort by score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:query.max_results]
        
    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform hybrid semantic + keyword search"""
        # Get semantic results
        semantic_query = SearchQuery(
            query=query.query,
            mode=SearchMode.SEMANTIC,
            max_results=query.max_results,
            min_similarity=query.min_similarity * 0.8,  # Lower threshold for hybrid
            memory_types=query.memory_types,
            time_range=query.time_range,
            agent_id=query.agent_id
        )
        semantic_results = await self._semantic_search(semantic_query)
        
        # Get keyword results
        keyword_query = SearchQuery(
            query=query.query,
            mode=SearchMode.KEYWORD,
            max_results=query.max_results,
            memory_types=query.memory_types,
            time_range=query.time_range,
            agent_id=query.agent_id
        )
        keyword_results = await self._keyword_search(keyword_query)
        
        # Combine and re-rank results
        return self._combine_results(semantic_results, keyword_results, query)
        
    async def _contextual_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform context-aware search"""
        # Start with hybrid search
        base_results = await self._hybrid_search(query)
        
        # Apply contextual boosting
        context = query.context
        
        for result in base_results:
            context_boost = 0.0
            
            # Boost based on context similarity
            if 'domain' in context:
                if context['domain'] in str(result.memory_entry.content):
                    context_boost += 0.1
                    result.match_reasons.append(f"domain_match: {context['domain']}")
                    
            if 'task_type' in context:
                if context['task_type'] in str(result.memory_entry.content):
                    context_boost += 0.1
                    result.match_reasons.append(f"task_type_match: {context['task_type']}")
                    
            if 'user_id' in context and hasattr(result.memory_entry, 'user_id'):
                if context['user_id'] == result.memory_entry.user_id:
                    context_boost += 0.15
                    result.match_reasons.append("user_context_match")
                    
            # Apply time-based boosting
            if query.boost_recent and hasattr(result.memory_entry, 'created_at'):
                age_hours = (datetime.now() - result.memory_entry.created_at).total_seconds() / 3600
                if age_hours < 24:
                    time_boost = 0.1 * (1 - age_hours / 24)
                    context_boost += time_boost
                    result.match_reasons.append("recent_boost")
                    
            # Update relevance score
            result.relevance_score = min(1.0, result.similarity_score + context_boost)
            
        # Re-sort by relevance
        base_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return base_results[:query.max_results]
        
    async def _learning_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform learning-based search with relevance feedback"""
        # Start with contextual search
        base_results = await self._contextual_search(query)
        
        # Apply learned relevance adjustments
        query_signature = self._generate_query_signature(query)
        
        if query_signature in self.query_feedback:
            feedback_data = self.query_feedback[query_signature]
            
            # Adjust scores based on historical feedback
            for result in base_results:
                memory_id = result.memory_entry.id
                adjustment = self.relevance_learning.get_relevance_adjustment(
                    query_signature, memory_id, feedback_data
                )
                
                if adjustment != 0:
                    result.relevance_score += adjustment
                    result.match_reasons.append(f"learning_adjustment: {adjustment:+.2f}")
                    
        # Re-sort by adjusted relevance
        base_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return base_results[:query.max_results]
        
    def _combine_results(self, semantic_results: List[SearchResult], 
                        keyword_results: List[SearchResult], 
                        query: SearchQuery) -> List[SearchResult]:
        """Combine semantic and keyword results with fusion scoring"""
        
        # Create unified result set
        combined_results = {}
        
        # Add semantic results (weight: 0.7)
        for result in semantic_results:
            memory_id = result.memory_entry.id
            combined_results[memory_id] = result
            result.relevance_score = result.similarity_score * 0.7
            
        # Add/update with keyword results (weight: 0.3)
        for result in keyword_results:
            memory_id = result.memory_entry.id
            
            if memory_id in combined_results:
                # Combine scores
                existing = combined_results[memory_id]
                existing.relevance_score += result.similarity_score * 0.3
                existing.match_reasons.extend(result.match_reasons)
                existing.match_reasons = list(set(existing.match_reasons))  # Remove duplicates
            else:
                # Add as keyword-only result
                result.relevance_score = result.similarity_score * 0.3
                combined_results[memory_id] = result
                
        # Convert to list and sort
        results = list(combined_results.values())
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(results):
            result.search_rank = i
            
        return results[:query.max_results]
        
    def _passes_filters(self, memory_entry: MemoryEntry, query: SearchQuery) -> bool:
        """Check if memory entry passes query filters"""
        
        # Memory type filter
        if query.memory_types and memory_entry.type not in query.memory_types:
            return False
            
        # Time range filter
        if query.time_range and hasattr(memory_entry, 'created_at'):
            start_time, end_time = query.time_range
            if not (start_time <= memory_entry.created_at <= end_time):
                return False
                
        # Agent ID filter
        if query.agent_id and hasattr(memory_entry, 'agent_id'):
            if memory_entry.agent_id != query.agent_id:
                return False
                
        return True
        
    def _extract_searchable_content(self, memory_entry: MemoryEntry) -> str:
        """Extract searchable content from memory entry"""
        content_parts = []
        
        # Add main content
        if hasattr(memory_entry, 'content'):
            if isinstance(memory_entry.content, dict):
                # Extract text from dict content
                content_parts.append(json.dumps(memory_entry.content))
            else:
                content_parts.append(str(memory_entry.content))
                
        # Add metadata
        if hasattr(memory_entry, 'metadata') and memory_entry.metadata:
            content_parts.append(json.dumps(memory_entry.metadata))
            
        # Add description if available
        if hasattr(memory_entry, 'description') and memory_entry.description:
            content_parts.append(memory_entry.description)
            
        return " ".join(content_parts)
        
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")
            
        # Truncate text if too long
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
            
        embedding = self.embedding_model.encode(text)
        return embedding.astype('float32')
        
    async def _rebuild_index_if_needed(self):
        """Rebuild FAISS index if needed"""
        if len(self.embeddings) == 0:
            self.index = None
            return
            
        # Create new index
        embedding_dim = list(self.embeddings.values())[0].shape[0]
        self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
        
        # Add embeddings to index
        embeddings_matrix = np.vstack(list(self.embeddings.values()))
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_matrix)
        
        self.index.add(embeddings_matrix)
        
        self.search_stats['performance_metrics']['index_size'] = len(self.embeddings)
        self.search_stats['performance_metrics']['embedding_cache_size'] = len(self.embeddings)
        
    def _generate_snippet(self, memory_entry: MemoryEntry, query: str, max_length: int = 200) -> str:
        """Generate relevant snippet from memory entry"""
        content = self._extract_searchable_content(memory_entry)
        
        if len(content) <= max_length:
            return content
            
        # Find best snippet containing query terms
        query_terms = query.lower().split()
        content_lower = content.lower()
        
        best_pos = 0
        max_matches = 0
        
        # Find position with most query term matches
        for i in range(0, len(content) - max_length, 20):
            snippet = content_lower[i:i + max_length]
            matches = sum(1 for term in query_terms if term in snippet)
            
            if matches > max_matches:
                max_matches = matches
                best_pos = i
                
        snippet = content[best_pos:best_pos + max_length]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(content):
            snippet = snippet + "..."
            
        return snippet
        
    def _generate_query_signature(self, query: SearchQuery) -> str:
        """Generate signature for query to track feedback"""
        signature_parts = [
            query.query.lower().strip(),
            str(sorted(query.memory_types) if query.memory_types else ""),
            query.agent_id or "",
            str(sorted(query.context.items()) if query.context else "")
        ]
        
        signature = "|".join(signature_parts)
        return hashlib.md5(signature.encode()).hexdigest()[:16]
        
    async def _post_process_results(self, query: SearchQuery, results: List[SearchResult]) -> List[SearchResult]:
        """Post-process search results"""
        
        # Add metadata if requested
        if query.include_metadata:
            for result in results:
                result.metadata = {
                    'search_mode': query.mode.value,
                    'query_length': len(query.query),
                    'result_age': self._calculate_age(result.memory_entry),
                    'content_length': len(self._extract_searchable_content(result.memory_entry))
                }
                
        # Ensure results are within similarity threshold
        filtered_results = [
            result for result in results 
            if result.similarity_score >= query.min_similarity
        ]
        
        return filtered_results
        
    def _calculate_age(self, memory_entry: MemoryEntry) -> Optional[str]:
        """Calculate age of memory entry"""
        if not hasattr(memory_entry, 'created_at') or not memory_entry.created_at:
            return None
            
        age = datetime.now() - memory_entry.created_at
        
        if age.days > 0:
            return f"{age.days} days"
        elif age.seconds > 3600:
            return f"{age.seconds // 3600} hours"
        else:
            return f"{age.seconds // 60} minutes"
            
    def _update_search_stats(self, result_count: int, search_time: float):
        """Update search statistics"""
        stats = self.search_stats
        
        # Update averages
        total_searches = stats['total_searches']
        
        # Running average for results per search
        stats['avg_results_per_search'] = (
            (stats['avg_results_per_search'] * (total_searches - 1) + result_count) / 
            total_searches
        )
        
        # Running average for search time
        current_avg_time = stats['performance_metrics']['avg_search_time']
        stats['performance_metrics']['avg_search_time'] = (
            (current_avg_time * (total_searches - 1) + search_time) / 
            total_searches
        )
        
    async def record_feedback(self, query: SearchQuery, result_feedback: List[Dict[str, Any]]):
        """Record user feedback for search results to improve future searches"""
        query_signature = self._generate_query_signature(query)
        
        if query_signature not in self.query_feedback:
            self.query_feedback[query_signature] = []
            
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query.query,
            'feedback': result_feedback
        }
        
        self.query_feedback[query_signature].append(feedback_entry)
        
        # Train relevance learner
        await self.relevance_learning.train_from_feedback(query_signature, result_feedback)
        
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get comprehensive search statistics"""
        stats = self.search_stats.copy()
        
        # Add current state info
        stats['current_state'] = {
            'total_memories': len(self.memory_entries),
            'embeddings_cached': len(self.embeddings),
            'index_built': self.index is not None,
            'feedback_queries': len(self.query_feedback)
        }
        
        # Top queries
        if stats['popular_queries']:
            sorted_queries = sorted(
                stats['popular_queries'].items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            stats['top_queries'] = [
                {'query': q[1]['query'], 'count': q[1]['count']}
                for q in sorted_queries[:10]
            ]
            
        return stats


class RelevanceLearner:
    """
    Machine learning component for improving search relevance
    """
    
    def __init__(self):
        self.relevance_adjustments: Dict[str, Dict[str, float]] = {}
        self.feedback_history: List[Dict[str, Any]] = []
        
    async def train_from_feedback(self, query_signature: str, feedback: List[Dict[str, Any]]):
        """Train relevance model from user feedback"""
        
        for fb in feedback:
            memory_id = fb.get('memory_id')
            relevance = fb.get('relevance', 0.0)  # -1 to 1 scale
            
            if memory_id:
                if query_signature not in self.relevance_adjustments:
                    self.relevance_adjustments[query_signature] = {}
                    
                # Simple learning: exponential moving average
                current = self.relevance_adjustments[query_signature].get(memory_id, 0.0)
                alpha = 0.3  # Learning rate
                
                new_adjustment = current * (1 - alpha) + relevance * alpha * 0.1
                self.relevance_adjustments[query_signature][memory_id] = new_adjustment
                
        # Store feedback history
        self.feedback_history.append({
            'query_signature': query_signature,
            'feedback': feedback,
            'timestamp': datetime.now().isoformat()
        })
        
        # Limit history size
        if len(self.feedback_history) > 1000:
            self.feedback_history = self.feedback_history[-800:]
            
    def get_relevance_adjustment(self, query_signature: str, memory_id: str, 
                               feedback_data: List[Dict[str, Any]]) -> float:
        """Get learned relevance adjustment for memory item"""
        
        if query_signature in self.relevance_adjustments:
            adjustments = self.relevance_adjustments[query_signature]
            return adjustments.get(memory_id, 0.0)
            
        return 0.0


# Example usage and testing
async def test_semantic_search():
    """Test the semantic search system"""
    
    # Initialize search engine
    search_engine = SemanticSearchEngine()
    await search_engine.initialize()
    
    # Add some test memories
    test_memories = [
        MemoryEntry(
            id="mem_1",
            type=MemoryType.SESSION,
            content="Python programming tutorial for beginners",
            created_at=datetime.now() - timedelta(hours=1)
        ),
        MemoryEntry(
            id="mem_2", 
            type=MemoryType.SEMANTIC,
            content="Machine learning algorithms and neural networks",
            created_at=datetime.now() - timedelta(hours=2)
        ),
        MemoryEntry(
            id="mem_3",
            type=MemoryType.AGENT,
            content="Database design and SQL query optimization",
            created_at=datetime.now() - timedelta(minutes=30)
        )
    ]
    
    for memory in test_memories:
        await search_engine.add_memory(memory)
        
    # Test different search modes
    test_queries = [
        SearchQuery("python programming", SearchMode.SEMANTIC),
        SearchQuery("machine learning", SearchMode.KEYWORD),
        SearchQuery("database SQL", SearchMode.HYBRID),
        SearchQuery("tutorial", SearchMode.CONTEXTUAL, context={"domain": "programming"})
    ]
    
    for query in test_queries:
        results = await search_engine.search(query)
        print(f"\nQuery: '{query.query}' ({query.mode.value})")
        print(f"Results: {len(results)}")
        
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.snippet[:60]}...")
            print(f"     Score: {result.relevance_score:.3f}")
            print(f"     Reasons: {', '.join(result.match_reasons)}")
            
    # Print statistics
    stats = search_engine.get_search_statistics()
    print(f"\nSearch Statistics:")
    print(f"  Total searches: {stats['total_searches']}")
    print(f"  Avg results per search: {stats['avg_results_per_search']:.1f}")
    print(f"  Avg search time: {stats['performance_metrics']['avg_search_time']:.3f}s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_semantic_search())