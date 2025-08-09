# Claude Code Configuration for vLLM Local Swarm with Authentication

## 🔐 PROJECT OVERVIEW: vLLM Local Swarm Authentication System

This is an **enterprise-grade AI/ML orchestration platform** with comprehensive authentication:
- **Multi-model vLLM serving** (Phi-3.5, configurable large models)
- **SPARC workflow orchestration** with agent coordination
- **JWT + API Key authentication** with role-based permissions
- **Distributed memory system** (Redis + Qdrant + PostgreSQL)
- **Production-ready deployment** with Docker & Nginx

### 🏗️ Core Architecture Components:
- **Authentication Service** (`auth/`) - JWT/API key management with PostgreSQL
- **Orchestrator Service** (`docker/scripts/`) - SPARC workflow coordination
- **Memory System** (`memory/`) - Distributed storage with Redis/Qdrant
- **vLLM Serving** - Local model hosting with GPU acceleration
- **Agent Framework** (`agents/`) - Specialized AI agents (coder, QA, researcher)
- **Observability** - Langfuse tracing + ClickHouse analytics

## 🚀 AUTHENTICATION-FIRST DEVELOPMENT PRACTICES

### 🔐 Security Commands (High Priority)
```bash
# Always test authentication first
npm run test:auth
pytest tests/test_authentication.py
docker-compose -f docker-compose.auth.yml logs auth-service

# Lint security-critical code
black auth/ --check
mypy auth/ --strict
ruff auth/ --select S  # Security lints

# Authentication service health
curl http://localhost:8005/health
curl -X POST http://localhost:8005/auth/verify-permission
```

### 🛡️ Production Security Checklist
Before deploying ANY changes:
1. **Authentication tests pass** - `pytest tests/test_authentication.py -v`
2. **JWT secret configured** - Check `JWT_SECRET_KEY` env var
3. **API keys secured** - No plaintext keys in logs/database
4. **Rate limiting active** - Nginx config applied
5. **HTTPS configured** - SSL certificates in place
6. **Database encrypted** - PostgreSQL with proper auth
7. **Redis secured** - Password protected if exposed

## 🚨 MANDATORY PARALLEL EXECUTION RULES

**CRITICAL**: This project requires extreme performance due to LLM inference costs and multi-service coordination.

### ⚡ GOLDEN RULES FOR vLLM SWARM:

1. **TodoWrite**: ALWAYS batch 8-12+ todos (authentication adds complexity)
2. **Authentication checks**: Batch ALL auth verifications together
3. **Service calls**: Parallel calls to orchestrator + memory + auth services
4. **Docker operations**: Start ALL containers simultaneously
5. **File operations**: Read/Write auth configs + service files together
6. **Git operations**: Commit auth changes + service updates together

### 🔐 Authentication-Specific Batching:

```javascript
// ✅ CORRECT - Batch all authentication operations
[Single Message]:
  // Authentication system setup
  - Read("auth/auth_service.py")
  - Read("auth/middleware.py") 
  - Read("docker-compose.auth.yml")
  - Write("auth/config.py", config)
  - Write(".env.auth", env_vars)
  - Bash("docker-compose -f docker-compose.auth.yml up -d auth-service")
  - Bash("curl -f http://localhost:8005/health")
  - Bash("pytest tests/test_authentication.py -v")
  
  // Service integration
  - Edit("docker/scripts/orchestrator_server.py", add_auth_middleware)
  - Edit("memory/core/memory_manager.py", add_user_context)
  - TodoWrite({ todos: [
      {id: "auth-setup", content: "Configure authentication service", status: "in_progress"},
      {id: "middleware", content: "Add auth middleware to all services", status: "pending"},
      {id: "user-mgmt", content: "Implement user management", status: "pending"},
      {id: "api-keys", content: "Setup API key management", status: "pending"},
      {id: "permissions", content: "Configure role-based permissions", status: "pending"},
      {id: "rate-limit", content: "Implement rate limiting", status: "pending"},
      {id: "monitoring", content: "Add auth metrics to observability", status: "pending"},
      {id: "docs-update", content: "Update API documentation", status: "pending"}
    ]})
```

### 🐝 vLLM Swarm Orchestration Pattern:

When working with this project, IMMEDIATELY spawn specialized agents:

```javascript
// ✅ MANDATORY for vLLM Swarm tasks
[BatchTool - Agent Spawn]:
  - mcp__claude-flow__swarm_init { 
      topology: "hierarchical", 
      maxAgents: 8,  // Optimal for AI/ML projects
      strategy: "specialized",
      project_type: "vllm-auth-swarm"
    }
  
  // Spawn vLLM-specialized agents
  - mcp__claude-flow__agent_spawn { type: "auth-architect", name: "Security Lead" }
  - mcp__claude-flow__agent_spawn { type: "ml-engineer", name: "vLLM Specialist" }
  - mcp__claude-flow__agent_spawn { type: "orchestration-expert", name: "SPARC Coordinator" }
  - mcp__claude-flow__agent_spawn { type: "devops-engineer", name: "Docker Specialist" }
  - mcp__claude-flow__agent_spawn { type: "qa-security", name: "Auth Tester" }
  - mcp__claude-flow__agent_spawn { type: "performance-analyst", name: "GPU Optimizer" }
```

## 🎯 PROJECT-SPECIFIC DEVELOPMENT COMMANDS

### 🔧 Authentication & Security
```bash
# Start authenticated stack
docker-compose -f docker-compose.yml -f docker-compose.auth.yml up -d

# Test authentication flow
curl -X POST http://localhost:8005/auth/register -d '{"username":"test","email":"test@example.com","password":"SecurePass123!"}'
curl -X POST http://localhost:8005/auth/login -d '{"username":"test","password":"SecurePass123!"}'

# Verify service integration
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8006/tasks
curl -H "X-API-Key: <API_KEY>" http://localhost:8006/stats

# Security testing
pytest tests/test_authentication.py -v --cov=auth
bandit -r auth/ -f json
```

### 🤖 vLLM Model Serving
```bash
# GPU verification
nvidia-smi
docker run --gpus all nvidia/cuda:11.8-base-ubuntu20.04 nvidia-smi

# Start model services
docker-compose up -d vllm-phi vllm-large
curl http://localhost:8000/v1/models
curl http://localhost:8001/v1/models

# Test inference
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"model":"phi-3.5-mini","messages":[{"role":"user","content":"Hello"}]}'
```

### 🧠 Memory & Orchestration
```bash
# Memory system health
docker-compose logs memory-api
curl http://localhost:8003/health

# SPARC workflow testing
curl -X POST http://localhost:8006/tasks \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"objective":"Test auth integration","task_definition":"Verify authentication works"}'

# Agent coordination
curl http://localhost:8006/agents/query \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"agent_type":"researcher","task_description":"Analyze performance"}'
```

### 📊 Observability & Monitoring
```bash
# Langfuse dashboard
open http://localhost:3000

# Service metrics
curl http://localhost:8005/stats  # Auth service
curl http://localhost:8006/stats  # Orchestrator
curl http://localhost:8003/stats  # Memory

# Performance monitoring
docker stats
docker-compose -f docker-compose.yml -f docker-compose.auth.yml logs -f
```

## 🔐 AUTHENTICATION INTEGRATION PATTERNS

### 🛡️ Adding Auth to New Services

When creating new services in this project:

```python
# ALWAYS use this pattern for FastAPI services
from auth.middleware import AuthenticationMiddleware, AuthConfig, require_auth

app = FastAPI()

# Configure authentication
auth_config = AuthConfig(
    auth_service_url="http://auth-service:8005",
    jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
    required_permissions=["service_name.access"],
    allow_anonymous=False  # Strict security
)

app.add_middleware(AuthenticationMiddleware, config=auth_config)

@app.get("/protected-endpoint")
@require_auth(["service_name.read"])
async def protected_endpoint(request: Request):
    user = get_current_user(request)
    return {"message": f"Hello {user['username']}"}
```

### 🔑 API Key Management for Services

```python
# For service-to-service communication
async def call_authenticated_service(endpoint: str, data: dict):
    api_key = os.getenv("VLLM_INTERNAL_API_KEY")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            endpoint,
            json=data,
            headers={"X-API-Key": api_key},
            timeout=30.0
        )
        return response.json()
```

## 🎯 PERMISSION SYSTEM FOR vLLM SWARM

### 👥 Role Definitions
- **admin**: Full system access, can manage users and services
- **ml-engineer**: Access to model serving, training, and inference
- **developer**: Access to orchestration and memory systems
- **analyst**: Read-only access to metrics and results
- **user**: Basic access to query agents and view own tasks

### 🔐 Permission Matrix
```python
ROLE_PERMISSIONS = {
    "admin": ["*"],
    "ml-engineer": [
        "models.*", "inference.*", "training.*",
        "orchestrator.tasks.*", "memory.write"
    ],
    "developer": [
        "orchestrator.*", "agents.*", "memory.*",
        "tasks.create", "tasks.read", "tasks.update"
    ],
    "analyst": [
        "tasks.read", "memory.read", "stats.read",
        "metrics.*", "observability.*"
    ],
    "user": [
        "tasks.create", "tasks.read", "agents.query",
        "memory.read:own"  # Only own memory
    ]
}
```

## 📊 PERFORMANCE OPTIMIZATION FOR AI/ML

### ⚡ GPU Memory Management
```python
# GPU optimization settings for vLLM
VLLM_OPTIMIZATIONS = {
    "gpu_memory_utilization": 0.8,
    "max_model_len": 32768,
    "tensor_parallel_size": 2,
    "pipeline_parallel_size": 1,
    "quantization": "awq",  # For memory efficiency
    "max_num_batched_tokens": 8192,
    "max_num_seqs": 64
}
```

### 🧠 Memory System Tuning
```python
# Redis configuration for high-performance caching
REDIS_CONFIG = {
    "maxmemory": "4gb",
    "maxmemory_policy": "allkeys-lru",
    "save": "900 1 300 10 60 10000",  # Persistence
    "tcp_keepalive": 300,
    "timeout": 300
}

# Qdrant vector database optimization
QDRANT_CONFIG = {
    "hnsw_ef": 128,
    "hnsw_m": 16,
    "vector_size": 1536,  # For text-embedding-3-small
    "distance": "Cosine",
    "shard_number": 2
}
```

## 🔄 WORKFLOW AUTOMATION HOOKS

### 🚀 Pre-Operation Hooks
```bash
# Authentication verification before operations
npx claude-flow@alpha hooks pre-auth-check --verify-tokens --check-permissions

# GPU availability check before model operations
npx claude-flow@alpha hooks pre-gpu-check --required-memory 4GB --verify-cuda

# Service dependency check
npx claude-flow@alpha hooks pre-service-check --services redis,postgresql,qdrant
```

### 📈 Post-Operation Hooks
```bash
# Performance metrics collection
npx claude-flow@alpha hooks post-metrics --gpu-usage --memory-usage --inference-time

# Security audit logging
npx claude-flow@alpha hooks post-security-log --user-actions --permission-checks

# Model performance tracking
npx claude-flow@alpha hooks post-model-metrics --token-usage --response-quality
```

## 🐳 DOCKER DEPLOYMENT PROFILES

### 🔐 Authentication-Enabled Profiles

```bash
# Development with auth
docker-compose -f docker-compose.yml -f docker-compose.auth.yml up -d

# Production with full security
docker-compose -f docker-compose.yml -f docker-compose.auth.yml --profile auth-full up -d

# With nginx reverse proxy
docker-compose -f docker-compose.yml -f docker-compose.auth.yml --profile auth-proxy up -d

# High-performance GPU cluster
docker-compose -f docker-compose.yml --profile large-model --profile gpu-cluster up -d
```

### 🏗️ Service Dependencies
Always start services in this order:
1. **Foundation**: `redis`, `langfuse-db`, `qdrant`
2. **Authentication**: `auth-service`
3. **Core**: `memory-api`, `orchestrator-auth`
4. **AI/ML**: `vllm-phi`, `vllm-large`
5. **Observability**: `langfuse-web`, `langfuse-worker`
6. **Optional**: `nginx-auth`, `open-webui`

## 📚 DOCUMENTATION STANDARDS

### 🔐 Security Documentation Requirements
Always document:
- **Authentication flows** with sequence diagrams
- **Permission matrices** with role explanations
- **API key management** procedures
- **Security testing** procedures
- **Incident response** plans

### 🤖 AI/ML Documentation Requirements
Always document:
- **Model configurations** and performance benchmarks
- **GPU requirements** and scaling guidelines
- **Inference patterns** and optimization tips
- **Agent behavior** and coordination protocols
- **Memory usage** patterns and cleanup procedures

## 🧪 TESTING STRATEGY

### 🔐 Authentication Testing (Priority 1)
```python
# Always run these tests first
pytest tests/test_authentication.py -v
pytest tests/test_auth_middleware.py -v
pytest tests/test_permissions.py -v

# Security testing
bandit -r auth/ -f json
safety check --json
semgrep --config=p/security-audit auth/
```

### 🤖 AI/ML System Testing
```python
# Model serving tests
pytest tests/test_vllm_integration.py -v
pytest tests/test_orchestrator.py -v
pytest tests/test_memory_system.py -v

# Performance tests
pytest tests/test_performance.py -v --benchmark-only
pytest tests/test_gpu_memory.py -v
```

### 🏗️ Integration Testing
```bash
# End-to-end authentication flow
pytest tests/integration_e2e.py::test_auth_workflow -v

# Multi-service coordination
pytest tests/integration_e2e.py::test_sparc_workflow -v

# Load testing with authentication
locust -f tests/load_test_auth.py --host=http://localhost:8006
```

## 🚨 EMERGENCY PROCEDURES

### 🔐 Security Incident Response
1. **Immediately revoke** compromised API keys via auth service
2. **Blacklist** suspicious JWT tokens in Redis
3. **Check logs** for unauthorized access patterns
4. **Rotate** JWT secret and restart auth service
5. **Audit** all user permissions and recent activities

### 🔧 Service Recovery
1. **Health check** all services: `./scripts/health-check.sh`
2. **Restart** failed services: `docker-compose restart <service>`
3. **Check** GPU memory: `nvidia-smi` and restart vLLM if needed
4. **Verify** authentication: `curl http://localhost:8005/health`
5. **Monitor** Langfuse for error patterns

## 🎯 SUCCESS METRICS

### 🔐 Security Metrics
- **Authentication success rate**: >99.5%
- **API key usage**: Properly attributed to users
- **Permission denials**: <1% false positives
- **JWT token refresh**: <5% failure rate
- **Rate limiting**: Effective against abuse

### ⚡ Performance Metrics
- **Model inference**: <2s average response time
- **Memory operations**: <100ms average latency
- **Task orchestration**: <5s end-to-end workflow
- **GPU utilization**: >70% during inference
- **Token efficiency**: <$0.01 per SPARC workflow

---

## 🎉 DEVELOPMENT PHILOSOPHY

**This is an enterprise-grade AI platform with security-first design.**

- **Authentication is not optional** - Every endpoint must be protected
- **Performance matters** - LLM inference is expensive, optimize everything
- **Observability is critical** - Log all security and performance events
- **Scalability is required** - Design for multi-GPU and multi-node deployment
- **Quality is non-negotiable** - Comprehensive testing at every layer

**Remember**: You're building a production AI platform that handles sensitive data and expensive compute resources. Security and performance are equally critical.

🤖 **Generated and customized for vLLM Local Swarm with enterprise authentication**

Co-Authored-By: Claude <noreply@anthropic.com>