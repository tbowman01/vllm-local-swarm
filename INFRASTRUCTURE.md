# vLLM Local Swarm - Infrastructure Overview

This document provides a comprehensive overview of the deployment infrastructure for the vLLM Local Swarm system.

## 🏗️ Infrastructure Components

### Complete Deployment Stack

The vLLM Local Swarm infrastructure consists of the following components:

```
📦 vllm-local-swarm/
├── 🐳 docker-compose.yml          # Complete Docker Compose stack
├── 🔧 .env.example               # Environment configuration template
├── 📊 Makefile                   # Deployment automation
├── 🛠️ scripts/
│   ├── deploy.sh                 # Unified deployment script
│   └── test-deployment.sh        # Comprehensive testing suite
├── 🐳 docker/                    # Custom Docker images
│   ├── ray/                      # Ray cluster containers
│   │   ├── Dockerfile.head       # Ray head node
│   │   ├── Dockerfile.worker     # Ray worker nodes
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── start-head.sh         # Head startup script
│   │   └── start-worker.sh       # Worker startup script
│   └── proxy/                    # OpenAI proxy service
│       ├── Dockerfile            # Proxy container
│       ├── proxy.py              # Proxy application
│       ├── health.py             # Health check script
│       └── requirements.txt      # Proxy dependencies
├── ☸️ helm/                       # Kubernetes Helm charts
│   ├── Chart.yaml                # Helm chart metadata
│   ├── values.yaml               # Default configuration
│   └── templates/                # Kubernetes manifests
│       ├── _helpers.tpl          # Template helpers
│       ├── serviceaccount.yaml   # RBAC configuration
│       ├── secrets.yaml          # Secret management
│       ├── vllm/                 # vLLM service templates
│       ├── ray/                  # Ray cluster templates
│       ├── langfuse/             # Observability templates
│       ├── clickhouse/           # Analytics database
│       ├── qdrant/               # Vector database
│       └── proxy/                # OpenAI proxy
└── ⚙️ configs/                    # Service configurations
    └── clickhouse/               # ClickHouse settings
        └── config.xml            # Database configuration
```

## 🚀 Deployment Options

### 1. Docker Compose (Development & Single-Node)

**Best for**: Local development, testing, single-machine deployments

**Features**:
- Complete service orchestration
- GPU support with NVIDIA runtime
- Profile-based service selection
- Persistent volume management
- Health monitoring
- Service discovery via bridge networking

**Quick Start**:
```bash
make compose-up                    # Basic services
make compose-up PROFILES=proxy,webui  # With additional services
```

### 2. Kubernetes with Helm (Production & Multi-Node)

**Best for**: Production deployments, multi-node clusters, high availability

**Features**:
- Scalable service deployment
- Resource management and limits
- Health checks and readiness probes
- Persistent volume claims
- Service mesh integration
- RBAC and security policies
- Ingress and load balancing

**Quick Start**:
```bash
make k8s-install NAMESPACE=vllm-swarm
```

## 📋 Service Architecture

### Core Services Matrix

| Service | Purpose | Dependencies | Scaling | Storage |
|---------|---------|--------------|---------|---------|
| **Redis** | Cache & Queue | None | Single | Memory |
| **ClickHouse** | Analytics DB | None | Single | Persistent |
| **Qdrant** | Vector DB | None | Single | Persistent |
| **PostgreSQL** | Metadata DB | None | Single | Persistent |
| **Langfuse Web** | Observability UI | PostgreSQL, ClickHouse | Horizontal | None |
| **Langfuse Worker** | Background Jobs | PostgreSQL, Redis | Horizontal | None |
| **vLLM Phi-3.5** | Primary LLM | None | Single | Cache |
| **vLLM Large** | Large LLM | None | Single | Cache |
| **Ray Head** | Orchestration | Redis, vLLM | Single | Logs |
| **Ray Workers** | Agent Runtime | Ray Head | Horizontal | Logs |

### Optional Services

| Service | Purpose | Profile | Dependencies |
|---------|---------|---------|--------------|
| **OpenAI Proxy** | GPT-4 Access | `proxy` | Redis (optional) |
| **Open WebUI** | Chat Interface | `webui` | vLLM Phi |
| **Langflow** | Visual Builder | `langflow` | PostgreSQL |

## 🔧 Configuration Management

### Environment Variables

**Core Configuration** (`.env`):
```bash
# Database passwords and secrets
LANGFUSE_DB_PASSWORD=secure-password
CLICKHOUSE_PASSWORD=secure-password
LANGFUSE_SECRET=32-char-secret-key

# Model configuration
LARGE_MODEL=microsoft/DialoGPT-large
LARGE_MODEL_TP=2
LARGE_MODEL_GPU_COUNT=2

# Resource limits
RAY_WORKER_REPLICAS=2
REDIS_MAX_MEMORY=2gb
```

**Kubernetes Configuration** (`values.yaml`):
```yaml
# Resource allocation
vllm:
  phi:
    resources:
      requests:
        cpu: 2
        memory: 8Gi
        nvidia.com/gpu: 1

# Scaling configuration
ray:
  worker:
    replicas: 2
    autoscaling:
      enabled: true
      maxReplicas: 10

# Storage configuration
global:
  storageClass: "fast-ssd"
```

### Profile System

The Docker Compose deployment supports multiple profiles for optional services:

- **`proxy`**: OpenAI GPT-4 proxy with rate limiting
- **`webui`**: Open WebUI chat interface
- **`langflow`**: Visual workflow builder
- **`large-model`**: Additional large model service

## 🌐 Networking Architecture

### Docker Compose Networking

```
Bridge Network: 172.20.0.0/16
├── Redis:         172.20.0.2:6379
├── ClickHouse:    172.20.0.3:8123,9000
├── Qdrant:        172.20.0.4:6333,6334
├── PostgreSQL:    172.20.0.5:5432
├── Langfuse Web:  172.20.0.6:3000
├── vLLM Phi:      172.20.0.7:8000
├── vLLM Large:    172.20.0.8:8001
├── Ray Head:      172.20.0.9:8265,10001
└── Ray Workers:   172.20.0.10+
```

### Kubernetes Networking

```
Cluster Services:
├── vllm-local-swarm-redis:6379
├── vllm-local-swarm-clickhouse:8123,9000
├── vllm-local-swarm-qdrant:6333,6334
├── vllm-local-swarm-postgresql:5432
├── vllm-local-swarm-langfuse-web:3000
├── vllm-local-swarm-vllm-phi:8000
├── vllm-local-swarm-vllm-large:8001
└── vllm-local-swarm-ray-head:8265,10001
```

## 💾 Storage Strategy

### Persistent Storage Requirements

| Service | Volume Type | Size | Purpose |
|---------|-------------|------|---------|
| ClickHouse | Block Storage | 20-100GB | Analytics data |
| PostgreSQL | Block Storage | 8-20GB | Metadata |
| Qdrant | Block Storage | 10-50GB | Vector embeddings |
| vLLM Cache | Block Storage | 50-200GB | Model cache |
| Ray Logs | Block Storage | 10GB | Execution logs |
| Redis | Memory | 2-8GB | Cache (volatile) |

### Storage Classes (Kubernetes)

**Recommended storage classes**:
- **Fast SSD**: For databases (ClickHouse, PostgreSQL)
- **Standard SSD**: For model cache and logs
- **NFS/Shared**: For multi-pod shared storage

## 🔐 Security Configuration

### Production Security Checklist

#### 1. Secrets Management
- [ ] Change all default passwords
- [ ] Use secure random secrets (32+ characters)
- [ ] Implement secret rotation
- [ ] Use Kubernetes secrets or external secret managers

#### 2. Network Security
- [ ] Enable network policies
- [ ] Configure TLS for external endpoints
- [ ] Implement service mesh for internal communication
- [ ] Use private container registries

#### 3. Access Control
- [ ] Enable RBAC
- [ ] Create service-specific accounts
- [ ] Implement pod security policies
- [ ] Use admission controllers

#### 4. Image Security
- [ ] Scan images for vulnerabilities
- [ ] Use minimal base images
- [ ] Run containers as non-root
- [ ] Enable read-only root filesystems where possible

## 📊 Monitoring & Observability

### Built-in Monitoring

**Health Checks**:
- HTTP endpoints for all services
- Kubernetes liveness/readiness probes
- Docker Compose health checks
- Custom test suite

**Observability Stack**:
- **Langfuse**: LLM request tracing and metrics
- **Ray Dashboard**: Cluster and job monitoring
- **ClickHouse**: Query and performance analytics
- **Qdrant**: Vector database metrics

### External Monitoring Integration

**Prometheus Integration**:
```yaml
monitoring:
  enabled: true
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
```

**Grafana Dashboards**:
- Ray cluster metrics
- vLLM performance
- Resource utilization
- Error rates and latency

## 🚀 Scaling Strategy

### Horizontal Scaling

**Auto-scaling components**:
- Ray workers (based on CPU/queue depth)
- Langfuse workers (based on job queue)
- vLLM services (manual scaling recommended)

**Manual scaling**:
```bash
# Docker Compose
docker-compose up --scale ray-worker=5

# Kubernetes
kubectl scale deployment vllm-local-swarm-ray-worker --replicas=5
```

### Vertical Scaling

**Resource adjustment**:
- Increase GPU memory allocation for larger models
- Scale CPU/memory for database services
- Adjust storage IOPS for performance

## 🔄 Deployment Automation

### Makefile Commands

```bash
# Docker Compose
make compose-up                    # Start services
make compose-down                  # Stop services
make compose-logs                  # View logs
make compose-build                 # Build images
make compose-clean                 # Clean up

# Kubernetes
make k8s-install                   # Install with Helm
make k8s-uninstall                 # Uninstall
make k8s-upgrade                   # Upgrade deployment
make k8s-status                    # Check status

# Development
make install-deps                  # Install dependencies
make test                          # Run tests
make check-deps                    # Check prerequisites
```

### Deployment Script Features

**Unified deployment** (`scripts/deploy.sh`):
- Supports both Docker and Kubernetes
- Automatic prerequisite checking
- GPU detection and configuration
- Profile-based service selection
- Environment validation
- Health monitoring

**Testing suite** (`scripts/test-deployment.sh`):
- Service health verification
- API functionality testing
- Performance benchmarking
- Integration testing
- Load testing
- Comprehensive reporting

## 🎯 Performance Optimization

### Resource Tuning

**GPU Optimization**:
```bash
# Maximize GPU utilization
VLLM_GPU_MEMORY_UTILIZATION=0.9
VLLM_TENSOR_PARALLEL_SIZE=2

# Balance memory and performance
VLLM_MAX_MODEL_LEN=32768
```

**Memory Optimization**:
```bash
# Ray object store
RAY_OBJECT_STORE_MEMORY=2000000000

# Redis memory limits
REDIS_MAX_MEMORY=4gb
REDIS_MAXMEMORY_POLICY=allkeys-lru
```

### Model Loading Optimization

**Pre-loading models**:
```bash
# Warm up model cache
docker run -v vllm_cache:/cache vllm/vllm-openai:latest \
  python -c "from transformers import AutoModel; AutoModel.from_pretrained('microsoft/Phi-3.5-mini-instruct', cache_dir='/cache')"
```

## 🚨 Disaster Recovery

### Backup Strategy

**Database backups**:
```bash
# PostgreSQL
kubectl exec -it postgresql-pod -- pg_dump -U langfuse langfuse > backup.sql

# ClickHouse
kubectl exec -it clickhouse-pod -- clickhouse-client --query "BACKUP DATABASE langfuse TO Disk('backups')"
```

**Volume snapshots**:
```bash
# Create persistent volume snapshots
kubectl create volumesnapshot clickhouse-backup --source=clickhouse-pvc
```

### Recovery Procedures

**Service recovery**:
1. Restore from volume snapshots
2. Recreate deployment with same configuration
3. Verify data integrity
4. Resume normal operations

**Cluster migration**:
1. Export Helm configuration
2. Backup all persistent volumes
3. Deploy to new cluster
4. Restore data
5. Update DNS/ingress

## 📚 Additional Resources

- **[Deployment Guide](DEPLOYMENT.md)**: Step-by-step deployment instructions
- **[Makefile](Makefile)**: Complete automation commands
- **[Docker Compose](docker-compose.yml)**: Service orchestration
- **[Helm Chart](helm/)**: Kubernetes deployment templates
- **[Scripts](scripts/)**: Deployment and testing automation

---

This infrastructure provides a robust, scalable foundation for the vLLM Local Swarm system, supporting both development and production use cases with comprehensive automation and monitoring capabilities.