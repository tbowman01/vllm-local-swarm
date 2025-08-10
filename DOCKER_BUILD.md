# 🐳 Docker Build & Container Management Guide

## 📋 Overview

This guide provides comprehensive instructions for building, deploying, and managing Docker containers in the vLLM Local Swarm project. The project uses a microservices architecture with multi-platform container support and automated GitHub Container Registry (GHCR) publishing.

---

## 🏗️ **Container Architecture**

### **Microservices Design**
- **🔐 auth-service**: JWT authentication and API key management
- **🧠 orchestrator**: SPARC workflow orchestration and agent coordination
- **💾 memory-api**: Distributed memory and vector storage management
- **🐳 vllm-swarm**: All-in-one composite container

### **Infrastructure Services**
- **Redis**: High-performance caching and session storage
- **PostgreSQL**: Relational database for authentication and audit logs
- **Qdrant**: Vector similarity search for AI memory
- **Langfuse**: Observability and tracing dashboard

---

## 🛠️ **Building Containers Locally**

### **Prerequisites**
```bash
# Required tools
docker >= 24.0
docker-compose >= 2.20
git >= 2.40

# Optional for multi-platform builds
docker buildx

# GPU support (optional)
nvidia-docker2
nvidia-container-toolkit
```

### **Individual Service Builds**

#### 🔐 Authentication Service
```bash
# Build auth service
docker build -f docker/Dockerfile.auth -t vllm-auth-service .

# Run locally
docker run -d -p 8005:8005 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/auth" \
  -e JWT_SECRET_KEY="your-secret-key-min32chars" \
  --name auth-service vllm-auth-service

# Health check
curl http://localhost:8005/health
```

#### 🧠 Orchestrator Service
```bash
# Build orchestrator
docker build -f docker/Dockerfile.orchestrator -t vllm-orchestrator .

# Run with auth integration
docker run -d -p 8006:8006 \
  -e AUTH_SERVICE_URL="http://auth-service:8005" \
  -e MEMORY_API_URL="http://memory-api:8003" \
  --link auth-service \
  --name orchestrator vllm-orchestrator

# Health check
curl http://localhost:8006/health
```

#### 💾 Memory API Service
```bash
# Build memory API
docker build -f docker/Dockerfile.memory-api -t vllm-memory-api .

# Run with vector database
docker run -d -p 8003:8003 \
  -e QDRANT_URL="http://qdrant:6333" \
  -e REDIS_URL="redis://redis:6379" \
  --name memory-api vllm-memory-api

# Health check
curl http://localhost:8003/health
```

#### 🐳 Composite All-in-One Container
```bash
# Build complete platform
docker build -f Dockerfile.composite -t vllm-swarm .

# Run with all services
docker run -d -p 8003:8003 -p 8004:8004 -p 8005:8005 \
  -e JWT_SECRET_KEY="your-secret-key-min32chars" \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/auth" \
  --name vllm-swarm vllm-swarm

# Health checks
curl http://localhost:8003/health  # Memory API
curl http://localhost:8005/health  # Auth Service
```

### **Multi-Platform Builds**

```bash
# Create buildx builder
docker buildx create --name multi-arch-builder --use
docker buildx inspect --bootstrap

# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -f docker/Dockerfile.auth \
  -t vllm-auth-service:multi-arch \
  --push .

# Verify multi-arch
docker buildx imagetools inspect vllm-auth-service:multi-arch
```

---

## 🚀 **Deployment Strategies**

### **1. Docker Compose - Local Development**

```bash
# Quick start with all services
git clone https://github.com/tbowman01/vllm-local-swarm
cd vllm-local-swarm
cp .env.example .env  # Configure environment variables
docker-compose up -d

# Check service status
docker-compose ps
docker-compose logs -f

# Stop services
docker-compose down
```

### **2. Docker Compose - With Authentication**

```bash
# Start with authentication enabled
docker-compose -f docker-compose.yml -f docker-compose.auth.yml up -d

# Verify authentication
curl -X POST http://localhost:8005/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"SecurePass123!"}'

curl -X POST http://localhost:8005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"SecurePass123!"}'
```

### **3. Production Deployment - GHCR Images**

```bash
# Use pre-built containers from GitHub Container Registry
docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d

# Available images:
# ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest
# ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest  
# ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest
# ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
```

### **4. Single Container Deployment**

```bash
# All-in-one container for simple deployments
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest

docker run -d \
  -p 8003:8003 -p 8005:8005 \
  -e JWT_SECRET_KEY="production-secret-key-change-this" \
  --name vllm-platform \
  ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
```

---

## 🔧 **Development Workflow**

### **Local Development Setup**

```bash
# 1. Clone repository
git clone https://github.com/tbowman01/vllm-local-swarm
cd vllm-local-swarm

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start infrastructure services
docker-compose up -d redis langfuse-db qdrant

# 4. Build and start application services
docker-compose up --build auth-service orchestrator memory-api

# 5. Run tests
pytest tests/ --cov=. --cov-report=html

# 6. Access services
echo "Auth Service: http://localhost:8005"
echo "Orchestrator: http://localhost:8006"  
echo "Memory API: http://localhost:8003"
echo "Langfuse Dashboard: http://localhost:3000"
```

### **Development with Hot Reload**

```bash
# Mount local code for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# This mounts:
# - ./auth:/app/auth (live auth code)
# - ./orchestrator:/app/orchestrator (live orchestrator code)  
# - ./memory:/app/memory (live memory code)
```

### **Building for Different Environments**

```bash
# Development build (with debug symbols)
docker build -f docker/Dockerfile.auth \
  --build-arg BUILD_ENV=development \
  -t vllm-auth-service:dev .

# Production build (optimized)
docker build -f docker/Dockerfile.auth \
  --build-arg BUILD_ENV=production \
  -t vllm-auth-service:prod .

# Testing build (with test dependencies)
docker build -f docker/Dockerfile.auth \
  --target testing \
  -t vllm-auth-service:test .
```

---

## 🔍 **Container Debugging & Monitoring**

### **Health Checks & Status**

```bash
# Check all container health
docker-compose ps

# Individual service health
curl http://localhost:8005/health  # Auth service
curl http://localhost:8006/health  # Orchestrator
curl http://localhost:8003/health  # Memory API

# Detailed health with metrics
curl http://localhost:8005/stats
curl http://localhost:8006/stats
curl http://localhost:8003/stats
```

### **Log Management**

```bash
# View all service logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f auth-service
docker-compose logs -f orchestrator
docker-compose logs -f memory-api

# Live log streaming with timestamps
docker-compose logs -f --timestamps

# Filter logs by level
docker-compose logs -f | grep ERROR
docker-compose logs -f | grep -i "authentication"
```

### **Container Inspection**

```bash
# Inspect running containers
docker inspect auth-service
docker stats auth-service

# Execute commands in running containers
docker exec -it auth-service bash
docker exec -it auth-service python -c "import sys; print(sys.version)"

# View container resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### **Network Debugging**

```bash
# Inspect Docker networks
docker network ls
docker network inspect vllm-network

# Test connectivity between services
docker exec -it orchestrator curl http://auth-service:8005/health
docker exec -it memory-api curl http://qdrant:6333/
```

---

## 🔐 **Security Best Practices**

### **Container Security**

```bash
# Scan for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image vllm-auth-service

# Check for secrets in images
docker run --rm -v $(pwd):/src \
  trufflesecurity/trufflehog filesystem /src

# Security benchmarking
docker run --rm --net host --pid host --userns host --cap-add audit_control \
  -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST \
  -v /etc:/etc:ro \
  -v /var/lib:/var/lib:ro \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  docker/docker-bench-security
```

### **Production Security Configuration**

```bash
# Run containers as non-root user
docker run -d --user 1000:1000 vllm-auth-service

# Limit container resources
docker run -d \
  --memory=512m \
  --cpus=0.5 \
  --pids-limit=100 \
  vllm-auth-service

# Use read-only filesystem where possible
docker run -d --read-only \
  --tmpfs /tmp \
  vllm-auth-service
```

---

## 📊 **Performance Optimization**

### **Build Optimization**

```bash
# Use BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker build -f docker/Dockerfile.auth .

# Multi-stage builds to reduce size
docker build --target production -f docker/Dockerfile.auth .

# Build cache optimization
docker build --cache-from vllm-auth-service:latest .
```

### **Runtime Optimization**

```bash
# Optimize for CPU-intensive workloads
docker run -d --cpus=2.0 --cpu-period=100000 --cpu-quota=200000 vllm-orchestrator

# Optimize for memory-intensive workloads
docker run -d --memory=2g --memory-swap=4g vllm-memory-api

# GPU optimization (for vLLM inference)
docker run -d --gpus all \
  -e CUDA_VISIBLE_DEVICES=0 \
  -e VLLM_GPU_MEMORY_UTILIZATION=0.90 \
  vllm-inference-server
```

### **Network Performance**

```bash
# Use host networking for maximum performance
docker run -d --network host vllm-auth-service

# Optimize Docker network
docker network create --driver bridge \
  --opt com.docker.network.driver.mtu=1500 \
  --subnet=172.20.0.0/16 \
  vllm-network
```

---

## 🏭 **CI/CD Integration**

### **GitHub Actions Container Publishing**

The project includes automated container building and publishing via GitHub Actions:

```yaml
# Triggered on:
- Push to main/develop branches
- Pull requests to main
- Version tags (v*)

# Builds and publishes:
- ghcr.io/tbowman01/vllm-local-swarm/auth-service
- ghcr.io/tbowman01/vllm-local-swarm/orchestrator  
- ghcr.io/tbowman01/vllm-local-swarm/memory-api
- ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm
```

### **Security Scanning Pipeline**

```bash
# Automated security scanning includes:
# 1. Trivy vulnerability scanning
# 2. Secrets detection
# 3. Best practices validation
# 4. SARIF report upload to GitHub Security

# View security scan results:
# GitHub Repository > Security > Code scanning alerts
```

### **Quality Gates**

```bash
# Before container publishing:
✅ All unit tests pass
✅ Integration tests pass  
✅ Security scans pass
✅ No critical vulnerabilities
✅ Build succeeds for amd64/arm64
```

---

## 🚨 **Troubleshooting**

### **Common Build Issues**

```bash
# Issue: Docker build fails with "no space left on device"
docker system prune -a --volumes
docker builder prune -a

# Issue: Multi-platform build fails
docker buildx rm multi-arch-builder
docker buildx create --name multi-arch-builder --use

# Issue: Cache issues during build
docker build --no-cache -f docker/Dockerfile.auth .
```

### **Common Runtime Issues**

```bash
# Issue: Container won't start
docker logs container-name
docker events &  # Monitor Docker events

# Issue: Service discovery problems
docker network inspect vllm-network
docker exec -it container-name nslookup service-name

# Issue: Permission denied
docker exec -it container-name ls -la /app
# Check file ownership and permissions

# Issue: Database connection failures
docker exec -it container-name env | grep DATABASE_URL
# Verify database connectivity
```

### **Performance Issues**

```bash
# Issue: High memory usage
docker stats
# Add memory limits: --memory=512m

# Issue: High CPU usage  
docker stats
# Add CPU limits: --cpus=1.0

# Issue: Slow startup times
docker logs container-name --timestamps
# Check for long-running initialization
```

---

## 📈 **Monitoring & Observability**

### **Container Metrics**

```bash
# Resource monitoring
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Export metrics to Prometheus
docker run -d -p 9323:9323 prom/docker-exporter

# Health check monitoring
while true; do curl -s http://localhost:8005/health && echo " - Auth OK"; sleep 5; done
```

### **Application Observability**

```bash
# Langfuse tracing dashboard
open http://localhost:3000

# Application metrics endpoints
curl http://localhost:8005/stats | jq '.'
curl http://localhost:8006/stats | jq '.'
curl http://localhost:8003/stats | jq '.'
```

---

## 🎯 **Best Practices Summary**

### **Development**
- ✅ Use multi-stage Dockerfiles for smaller images
- ✅ Implement proper health checks
- ✅ Use non-root users in containers
- ✅ Leverage build cache effectively
- ✅ Mount volumes for development

### **Production** 
- ✅ Use specific image tags (not `:latest`)
- ✅ Implement resource limits
- ✅ Use secrets management
- ✅ Enable logging and monitoring
- ✅ Regular security scanning

### **Security**
- ✅ Scan images for vulnerabilities
- ✅ Use minimal base images
- ✅ Avoid secrets in images
- ✅ Implement network policies
- ✅ Regular updates and patches

---

## 🔗 **Quick Reference**

### **Essential Commands**
```bash
# Build all services
docker-compose build

# Start platform
docker-compose up -d

# View logs  
docker-compose logs -f

# Health check all
curl http://localhost:8005/health && curl http://localhost:8006/health && curl http://localhost:8003/health

# Clean up
docker-compose down --volumes --remove-orphans
docker system prune -a
```

### **Container Registry**
```bash
# Pull latest images
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest

# All available images
ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest
ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest
ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest  
ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
```

---

**🎉 The vLLM Local Swarm Docker ecosystem is production-ready with enterprise-grade container management!**

*Last Updated: August 10, 2025*  
*Container Registry: GitHub Container Registry (GHCR)*  
*Multi-Platform: AMD64 + ARM64 Support*