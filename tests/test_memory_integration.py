#!/usr/bin/env python3
"""
Integration Tests for Memory System

Tests the complete memory and observability system integration.
"""

import asyncio
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from memory.core import (
    MemoryManager, MemoryConfig, MemoryEntry, MemoryQuery, MemoryType,
    RedisConfig, QdrantConfig, LangfuseConfig, ClickHouseConfig, EmbeddingConfig
)
from memory.tools import MemoryTool, CoordinationTool, AnalyticsTool


class TestMemorySystemIntegration:
    """Integration tests for the complete memory system."""
    
    @pytest.fixture
    async def memory_config(self):
        """Create test configuration."""
        # Use in-memory/local configurations for testing
        config = MemoryConfig(
            redis=RedisConfig(
                host="localhost",
                port=6379,
                db=1  # Use different DB for testing
            ),
            qdrant=QdrantConfig(
                host="localhost",
                port=6333,
                collection_name="test_memory",
                vector_size=384
            ),
            langfuse=LangfuseConfig(
                enabled=False  # Disable for testing
            ),
            clickhouse=ClickHouseConfig(
                host="localhost",
                port=8123,
                database="test_db"
            ),
            embedding=EmbeddingConfig(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu"
            ),
            data_retention_days=1,  # Short retention for testing
            memory_base_path=Path(tempfile.mkdtemp()),
            logs_path=Path(tempfile.mkdtemp())
        )
        return config
    
    @pytest.fixture
    async def memory_manager(self, memory_config):
        """Create and initialize memory manager."""
        manager = MemoryManager(memory_config)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.fixture
    async def test_agents(self, memory_manager):
        """Create test agents with memory tools."""
        agents = {}
        for agent_id in ["agent1", "agent2", "agent3"]:
            agents[agent_id] = {
                "memory_tool": MemoryTool(memory_manager, agent_id),
                "coordination_tool": CoordinationTool(memory_manager, agent_id)
            }
            # Set session
            session_id = "test_session_123"
            agents[agent_id]["memory_tool"].set_session(session_id)
            agents[agent_id]["coordination_tool"].set_session(session_id)
        
        return agents
    
    @pytest.mark.asyncio
    async def test_basic_memory_operations(self, memory_manager):
        """Test basic memory store/retrieve operations."""
        # Create test entry
        entry = MemoryEntry(
            id="test_entry_1",
            type=MemoryType.SESSION,
            content={"test": "data", "value": 42},
            metadata={"category": "test"},
            timestamp=datetime.utcnow(),
            agent_id="test_agent",
            session_id="test_session",
            tags=["test", "basic"]
        )
        
        # Store entry
        entry_id = await memory_manager.store(entry)
        assert entry_id == "test_entry_1"
        
        # Retrieve entry
        retrieved = await memory_manager.retrieve(entry_id, MemoryType.SESSION)
        assert retrieved is not None
        assert retrieved.content == entry.content
        assert retrieved.agent_id == entry.agent_id
        
        # Search for entry
        query = MemoryQuery(
            query="test",
            type=MemoryType.SESSION,
            agent_id="test_agent",
            tags=["test"]
        )
        
        results = await memory_manager.search(query)
        assert len(results) >= 1
        assert any(r.id == entry_id for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_tools(self, test_agents):
        """Test memory tools functionality."""
        agent1_tools = test_agents["agent1"]
        memory_tool = agent1_tools["memory_tool"]
        
        # Store knowledge
        knowledge_id = await memory_tool.store_knowledge(
            {"fact": "The sky is blue", "confidence": 0.95},
            "Basic fact about sky color",
            tags=["fact", "nature"]
        )
        assert knowledge_id is not None
        
        # Store context
        context_id = await memory_tool.store_context(
            {"current_task": "testing", "progress": 0.5},
            "task_state",
            tags=["task"]
        )
        assert context_id is not None
        
        # Search knowledge
        knowledge_results = await memory_tool.retrieve_knowledge("sky color")
        assert len(knowledge_results) >= 1
        
        # Search context
        context_results = await memory_tool.retrieve_context("task_state")
        assert len(context_results) >= 1
        
        # Test key-value storage
        await memory_tool.remember("test_key", "test_value", permanent=False)
        retrieved_value = await memory_tool.recall("test_key", permanent=False)
        assert retrieved_value == "test_value"
    
    @pytest.mark.asyncio
    async def test_agent_coordination(self, test_agents):
        """Test agent coordination features."""
        agent1_coord = test_agents["agent1"]["coordination_tool"]
        agent2_coord = test_agents["agent2"]["coordination_tool"]
        
        # Agent 1 creates handoff to Agent 2
        handoff_id = await agent1_coord.handoff_to_agent(
            "agent2",
            {"task": "process data", "deadline": "2024-01-01"},
            "task_delegation",
            "high"
        )
        assert handoff_id is not None
        
        # Agent 2 checks pending handoffs
        pending = await agent2_coord.get_pending_handoffs()
        assert len(pending) >= 1
        
        handoff = pending[0]
        assert handoff["from_agent"] == "agent1"
        assert handoff["priority"] == "high"
        
        # Agent 2 accepts handoff
        accepted = await agent2_coord.accept_handoff(
            handoff["handoff_id"],
            "Accepting task"
        )
        assert accepted is True
        
        # Agent 2 completes handoff
        completed = await agent2_coord.complete_handoff(
            handoff["handoff_id"],
            {"result": "task completed successfully"},
            "Finished processing"
        )
        assert completed is True
        
        # Test context sharing
        context_id = await agent1_coord.share_context(
            "shared_data",
            {"important": "information", "shared_by": "agent1"},
            "session"
        )
        assert context_id is not None
        
        # Agent 2 retrieves shared context
        shared_contexts = await agent2_coord.get_shared_context("shared_data")
        assert len(shared_contexts) >= 1
        assert shared_contexts[0]["context_data"]["important"] == "information"
        
        # Test status broadcasting
        status_id = await agent1_coord.broadcast_status(
            "working",
            {"current_task": "analysis", "progress": 0.75}
        )
        assert status_id is not None
        
        # Agent 2 checks agent statuses
        statuses = await agent2_coord.get_agent_status("agent1")
        assert len(statuses) >= 1
        assert statuses[0]["status"] == "working"
    
    @pytest.mark.asyncio
    async def test_analytics(self, memory_manager, test_agents):
        """Test analytics functionality."""
        analytics_tool = AnalyticsTool(memory_manager)
        
        # Generate some test data
        agent1_memory = test_agents["agent1"]["memory_tool"]
        
        # Store multiple entries
        for i in range(5):
            await agent1_memory.store_knowledge(
                {"item": i, "category": "test_data"},
                f"Test item {i}",
                tags=["test", "analytics"]
            )
            
            await agent1_memory.learn_from_interaction(
                {"interaction": f"test_{i}"},
                "success",
                0.8 + (i * 0.05)  # Increasing effectiveness
            )
        
        # Test agent performance analysis
        performance = await analytics_tool.analyze_agent_performance("agent1")
        assert performance["agent_id"] == "agent1"
        assert performance["total_activities"] >= 5
        assert performance["learning_metrics"]["learnings_created"] >= 5
        
        # Test memory usage analysis
        memory_usage = await analytics_tool.analyze_memory_usage()
        assert "memory_type_distribution" in memory_usage
        assert memory_usage["memory_type_distribution"]["semantic"] >= 5
        
        # Test learning effectiveness analysis
        learning_analysis = await analytics_tool.analyze_learning_effectiveness("agent1")
        assert learning_analysis["agent_id"] == "agent1"
        assert learning_analysis["total_learning_events"] >= 5
        assert learning_analysis["effectiveness_metrics"]["avg_effectiveness"] > 0.8
        
        # Test system health report
        health_report = await analytics_tool.generate_system_health_report()
        assert "summary" in health_report
        assert "overall_health" in health_report["summary"]
        assert health_report["recent_activity"]["total_activities"] >= 10
    
    @pytest.mark.asyncio
    async def test_semantic_memory_search(self, memory_manager):
        """Test semantic memory search functionality."""
        if not memory_manager.semantic_memory:
            pytest.skip("Semantic memory not available")
        
        # Store related entries
        entries = [
            ("Python programming", "Learn about Python syntax and features"),
            ("Machine learning", "Understanding ML algorithms and applications"),
            ("Data science", "Analysis of data using statistical methods"),
            ("Web development", "Creating websites with HTML, CSS, and JavaScript")
        ]
        
        for content, description in entries:
            entry = MemoryEntry(
                id=None,
                type=MemoryType.SEMANTIC,
                content={"topic": content, "description": description},
                metadata={"domain": "technology"},
                timestamp=datetime.utcnow(),
                agent_id="test_agent",
                tags=["knowledge", "technology"]
            )
            await memory_manager.store(entry)
        
        # Search for related content
        query = MemoryQuery(
            query="programming and development",
            type=MemoryType.SEMANTIC,
            limit=3,
            similarity_threshold=0.3
        )
        
        results = await memory_manager.search(query)
        assert len(results) >= 2  # Should find Python and Web development
        
        # Verify similarity scores
        for result in results:
            assert "similarity_score" in result.metadata
            assert result.metadata["similarity_score"] >= 0.3
    
    @pytest.mark.asyncio
    async def test_memory_lifecycle(self, memory_manager):
        """Test complete memory lifecycle including cleanup."""
        # Create entries with different timestamps
        old_time = datetime.utcnow() - timedelta(days=2)
        recent_time = datetime.utcnow()
        
        old_entry = MemoryEntry(
            id="old_entry",
            type=MemoryType.SESSION,
            content={"data": "old"},
            metadata={},
            timestamp=old_time,
            agent_id="test_agent",
            tags=["old"]
        )
        
        recent_entry = MemoryEntry(
            id="recent_entry",
            type=MemoryType.SESSION,
            content={"data": "recent"},
            metadata={},
            timestamp=recent_time,
            agent_id="test_agent",
            tags=["recent"]
        )
        
        # Store both entries
        await memory_manager.store(old_entry)
        await memory_manager.store(recent_entry)
        
        # Verify both exist
        assert await memory_manager.retrieve("old_entry") is not None
        assert await memory_manager.retrieve("recent_entry") is not None
        
        # Test deletion
        deleted = await memory_manager.delete("old_entry")
        assert deleted is True
        
        # Verify deletion
        assert await memory_manager.retrieve("old_entry") is None
        assert await memory_manager.retrieve("recent_entry") is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_manager):
        """Test concurrent memory operations."""
        # Create multiple concurrent store operations
        tasks = []
        for i in range(10):
            entry = MemoryEntry(
                id=f"concurrent_{i}",
                type=MemoryType.SESSION,
                content={"index": i, "data": f"concurrent_data_{i}"},
                metadata={"batch": "concurrent_test"},
                timestamp=datetime.utcnow(),
                agent_id=f"agent_{i % 3}",  # 3 different agents
                tags=["concurrent", "test"]
            )
            tasks.append(memory_manager.store(entry))
        
        # Execute all stores concurrently
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        
        # Verify all entries were stored
        for i in range(10):
            retrieved = await memory_manager.retrieve(f"concurrent_{i}")
            assert retrieved is not None
            assert retrieved.content["index"] == i
        
        # Test concurrent searches
        search_tasks = []
        for i in range(5):
            query = MemoryQuery(
                query="concurrent",
                tags=["concurrent"],
                limit=10
            )
            search_tasks.append(memory_manager.search(query))
        
        search_results = await asyncio.gather(*search_tasks)
        for results in search_results:
            assert len(results) >= 10
    
    @pytest.mark.asyncio
    async def test_error_handling(self, memory_manager):
        """Test error handling in memory operations."""
        # Test retrieving non-existent entry
        result = await memory_manager.retrieve("non_existent_id")
        assert result is None
        
        # Test deleting non-existent entry
        deleted = await memory_manager.delete("non_existent_id")
        assert deleted is False
        
        # Test invalid memory type in query
        with pytest.raises(ValueError):
            MemoryQuery(query="test", type="invalid_type")
    
    @pytest.mark.asyncio
    async def test_system_stats(self, memory_manager):
        """Test system statistics."""
        stats = await memory_manager.get_system_stats()
        
        assert "initialized" in stats
        assert "timestamp" in stats
        assert "subsystems" in stats
        assert stats["initialized"] is True
        
        # Check subsystem stats
        if memory_manager.session_memory:
            assert "session" in stats["subsystems"]
        
        if memory_manager.semantic_memory:
            assert "semantic" in stats["subsystems"]
        
        if memory_manager.observability:
            assert "observability" in stats["subsystems"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])