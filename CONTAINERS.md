# 🐳 Container Deployment Guide

## Published Containers

All containers are automatically built and published to GitHub Container Registry (GHCR) on every push to `main`.

### Available Images

| Service | Image | Description |
|---------|-------|-------------|
| **Authentication** | `ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest` | JWT + API key authentication |
| **Orchestrator** | `ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest` | SPARC workflow orchestration |
| **Memory API** | `ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest` | Vector memory management |
| **All-in-One** | `ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest` | Complete platform |

## Quick Start with Published Containers

### Option 1: Individual Services
```bash
# Use published containers with existing infrastructure
docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d

# This starts:
# - Published auth, orchestrator, and memory services from GHCR
# - Local infrastructure (Redis, PostgreSQL, Qdrant, vLLM)
```

### Option 2: All-in-One Container
```bash
# Start complete platform in single container
docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml --profile all-in-one up -d

# This starts:
# - All services (auth, orchestrator, memory) in one container
# - Local infrastructure (Redis, PostgreSQL, Qdrant, vLLM)
```

### Option 3: Pure Container Deployment
```bash
# Pull and run the all-in-one container directly
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest

docker run -d --name vllm-swarm \
  -p 8003:8003 -p 8004:8004 -p 8005:8005 \
  -e JWT_SECRET_KEY="your-production-jwt-secret" \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/auth" \
  -e REDIS_URL="redis://redis-host:6379" \
  -e QDRANT_URL="http://qdrant-host:6333" \
  ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
```

## Authentication Setup

### Environment Variables
```bash
# Required for all deployments
JWT_SECRET_KEY="change-this-to-a-secure-random-string-min-32-chars"
DATABASE_URL="postgresql+asyncpg://langfuse:password@langfuse-db:5432/auth"
REDIS_URL="redis://redis:6379"

# Optional customization
JWT_EXPIRATION_HOURS=24
REFRESH_TOKEN_EXPIRATION_DAYS=30
AUTH_PORT=8005
ORCHESTRATOR_PORT=8004
MEMORY_PORT=8003
```

### First Time Setup
```bash
# 1. Start the platform
docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d

# 2. Wait for services to be ready (30-60 seconds)
docker logs -f vllm-auth-service-ghcr

# 3. Login with default admin account
curl -X POST http://localhost:8005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 4. Create your API key
TOKEN="your-jwt-token-from-step-3"
curl -X POST http://localhost:8005/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"my-api-key","permissions":["models.*","tasks.*"]}'
```

## Health Monitoring

### Service Health Checks
```bash
# Authentication Service
curl http://localhost:8005/health

# Orchestrator
curl http://localhost:8004/health

# Memory API
curl http://localhost:8003/health

# All services status (for all-in-one)
docker exec vllm-swarm-all-in-one curl -s http://localhost:8005/health && \
docker exec vllm-swarm-all-in-one curl -s http://localhost:8004/health && \
docker exec vllm-swarm-all-in-one curl -s http://localhost:8003/health
```

### Observability Dashboard
- **Langfuse**: http://localhost:3000 (when using full compose setup)
- **Container Logs**: `docker logs <container-name>`
- **Service Metrics**: Available at `/stats` endpoint on each service

## Container Security

### Security Features
- ✅ **Non-root user**: All containers run as unprivileged user
- ✅ **Health checks**: Built-in health monitoring
- ✅ **Multi-arch**: Supports AMD64 and ARM64
- ✅ **Vulnerability scanning**: Automatic Trivy scans
- ✅ **Minimal base**: Python slim images

### Production Security
```bash
# 1. Use strong secrets
JWT_SECRET_KEY=$(openssl rand -hex 32)

# 2. Enable TLS in production
# Use reverse proxy (nginx) with SSL certificates

# 3. Restrict network access
# Configure firewall rules for port access

# 4. Monitor container security
docker scan ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
```

## Scaling and Deployment

### Horizontal Scaling
```bash
# Scale individual services
docker-compose -f docker-compose.ghcr.yml up -d --scale orchestrator=3

# Load balancer configuration required for multiple instances
```

### Kubernetes Deployment
```yaml
# Example Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-swarm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm-swarm
  template:
    metadata:
      labels:
        app: vllm-swarm
    spec:
      containers:
      - name: vllm-swarm
        image: ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
        ports:
        - containerPort: 8005
        - containerPort: 8004
        - containerPort: 8003
        env:
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: vllm-secrets
              key: jwt-secret
```

## Troubleshooting

### Common Issues
```bash
# Container won't start
docker logs <container-name>

# Service unhealthy
curl http://localhost:8005/health -v

# Database connection issues
docker exec <container> ping langfuse-db

# Permission denied
# Check if container is running as correct user
docker exec <container> whoami
```

### Update Containers
```bash
# Pull latest versions
docker-compose -f docker-compose.ghcr.yml pull

# Recreate with new images
docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d --force-recreate
```

## Tags and Versioning

### Available Tags
- `latest` - Latest stable release from main branch
- `main` - Latest development version
- `v1.0.0` - Specific version releases
- `sha-abc123` - Specific commit builds

### Example Usage
```bash
# Use specific version
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:v1.0.0

# Use development version
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:main

# Use commit-specific build
docker pull ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:sha-abc123
```

---

## 🚀 Production Ready

All containers are production-ready with:
- Complete authentication system
- Health monitoring
- Security scanning
- Multi-architecture support
- Automatic updates via CI/CD

For support, see the main [README.md](README.md) or open an issue on GitHub.