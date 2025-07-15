#!/usr/bin/env python3
"""
OpenAI API Proxy Server
Provides rate-limited access to OpenAI GPT-4.1 with caching and monitoring.
"""

import os
import asyncio
import time
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from pydantic import BaseModel
import structlog
import redis

# Configure structured logging
logger = structlog.get_logger()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROXY_PORT = int(os.getenv("PROXY_PORT", 8002))
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", 100))
ALLOWED_MODELS = os.getenv("ALLOWED_MODELS", "gpt-4-turbo-preview,gpt-4,gpt-3.5-turbo").split(",")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Initialize Redis for rate limiting and caching
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Connected to Redis for caching")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# FastAPI app
app = FastAPI(
    title="vLLM Local Swarm - OpenAI Proxy",
    description="Rate-limited OpenAI API proxy with caching",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict]
    usage: Dict

# Rate limiting
class RateLimiter:
    def __init__(self, redis_client, rate_limit_rpm: int):
        self.redis_client = redis_client
        self.rate_limit_rpm = rate_limit_rpm
        self.window_size = 60  # 1 minute
        
    async def is_allowed(self, client_id: str) -> bool:
        if not self.redis_client:
            return True
            
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        # Clean old entries
        key = f"rate_limit:{client_id}"
        self.redis_client.zremrangebyscore(key, 0, window_start)
        
        # Count current requests
        current_count = self.redis_client.zcard(key)
        
        if current_count >= self.rate_limit_rpm:
            return False
            
        # Add current request
        self.redis_client.zadd(key, {str(current_time): current_time})
        self.redis_client.expire(key, self.window_size)
        
        return True

rate_limiter = RateLimiter(redis_client, RATE_LIMIT_RPM)

# Dependency to get client ID
async def get_client_id(request: Request) -> str:
    return request.client.host

# Cache for responses
class ResponseCache:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour
        
    def _generate_cache_key(self, request: ChatCompletionRequest) -> str:
        # Create a cache key based on model and messages
        messages_str = json.dumps([m.dict() for m in request.messages], sort_keys=True)
        return f"cache:{request.model}:{hash(messages_str)}"
        
    async def get(self, request: ChatCompletionRequest) -> Optional[Dict]:
        if not self.redis_client:
            return None
            
        key = self._generate_cache_key(request)
        cached = self.redis_client.get(key)
        if cached:
            logger.info("Cache hit", cache_key=key)
            return json.loads(cached)
        return None
        
    async def set(self, request: ChatCompletionRequest, response: Dict):
        if not self.redis_client:
            return
            
        key = self._generate_cache_key(request)
        self.redis_client.setex(key, self.cache_ttl, json.dumps(response))
        logger.info("Response cached", cache_key=key)

response_cache = ResponseCache(redis_client)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "allowed_models": ALLOWED_MODELS,
        "redis_connected": redis_client is not None
    }

@app.get("/v1/models")
async def list_models():
    """List available models"""
    models = []
    for model in ALLOWED_MODELS:
        models.append({
            "id": model,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "openai"
        })
    
    return {
        "object": "list",
        "data": models
    }

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    client_id: str = Depends(get_client_id)
):
    """Proxy chat completions to OpenAI with rate limiting and caching"""
    
    # Validate API key
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    # Validate model
    if request.model not in ALLOWED_MODELS:
        raise HTTPException(
            status_code=400, 
            detail=f"Model {request.model} not allowed. Available models: {ALLOWED_MODELS}"
        )
    
    # Check rate limit
    if not await rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_RPM} requests per minute."
        )
    
    # Check cache for non-streaming requests
    if not request.stream:
        cached_response = await response_cache.get(request)
        if cached_response:
            return cached_response
    
    logger.info(
        "Proxying request to OpenAI",
        model=request.model,
        client_id=client_id,
        message_count=len(request.messages),
        stream=request.stream
    )
    
    # Prepare OpenAI request
    openai_headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    request_data = request.dict(exclude_none=True)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            if request.stream:
                # Handle streaming response
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    headers=openai_headers,
                    json=request_data
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.atext()
                        logger.error(
                            "OpenAI API error",
                            status_code=response.status_code,
                            error=error_text
                        )
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"OpenAI API error: {error_text}"
                        )
                    
                    return StreamingResponse(
                        response.aiter_text(),
                        media_type="text/plain"
                    )
            else:
                # Handle regular response
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=openai_headers,
                    json=request_data
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(
                        "OpenAI API error",
                        status_code=response.status_code,
                        error=error_text
                    )
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"OpenAI API error: {error_text}"
                    )
                
                response_data = response.json()
                
                # Cache the response
                await response_cache.set(request, response_data)
                
                logger.info(
                    "OpenAI request completed",
                    model=request.model,
                    tokens_used=response_data.get("usage", {}).get("total_tokens", 0)
                )
                
                return response_data
                
        except httpx.TimeoutException:
            logger.error("OpenAI API timeout")
            raise HTTPException(status_code=504, detail="OpenAI API timeout")
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get proxy statistics"""
    stats = {
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
        "rate_limit_rpm": RATE_LIMIT_RPM,
        "allowed_models": ALLOWED_MODELS,
        "redis_connected": redis_client is not None
    }
    
    if redis_client:
        try:
            # Get cache stats
            cache_keys = redis_client.keys("cache:*")
            rate_limit_keys = redis_client.keys("rate_limit:*")
            
            stats.update({
                "cached_responses": len(cache_keys),
                "active_clients": len(rate_limit_keys)
            })
        except Exception as e:
            logger.warning(f"Failed to get Redis stats: {e}")
    
    return stats

# Startup event
@app.on_event("startup")
async def startup_event():
    app.state.start_time = time.time()
    logger.info(
        "OpenAI Proxy started",
        port=PROXY_PORT,
        rate_limit_rpm=RATE_LIMIT_RPM,
        allowed_models=ALLOWED_MODELS
    )

if __name__ == "__main__":
    uvicorn.run(
        "proxy:app",
        host="0.0.0.0",
        port=PROXY_PORT,
        log_level="info",
        access_log=True
    )