#!/usr/bin/env python3
"""
Orchestrator API Server for vLLM Local Swarm

Provides REST API for task orchestration and SPARC workflow management.
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
import httpx

# Add src path
sys.path.insert(0, "/app/src")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "8004"))
MODEL_SERVICE_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:8000")
MEMORY_API_URL = os.getenv("MEMORY_API_URL", "http://localhost:8003")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# FastAPI app
app = FastAPI(title="SPARC Orchestrator API", version="1.0.0")

# Request/Response models
class TaskRequest(BaseModel):
    objective: str
    task_definition: str
    priority: str = "medium"
    session_id: Optional[str] = None
    use_gpt4_fallback: bool = False
    context: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    task_id: str
    status: str
    summary: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    current_stage: str
    progress: float
    agents_involved: List[str]
    started_at: str
    updated_at: str

class AgentRequest(BaseModel):
    agent_type: str
    task_description: str
    context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    agent_id: str
    agent_type: str
    response: str
    confidence: float
    processing_time: float
    tokens_used: int

# In-memory task storage (in production, this would be in a database)
active_tasks: Dict[str, Dict[str, Any]] = {}
task_counter = 0

def generate_task_id() -> str:
    """Generate a unique task ID"""
    global task_counter
    task_counter += 1
    return f"task_{int(datetime.now().timestamp())}_{task_counter}"

async def call_model_service(messages: List[Dict[str, str]], model: str = "simple-test-model") -> Dict[str, Any]:
    """Call the model service for LLM responses"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MODEL_SERVICE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2048
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Model service call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model service error: {e}")

async def store_memory(key: str, value: Any, session_id: str, agent_id: str = None):
    """Store data in memory service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMORY_API_URL}/memory/store",
                json={
                    "key": key,
                    "value": value,
                    "memory_type": "session",
                    "session_id": session_id,
                    "agent_id": agent_id
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning(f"Memory store failed: {e}")
        return None

async def retrieve_memory(key: str, memory_type: str = "session"):
    """Retrieve data from memory service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMORY_API_URL}/memory/retrieve",
                json={
                    "key": key,
                    "memory_type": memory_type
                },
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning(f"Memory retrieve failed: {e}")
        return None

async def execute_sparc_workflow(task_request: TaskRequest) -> TaskResponse:
    """Execute the SPARC workflow for a task"""
    task_id = generate_task_id()
    session_id = task_request.session_id or f"session_{task_id}"
    
    # Initialize task tracking
    task_data = {
        "task_id": task_id,
        "objective": task_request.objective,
        "task_definition": task_request.task_definition,
        "priority": task_request.priority,
        "session_id": session_id,
        "status": "in_progress",
        "current_stage": "specification",
        "progress": 0.0,
        "agents_involved": [],
        "started_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "results": {},
        "error": None
    }
    
    active_tasks[task_id] = task_data
    
    try:
        # SPARC Workflow Stages
        stages = [
            ("specification", "planner", "Analyze and specify the task requirements"),
            ("pseudocode", "planner", "Create pseudocode and high-level approach"),
            ("architecture", "planner", "Design system architecture"),
            ("implementation", "coder", "Implement the solution"),
            ("refinement", "critic", "Review and refine the implementation"),
            ("testing", "qa", "Test and validate the solution"),
            ("completion", "judge", "Final evaluation and approval")
        ]
        
        stage_results = {}
        
        for i, (stage_name, agent_type, stage_description) in enumerate(stages):
            task_data["current_stage"] = stage_name
            task_data["progress"] = (i / len(stages)) * 100
            task_data["updated_at"] = datetime.now().isoformat()
            
            if agent_type not in task_data["agents_involved"]:
                task_data["agents_involved"].append(agent_type)
            
            logger.info(f"Executing stage {stage_name} with {agent_type} agent")
            
            # Prepare context for the agent
            context = {
                "task_id": task_id,
                "objective": task_request.objective,
                "task_definition": task_request.task_definition,
                "stage": stage_name,
                "stage_description": stage_description,
                "previous_results": stage_results,
                "session_id": session_id
            }
            
            # Create messages for the model
            messages = [
                {
                    "role": "system",
                    "content": f"You are a {agent_type} agent in a SPARC workflow. Your current task is: {stage_description}"
                },
                {
                    "role": "user",
                    "content": f"Task: {task_request.objective}\n\nDefinition: {task_request.task_definition}\n\nContext: {json.dumps(context, indent=2)}\n\nPlease provide your {agent_type} response for the {stage_name} stage."
                }
            ]
            
            # Call model service
            response = await call_model_service(messages)
            
            # Extract response content
            if response.get("choices") and len(response["choices"]) > 0:
                stage_result = response["choices"][0]["message"]["content"]
                stage_results[stage_name] = {
                    "agent_type": agent_type,
                    "response": stage_result,
                    "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Store in memory
                await store_memory(
                    f"task_{task_id}_stage_{stage_name}",
                    stage_result,
                    session_id,
                    agent_type
                )
                
                logger.info(f"Completed stage {stage_name}")
            else:
                raise Exception(f"No response from {agent_type} agent for stage {stage_name}")
            
            # Simulate processing time
            await asyncio.sleep(0.5)
        
        # Task completed successfully
        task_data["status"] = "completed"
        task_data["progress"] = 100.0
        task_data["results"] = stage_results
        task_data["updated_at"] = datetime.now().isoformat()
        
        return TaskResponse(
            task_id=task_id,
            status="completed",
            summary=f"Task '{task_request.objective}' completed successfully through SPARC workflow",
            results=stage_results,
            created_at=task_data["started_at"],
            updated_at=task_data["updated_at"]
        )
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        task_data["status"] = "failed"
        task_data["error"] = str(e)
        task_data["updated_at"] = datetime.now().isoformat()
        
        return TaskResponse(
            task_id=task_id,
            status="failed",
            summary=f"Task '{task_request.objective}' failed: {str(e)}",
            error=str(e),
            created_at=task_data["started_at"],
            updated_at=task_data["updated_at"]
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_tasks": len(active_tasks),
        "services": {}
    }
    
    # Check model service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MODEL_SERVICE_URL}/health", timeout=5.0)
            health_status["services"]["model"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health_status["services"]["model"] = "unhealthy"
    
    # Check memory service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MEMORY_API_URL}/health", timeout=5.0)
            health_status["services"]["memory"] = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        health_status["services"]["memory"] = "unhealthy"
    
    return health_status

@app.post("/tasks")
async def create_task(task_request: TaskRequest):
    """Create and execute a new task"""
    try:
        result = await execute_sparc_workflow(task_request)
        return result
    except Exception as e:
        logger.error(f"Task creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = active_tasks[task_id]
    
    return TaskStatus(
        task_id=task_id,
        status=task_data["status"],
        current_stage=task_data["current_stage"],
        progress=task_data["progress"],
        agents_involved=task_data["agents_involved"],
        started_at=task_data["started_at"],
        updated_at=task_data["updated_at"]
    )

@app.get("/tasks/{task_id}/results")
async def get_task_results(task_id: str):
    """Get results of a completed task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = active_tasks[task_id]
    
    return TaskResponse(
        task_id=task_id,
        status=task_data["status"],
        summary=f"Task results for '{task_data['objective']}'",
        results=task_data.get("results"),
        error=task_data.get("error"),
        created_at=task_data["started_at"],
        updated_at=task_data["updated_at"]
    )

@app.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return {
        "tasks": [
            {
                "task_id": task_id,
                "objective": task_data["objective"],
                "status": task_data["status"],
                "current_stage": task_data["current_stage"],
                "progress": task_data["progress"],
                "started_at": task_data["started_at"],
                "updated_at": task_data["updated_at"]
            }
            for task_id, task_data in active_tasks.items()
        ],
        "total_tasks": len(active_tasks)
    }

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = active_tasks[task_id]
    task_data["status"] = "cancelled"
    task_data["updated_at"] = datetime.now().isoformat()
    
    return {"message": f"Task {task_id} cancelled", "task_id": task_id}

@app.post("/agents/query")
async def query_agent(agent_request: AgentRequest):
    """Query a specific agent directly"""
    try:
        # Create messages for the agent
        messages = [
            {
                "role": "system",
                "content": f"You are a {agent_request.agent_type} agent."
            },
            {
                "role": "user",
                "content": agent_request.task_description
            }
        ]
        
        # Add context if provided
        if agent_request.context:
            messages[1]["content"] += f"\n\nContext: {json.dumps(agent_request.context, indent=2)}"
        
        # Call model service
        start_time = datetime.now()
        response = await call_model_service(messages)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Extract response
        if response.get("choices") and len(response["choices"]) > 0:
            agent_response = response["choices"][0]["message"]["content"]
            
            return AgentResponse(
                agent_id=f"{agent_request.agent_type}_{int(datetime.now().timestamp())}",
                agent_type=agent_request.agent_type,
                response=agent_response,
                confidence=0.85,  # Mock confidence score
                processing_time=processing_time,
                tokens_used=response.get("usage", {}).get("total_tokens", 0)
            )
        else:
            raise Exception("No response from agent")
            
    except Exception as e:
        logger.error(f"Agent query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_orchestrator_stats():
    """Get orchestrator statistics"""
    return {
        "total_tasks": len(active_tasks),
        "active_tasks": len([t for t in active_tasks.values() if t["status"] == "in_progress"]),
        "completed_tasks": len([t for t in active_tasks.values() if t["status"] == "completed"]),
        "failed_tasks": len([t for t in active_tasks.values() if t["status"] == "failed"]),
        "cancelled_tasks": len([t for t in active_tasks.values() if t["status"] == "cancelled"]),
        "uptime": datetime.now().isoformat(),
        "model_service_url": MODEL_SERVICE_URL,
        "memory_api_url": MEMORY_API_URL
    }

if __name__ == "__main__":
    logger.info(f"Starting SPARC Orchestrator API on port {ORCHESTRATOR_PORT}")
    logger.info(f"Model Service: {MODEL_SERVICE_URL}")
    logger.info(f"Memory API: {MEMORY_API_URL}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=ORCHESTRATOR_PORT,
        log_level="info"
    )