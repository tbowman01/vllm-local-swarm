#!/usr/bin/env python3
"""
Simple Memory API Service for vLLM Local Swarm Testing

This provides a simplified memory service for testing without complex dependencies.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
API_PORT = int(os.getenv("API_PORT", "8003"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Initialize Redis connection
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_URL}")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# FastAPI app
app = FastAPI(title="Simple Memory API Service", version="1.0.0")

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

# In-memory storage for simplicity
memory_store: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_client is not None,
        "memory_entries": len(memory_store)
    }

@app.post("/memory/store")
async def store_memory(request: MemoryStoreRequest):
    """Store a memory entry"""
    try:
        # Create entry
        entry = {
            "key": request.key,
            "value": request.value,
            "memory_type": request.memory_type,
            "session_id": request.session_id,
            "agent_id": request.agent_id,
            "metadata": request.metadata or {},
            "tags": request.tags or [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Store in memory
        memory_store[request.key] = entry
        
        # Also store in Redis if available
        if redis_client:
            try:
                redis_client.set(f"memory:{request.key}", json.dumps(entry))
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")
        
        return MemoryResponse(
            success=True,
            data={"entry_id": request.key},
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
        # Check in-memory store first
        entry = memory_store.get(request.key)
        
        # If not found, check Redis
        if not entry and redis_client:
            try:
                redis_data = redis_client.get(f"memory:{request.key}")
                if redis_data:
                    entry = json.loads(redis_data)
            except Exception as e:
                logger.warning(f"Redis retrieve failed: {e}")
        
        if entry:
            return MemoryResponse(
                success=True,
                data=entry,
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
        results = []
        
        # Simple search through in-memory store
        for key, entry in memory_store.items():
            if request.query.lower() in str(entry.get("value", "")).lower():
                if request.memory_type is None or entry.get("memory_type") == request.memory_type:
                    if request.session_id is None or entry.get("session_id") == request.session_id:
                        if request.agent_id is None or entry.get("agent_id") == request.agent_id:
                            results.append(entry)
                            if len(results) >= request.limit:
                                break
        
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

@app.get("/stats")
async def get_memory_stats():
    """Get memory system statistics"""
    try:
        stats = {
            "total_entries": len(memory_store),
            "memory_types": {},
            "sessions": set(),
            "agents": set()
        }
        
        for entry in memory_store.values():
            # Count memory types
            mem_type = entry.get("memory_type", "unknown")
            stats["memory_types"][mem_type] = stats["memory_types"].get(mem_type, 0) + 1
            
            # Collect sessions and agents
            if entry.get("session_id"):
                stats["sessions"].add(entry["session_id"])
            if entry.get("agent_id"):
                stats["agents"].add(entry["agent_id"])
        
        # Convert sets to lists for JSON serialization
        stats["sessions"] = list(stats["sessions"])
        stats["agents"] = list(stats["agents"])
        
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

if __name__ == "__main__":
    logger.info(f"Starting Simple Memory API Service on port {API_PORT}")
    logger.info(f"Redis: {REDIS_URL}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=API_PORT,
        log_level="info"
    )