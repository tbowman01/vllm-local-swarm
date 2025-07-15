#!/usr/bin/env python3
"""
Memory API Server for vLLM Local Swarm

Provides REST API for memory operations across the swarm.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Add memory path
sys.path.insert(0, "/app/memory")

from core.memory_manager import MemoryManager, MemoryEntry, MemoryType, MemoryQuery
from core.session_memory import SessionMemory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_PORT = int(os.getenv("API_PORT", "8003"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Initialize global memory manager
memory_manager = MemoryManager()

# FastAPI app
app = FastAPI(title="Memory API Service", version="1.0.0")

# Request/Response models
class MemoryStoreRequest(BaseModel):
    key: str
    value: Any
    memory_type: str = "session"
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class MemoryRetrieveRequest(BaseModel):
    key: str
    memory_type: str = "session"

class MemorySearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    limit: int = 10
    tags: Optional[List[str]] = None

class MemoryResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: str

class SessionCreateRequest(BaseModel):
    session_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    success: bool

@app.on_event("startup")
async def startup_event():
    """Initialize memory manager on startup"""
    try:
        await memory_manager.initialize()
        logger.info("Memory manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize memory manager: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await memory_manager.shutdown()
        logger.info("Memory manager shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = await memory_manager.get_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory_stats": stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/memory/store")
async def store_memory(request: MemoryStoreRequest):
    """Store a memory entry"""
    try:
        # Convert string memory type to enum
        memory_type = MemoryType(request.memory_type.upper())
        
        # Create memory entry
        entry = MemoryEntry(
            id=request.key,
            type=memory_type,
            content=request.value,
            metadata=request.metadata or {},
            timestamp=datetime.now(),
            session_id=request.session_id,
            agent_id=request.agent_id,
            tags=request.tags or []
        )
        
        # Store entry
        entry_id = await memory_manager.store(entry)
        
        return MemoryResponse(
            success=True,
            data={"entry_id": entry_id},
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Memory store error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.post("/memory/retrieve")
async def retrieve_memory(request: MemoryRetrieveRequest):
    """Retrieve a memory entry"""
    try:
        # Convert string memory type to enum
        memory_type = MemoryType(request.memory_type.upper()) if request.memory_type else None
        
        # Retrieve entry
        entry = await memory_manager.retrieve(request.key, memory_type)
        
        if entry:
            return MemoryResponse(
                success=True,
                data={
                    "entry_id": entry.id,
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "timestamp": entry.timestamp.isoformat(),
                    "session_id": entry.session_id,
                    "agent_id": entry.agent_id,
                    "tags": entry.tags
                },
                timestamp=datetime.now().isoformat()
            )
        else:
            return MemoryResponse(
                success=False,
                error="Entry not found",
                timestamp=datetime.now().isoformat()
            )
        
    except Exception as e:
        logger.error(f"Memory retrieve error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """Search memory entries"""
    try:
        # Create memory query
        query = MemoryQuery(
            query=request.query,
            type=MemoryType(request.memory_type.upper()) if request.memory_type else None,
            session_id=request.session_id,
            agent_id=request.agent_id,
            limit=request.limit,
            tags=request.tags or []
        )
        
        # Search entries
        entries = await memory_manager.search(query)
        
        # Format results
        results = []
        for entry in entries:
            results.append({
                "entry_id": entry.id,
                "content": entry.content,
                "metadata": entry.metadata,
                "timestamp": entry.timestamp.isoformat(),
                "session_id": entry.session_id,
                "agent_id": entry.agent_id,
                "tags": entry.tags,
                "type": entry.type.value
            })
        
        return MemoryResponse(
            success=True,
            data={"results": results, "count": len(results)},
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.post("/sessions/create")
async def create_session(request: SessionCreateRequest):
    """Create a new session"""
    try:
        session_memory = SessionMemory(request.session_id)
        
        return SessionResponse(
            session_id=session_memory.session_id,
            created_at=session_memory.created_at.isoformat(),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        return SessionResponse(
            session_id="",
            created_at="",
            success=False
        )

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information"""
    try:
        session_data = await memory_manager.get_session_memory(session_id)
        
        return MemoryResponse(
            success=True,
            data=session_data,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Session retrieval error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.get("/agents/{agent_id}/memory")
async def get_agent_memory(agent_id: str):
    """Get all memory for a specific agent"""
    try:
        agent_data = await memory_manager.get_agent_memory(agent_id)
        
        return MemoryResponse(
            success=True,
            data=agent_data,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Agent memory retrieval error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.get("/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        stats = await memory_manager.get_system_stats()
        
        return MemoryResponse(
            success=True,
            data=stats,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.delete("/memory/{entry_id}")
async def delete_memory(entry_id: str, memory_type: Optional[str] = None):
    """Delete a memory entry"""
    try:
        # Convert string memory type to enum
        mem_type = MemoryType(memory_type.upper()) if memory_type else None
        
        # Delete entry
        deleted = await memory_manager.delete(entry_id, mem_type)
        
        return MemoryResponse(
            success=deleted,
            data={"deleted": deleted},
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Memory deletion error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear all memory for a session"""
    try:
        await memory_manager.clear_session(session_id)
        
        return MemoryResponse(
            success=True,
            data={"session_id": session_id, "cleared": True},
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Session clearing error: {e}")
        return MemoryResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

if __name__ == "__main__":
    logger.info(f"Starting Memory API Server on port {API_PORT}")
    logger.info(f"Redis: {REDIS_URL}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )