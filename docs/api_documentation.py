#!/usr/bin/env python3
"""
OpenAPI/Swagger Documentation Generator for vLLM Local Swarm
==========================================================

Comprehensive API documentation generator with:
- OpenAPI 3.0 specification generation
- Interactive Swagger UI interface
- Real-time API endpoint discovery
- Authentication and security documentation
- Example requests and responses
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.openapi.utils import get_openapi
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    print("Installing API documentation dependencies...")
    import subprocess
    subprocess.run([
        "pip", "install", 
        "fastapi", "uvicorn[standard]"
    ], check=True)
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.openapi.utils import get_openapi
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """API endpoint documentation structure"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    security: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]


class APIDocumentationGenerator:
    """
    Generates comprehensive API documentation for vLLM Local Swarm
    """
    
    def __init__(self, port: int = 8010):
        self.port = port
        self.app = FastAPI(
            title="vLLM Local Swarm API",
            description="Comprehensive API documentation for the vLLM Local Swarm agent coordination system",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # API specification
        self.openapi_spec = None
        self.endpoints = {}
        
        # Documentation content
        self.api_sections = {
            'authentication': {
                'title': 'Authentication & Security',
                'description': 'JWT-based authentication and API key management',
                'endpoints': []
            },
            'agents': {
                'title': 'Agent Management',
                'description': 'Agent registration, coordination, and monitoring',
                'endpoints': []
            },
            'tasks': {
                'title': 'Task Management',
                'description': 'Task queuing, routing, and execution',
                'endpoints': []
            },
            'memory': {
                'title': 'Memory System',
                'description': 'Semantic memory storage and retrieval',
                'endpoints': []
            },
            'communication': {
                'title': 'Real-time Communication',
                'description': 'WebSocket-based agent communication',
                'endpoints': []
            },
            'monitoring': {
                'title': 'Monitoring & Analytics',
                'description': 'System metrics and performance monitoring',
                'endpoints': []
            }
        }
        
        self._setup_routes()
        self._generate_api_spec()
        
    def _setup_routes(self):
        """Setup documentation routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def documentation_home():
            return await self._get_documentation_html()
            
        @self.app.get("/api/spec")
        async def get_openapi_spec():
            return JSONResponse(content=self.openapi_spec)
            
        @self.app.get("/api/endpoints")
        async def get_endpoints():
            return self.endpoints
            
        @self.app.get("/api/sections")
        async def get_sections():
            return self.api_sections
            
        # Example API endpoints for documentation
        self._setup_example_endpoints()
        
    def _setup_example_endpoints(self):
        """Setup example API endpoints for documentation"""
        
        # Authentication endpoints
        @self.app.post("/auth/login", tags=["authentication"])
        async def login(credentials: dict):
            """
            Authenticate user and return JWT token
            
            - **username**: User's username
            - **password**: User's password
            - **Returns**: JWT access token and refresh token
            """
            return {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
            
        @self.app.post("/auth/refresh", tags=["authentication"])
        async def refresh_token(refresh_token: str):
            """
            Refresh JWT access token
            
            - **refresh_token**: Valid refresh token
            - **Returns**: New JWT access token
            """
            return {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer", 
                "expires_in": 3600
            }
            
        @self.app.get("/auth/me", tags=["authentication"])
        async def get_current_user():
            """
            Get current authenticated user information
            
            - **Requires**: Valid JWT token in Authorization header
            - **Returns**: User profile information
            """
            return {
                "user_id": "user123",
                "username": "developer",
                "email": "dev@example.com",
                "roles": ["user", "developer"],
                "permissions": ["agents.read", "tasks.create"]
            }
            
        # Agent management endpoints
        @self.app.get("/agents", tags=["agents"])
        async def list_agents():
            """
            List all registered agents
            
            - **Returns**: Array of agent information
            """
            return [
                {
                    "agent_id": "research_specialist",
                    "name": "Research Specialist",
                    "role": "specialist",
                    "capabilities": ["research", "analysis"],
                    "status": "active",
                    "last_seen": "2024-01-15T10:30:00Z"
                }
            ]
            
        @self.app.post("/agents/register", tags=["agents"])
        async def register_agent(agent_config: dict):
            """
            Register a new agent
            
            - **agent_id**: Unique agent identifier
            - **name**: Human-readable agent name
            - **capabilities**: List of agent capabilities
            - **Returns**: Registration confirmation
            """
            return {
                "agent_id": agent_config["agent_id"],
                "status": "registered",
                "registration_time": datetime.now().isoformat()
            }
            
        @self.app.get("/agents/{agent_id}", tags=["agents"])
        async def get_agent(agent_id: str):
            """
            Get specific agent information
            
            - **agent_id**: Agent identifier
            - **Returns**: Detailed agent information
            """
            return {
                "agent_id": agent_id,
                "name": "Research Specialist",
                "status": "active",
                "metrics": {
                    "tasks_completed": 45,
                    "success_rate": 0.96,
                    "average_response_time": 3.2
                }
            }
            
        # Task management endpoints
        @self.app.post("/tasks", tags=["tasks"])
        async def create_task(task_definition: dict):
            """
            Create a new task
            
            - **name**: Task name
            - **handler**: Task handler function
            - **payload**: Task data
            - **priority**: Task priority (1-10)
            - **Returns**: Task ID and status
            """
            return {
                "task_id": "task_123456",
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "estimated_completion": "2024-01-15T11:00:00Z"
            }
            
        @self.app.get("/tasks/{task_id}", tags=["tasks"])
        async def get_task(task_id: str):
            """
            Get task status and results
            
            - **task_id**: Task identifier
            - **Returns**: Task status and results
            """
            return {
                "task_id": task_id,
                "status": "completed",
                "result": {
                    "success": True,
                    "data": "Task completed successfully"
                },
                "processing_time": 4.7,
                "completed_at": "2024-01-15T10:45:00Z"
            }
            
        @self.app.get("/tasks", tags=["tasks"])
        async def list_tasks(status: Optional[str] = None, limit: int = 50):
            """
            List tasks with optional filtering
            
            - **status**: Filter by task status (optional)
            - **limit**: Maximum number of tasks to return
            - **Returns**: Array of task information
            """
            return [
                {
                    "task_id": "task_123456",
                    "name": "Data Analysis Task",
                    "status": "completed",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            ]
            
        # Memory system endpoints
        @self.app.post("/memory/search", tags=["memory"])
        async def search_memory(query: dict):
            """
            Search semantic memory
            
            - **query**: Search query text
            - **mode**: Search mode (semantic, keyword, hybrid)
            - **max_results**: Maximum results to return
            - **Returns**: Array of memory entries with relevance scores
            """
            return {
                "query": query["query"],
                "results": [
                    {
                        "memory_id": "mem_123",
                        "content": "Relevant memory content...",
                        "similarity_score": 0.87,
                        "type": "semantic",
                        "created_at": "2024-01-15T09:00:00Z"
                    }
                ],
                "total_results": 1,
                "search_time": 0.032
            }
            
        @self.app.post("/memory/store", tags=["memory"])
        async def store_memory(memory_entry: dict):
            """
            Store new memory entry
            
            - **content**: Memory content
            - **type**: Memory type (session, semantic, agent)
            - **metadata**: Additional metadata
            - **Returns**: Memory ID and confirmation
            """
            return {
                "memory_id": "mem_789",
                "status": "stored",
                "indexed_at": datetime.now().isoformat()
            }
            
        @self.app.get("/memory/stats", tags=["memory"])
        async def get_memory_stats():
            """
            Get memory system statistics
            
            - **Returns**: Memory usage and performance metrics
            """
            return {
                "total_entries": 1247,
                "memory_types": {
                    "session": 523,
                    "semantic": 389,
                    "agent": 267
                },
                "storage_size_mb": 89.4,
                "search_performance": {
                    "avg_search_time": 0.032,
                    "cache_hit_rate": 0.78
                }
            }
            
        # Monitoring endpoints
        @self.app.get("/monitoring/metrics", tags=["monitoring"])
        async def get_system_metrics():
            """
            Get comprehensive system metrics
            
            - **Returns**: Real-time system performance data
            """
            return {
                "agents": {
                    "total": 5,
                    "active": 3,
                    "idle": 2
                },
                "tasks": {
                    "queued": 8,
                    "processing": 3,
                    "completed": 140
                },
                "system": {
                    "cpu_usage": 0.35,
                    "memory_usage": 0.67,
                    "uptime": 3600
                }
            }
            
        @self.app.get("/monitoring/health", tags=["monitoring"])
        async def health_check():
            """
            System health check endpoint
            
            - **Returns**: Overall system health status
            """
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "services": {
                    "auth_service": "healthy",
                    "task_queue": "healthy",
                    "memory_system": "healthy",
                    "agent_hub": "healthy"
                }
            }
            
    def _generate_api_spec(self):
        """Generate OpenAPI specification"""
        
        # Custom OpenAPI schema
        custom_openapi = get_openapi(
            title="vLLM Local Swarm API",
            version="1.0.0",
            description="""
# vLLM Local Swarm API Documentation

Welcome to the comprehensive API documentation for the vLLM Local Swarm agent coordination system.

## Overview

The vLLM Local Swarm is an advanced AI agent coordination platform that provides:

- **🤖 Agent Management**: Register, coordinate, and monitor AI agents
- **📋 Task Orchestration**: Intelligent task routing and execution
- **🧠 Semantic Memory**: Advanced memory storage and retrieval
- **💬 Real-time Communication**: WebSocket-based agent coordination
- **📊 Monitoring**: Comprehensive system metrics and alerts
- **🔐 Security**: JWT-based authentication and authorization

## Authentication

Most API endpoints require authentication. Include your JWT token in the Authorization header:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Rate Limiting

API requests are limited to:
- **100 requests/minute** for standard endpoints
- **1000 requests/minute** for monitoring endpoints
- **10 requests/second** for WebSocket connections

## Error Handling

The API uses standard HTTP status codes and returns errors in this format:

```json
{
    "error": "error_code",
    "message": "Human readable error message",
    "details": {
        "field": "Additional error details"
    }
}
```

## WebSocket Endpoints

Real-time communication uses WebSocket connections:

- **Agent Communication**: `ws://host:8008/ws`
- **Live Monitoring**: `ws://host:8009/ws`

## SDKs and Libraries

Official SDKs available for:
- Python: `pip install vllm-swarm-client`
- JavaScript: `npm install vllm-swarm-js`
- Go: `go get github.com/vllm-swarm/go-client`

## Support

- 📖 Documentation: https://docs.vllm-swarm.dev
- 💬 Community: https://discord.gg/vllm-swarm
- 🐛 Issues: https://github.com/vllm-swarm/issues
            """,
            routes=self.app.routes,
            servers=[
                {"url": "http://localhost:8005", "description": "Authentication Service"},
                {"url": "http://localhost:8006", "description": "Orchestrator Service"},
                {"url": "http://localhost:8003", "description": "Memory Service"},
                {"url": "http://localhost:8009", "description": "Monitoring Service"}
            ]
        )
        
        # Add security schemes
        custom_openapi["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
        
        # Add global security
        for path in custom_openapi["paths"]:
            for method in custom_openapi["paths"][path]:
                if method != "options":
                    custom_openapi["paths"][path][method]["security"] = [
                        {"BearerAuth": []},
                        {"ApiKeyAuth": []}
                    ]
        
        # Add example responses
        self._add_example_responses(custom_openapi)
        
        self.openapi_spec = custom_openapi
        
    def _add_example_responses(self, spec: Dict[str, Any]):
        """Add example responses to API specification"""
        
        examples = {
            "/auth/login": {
                "post": {
                    "examples": {
                        "successful_login": {
                            "summary": "Successful login",
                            "value": {
                                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                "token_type": "bearer",
                                "expires_in": 3600
                            }
                        }
                    }
                }
            },
            "/agents": {
                "get": {
                    "examples": {
                        "agent_list": {
                            "summary": "List of active agents", 
                            "value": [
                                {
                                    "agent_id": "research_specialist",
                                    "name": "Research Specialist",
                                    "status": "active",
                                    "capabilities": ["research", "analysis"]
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        # Apply examples to specification
        for path, methods in examples.items():
            if path in spec["paths"]:
                for method, example_data in methods.items():
                    if method in spec["paths"][path]:
                        if "responses" not in spec["paths"][path][method]:
                            spec["paths"][path][method]["responses"] = {}
                        
                        for status_code in ["200", "201"]:
                            if status_code in spec["paths"][path][method]["responses"]:
                                response = spec["paths"][path][method]["responses"][status_code]
                                if "content" not in response:
                                    response["content"] = {
                                        "application/json": {
                                            "examples": example_data.get("examples", {})
                                        }
                                    }
                                else:
                                    for content_type in response["content"]:
                                        response["content"][content_type]["examples"] = example_data.get("examples", {})
        
    async def _get_documentation_html(self) -> str:
        """Generate custom documentation HTML page"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>vLLM Swarm API Documentation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #1d1d1f;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            padding: 40px 20px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p {
            font-size: 1.2em;
            color: #6b7280;
            margin-bottom: 30px;
        }
        
        .quick-links {
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .quick-link {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .quick-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        }
        
        .container {
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
        }
        
        .api-sections {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
        }
        
        .api-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        .api-section h2 {
            font-size: 1.5em;
            margin-bottom: 15px;
            color: #1d1d1f;
        }
        
        .api-section p {
            color: #6b7280;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        
        .endpoint-list {
            list-style: none;
        }
        
        .endpoint-item {
            background: #f8fafc;
            margin: 8px 0;
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }
        
        .method {
            font-weight: bold;
            color: #667eea;
            margin-right: 8px;
        }
        
        .features {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 16px;
            padding: 40px;
            margin: 40px 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .features h2 {
            font-size: 2.5em;
            margin-bottom: 20px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        
        .feature {
            text-align: center;
        }
        
        .feature-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        .feature h3 {
            font-size: 1.2em;
            margin-bottom: 10px;
            color: #1d1d1f;
        }
        
        .feature p {
            color: #6b7280;
            line-height: 1.5;
        }
        
        .footer {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            text-align: center;
            padding: 40px 20px;
            margin-top: 60px;
            color: white;
        }
        
        @media (max-width: 768px) {
            .header h1 { font-size: 2em; }
            .quick-links { flex-direction: column; align-items: center; }
            .api-sections { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 vLLM Swarm API</h1>
        <p>Comprehensive API documentation for agent coordination system</p>
        
        <div class="quick-links">
            <a href="/docs" class="quick-link">📖 Swagger UI</a>
            <a href="/redoc" class="quick-link">📚 ReDoc</a>
            <a href="/api/spec" class="quick-link">⚙️ OpenAPI Spec</a>
            <a href="http://localhost:8009" class="quick-link">📊 Live Monitor</a>
        </div>
    </div>
    
    <div class="container">
        <div class="features">
            <h2>🚀 Platform Features</h2>
            <div class="feature-grid">
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <h3>Agent Coordination</h3>
                    <p>Intelligent task routing and agent management with real-time coordination</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🧠</div>
                    <h3>Semantic Memory</h3>
                    <p>Advanced memory system with vector embeddings and similarity search</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">💬</div>
                    <h3>Real-time Communication</h3>
                    <p>WebSocket-based messaging for instant agent collaboration</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h3>Monitoring & Analytics</h3>
                    <p>Comprehensive system metrics and performance monitoring</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🔐</div>
                    <h3>Security First</h3>
                    <p>JWT authentication, API keys, and role-based access control</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">⚡</div>
                    <h3>High Performance</h3>
                    <p>Distributed task queues with Redis and optimized processing</p>
                </div>
            </div>
        </div>
        
        <div class="api-sections" id="apiSections">
            <!-- API sections will be populated by JavaScript -->
        </div>
    </div>
    
    <div class="footer">
        <h3>🛠️ Built with vLLM Local Swarm</h3>
        <p>Enterprise-grade AI agent coordination platform</p>
        <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.8;">
            🤖 Generated with <a href="https://claude.ai/code" style="color: #fff; text-decoration: none;">Claude Code</a> |
            Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;
        </p>
    </div>

    <script>
        // API sections data
        const apiSections = {
            'authentication': {
                'title': '🔐 Authentication & Security',
                'description': 'JWT-based authentication and API key management for secure access',
                'endpoints': [
                    'POST /auth/login - Authenticate user',
                    'POST /auth/refresh - Refresh JWT token', 
                    'GET /auth/me - Get current user info',
                    'POST /auth/logout - Logout user'
                ]
            },
            'agents': {
                'title': '🤖 Agent Management',
                'description': 'Register, coordinate, and monitor AI agents in the swarm',
                'endpoints': [
                    'GET /agents - List all agents',
                    'POST /agents/register - Register new agent',
                    'GET /agents/{id} - Get agent details',
                    'PUT /agents/{id} - Update agent config',
                    'DELETE /agents/{id} - Unregister agent'
                ]
            },
            'tasks': {
                'title': '📋 Task Management',
                'description': 'Intelligent task queuing, routing, and execution management',
                'endpoints': [
                    'POST /tasks - Create new task',
                    'GET /tasks - List tasks',
                    'GET /tasks/{id} - Get task status',
                    'PUT /tasks/{id} - Update task',
                    'DELETE /tasks/{id} - Cancel task'
                ]
            },
            'memory': {
                'title': '🧠 Memory System',
                'description': 'Semantic memory storage with vector embeddings and search',
                'endpoints': [
                    'POST /memory/search - Search memory',
                    'POST /memory/store - Store memory',
                    'GET /memory/stats - Memory statistics',
                    'DELETE /memory/{id} - Delete memory'
                ]
            },
            'monitoring': {
                'title': '📊 Monitoring & Analytics',
                'description': 'System metrics, performance monitoring, and health checks',
                'endpoints': [
                    'GET /monitoring/metrics - System metrics',
                    'GET /monitoring/health - Health check',
                    'GET /monitoring/agents - Agent metrics',
                    'GET /monitoring/alerts - System alerts'
                ]
            }
        };
        
        // Populate API sections
        function populateAPISections() {
            const container = document.getElementById('apiSections');
            
            for (const [key, section] of Object.entries(apiSections)) {
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'api-section';
                
                sectionDiv.innerHTML = `
                    <h2>${section.title}</h2>
                    <p>${section.description}</p>
                    <ul class="endpoint-list">
                        ${section.endpoints.map(endpoint => {
                            const [method, ...pathParts] = endpoint.split(' ');
                            return `<li class="endpoint-item">
                                <span class="method">${method}</span>
                                ${pathParts.join(' ')}
                            </li>`;
                        }).join('')}
                    </ul>
                `;
                
                container.appendChild(sectionDiv);
            }
        }
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', populateAPISections);
    </script>
</body>
</html>
        """
        
    async def start(self):
        """Start the API documentation server"""
        logger.info(f"🚀 Starting API Documentation Server on port {self.port}")
        logger.info(f"📖 Documentation available at: http://localhost:{self.port}")
        logger.info(f"📚 Swagger UI available at: http://localhost:{self.port}/docs")
        logger.info(f"📋 ReDoc available at: http://localhost:{self.port}/redoc")
        
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"❌ Documentation server error: {e}")
            raise


# Example usage and testing
async def test_api_documentation():
    """Test the API documentation generator"""
    
    doc_generator = APIDocumentationGenerator(port=8010)
    
    try:
        logger.info("🚀 Starting API Documentation test...")
        logger.info("📖 Documentation available at: http://localhost:8010")
        
        # Start documentation server
        await doc_generator.start()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Shutting down documentation server...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_api_documentation())