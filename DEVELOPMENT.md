# 🚀 Development Guide - vLLM Local Swarm

## 📋 Overview

This comprehensive development guide provides everything needed to contribute to the vLLM Local Swarm project. The platform follows security-first development practices with London TDD, zero-trust architecture, and enterprise-grade quality standards.

---

## 🎯 **Development Philosophy**

### **Core Principles**
1. **🔐 Security First**: Every feature starts with security considerations
2. **🧪 London TDD**: Test-driven development with 100% coverage requirement
3. **🏗️ Zero-Trust Architecture**: Nothing is trusted without verification
4. **📊 Complete Observability**: Every action must be traceable and auditable
5. **⚡ Performance Critical**: Optimized for AI/ML workloads and GPU efficiency
6. **📝 Documentation Driven**: Code is documentation, documentation is code

### **Quality Gates**
- ✅ **100% Test Coverage**: No exceptions, no compromises
- ✅ **Security Scanning**: Automated vulnerability detection
- ✅ **Type Safety**: Full TypeScript/Python type hints
- ✅ **Code Quality**: Automated linting and formatting
- ✅ **Performance Testing**: Load and stress testing required
- ✅ **Documentation**: Complete API and architectural docs

---

## 🛠️ **Development Environment Setup**

### **Prerequisites**

#### Required Tools
```bash
# Core development tools
git >= 2.40.0
python >= 3.11.0
node.js >= 18.0.0
docker >= 24.0.0
docker-compose >= 2.20.0

# Python development
poetry >= 1.6.0
# OR
pip >= 23.0.0

# Testing and quality
pytest >= 7.4.0
mypy >= 1.17.0
black >= 23.0.0
ruff >= 0.5.0
bandit >= 1.7.0
```

#### Optional but Recommended
```bash
# GPU development (for vLLM)
nvidia-docker2
nvidia-container-toolkit
cuda >= 11.8

# Advanced tooling
k9s               # Kubernetes debugging
lazydocker        # Docker TUI
httpie           # API testing
jq               # JSON processing
```

### **Initial Setup**

#### 1. Repository Setup
```bash
# Clone repository
git clone https://github.com/tbowman01/vllm-local-swarm
cd vllm-local-swarm

# Set up git hooks
git config core.hooksPath .githooks
chmod +x .githooks/*

# Configure git for security
git config --local user.name "Your Name"
git config --local user.email "your.email@company.com"
git config --local commit.gpgsign true
```

#### 2. Python Environment
```bash
# Using Poetry (recommended)
poetry install --with dev,test
poetry shell

# OR using pip + venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.dev.txt
```

#### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Configure for development
cat > .env << 'EOF'
# Development Configuration
NODE_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database URLs
DATABASE_URL=postgresql+asyncpg://langfuse:langfuse123@localhost:5432/auth
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# Authentication
JWT_SECRET_KEY=dev-jwt-secret-key-change-this-in-production-min32chars
API_SECRET_KEY=dev-api-secret-key-for-service-communication

# Observability
LANGFUSE_SECRET_KEY=sk-lf-development-key
LANGFUSE_PUBLIC_KEY=pk-lf-development-key
LANGFUSE_HOST=http://localhost:3000

# AI/ML Configuration
VLLM_GPU_MEMORY_UTILIZATION=0.90
VLLM_MAX_MODEL_LEN=16384
OPENAI_API_KEY=your-openai-key-for-testing
ANTHROPIC_API_KEY=your-claude-key-for-testing
EOF
```

#### 4. Infrastructure Services
```bash
# Start required infrastructure
docker-compose up -d redis langfuse-db qdrant langfuse-web

# Verify services are running
docker-compose ps
curl http://localhost:6379/ping  # Redis
curl http://localhost:6333/      # Qdrant
curl http://localhost:3000       # Langfuse
```

#### 5. Development Database Setup
```bash
# Create auth database
docker exec vllm-langfuse-db psql -U langfuse -c "CREATE DATABASE auth;"

# Run database migrations
python -c "
from auth.database import create_tables
import asyncio
asyncio.run(create_tables())
"

# Create admin user
python -c "
from auth.auth_service import create_admin_user
import asyncio
asyncio.run(create_admin_user('admin', 'admin@localhost', 'DevPassword123!'))
"
```

---

## 🧪 **Testing Framework**

### **London TDD Workflow**

#### Phase 1: RED (Write Failing Tests)
```bash
# ALWAYS write tests first
# Example: Adding new authentication feature

# 1. Write failing unit test
cat > tests/auth/test_new_feature.py << 'EOF'
import pytest
from auth.new_feature import NewFeature

def test_new_feature_authentication():
    """Test new feature requires authentication"""
    feature = NewFeature()
    
    with pytest.raises(AuthenticationError):
        feature.process_without_auth()

def test_new_feature_with_valid_token():
    """Test new feature works with valid JWT"""
    feature = NewFeature()
    token = "valid-jwt-token"
    
    result = feature.process_with_auth(token)
    assert result.success is True
    assert result.user_id is not None
EOF

# 2. Run test - MUST FAIL
pytest tests/auth/test_new_feature.py -v
# ❌ EXPECTED: Tests should fail (RED phase)
```

#### Phase 2: GREEN (Write Minimal Implementation)
```bash
# 3. Write minimal code to pass tests
cat > auth/new_feature.py << 'EOF'
from auth.exceptions import AuthenticationError
from auth.jwt_manager import validate_jwt

class NewFeature:
    def process_without_auth(self):
        raise AuthenticationError("Authentication required")
    
    def process_with_auth(self, token):
        user_id = validate_jwt(token)
        return {"success": True, "user_id": user_id}
EOF

# 4. Run test - MUST PASS
pytest tests/auth/test_new_feature.py -v
# ✅ EXPECTED: Tests should pass (GREEN phase)
```

#### Phase 3: REFACTOR (Improve While Maintaining Tests)
```bash
# 5. Refactor and improve
# 6. Ensure tests still pass
pytest tests/auth/test_new_feature.py -v

# 7. Check coverage - MUST BE 100%
pytest tests/auth/test_new_feature.py --cov=auth.new_feature --cov-fail-under=100
# ✅ REQUIRED: 100% coverage
```

### **Test Categories**

#### 🔐 Security Tests (Highest Priority)
```bash
# Authentication tests
pytest tests/auth/test_authentication.py -v
pytest tests/auth/test_jwt_validation.py -v  
pytest tests/auth/test_api_keys.py -v

# Authorization tests
pytest tests/auth/test_permissions.py -v
pytest tests/auth/test_rbac.py -v

# Input validation tests
pytest tests/security/test_input_validation.py -v
pytest tests/security/test_sql_injection.py -v
pytest tests/security/test_xss_prevention.py -v

# Run all security tests
pytest tests/security/ tests/auth/ -v --cov=auth --cov-fail-under=100
```

#### 🧠 Agent & Memory Tests
```bash
# Agent coordination tests
pytest tests/agents/test_task_assignment.py -v
pytest tests/agents/test_collision_prevention.py -v
pytest tests/agents/test_memory_persistence.py -v

# Memory system tests  
pytest tests/memory/test_vector_storage.py -v
pytest tests/memory/test_context_retrieval.py -v
pytest tests/memory/test_audit_trails.py -v

# Integration tests
pytest tests/integration/test_agent_workflows.py -v
```

#### 🔄 Integration Tests
```bash
# End-to-end workflow tests
pytest tests/integration/test_e2e_workflows.py -v

# Service communication tests
pytest tests/integration/test_service_mesh.py -v

# Database integration tests
pytest tests/integration/test_database_operations.py -v

# Run all integration tests
pytest tests/integration/ -v --maxfail=1
```

#### ⚡ Performance Tests
```bash
# Load testing
pytest tests/performance/test_authentication_load.py -v --benchmark-only
pytest tests/performance/test_memory_operations.py -v --benchmark-only

# Stress testing
pytest tests/performance/test_concurrent_requests.py -v
pytest tests/performance/test_memory_usage.py -v

# GPU performance testing
pytest tests/performance/test_vllm_inference.py -v --gpu-required
```

### **Running Test Suites**

```bash
# Quick development test run
pytest tests/unit/ -v --maxfail=5 -x

# Full test suite with coverage
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing --cov-fail-under=100

# Security-focused test run  
pytest tests/security/ tests/auth/ -v --tb=short

# Performance benchmarking
pytest tests/performance/ -v --benchmark-only --benchmark-sort=mean

# Continuous testing (watch mode)
ptw . --runner "pytest tests/unit/ -v"
```

---

## 🏗️ **Architecture & Code Organization**

### **Project Structure**

```
vllm-local-swarm/
├── auth/                     # 🔐 Authentication service
│   ├── __init__.py
│   ├── auth_service.py       # Main FastAPI service
│   ├── database.py           # SQLAlchemy models
│   ├── jwt_manager.py        # JWT token handling
│   ├── middleware.py         # Auth middleware
│   └── exceptions.py         # Custom exceptions
├── orchestrator/             # 🧠 SPARC orchestration
│   ├── __init__.py
│   ├── sparc_workflow.py     # Main workflow engine
│   ├── agent_coordinator.py  # Agent management
│   └── task_manager.py       # Task distribution
├── memory/                   # 💾 Memory & vector storage
│   ├── __init__.py
│   ├── core/
│   │   ├── memory_manager.py # Core memory operations
│   │   └── vector_store.py   # Qdrant integration
│   └── adapters/
│       ├── redis_adapter.py  # Redis caching
│       └── postgres_adapter.py # Audit storage
├── tests/                    # 🧪 Test suites
│   ├── auth/                 # Auth service tests
│   ├── orchestrator/         # Orchestrator tests
│   ├── memory/               # Memory system tests
│   ├── integration/          # E2E tests
│   ├── security/             # Security tests
│   └── performance/          # Performance tests
├── docker/                   # 🐳 Container definitions
│   ├── Dockerfile.auth
│   ├── Dockerfile.orchestrator
│   └── Dockerfile.memory-api
├── docs/                     # 📚 Documentation
├── scripts/                  # 🔧 Utility scripts
└── .github/                  # 🤖 CI/CD workflows
```

### **Coding Standards**

#### Python Code Style
```bash
# Formatting (required)
black . --line-length=88
isort . --profile black

# Linting (required)
ruff check . --select E,W,F,I,N,UP,S,B
mypy . --strict

# Security scanning (required)
bandit -r auth/ orchestrator/ memory/ -f json
safety check --json

# Type checking example
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')

async def authenticate_user(request: AuthRequest) -> Dict[str, Union[str, bool]]:
    """Authenticate user with comprehensive type safety."""
    # Implementation with full type hints
```

#### Security Patterns
```python
# ALWAYS use these security patterns

# 1. Input validation
from pydantic import BaseModel, validator
from auth.exceptions import ValidationError

class UserInput(BaseModel):
    username: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

# 2. SQL injection prevention  
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user_safe(db: AsyncSession, username: str):
    # ✅ CORRECT: Using parameterized queries
    result = await db.execute(
        text("SELECT * FROM users WHERE username = :username"),
        {"username": username}
    )
    return result.fetchone()

# 3. Authentication decorators
from functools import wraps
from auth.jwt_manager import verify_jwt

def require_auth(permissions: List[str] = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            token = request.headers.get("Authorization")
            user = await verify_jwt(token)
            
            if permissions and not user.has_permissions(permissions):
                raise PermissionError("Insufficient permissions")
                
            return await func(request, user=user, *args, **kwargs)
        return wrapper
    return decorator

# 4. Audit logging
from auth.audit import AuditLogger

audit_logger = AuditLogger()

@audit_logger.log_action("user_login")
async def login_user(username: str, password: str):
    # All actions automatically logged with context
    pass
```

---

## 🔄 **Development Workflow**

### **Feature Development Process**

#### 1. Planning Phase
```bash
# Create feature branch
git checkout -b feature/user-session-management

# Update TODO list with feature breakdown
# Use Claude Code TodoWrite to track tasks:
# - Write security tests for session management
# - Implement JWT refresh token rotation
# - Add session invalidation endpoints  
# - Create audit trail for session events
# - Add rate limiting for login attempts
# - Document new security endpoints
```

#### 2. London TDD Implementation
```bash
# RED: Write failing tests first
mkdir -p tests/auth/
touch tests/auth/test_session_management.py

# Write comprehensive failing tests
pytest tests/auth/test_session_management.py -v  # Should fail

# GREEN: Implement minimal code
touch auth/session_manager.py
# Write minimal implementation
pytest tests/auth/test_session_management.py -v  # Should pass

# REFACTOR: Improve code quality
# Refactor while maintaining green tests
pytest tests/auth/test_session_management.py --cov=auth.session_manager --cov-fail-under=100
```

#### 3. Security & Quality Validation
```bash
# Run security tests
pytest tests/security/ -v -k session
bandit -r auth/session_manager.py -f json

# Type checking
mypy auth/session_manager.py --strict

# Code quality
black auth/session_manager.py
ruff check auth/session_manager.py --select S,B

# Integration testing
pytest tests/integration/ -v -k session
```

#### 4. Documentation & PR
```bash
# Update API documentation
# Add to README.md or API docs

# Create comprehensive commit
git add .
git commit -m "🔐 feat: Add secure session management with JWT refresh

- Implement JWT refresh token rotation
- Add session invalidation endpoints
- Include comprehensive audit logging
- Add rate limiting for authentication
- 100% test coverage maintained
- Security scans passing

🧪 Generated with London TDD methodology
🛡️ Security-first implementation

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and create PR
git push origin feature/user-session-management
gh pr create --title "🔐 Add secure session management" --body "..."
```

### **Daily Development Workflow**

```bash
# Morning startup routine
cd vllm-local-swarm

# 1. Update codebase
git checkout main
git pull origin main

# 2. Start infrastructure
docker-compose up -d redis langfuse-db qdrant langfuse-web

# 3. Activate environment
poetry shell  # or source venv/bin/activate

# 4. Run health checks
python -c "
import asyncio
from auth.database import test_connection
asyncio.run(test_connection())
print('✅ Database connection OK')
"

curl http://localhost:6379/ping && echo " - Redis OK"
curl http://localhost:6333/ && echo " - Qdrant OK"
curl http://localhost:3000 && echo " - Langfuse OK"

# 5. Run test suite
pytest tests/unit/ -v --maxfail=3

# 6. Ready for development!
echo "🚀 Development environment ready!"
```

### **Code Review Process**

#### Pre-Review Checklist
```bash
# Before requesting review, ensure:

# ✅ All tests pass
pytest tests/ --cov=. --cov-fail-under=100

# ✅ Security scans pass
bandit -r . -f json
safety check --json
ruff check . --select S,B

# ✅ Type checking passes
mypy . --strict

# ✅ Code formatting applied
black . --check
isort . --check-only --profile black

# ✅ Performance tests pass
pytest tests/performance/ -v --benchmark-only

# ✅ Documentation updated
# Check that all new features are documented
```

#### Review Criteria
1. **🔐 Security**: All security patterns followed
2. **🧪 Testing**: 100% coverage with meaningful tests
3. **📝 Documentation**: Clear and comprehensive
4. **⚡ Performance**: No performance regressions
5. **🏗️ Architecture**: Follows existing patterns
6. **🔍 Observability**: Proper logging and tracing

---

## 🔧 **Development Tools & Scripts**

### **Utility Scripts**

#### Development Helper Scripts
```bash
# Create executable scripts
mkdir -p scripts/dev

# Health check script
cat > scripts/dev/health-check.sh << 'EOF'
#!/bin/bash
echo "🔍 Checking service health..."

services=("redis:6379" "langfuse-db:5432" "qdrant:6333" "langfuse:3000")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if nc -z localhost $port; then
        echo "✅ $name is running on port $port"
    else
        echo "❌ $name is not accessible on port $port"
    fi
done
EOF
chmod +x scripts/dev/health-check.sh

# Database reset script
cat > scripts/dev/reset-database.sh << 'EOF'
#!/bin/bash
echo "🗄️ Resetting development database..."

docker exec vllm-langfuse-db psql -U langfuse -c "DROP DATABASE IF EXISTS auth;"
docker exec vllm-langfuse-db psql -U langfuse -c "CREATE DATABASE auth;"

python -c "
from auth.database import create_tables
import asyncio
asyncio.run(create_tables())
print('✅ Database tables created')
"

python -c "
from auth.auth_service import create_admin_user
import asyncio
asyncio.run(create_admin_user('admin', 'admin@localhost', 'DevPassword123!'))
print('✅ Admin user created')
"
EOF
chmod +x scripts/dev/reset-database.sh

# Full test runner
cat > scripts/dev/run-tests.sh << 'EOF'
#!/bin/bash
echo "🧪 Running comprehensive test suite..."

# Unit tests with coverage
echo "1️⃣ Running unit tests..."
pytest tests/unit/ --cov=. --cov-report=html --cov-fail-under=100

# Security tests  
echo "2️⃣ Running security tests..."
pytest tests/security/ tests/auth/ -v

# Integration tests
echo "3️⃣ Running integration tests..."
pytest tests/integration/ -v

# Performance tests
echo "4️⃣ Running performance tests..."
pytest tests/performance/ -v --benchmark-only

echo "✅ All tests completed!"
EOF
chmod +x scripts/dev/run-tests.sh
```

#### Code Quality Scripts
```bash
# Comprehensive code quality check
cat > scripts/dev/quality-check.sh << 'EOF'
#!/bin/bash
echo "🔍 Running code quality checks..."

# Formatting check
echo "Checking code formatting..."
black . --check --diff
isort . --check-only --diff --profile black

# Linting
echo "Running linting..."
ruff check . --select E,W,F,I,N,UP,S,B

# Type checking
echo "Running type checker..."
mypy . --strict

# Security scanning
echo "Running security scans..."
bandit -r auth/ orchestrator/ memory/ -f json
safety check --json

# Dependency checking
echo "Checking dependencies..."
pip-audit

echo "✅ Quality checks completed!"
EOF
chmod +x scripts/dev/quality-check.sh
```

### **Development Shortcuts**

```bash
# Add to ~/.bashrc or ~/.zshrc
alias vllm-dev="cd ~/Projects/vllm-local-swarm && poetry shell"
alias vllm-test="./scripts/dev/run-tests.sh"
alias vllm-quality="./scripts/dev/quality-check.sh"
alias vllm-health="./scripts/dev/health-check.sh"
alias vllm-reset="./scripts/dev/reset-database.sh"

# Quick service management
alias vllm-up="docker-compose up -d"
alias vllm-down="docker-compose down"
alias vllm-logs="docker-compose logs -f"
alias vllm-ps="docker-compose ps"
```

---

## 🚀 **Performance & Optimization**

### **Profiling & Monitoring**

#### Python Performance Profiling
```bash
# Install profiling tools
pip install py-spy memory_profiler line_profiler

# Profile authentication service
py-spy record -o auth-profile.svg -- python auth/auth_service.py

# Memory profiling
mprof run auth/auth_service.py
mprof plot

# Line-by-line profiling
kernprof -l -v auth/jwt_manager.py
```

#### Database Performance
```bash
# PostgreSQL query analysis
docker exec -it vllm-langfuse-db psql -U langfuse -c "
EXPLAIN ANALYZE SELECT * FROM users WHERE username = 'admin';
"

# Redis performance testing
docker exec -it vllm-redis redis-cli --latency-history -i 1

# Qdrant performance testing
curl -X POST http://localhost:6333/collections/memory/points/search \
  -H "Content-Type: application/json" \
  -d '{"vector": [0.1, 0.2, 0.3], "top": 10, "with_payload": true}'
```

#### Load Testing
```bash
# Install load testing tools
pip install locust httpx

# Create load test script
cat > tests/performance/load_test.py << 'EOF'
from locust import HttpUser, task, between

class AuthenticationUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login and get token
        response = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "DevPassword123!"
        })
        self.token = response.json()["access_token"]
        
    @task(3)
    def validate_token(self):
        self.client.get("/auth/validate", headers={
            "Authorization": f"Bearer {self.token}"
        })
        
    @task(1)
    def refresh_token(self):
        self.client.post("/auth/refresh", headers={
            "Authorization": f"Bearer {self.token}"
        })
EOF

# Run load test
locust -f tests/performance/load_test.py --host=http://localhost:8005
```

### **Optimization Strategies**

#### Code Optimization
```python
# Use async/await for I/O operations
import asyncio
import httpx
from functools import lru_cache

# ✅ GOOD: Async database operations
async def get_user_async(user_id: str) -> Optional[User]:
    async with get_db_session() as db:
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

# ✅ GOOD: Connection pooling
@lru_cache(maxsize=1)
def get_http_client():
    return httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )

# ✅ GOOD: Caching expensive operations
from functools import lru_cache
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

@lru_cache(maxsize=1000)
def get_user_permissions(user_id: str) -> List[str]:
    cached = redis_client.get(f"permissions:{user_id}")
    if cached:
        return json.loads(cached)
    
    # Expensive database operation
    permissions = fetch_permissions_from_db(user_id)
    redis_client.setex(f"permissions:{user_id}", 300, json.dumps(permissions))
    return permissions
```

#### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_users_username ON users(username);
CREATE INDEX CONCURRENTLY idx_sessions_user_id ON sessions(user_id);
CREATE INDEX CONCURRENTLY idx_audit_logs_timestamp ON audit_logs(timestamp);

-- Optimize queries with EXPLAIN ANALYZE
EXPLAIN ANALYZE SELECT u.*, s.session_id 
FROM users u 
JOIN sessions s ON u.id = s.user_id 
WHERE u.username = $1 AND s.expires_at > NOW();
```

---

## 📊 **Monitoring & Observability**

### **Application Metrics**

#### Custom Metrics Collection
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time
from functools import wraps

# Define metrics
auth_requests_total = Counter('auth_requests_total', 'Total authentication requests', ['method', 'status'])
auth_request_duration = Histogram('auth_request_duration_seconds', 'Authentication request duration')
active_sessions = Gauge('active_sessions_total', 'Number of active sessions')

# Metrics decorator
def track_metrics(metric_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                auth_requests_total.labels(method=func.__name__, status='success').inc()
                return result
            except Exception as e:
                auth_requests_total.labels(method=func.__name__, status='error').inc()
                raise
            finally:
                auth_request_duration.observe(time.time() - start_time)
        return wrapper
    return decorator

# Usage in authentication service
@track_metrics("authenticate_user")
async def authenticate_user(username: str, password: str):
    # Implementation with automatic metrics collection
    pass
```

#### Health Checks
```python
# health.py
from fastapi import APIRouter, Depends
from auth.database import get_db_session
from memory.vector_store import get_qdrant_client
import redis
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Database health
    try:
        async with get_db_session() as db:
            await db.execute(text("SELECT 1"))
        checks["services"]["database"] = "healthy"
    except Exception as e:
        checks["services"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
    
    # Redis health
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        checks["services"]["redis"] = "healthy"
    except Exception as e:
        checks["services"]["redis"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
    
    # Qdrant health
    try:
        client = get_qdrant_client()
        await client.get_collections()
        checks["services"]["qdrant"] = "healthy"
    except Exception as e:
        checks["services"]["qdrant"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
    
    return checks
```

---

## 🔒 **Security Development Practices**

### **Threat Modeling**

#### Security Assessment Checklist
```markdown
# Security Threat Model - Feature Development

## Data Flow Analysis
- [ ] Identify all data inputs and outputs
- [ ] Map data storage locations
- [ ] Document data transformation points
- [ ] Identify external dependencies

## Trust Boundaries  
- [ ] User → Application boundary
- [ ] Application → Database boundary
- [ ] Service → Service boundaries
- [ ] Application → External API boundaries

## Threat Categories (STRIDE)
- [ ] **Spoofing**: Identity verification mechanisms
- [ ] **Tampering**: Data integrity protections  
- [ ] **Repudiation**: Audit logging and non-repudiation
- [ ] **Information Disclosure**: Data protection measures
- [ ] **Denial of Service**: Rate limiting and resource protection
- [ ] **Elevation of Privilege**: Authorization controls

## Security Controls
- [ ] Input validation implemented
- [ ] Output encoding applied
- [ ] Authentication mechanisms in place
- [ ] Authorization checks implemented  
- [ ] Audit logging configured
- [ ] Error handling secures
```

### **Security Testing**

#### Automated Security Tests
```python
# tests/security/test_authentication_security.py
import pytest
from auth.auth_service import authenticate_user
from auth.exceptions import AuthenticationError

class TestAuthenticationSecurity:
    
    @pytest.mark.asyncio
    async def test_prevents_sql_injection(self):
        """Test SQL injection prevention"""
        malicious_inputs = [
            "admin'; DROP TABLE users; --",
            "admin' OR '1'='1",
            "admin' UNION SELECT * FROM passwords --"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(AuthenticationError):
                await authenticate_user(malicious_input, "password")
    
    @pytest.mark.asyncio
    async def test_prevents_timing_attacks(self):
        """Test timing attack prevention"""
        import time
        
        # Test with valid vs invalid usernames
        start_time = time.time()
        try:
            await authenticate_user("valid_user", "wrong_password")
        except AuthenticationError:
            pass
        valid_user_time = time.time() - start_time
        
        start_time = time.time()
        try:
            await authenticate_user("invalid_user", "wrong_password")
        except AuthenticationError:
            pass
        invalid_user_time = time.time() - start_time
        
        # Timing should be similar (within 10ms)
        assert abs(valid_user_time - invalid_user_time) < 0.01
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting prevents brute force"""
        # Attempt multiple failed logins
        for _ in range(10):
            with pytest.raises(AuthenticationError):
                await authenticate_user("admin", "wrong_password")
        
        # 11th attempt should be rate limited
        with pytest.raises(RateLimitExceeded):
            await authenticate_user("admin", "wrong_password")
```

---

## 📚 **Documentation Standards**

### **Code Documentation**

```python
# Example: Comprehensive function documentation
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def authenticate_user(
    username: str,
    password: str,
    request_ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Authenticate user credentials and return JWT token.
    
    This function implements secure authentication with:
    - Password hash verification using bcrypt
    - Rate limiting by IP address
    - Audit logging for security events
    - Timing attack prevention
    
    Args:
        username: User's login username (3-50 characters)
        password: Plain text password (will be hashed for comparison)
        request_ip: Client IP address for rate limiting (optional)
        
    Returns:
        Dictionary containing:
        - access_token: JWT access token (expires in 1 hour)
        - refresh_token: JWT refresh token (expires in 30 days)
        - user_id: Unique user identifier
        - expires_in: Token expiration time in seconds
        
    Raises:
        AuthenticationError: Invalid credentials provided
        RateLimitExceeded: Too many failed attempts from IP
        ValidationError: Invalid input format
        
    Example:
        >>> result = await authenticate_user("admin", "SecurePass123!")
        >>> print(result["access_token"])
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        
    Security Considerations:
        - Uses constant-time comparison to prevent timing attacks
        - Implements exponential backoff for failed attempts
        - Logs all authentication attempts for security monitoring
        - Never logs passwords or sensitive information
        
    Performance:
        - Average response time: 50-100ms
        - Cached user lookups reduce database queries
        - Rate limiting prevents DoS attacks
    """
    logger.info(f"Authentication attempt for username: {username}")
    
    # Implementation...
```

### **API Documentation**

```python
# Example: FastAPI with comprehensive documentation
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

app = FastAPI(
    title="vLLM Local Swarm Authentication API",
    description="""
    Secure authentication service for the vLLM Local Swarm platform.
    
    ## Features
    - JWT-based authentication
    - API key management  
    - Role-based access control
    - Comprehensive audit logging
    - Rate limiting and security controls
    
    ## Security
    All endpoints require authentication except for registration and login.
    Use Bearer token authentication for protected endpoints.
    
    ## Rate Limits
    - Login attempts: 5 per minute per IP
    - Token validation: 100 per minute per user
    - API key requests: 10 per minute per user
    """,
    version="2.0.0",
    contact={
        "name": "vLLM Local Swarm Team",
        "url": "https://github.com/tbowman01/vllm-local-swarm",
        "email": "support@vllm-swarm.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

class LoginRequest(BaseModel):
    """User login credentials."""
    username: str = Field(..., min_length=3, max_length=50, description="User's username")
    password: str = Field(..., min_length=8, description="User's password")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "admin",
                "password": "SecurePassword123!"
            }
        }

@app.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Authenticate user and return JWT tokens",
    description="""
    Authenticate user credentials and return JWT access and refresh tokens.
    
    **Security Features:**
    - bcrypt password hashing
    - Rate limiting (5 attempts per minute per IP)
    - Timing attack prevention
    - Comprehensive audit logging
    
    **Response:**
    Returns JWT tokens for API authentication. Access tokens expire in 1 hour,
    refresh tokens expire in 30 days.
    """,
    responses={
        200: {
            "description": "Authentication successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "expires_in": 3600,
                        "user_id": "12345"
                    }
                }
            }
        },
        401: {"description": "Invalid credentials"},
        429: {"description": "Rate limit exceeded"},
        422: {"description": "Invalid input format"}
    }
)
async def login(request: LoginRequest):
    """Authenticate user and return JWT tokens."""
    # Implementation...
```

---

## 🎯 **Contribution Guidelines**

### **Pull Request Process**

#### 1. Before Creating PR
```bash
# Ensure all quality gates pass
./scripts/dev/quality-check.sh
./scripts/dev/run-tests.sh

# Update documentation if needed
# Update CHANGELOG.md with changes
# Ensure all TODOs are addressed
```

#### 2. PR Description Template
```markdown
## 🎯 Description
Brief description of what this PR accomplishes.

## 🔐 Security Considerations
- [ ] Security threat model updated
- [ ] Input validation implemented
- [ ] Authentication/authorization tested
- [ ] No secrets exposed in code or logs
- [ ] Security tests added and passing

## 🧪 Testing
- [ ] Unit tests added/updated (100% coverage maintained)
- [ ] Integration tests passing
- [ ] Security tests passing
- [ ] Performance tests passing (if applicable)

## 📚 Documentation
- [ ] Code comments added for complex logic
- [ ] API documentation updated
- [ ] README updated (if needed)
- [ ] Architecture docs updated (if needed)

## ⚡ Performance Impact
- [ ] No performance regressions introduced
- [ ] Load testing completed (if applicable)
- [ ] Memory usage analyzed
- [ ] Database queries optimized

## 🔍 Review Checklist
- [ ] Code follows project conventions
- [ ] Security best practices followed
- [ ] Error handling implemented
- [ ] Logging and observability added
- [ ] Backward compatibility maintained

## 🚀 Deployment Notes
Any special deployment considerations or migration steps.
```

#### 3. Review Response
```bash
# Address review feedback
git checkout feature/branch-name

# Make requested changes
# Run quality checks again
./scripts/dev/quality-check.sh

# Commit changes
git add .
git commit -m "📝 docs: Address review feedback

- Fixed typo in documentation
- Updated test case for edge condition
- Improved error message clarity"

git push origin feature/branch-name
```

### **Release Process**

#### Version Management
```bash
# Update version numbers
# Follow semantic versioning: MAJOR.MINOR.PATCH

# Create release branch
git checkout -b release/v2.1.0

# Update version files
echo "2.1.0" > VERSION
sed -i 's/version = ".*"/version = "2.1.0"/' pyproject.toml

# Update CHANGELOG.md
cat >> CHANGELOG.md << 'EOF'
## [2.1.0] - 2025-08-10

### Added
- Secure session management with JWT refresh token rotation
- Advanced agent memory anti-collision system
- Multi-architecture container builds (AMD64, ARM64)
- Comprehensive security testing suite

### Changed
- Improved authentication performance by 40%
- Enhanced observability with detailed metrics
- Updated documentation with development guides

### Fixed
- Security vulnerability in token validation
- Memory leak in agent coordination
- Container build optimization issues
EOF

# Create release commit
git add .
git commit -m "🚀 release: Prepare v2.1.0

- Update version to 2.1.0
- Update CHANGELOG with new features
- Prepare for production release"

# Create and push tag
git tag -a v2.1.0 -m "Release version 2.1.0"
git push origin v2.1.0

# Merge to main
git checkout main
git merge release/v2.1.0
git push origin main
```

---

## 🎉 **Success Metrics**

### **Development Quality Metrics**
- ✅ **100% Test Coverage**: Maintained across all code
- ✅ **Zero Critical Security Issues**: Automated scanning
- ✅ **Sub-100ms Response Time**: Authentication endpoints
- ✅ **99.9% Uptime**: Production environment
- ✅ **Complete Documentation**: All APIs documented

### **Team Productivity Metrics**  
- ✅ **Same-Day PR Reviews**: 95% of PRs reviewed within 24 hours
- ✅ **Fast CI/CD**: Full pipeline under 10 minutes
- ✅ **Developer Onboarding**: New developers productive in 1 day
- ✅ **Issue Resolution**: 90% of bugs fixed within 1 week
- ✅ **Feature Delivery**: Regular fortnightly releases

---

## 🔗 **Resources & References**

### **Official Documentation**
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async Tutorial](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [Pytest Documentation](https://docs.pytest.org/)

### **Security Resources**
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [Python Security Guidelines](https://python.org/dev/security/)
- [Container Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

### **Testing Resources**
- [London TDD Methodology](https://github.com/testdouble/contributing-tests/wiki/London-school-TDD)
- [Property-Based Testing](https://hypothesis.readthedocs.io/)
- [Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)

---

**🎉 Welcome to the vLLM Local Swarm development team! Let's build secure, performant, and well-tested AI infrastructure together!**

*Last Updated: August 10, 2025*  
*Development Framework: London TDD + Security-First*  
*Quality Standard: Enterprise-Grade with 100% Test Coverage*