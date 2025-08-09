# vllm-local-swarm

**Slogan:**

> "Collaborative AI, Local Performance"

---

## Overview

This project deploys a **fully self-hosted, SPARC-aligned multi-agent LLM swarm** with **enterprise-grade authentication** using open-source technologies. It is designed for local-first, scalable, and feedback-driven collaborative AI with comprehensive security and user management.

### 🎯 Key Capabilities

* **🔐 Enterprise Authentication**: JWT + API key dual authentication with role-based access control
* Modular agents (Planner, Researcher, Coder, QA, Critic, Judge)
* Distributed orchestration with Ray (SwarmCoordinator)
* Fast local inference with vLLM (Phi-3.5, Gemini 1.5 Pro)
* Optional fallback to GPT-4.1 via proxy
* **🛡️ Security-First**: User management, session handling, rate limiting, and audit logging
* Langfuse + ClickHouse + Redis for observability and memory
* Visual agent workflow building via Langflow
* Autoscaling via KEDA
* Optional Web UI via Open WebUI (for user prompts and chat)
* Deployable via Docker Compose or K3s/Helm
* Docs-as-code with Docusaurus v2.0 (Rancher-style architecture docs)

---

## 🔧 Architecture Components

| Component           | Description                                                 | Status |
| ------------------- | ----------------------------------------------------------- | ------ |
| **🔐 Auth Service** | **JWT + API key authentication with user management**       | **✅ Core** |
| `Ray`               | Agent orchestration + SwarmCoordinator                      | ✅ Core |
| `vLLM`              | Inference engine for serving local models (Phi-3.5)         | ✅ Core |
| `Langfuse`          | Observability layer (tracing, scoring, structured logs)     | ✅ Core |
| `Redis`             | Fast in-memory short-term state, sessions & Langfuse queue  | ✅ Core |
| `Qdrant`            | Vector DB for persistent semantic memory                    | ✅ Core |
| `PostgreSQL`        | Primary database for Langfuse + user authentication        | ✅ Core |
| `ClickHouse`    | Optional long-term structured trace store                   | 🔄 Optional |
| `GPT-4.1 Proxy` | Optional HTTP-based fallback to OpenAI                      | 🔄 Optional |
| `Langflow`      | Visual graph builder for agent workflows                    | 🔄 Optional |
| `Open WebUI`    | Optional web-based interface for user interaction with LLMs | 🔄 Optional |
| `KEDA`          | Autoscaling agent pods based on task load                   | 🔄 K8s Only |
| `K3s/Cilium`    | Lightweight Kubernetes + secure eBPF networking             | 🔄 K8s Only |

---

## 🔐 Authentication System

### Enterprise-Grade Security Features

* **Dual Authentication**: JWT tokens + API keys for flexible access control
* **Role-Based Access Control (RBAC)**: Admin, user, and viewer roles with granular permissions
* **Session Management**: Secure token refresh and blacklisting via Redis
* **Rate Limiting**: Configurable request limits per user/IP
* **Audit Logging**: Complete activity tracking for security compliance
* **Password Security**: bcrypt hashing with configurable complexity
* **API Security**: CORS protection, security headers, and input validation

### Authentication Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  Auth Service    │───▶│   PostgreSQL    │
│                 │    │  (Port: 8005)    │    │  (User Store)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐              │
         │              │     Redis       │              │
         │              │  (Sessions)     │              │
         │              └─────────────────┘              │
         │                                               │
         ▼              ┌─────────────────────────────────▼──┐
┌─────────────────┐    │         Protected Services         │
│  Nginx Proxy    │───▶│  • Orchestrator (8006)            │
│  (Port: 80)     │    │  • Memory API (8007)              │
└─────────────────┘    │  • vLLM Models (8000, 8001)       │
                       └────────────────────────────────────┘
```

### User Roles & Permissions

| Role    | Permissions                                              |
|---------|----------------------------------------------------------|
| **Admin**   | Full system access, user management, service config     |
| **User**    | Create tasks, access agents, manage own API keys        |
| **Viewer**  | Read-only access to tasks, results, and system metrics  |

## System Diagram

![alt text](image.png)

## 🚀 Quick Start with Authentication

### Prerequisites
- **OS**: Linux, macOS, or Windows (with WSL2)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **Docker**: Docker Engine 20.10+ and Docker Compose 2.0+
- **Python**: 3.10+ (for development)

### Option A: Secure Deployment with Authentication (Recommended)

```bash
git clone https://github.com/tbowman01/vllm-local-swarm.git
cd vllm-local-swarm

# Setup development environment with authentication
make dev-setup

# Deploy with authentication enabled
make dev-start

# Create admin user and demo accounts
make auth-setup

# Test authentication system
make auth-demo
```

**🔓 Access Your Authenticated Services:**
- **Authentication API**: http://localhost:8005
- **Orchestrator**: http://localhost:8006 (requires authentication)
- **Memory API**: http://localhost:8007 (requires authentication) 
- **Web UI**: http://localhost (via Nginx proxy)

### Option B: Development Without Authentication

```bash
git clone https://github.com/tbowman01/vllm-local-swarm.git
cd vllm-local-swarm

# Install dependencies only
make install-deps

# Start basic services without auth
make quick-start

# Check system health
make health-check
```

### System Validation

Run comprehensive integration tests:

```bash
python tests/integration_e2e.py
```

All tests should pass before deployment.

## 🛠️ Service Management

### Core Service Commands

| Command | Description |
|---------|-------------|
| `make up-basic` | Start Redis, Qdrant, Langfuse |
| `make up-ray` | Start Ray head and worker services |
| `make build-ray` | Build Ray Docker images |
| `make health-check` | Check all service health |
| `make compose-logs` | View all service logs |
| `make compose-down` | Stop all services |

### Individual Service Commands

| Command | Description |
|---------|-------------|
| `make up-ray-head` | Start Ray head service |
| `make up-ray-worker` | Start Ray worker services |
| `make up-clickhouse` | Start ClickHouse (optional) |
| `make logs-ray-head` | View Ray head logs |
| `make logs-langfuse` | View Langfuse logs |
| `make logs-clickhouse` | View ClickHouse logs |

### Health Check Commands

| Command | Description |
|---------|-------------|
| `make health-basic` | Check basic services |
| `make health-ray` | Check Ray services |
| `make health-clickhouse` | Check ClickHouse service |

### Development Commands

| Command | Description |
|---------|-------------|
| `make dev-setup` | Complete development setup |
| `make dev-reset` | Reset development environment |
| `make restart-basic` | Restart basic services |
| `make restart-ray` | Restart Ray services |

### Service Profiles

Start services with specific profiles:

```bash
# Start with OpenAI proxy
make compose-up PROFILES=proxy

# Start with web UI
make compose-up PROFILES=webui

# Start with ClickHouse (high memory)
make compose-up PROFILES=clickhouse

# Combine multiple profiles
make compose-up PROFILES=proxy,webui,clickhouse
```

### Service-Specific Operations

```bash
# Build specific service
make compose-build SERVICE=ray-head

# Start specific service
make compose-up SERVICE=ray-worker

# View specific service logs
make compose-logs SERVICE=langfuse-web

# Stop specific service
make compose-down SERVICE=clickhouse
```

## 📊 Access Points

After successful deployment, access these interfaces:

- **Ray Dashboard**: http://localhost:8265
- **Langfuse Observability**: http://localhost:3000
- **Qdrant Vector DB**: http://localhost:6333/dashboard
- **vLLM API**: http://localhost:8000
- **Open WebUI** (if enabled): http://localhost:8080
- **Langflow** (if enabled): http://localhost:7860

## 🔧 Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database & Security
LANGFUSE_DB_PASSWORD=your_secure_password
LANGFUSE_SECRET=your_secret_key
LANGFUSE_ENCRYPTION_KEY=your_encryption_key

# Optional: OpenAI API for fallback
OPENAI_API_KEY=sk-your-openai-key

# Ray Configuration
RAY_WORKER_REPLICAS=2
RAY_OBJECT_STORE_MEMORY=1000000000

# ClickHouse (Optional)
CLICKHOUSE_URL=  # Empty = disabled
CLICKHOUSE_MEMORY_LIMIT=512M
```

### Memory Optimization

For systems with limited memory:

```bash
# Reduce Ray memory usage
RAY_OBJECT_STORE_MEMORY=500000000

# Disable ClickHouse
CLICKHOUSE_URL=

# Start fewer services
make up-basic  # Only essential services
```

## 🧪 Testing

### Integration Tests

```bash
# Run comprehensive end-to-end tests
python tests/integration_e2e.py

# Run specific test scenarios
python test_sparc_workflow.py
```

### Manual Testing

```bash
# Check all services
make health-check

# Test individual components
curl http://localhost:6333/health  # Qdrant
curl http://localhost:3000/api/public/health  # Langfuse
```

## 🛠️ Troubleshooting

### Common Issues

1. **Services won't start**: Check `make health-check` and logs
2. **Memory issues**: Reduce memory limits in `.env`
3. **Port conflicts**: Check for processes using ports 3000, 6333, 8000, 8265
4. **Build failures**: Run `make compose-clean` and rebuild

### Getting Help

- Check `docs/TROUBLESHOOTING.md` for detailed solutions
- View service logs: `make logs-<service-name>`
- Reset environment: `make dev-reset`

## 🐳 Kubernetes Deployment

For production deployment:

```bash
# Install with Helm
helm install vllm-local-swarm ./helm

# Check deployment
make k8s-status

# Upgrade deployment
make k8s-upgrade
```

---

## 🧠 Memory System

* **Short-Term Memory:** Redis for session context & agent handoffs
* **Semantic Memory:** Qdrant for vector-based semantic recall
* **Observability:** Langfuse with PostgreSQL for tracing and metrics
* **Long-Term Storage:** ClickHouse for historical trace logs (optional)

---

## 📟 CLI Usage (SPARC-style)

```bash
sparc new "Generate a Python API for task management"
sparc status <task-id>
sparc review <task-id>
sparc self-improve
```

---

## 🤖 Agent Roles

* `Planner`: Task breakdown, coordination
* `Researcher`: Source-aware evidence gathering
* `Coder`: Code generation, refinement
* `QA`: Test execution, validation
* `Critic`: Structural and logical critique
* `Judge`: Scoring, revision suggestion, and completion approval

---

## 🛠️ Auto-Updating

Agents can:

* Rewrite prompt scaffolding
* Modify routing DAGs
* Propose and apply config updates
* Trigger improvement tasks and redeploy

---

## 🔍 Monitoring & Observability

* **Langfuse Dashboard**: `http://localhost:3000` - Tracing, metrics, and observability
* **Ray Dashboard**: `http://localhost:8265` - Ray cluster monitoring and task management
* **Qdrant UI**: `http://localhost:6333/dashboard` - Vector database management
* **Open WebUI** (optional): `http://localhost:8080` - Interactive chat interface
* **Langflow** (optional): `http://localhost:7860` - Visual workflow builder

---

## 📦 Output Directory Structure

```text
.
├── docker-compose.yml
├── helm/
├── cli/
│   └── sparc.py
├── ray/
│   └── coordinator.py
├── models/
│   └── vllm-models/
├── prompts/
│   ├── planner.md
│   └── researcher.md
├── memory/
│   ├── redis/
│   ├── clickhouse/
│   └── vector/
├── ui/
│   └── open-webui/  # optional frontend integration
├── docs/
│   └── docusaurus/  # Docusaurus v2.0 project for architecture docs
└── README.md
```

---

## 🧠 Slogan

> **"Collaborative AI, Local Performance"**

---

## License

MIT License. Attribution encouraged for derivative frameworks.

---

## 📚 Documentation

### Quick References
- **[Quick Start Guide](docs/QUICK_START.md)** - Step-by-step setup instructions
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Integration Testing](tests/integration_e2e.py)** - Comprehensive test suite

### Service-Specific Documentation
- **Service Builds**: Individual service management and builds
- **Health Checks**: System monitoring and health validation
- **Performance Optimization**: Memory and resource tuning

### Command Reference
Run `make help` for a complete list of available commands and usage examples.

For full setup instructions and documentation, visit:
📖 [https://github.com/tbowman01/vllm-local-swarm](https://github.com/tbowman01/vllm-local-swarm)
