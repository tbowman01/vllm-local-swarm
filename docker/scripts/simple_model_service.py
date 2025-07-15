#!/usr/bin/env python3
"""
Simple Model Service for vLLM Local Swarm Testing

This provides a mock model service that simulates LLM responses for testing
without requiring heavy GPU resources.
"""

import asyncio
import json
import logging
import os
import time
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
MODEL_NAME = os.getenv("MODEL_NAME", "simple-test-model")
MODEL_PORT = int(os.getenv("MODEL_PORT", "8000"))
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
app = FastAPI(title="Simple Model Service", version="1.0.0")

# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "simple-model-service"

# Mock responses for different agent types
AGENT_RESPONSES = {
    "planner": {
        "system_prompt": "You are a planner agent that breaks down tasks into actionable steps.",
        "sample_response": """Based on the task, I'll break this down into the following steps:

1. **Analysis Phase**
   - Understand the requirements
   - Identify key components
   - Assess complexity

2. **Design Phase**
   - Create system architecture
   - Define interfaces
   - Plan implementation approach

3. **Implementation Phase**
   - Set up development environment
   - Implement core functionality
   - Add error handling

4. **Testing Phase**
   - Unit testing
   - Integration testing
   - User acceptance testing

5. **Deployment Phase**
   - Prepare production environment
   - Deploy and monitor
   - Documentation and handoff

Each step should be assigned to appropriate specialists for optimal results."""
    },
    "researcher": {
        "system_prompt": "You are a researcher agent that gathers and analyzes information.",
        "sample_response": """Based on my research, here are the key findings:

## Research Summary

**Topic**: [Extracted from user query]

**Key Findings**:
1. Current industry standards and best practices
2. Available tools and technologies
3. Potential challenges and solutions
4. Performance benchmarks and comparisons

**Sources**:
- Technical documentation
- Industry reports
- Academic papers
- Community discussions

**Recommendations**:
- Adopt proven methodologies
- Consider scalability from the start
- Implement proper monitoring
- Follow security best practices

**Next Steps**:
- Validate findings with stakeholders
- Prepare detailed implementation plan
- Identify required resources"""
    },
    "coder": {
        "system_prompt": "You are a coder agent that implements solutions and writes code.",
        "sample_response": """I'll implement the requested functionality:

```python
# Example implementation
class TaskProcessor:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def process_task(self, task):
        \"\"\"Process a task according to specifications\"\"\"
        try:
            # Validate input
            if not self.validate_task(task):
                raise ValueError("Invalid task format")
            
            # Execute processing logic
            result = await self.execute_task(task)
            
            # Return formatted result
            return {
                "status": "success",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Task processing failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def validate_task(self, task):
        \"\"\"Validate task format and requirements\"\"\"
        return task and isinstance(task, dict)
    
    async def execute_task(self, task):
        \"\"\"Execute the actual task logic\"\"\"
        # Implementation would go here
        await asyncio.sleep(0.1)  # Simulate processing
        return f"Processed task: {task.get('description', 'Unknown')}"
```

The implementation includes:
- Proper error handling
- Logging integration
- Async/await patterns
- Clear documentation
- Validation logic"""
    },
    "qa": {
        "system_prompt": "You are a QA agent that tests and validates implementations.",
        "sample_response": """## Quality Assurance Report

### Test Results Summary
- **Total Tests**: 15
- **Passed**: 13
- **Failed**: 2
- **Coverage**: 87%

### Test Categories
1. **Unit Tests** ✅
   - Core functionality validated
   - Edge cases handled
   - Error conditions tested

2. **Integration Tests** ✅
   - API endpoints working
   - Database connections stable
   - External service integration verified

3. **Performance Tests** ⚠️
   - Response time: 150ms (target: 100ms)
   - Memory usage: 245MB (acceptable)
   - Concurrent users: 50 (target: 100)

### Issues Found
1. **Memory leak** in task processing loop
2. **Race condition** in concurrent requests

### Recommendations
1. Implement proper cleanup in task processor
2. Add synchronization for shared resources
3. Increase test coverage to 95%
4. Add performance monitoring

### Next Steps
- Fix identified issues
- Re-run test suite
- Performance optimization
- Security audit"""
    },
    "critic": {
        "system_prompt": "You are a critic agent that reviews and provides feedback.",
        "sample_response": """## Critical Review

### Strengths
1. **Architecture**: Well-structured and modular design
2. **Documentation**: Clear and comprehensive
3. **Error Handling**: Robust exception management
4. **Testing**: Good coverage of main scenarios

### Areas for Improvement

#### Code Quality
- **Complexity**: Some functions are too long and should be broken down
- **Naming**: Variable names could be more descriptive
- **Comments**: Missing documentation for complex algorithms

#### Performance
- **Efficiency**: Algorithm choice could be optimized
- **Memory Usage**: Potential for memory leaks in long-running processes
- **Scalability**: Current design may not scale beyond 100 concurrent users

#### Security
- **Input Validation**: Need stricter validation of user inputs
- **Authentication**: Missing proper authentication mechanisms
- **Data Exposure**: Sensitive data might be logged

### Recommendations
1. Refactor large functions into smaller, focused methods
2. Implement comprehensive input validation
3. Add performance monitoring and alerting
4. Consider using design patterns for better maintainability
5. Add security headers and proper authentication

### Alternative Approaches
- Consider using event-driven architecture
- Implement caching layer for better performance
- Use containerization for better deployment"""
    },
    "judge": {
        "system_prompt": "You are a judge agent that makes final decisions and evaluations.",
        "sample_response": """## Final Evaluation

### Decision: **APPROVED WITH CONDITIONS**

### Evaluation Criteria
1. **Functionality** (Weight: 30%): **85/100**
   - Meets core requirements
   - Minor edge cases need attention

2. **Quality** (Weight: 25%): **78/100**
   - Good structure and documentation
   - Some code quality issues identified

3. **Performance** (Weight: 20%): **72/100**
   - Acceptable performance for current scale
   - Optimization needed for production

4. **Security** (Weight: 15%): **65/100**
   - Basic security measures in place
   - Enhanced security required

5. **Maintainability** (Weight: 10%): **88/100**
   - Well-organized codebase
   - Clear documentation

### Overall Score: **77/100**

### Conditions for Approval
1. Fix critical security vulnerabilities
2. Optimize performance bottlenecks
3. Increase test coverage to 95%
4. Complete security audit

### Timeline
- **Immediate**: Address security issues
- **Week 1**: Performance optimization
- **Week 2**: Enhanced testing
- **Week 3**: Final review and deployment

### Next Steps
1. Development team to address conditions
2. Schedule follow-up review in 2 weeks
3. Prepare production deployment plan
4. Monitor post-deployment metrics"""
    }
}

def get_agent_response(messages: List[ChatMessage], model_name: str) -> str:
    """Generate appropriate response based on the conversation context."""
    
    # Analyze messages to determine agent type
    agent_type = "planner"  # default
    
    # Look for context clues in messages
    full_context = " ".join([msg.content.lower() for msg in messages])
    
    if any(word in full_context for word in ["research", "analyze", "investigate", "study"]):
        agent_type = "researcher"
    elif any(word in full_context for word in ["code", "implement", "program", "develop"]):
        agent_type = "coder"
    elif any(word in full_context for word in ["test", "validate", "verify", "qa"]):
        agent_type = "qa"
    elif any(word in full_context for word in ["review", "critique", "evaluate", "assess"]):
        agent_type = "critic"
    elif any(word in full_context for word in ["decide", "judge", "approve", "final"]):
        agent_type = "judge"
    
    # Get appropriate response
    response_template = AGENT_RESPONSES.get(agent_type, AGENT_RESPONSES["planner"])
    
    # Customize response based on latest message
    latest_message = messages[-1].content if messages else "No specific task provided"
    
    # Add task-specific context
    if "task" in latest_message.lower():
        response = f"Task: {latest_message}\n\n{response_template['sample_response']}"
    else:
        response = response_template['sample_response']
    
    return response

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_client is not None
    }

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            ModelInfo(
                id=MODEL_NAME,
                created=int(time.time()),
                owned_by="simple-model-service"
            )
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """Handle chat completion requests"""
    try:
        # Generate response
        response_content = get_agent_response(request.messages, request.model)
        
        # Create response
        response = ChatResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": sum(len(msg.content.split()) for msg in request.messages),
                "completion_tokens": len(response_content.split()),
                "total_tokens": sum(len(msg.content.split()) for msg in request.messages) + len(response_content.split())
            }
        )
        
        # Log to Redis if available
        if redis_client:
            try:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "model": request.model,
                    "messages": len(request.messages),
                    "response_length": len(response_content),
                    "usage": response.usage
                }
                redis_client.lpush("model_requests", json.dumps(log_entry))
                redis_client.ltrim("model_requests", 0, 1000)  # Keep last 1000 requests
            except Exception as e:
                logger.warning(f"Failed to log to Redis: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    stats = {
        "model": MODEL_NAME,
        "uptime": time.time(),
        "redis_connected": redis_client is not None,
        "total_requests": 0
    }
    
    if redis_client:
        try:
            stats["total_requests"] = redis_client.llen("model_requests")
            # Get recent requests
            recent_requests = redis_client.lrange("model_requests", 0, 9)
            stats["recent_requests"] = [json.loads(req) for req in recent_requests]
        except Exception as e:
            logger.warning(f"Failed to get stats from Redis: {e}")
    
    return stats

if __name__ == "__main__":
    logger.info(f"Starting Simple Model Service on port {MODEL_PORT}")
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Redis: {REDIS_URL}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=MODEL_PORT,
        log_level="info"
    )