#!/usr/bin/env python3
"""
Memory System API Startup Script

Starts the complete memory management system with all components.
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add the memory module to the path
sys.path.insert(0, '/app')

from memory.core import MemoryManager, MemoryConfig
from memory.tools import MemoryTool, CoordinationTool, AnalyticsTool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global memory manager
memory_manager: MemoryManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global memory_manager
    
    try:
        # Initialize memory system
        logger.info("Starting memory management system...")
        
        # Load configuration from environment
        config = MemoryConfig.from_env()
        logger.info(f"Loaded configuration: {config.to_dict()}")
        
        # Initialize memory manager
        memory_manager = MemoryManager(config)
        await memory_manager.initialize()
        
        logger.info("Memory management system started successfully")
        
        # Store in app state
        app.state.memory_manager = memory_manager
        app.state.analytics_tool = AnalyticsTool(memory_manager)
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start memory system: {e}")
        raise
    finally:
        # Shutdown
        if memory_manager:
            logger.info("Shutting down memory management system...")
            await memory_manager.shutdown()
            logger.info("Memory management system shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="vLLM Local Swarm Memory System",
    description="Memory management API for multi-agent coordination",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if not memory_manager or not memory_manager._initialized:
            raise HTTPException(status_code=503, detail="Memory system not initialized")
        
        # Get basic stats
        stats = await memory_manager.get_system_stats()
        
        return {
            "status": "healthy",
            "timestamp": stats["timestamp"].isoformat(),
            "initialized": stats["initialized"],
            "subsystems": stats["subsystems"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    try:
        stats = await memory_manager.get_system_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/agent/{agent_id}")
async def get_agent_analytics(agent_id: str, days: int = 7):
    """Get analytics for a specific agent."""
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        analytics = await app.state.analytics_tool.analyze_agent_performance(
            agent_id, (start_time, end_time)
        )
        return analytics
    except Exception as e:
        logger.error(f"Failed to get agent analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/coordination")
async def get_coordination_analytics(session_id: str = None, hours: int = 24):
    """Get coordination analytics."""
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = await app.state.analytics_tool.analyze_coordination_patterns(
            session_id, (start_time, end_time)
        )
        return analytics
    except Exception as e:
        logger.error(f"Failed to get coordination analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/memory")
async def get_memory_analytics(hours: int = 24):
    """Get memory usage analytics."""
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        analytics = await app.state.analytics_tool.analyze_memory_usage(
            (start_time, end_time)
        )
        return analytics
    except Exception as e:
        logger.error(f"Failed to get memory analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/learning")
async def get_learning_analytics(agent_id: str = None, days: int = 30):
    """Get learning effectiveness analytics."""
    try:
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        analytics = await app.state.analytics_tool.analyze_learning_effectiveness(
            agent_id, (start_time, end_time)
        )
        return analytics
    except Exception as e:
        logger.error(f"Failed to get learning analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/health")
async def get_system_health():
    """Get system health report."""
    try:
        health_report = await app.state.analytics_tool.generate_system_health_report()
        return health_report
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/store")
async def store_memory(entry_data: dict):
    """Store a memory entry."""
    try:
        from memory.core.memory_manager import MemoryEntry, MemoryType
        from datetime import datetime
        
        # Create memory entry from data
        entry = MemoryEntry(
            id=entry_data.get("id"),
            type=MemoryType(entry_data["type"]),
            content=entry_data["content"],
            metadata=entry_data.get("metadata", {}),
            timestamp=datetime.fromisoformat(entry_data["timestamp"]) if "timestamp" in entry_data else datetime.utcnow(),
            agent_id=entry_data.get("agent_id"),
            session_id=entry_data.get("session_id"),
            tags=entry_data.get("tags", [])
        )
        
        entry_id = await memory_manager.store(entry)
        return {"entry_id": entry_id, "status": "stored"}
    except Exception as e:
        logger.error(f"Failed to store memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/retrieve/{entry_id}")
async def retrieve_memory(entry_id: str, memory_type: str = None):
    """Retrieve a memory entry by ID."""
    try:
        from memory.core.memory_manager import MemoryType
        
        mem_type = MemoryType(memory_type) if memory_type else None
        entry = await memory_manager.retrieve(entry_id, mem_type)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        
        return {
            "id": entry.id,
            "type": entry.type.value,
            "content": entry.content,
            "metadata": entry.metadata,
            "timestamp": entry.timestamp.isoformat(),
            "agent_id": entry.agent_id,
            "session_id": entry.session_id,
            "tags": entry.tags
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/search")
async def search_memory(query_data: dict):
    """Search memory entries."""
    try:
        from memory.core.memory_manager import MemoryQuery, MemoryType
        from datetime import datetime
        
        # Create query from data
        query = MemoryQuery(
            query=query_data["query"],
            type=MemoryType(query_data["type"]) if query_data.get("type") else None,
            agent_id=query_data.get("agent_id"),
            session_id=query_data.get("session_id"),
            tags=query_data.get("tags", []),
            limit=query_data.get("limit", 10),
            similarity_threshold=query_data.get("similarity_threshold", 0.7)
        )
        
        # Add time range if provided
        if query_data.get("time_range"):
            start_str, end_str = query_data["time_range"]
            query.time_range = (
                datetime.fromisoformat(start_str),
                datetime.fromisoformat(end_str)
            )
        
        results = await memory_manager.search(query)
        
        # Format results
        formatted_results = []
        for entry in results:
            formatted_results.append({
                "id": entry.id,
                "type": entry.type.value,
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp.isoformat(),
                "agent_id": entry.agent_id,
                "session_id": entry.session_id,
                "tags": entry.tags
            })
        
        return {
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        logger.error(f"Failed to search memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    # Setup signal handlers
    setup_signal_handlers()
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8090"))
    workers = int(os.getenv("WORKERS", "1"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logger.info(f"Starting Memory System API on {host}:{port}")
    
    # Run the application
    uvicorn.run(
        "start-memory-api:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        reload=False,
        access_log=True
    )