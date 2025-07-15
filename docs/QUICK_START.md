# vLLM Local Swarm - Quick Start Guide

Get your vLLM Local Swarm up and running in minutes with this step-by-step guide.

## 🚀 Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows (with WSL2)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **Docker**: Docker Engine 20.10+ and Docker Compose 2.0+
- **Python**: 3.10+ (for development)

### Optional (for GPU acceleration)
- **GPU**: NVIDIA GPU with CUDA support
- **CUDA**: 11.8+ or 12.0+
- **nvidia-docker**: For GPU container support

## 📋 Installation Steps

### Step 1: Clone and Setup
```bash
# Clone the repository
git clone https://github.com/tbowman01/vllm-local-swarm.git
cd vllm-local-swarm

# Create environment file
cp .env.example .env
```

### Step 2: Configure Environment
Edit `.env` file with your preferences:
```bash
# Basic configuration
LANGFUSE_DB_PASSWORD=your_secure_password
LANGFUSE_SECRET=your_secret_key
LANGFUSE_ENCRYPTION_KEY=your_encryption_key

# Optional: Add OpenAI API key for fallback
OPENAI_API_KEY=your_openai_key

# Ray configuration
RAY_WORKER_REPLICAS=2
RAY_OBJECT_STORE_MEMORY=1000000000
```

### Step 3: Quick Start (Recommended)
```bash
# Start basic services first
make up-basic

# Wait for services to be healthy (30-60 seconds)
make compose-ps

# Build and start Ray services
make build-ray
make up-ray
```

### Step 4: Verify Installation
```bash
# Check all services are running
make compose-ps

# View service logs
make logs-ray-head
make logs-langfuse
```

## 🎯 Service-by-Service Setup

### Option A: Minimal Setup (Development)
```bash
# Start only essential services
make up-basic              # Redis, Qdrant, Langfuse
make build-ray-head        # Build Ray coordinator
make up-ray-head           # Start Ray head node
```

### Option B: Full Setup (Production-like)
```bash
# Start all basic services
make up-basic

# Build all custom services
make build-all-custom

# Start Ray cluster
make up-ray

# Optional: Add proxy for OpenAI fallback
make compose-up PROFILES=proxy
```

### Option C: Step-by-Step (Debugging)
```bash
# 1. Start Redis first
make compose-up SERVICE=redis
make compose-logs SERVICE=redis

# 2. Start Qdrant vector database
make compose-up SERVICE=qdrant
make compose-logs SERVICE=qdrant

# 3. Start Langfuse database
make compose-up SERVICE=langfuse-db
make compose-logs SERVICE=langfuse-db

# 4. Start Langfuse web interface
make compose-up SERVICE=langfuse-web
make compose-logs SERVICE=langfuse-web

# 5. Build and start Ray services
make build-ray-head
make up-ray-head
make logs-ray-head
```

## 🔍 Verification & Testing

### Check Service Health
```bash
# View all running services
make compose-ps

# Check specific service logs
make logs-ray-head
make logs-langfuse

# Test service endpoints
curl http://localhost:6379/ping     # Redis (should return PONG)
curl http://localhost:6333/health   # Qdrant
curl http://localhost:3000/api/public/health  # Langfuse
curl http://localhost:8265          # Ray Dashboard
```

### Access Web Interfaces
- **Ray Dashboard**: http://localhost:8265
- **Langfuse**: http://localhost:3000
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### Test Ray Cluster
```bash
# Check Ray cluster status
docker exec vllm-ray-head ray status

# View Ray logs
make logs-ray-head
make logs-ray-worker
```

## 🛠️ Common Development Workflows

### 1. Development Iteration
```bash
# Make changes to Ray code
make build-ray-head        # Rebuild only Ray head
make up-ray-head           # Restart Ray head
make logs-ray-head         # Monitor logs
```

### 2. Testing Changes
```bash
# Restart specific service
make compose-down SERVICE=ray-head
make compose-up SERVICE=ray-head

# View logs for debugging
make logs-ray-head
```

### 3. Clean Restart
```bash
# Stop all services
make compose-down

# Clean up volumes (optional)
make compose-clean

# Start fresh
make up-basic
make build-ray
make up-ray
```

## 📊 Service Overview

### Core Services (Always Required)
| Service | Purpose | Port | Health Check |
|---------|---------|------|-------------|
| Redis | Cache & messaging | 6379 | `redis-cli ping` |
| Qdrant | Vector database | 6333 | `curl localhost:6333/health` |
| Langfuse DB | PostgreSQL | 5432 | Internal |
| Langfuse Web | Observability UI | 3000 | `curl localhost:3000/api/public/health` |

### Ray Services (Custom Built)
| Service | Purpose | Port | Health Check |
|---------|---------|------|-------------|
| Ray Head | Cluster coordinator | 8265 | `ray status` |
| Ray Worker | Compute nodes | - | `ray status` |

### Optional Services
| Service | Purpose | Port | Profile |
|---------|---------|------|---------|
| OpenAI Proxy | API fallback | 8002 | `proxy` |
| Open WebUI | Chat interface | 8080 | `webui` |
| Langflow | Visual workflows | 7860 | `langflow` |
| vLLM Models | Local inference | 8000 | `large-model` |

## 🚨 Troubleshooting Quick Fixes

### Services Won't Start
```bash
# Check Docker is running
docker ps

# Check for port conflicts
sudo netstat -tulpn | grep :6379

# Restart Docker daemon
sudo systemctl restart docker
```

### Build Failures
```bash
# Clear Docker cache
docker system prune -f

# Rebuild without cache
make compose-build --no-cache

# Check disk space
df -h
```

### Memory Issues
```bash
# Check memory usage
docker stats

# Reduce Ray memory allocation in .env
RAY_OBJECT_STORE_MEMORY=500000000

# Stop unused services
make compose-down SERVICE=service-name
```

### Connection Issues
```bash
# Check service dependencies
make compose-ps

# Restart networking
make compose-down
make compose-up
```

## 🔧 Advanced Configuration

### GPU Support (Optional)
```bash
# Install nvidia-docker
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Enable GPU in compose
make compose-up PROFILES=large-model
```

### Performance Tuning
```bash
# Increase Ray worker replicas
echo "RAY_WORKER_REPLICAS=4" >> .env

# Adjust memory limits
echo "RAY_OBJECT_STORE_MEMORY=2000000000" >> .env

# Restart services
make compose-down
make compose-up
```

### Custom Models
```bash
# Edit .env for custom models
LARGE_MODEL=microsoft/DialoGPT-large
LARGE_MODEL_TP=2

# Start with large model profile
make compose-up PROFILES=large-model
```

## 🎯 Next Steps

After successful installation:

1. **Explore the Ray Dashboard**: Visit http://localhost:8265
2. **Check Langfuse**: Visit http://localhost:3000 for observability
3. **Test the API**: Use the endpoints to test functionality
4. **Read the Service Guide**: See `docs/SERVICE_BUILDS.md` for detailed service management
5. **Configure for Production**: Review `DEPLOYMENT.md` for production setup

## 📚 Additional Resources

- **Service Management**: `docs/SERVICE_BUILDS.md`
- **Deployment Guide**: `DEPLOYMENT.md`
- **Infrastructure Details**: `INFRASTRUCTURE.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md` (coming soon)

## 🆘 Getting Help

If you encounter issues:

1. Check the **Troubleshooting** section above
2. Review service logs: `make logs-<service-name>`
3. Check GitHub issues: https://github.com/tbowman01/vllm-local-swarm/issues
4. Verify system requirements and dependencies

---

**Happy Swarming!** 🐝

Your vLLM Local Swarm is now ready for collaborative AI development.