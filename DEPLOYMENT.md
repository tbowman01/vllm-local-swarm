# 🚀 vLLM Local Swarm - Deployment Guide

This guide provides comprehensive instructions for deploying the vLLM Local Swarm system with **enterprise-grade authentication** using Docker Compose or Kubernetes.

## 📋 Table of Contents

- [🔐 Authentication-First Deployment](#-authentication-first-deployment)
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Authentication Configuration](#authentication-configuration)
- [Service Overview](#service-overview)
- [Security & Monitoring](#security--monitoring)
- [Troubleshooting](#troubleshooting)
- [Production Considerations](#production-considerations)

## 🔐 Authentication-First Deployment

**⚡ TL;DR - Secure Deployment in 4 Commands:**
```bash
make dev-setup      # Setup environment with authentication
make dev-start      # Deploy with auth enabled
make auth-setup     # Create admin user
make auth-demo      # Test authentication
```

## 🚀 Quick Start

### Option 1: Secure Docker Compose Deployment (Recommended)

```bash
# Clone the repository
git clone https://github.com/tbowman01/vllm-local-swarm.git
cd vllm-local-swarm

# Complete authenticated deployment
make dev-setup && make dev-start && make auth-setup

# Verify deployment
make health-check && make auth-health
```

### Option 2: Kubernetes (Recommended for Production)

```bash
# Install with Helm
make k8s-install NAMESPACE=vllm-swarm

# Check status
make k8s-status NAMESPACE=vllm-swarm
```

## 📦 Prerequisites

### General Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Memory**: Minimum 16GB RAM (32GB+ recommended for large models)
- **Storage**: Minimum 100GB free space
- **Network**: Internet access for downloading models

### Docker Compose Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- NVIDIA Docker runtime (for GPU support)

### Kubernetes Requirements

- Kubernetes 1.24+
- Helm 3.8+
- kubectl configured
- NVIDIA GPU Operator (for GPU support)

### GPU Support (Optional but Recommended)

- NVIDIA GPU with 8GB+ VRAM
- NVIDIA drivers 470.57.02+
- CUDA 11.8+

## 🐳 Docker Compose Deployment

### Basic Deployment

1. **Clone and Configure**
   ```bash
   git clone https://github.com/your-org/vllm-local-swarm.git
   cd vllm-local-swarm
   
   # Copy and edit environment file
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Core Services**
   ```bash
   make compose-up
   ```

3. **Verify Deployment**
   ```bash
   make compose-logs
   docker-compose ps
   ```

### Advanced Deployment with Profiles

The system supports several optional services via Docker Compose profiles:

```bash
# Include OpenAI proxy for GPT-4 fallback
make compose-up PROFILES=proxy

# Include web interface
make compose-up PROFILES=webui

# Include visual workflow builder
make compose-up PROFILES=langflow

# Include large model service
make compose-up PROFILES=large-model

# Combine multiple profiles
make compose-up PROFILES=proxy,webui,langflow
```

### Service Configuration

#### Core Services (Always Running)
- **Redis**: In-memory cache and message queue
- **ClickHouse**: Long-term trace storage
- **Qdrant**: Vector database for semantic memory
- **PostgreSQL**: Langfuse database
- **Langfuse**: Observability platform (web + worker)
- **vLLM (Phi-3.5)**: Local model serving
- **Ray**: Distributed orchestration (head + workers)

#### Optional Services (Profile-based)
- **OpenAI Proxy**: Rate-limited access to GPT-4
- **Open WebUI**: Chat interface
- **Langflow**: Visual workflow builder
- **vLLM Large**: Additional model service

### Environment Configuration

Key environment variables in `.env`:

```bash
# Database passwords
LANGFUSE_DB_PASSWORD=langfuse123
CLICKHOUSE_PASSWORD=langfuse123

# Langfuse configuration
LANGFUSE_SECRET=your-secret-key-change-this
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key

# OpenAI proxy (optional)
OPENAI_API_KEY=sk-your-openai-key

# Resource limits
RAY_WORKER_REPLICAS=2
LARGE_MODEL_GPU_COUNT=2
```

## ☸️ Kubernetes Deployment

### Helm Installation

1. **Add Dependencies**
   ```bash
   cd helm
   helm dependency update
   ```

2. **Install with Default Values**
   ```bash
   helm install vllm-local-swarm . \
     --namespace vllm-swarm \
     --create-namespace
   ```

3. **Install with Custom Values**
   ```bash
   # Create custom values file
   cp values.yaml my-values.yaml
   # Edit my-values.yaml
   
   helm install vllm-local-swarm . \
     --namespace vllm-swarm \
     --create-namespace \
     --values my-values.yaml
   ```

### GPU Configuration

Enable GPU support in `values.yaml`:

```yaml
vllm:
  phi:
    resources:
      requests:
        nvidia.com/gpu: 1
      limits:
        nvidia.com/gpu: 1

  large:
    enabled: true
    resources:
      requests:
        nvidia.com/gpu: 2
      limits:
        nvidia.com/gpu: 2
```

### Scaling Configuration

Configure autoscaling for Ray workers:

```yaml
ray:
  worker:
    replicas: 2
    autoscaling:
      enabled: true
      minReplicas: 1
      maxReplicas: 10
      targetCPUUtilizationPercentage: 70
```

### Storage Configuration

Configure persistent storage:

```yaml
global:
  storageClass: "fast-ssd"

vllm:
  phi:
    persistence:
      enabled: true
      size: 50Gi

clickhouse:
  persistence:
    enabled: true
    size: 100Gi
```

### Networking Configuration

Configure ingress for external access:

```yaml
langfuse:
  web:
    ingress:
      enabled: true
      className: "nginx"
      annotations:
        cert-manager.io/cluster-issuer: "letsencrypt"
      hosts:
        - host: langfuse.yourdomain.com
          paths:
            - path: /
              pathType: Prefix
      tls:
        - secretName: langfuse-tls
          hosts:
            - langfuse.yourdomain.com
```

## ⚙️ Configuration

### Model Configuration

Configure which models to serve:

**Docker Compose** (`.env`):
```bash
# Phi-3.5 model (always enabled)
VLLM_PHI_MODEL=microsoft/Phi-3.5-mini-instruct

# Large model (optional)
LARGE_MODEL=microsoft/DialoGPT-large
LARGE_MODEL_TP=2
```

**Kubernetes** (`values.yaml`):
```yaml
vllm:
  phi:
    model: "microsoft/Phi-3.5-mini-instruct"
    env:
      VLLM_TENSOR_PARALLEL_SIZE: 1
      VLLM_GPU_MEMORY_UTILIZATION: 0.8

  large:
    enabled: true
    model: "microsoft/DialoGPT-large"
    env:
      VLLM_TENSOR_PARALLEL_SIZE: 2
```

### Resource Limits

**Docker Compose**:
Resources are controlled via Docker Compose deploy sections and environment variables.

**Kubernetes**:
```yaml
vllm:
  phi:
    resources:
      requests:
        cpu: 2
        memory: 8Gi
        nvidia.com/gpu: 1
      limits:
        cpu: 4
        memory: 16Gi
        nvidia.com/gpu: 1
```

### Security Configuration

**Docker Compose**:
- Uses bridge networking with isolated subnet
- No authentication by default (suitable for local development)

**Kubernetes**:
```yaml
# Enable RBAC
rbac:
  create: true

# Pod Security Context
podSecurityContext:
  fsGroup: 1000

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: false
  allowPrivilegeEscalation: false

# Network Policies (optional)
networkPolicy:
  enabled: true
```

## 🏗️ Service Overview

### Architecture Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Ray Cluster   │    │   vLLM Models   │    │  Observability  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Ray Head    │ │    │ │ Phi-3.5     │ │    │ │ Langfuse    │ │
│ │ (Dashboard) │ │    │ │ (Primary)   │ │    │ │ (Web + API) │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Ray Workers │ │    │ │ Large Model │ │    │ │ ClickHouse  │ │
│ │ (Agents)    │ │    │ │ (Optional)  │ │    │ │ (Storage)   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌─────────────────────────────────────────────────┐
        │                Memory Layer                     │
        │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ │
        │ │    Redis    │ │   Qdrant    │ │ PostgreSQL  │ │
        │ │  (Cache)    │ │ (Vectors)   │ │ (Metadata)  │ │
        │ └─────────────┘ └─────────────┘ └─────────────┘ │
        └─────────────────────────────────────────────────┘
```

### Port Mapping

| Service | Docker Port | K8s Service | Description |
|---------|-------------|-------------|-------------|
| Langfuse Web | 3000 | langfuse-web:3000 | Observability dashboard |
| Ray Dashboard | 8265 | ray-head:8265 | Ray cluster monitoring |
| vLLM Phi-3.5 | 8000 | vllm-phi:8000 | Primary model API |
| vLLM Large | 8001 | vllm-large:8001 | Large model API |
| OpenAI Proxy | 8002 | openai-proxy:8002 | GPT-4 proxy |
| Qdrant | 6333 | qdrant:6333 | Vector database |
| ClickHouse | 8123 | clickhouse:8123 | Analytics database |
| Redis | 6379 | redis:6379 | Cache and queue |
| Open WebUI | 8080 | open-webui:8080 | Chat interface |
| Langflow | 7860 | langflow:7860 | Workflow builder |

## 📊 Monitoring & Observability

### Built-in Dashboards

1. **Langfuse Dashboard** (`http://localhost:3000`)
   - LLM request tracing
   - Performance metrics
   - Cost analysis
   - Session management

2. **Ray Dashboard** (`http://localhost:8265`)
   - Cluster status
   - Job monitoring
   - Resource utilization
   - Task execution

3. **Qdrant Dashboard** (`http://localhost:6333/dashboard`)
   - Vector collections
   - Search performance
   - Index statistics

### Health Checks

All services include comprehensive health checks:

```bash
# Docker Compose
docker-compose ps

# Kubernetes
kubectl get pods -n vllm-swarm
```

### Logging

**Docker Compose**:
```bash
# View all logs
make compose-logs

# View specific service
docker-compose logs -f langfuse-web
```

**Kubernetes**:
```bash
# View pod logs
kubectl logs -f deployment/vllm-local-swarm-langfuse-web -n vllm-swarm

# View all logs
kubectl logs -l app.kubernetes.io/instance=vllm-local-swarm -n vllm-swarm
```

## 🔧 Troubleshooting

### Common Issues

#### 1. GPU Not Detected

**Symptoms**: vLLM fails to start, GPU memory errors

**Solutions**:
```bash
# Check GPU availability
nvidia-smi

# Verify Docker GPU runtime
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Check NVIDIA Docker runtime
docker info | grep nvidia
```

#### 2. Out of Memory Errors

**Symptoms**: Services crashing with OOM errors

**Solutions**:
- Reduce `VLLM_GPU_MEMORY_UTILIZATION` in `.env`
- Decrease `RAY_OBJECT_STORE_MEMORY`
- Scale down Ray worker replicas
- Use smaller models

#### 3. Model Download Failures

**Symptoms**: vLLM containers failing to start, model loading errors

**Solutions**:
```bash
# Check disk space
df -h

# Manually download models
docker run -v ./models:/app/models vllm/vllm-openai:latest \
  python -c "from transformers import AutoModel; AutoModel.from_pretrained('microsoft/Phi-3.5-mini-instruct')"
```

#### 4. Service Connectivity Issues

**Symptoms**: Services unable to communicate

**Solutions**:
```bash
# Docker Compose - check network
docker network ls
docker network inspect vllm-local-swarm_vllm-network

# Kubernetes - check services
kubectl get services -n vllm-swarm
kubectl describe service vllm-local-swarm-langfuse-web -n vllm-swarm
```

#### 5. Persistent Volume Issues

**Symptoms**: Data loss on restart, mount failures

**Solutions**:
```bash
# Docker Compose - check volumes
docker volume ls
docker volume inspect vllm-local-swarm_clickhouse_data

# Kubernetes - check PVCs
kubectl get pvc -n vllm-swarm
kubectl describe pvc vllm-local-swarm-clickhouse-data -n vllm-swarm
```

### Performance Optimization

#### Model Loading Optimization

```bash
# Preload models to shared volume
docker run -v vllm_cache:/cache vllm/vllm-openai:latest \
  python -c "
from transformers import AutoTokenizer, AutoModel
model = AutoModel.from_pretrained('microsoft/Phi-3.5-mini-instruct', cache_dir='/cache')
tokenizer = AutoTokenizer.from_pretrained('microsoft/Phi-3.5-mini-instruct', cache_dir='/cache')
"
```

#### Resource Tuning

**For High-Memory Systems (32GB+)**:
```yaml
# values.yaml
vllm:
  phi:
    env:
      VLLM_GPU_MEMORY_UTILIZATION: 0.9
      VLLM_MAX_MODEL_LEN: 65536

ray:
  head:
    resources:
      requests:
        memory: 8Gi
      limits:
        memory: 16Gi
```

**For Low-Memory Systems (16GB)**:
```yaml
# values.yaml
vllm:
  phi:
    env:
      VLLM_GPU_MEMORY_UTILIZATION: 0.7
      VLLM_MAX_MODEL_LEN: 16384

ray:
  worker:
    replicas: 1
```

## 🚀 Production Considerations

### Security Hardening

1. **Change Default Passwords**
   ```bash
   # Generate secure passwords
   openssl rand -base64 32  # For secrets
   openssl rand -hex 16     # For salts
   ```

2. **Enable TLS**
   ```yaml
   # values.yaml
   langfuse:
     web:
       ingress:
         enabled: true
         annotations:
           cert-manager.io/cluster-issuer: "letsencrypt"
         tls:
           - secretName: langfuse-tls
             hosts:
               - langfuse.yourdomain.com
   ```

3. **Network Policies**
   ```yaml
   # values.yaml
   networkPolicy:
     enabled: true
   ```

### High Availability

1. **Database Clustering**
   ```yaml
   # values.yaml
   postgresql:
     architecture: replication
     readReplicas:
       replicaCount: 2

   redis:
     architecture: replication
     replica:
       replicaCount: 2
   ```

2. **Multi-Zone Deployment**
   ```yaml
   # values.yaml
   vllm:
     phi:
       affinity:
         podAntiAffinity:
           preferredDuringSchedulingIgnoredDuringExecution:
           - weight: 100
             podAffinityTerm:
               labelSelector:
                 matchLabels:
                   app.kubernetes.io/component: vllm-phi
               topologyKey: topology.kubernetes.io/zone
   ```

### Backup Strategy

1. **Database Backups**
   ```bash
   # PostgreSQL backup
   kubectl exec -it postgresql-pod -- pg_dump -U langfuse langfuse > backup.sql

   # ClickHouse backup
   kubectl exec -it clickhouse-pod -- clickhouse-client --query "BACKUP DATABASE langfuse TO Disk('backups', 'backup.zip')"
   ```

2. **Model Cache Backup**
   ```bash
   # Backup model cache volume
   docker run --rm -v vllm_cache:/data -v $(pwd):/backup ubuntu tar czf /backup/model-cache.tar.gz /data
   ```

### Monitoring Setup

1. **Prometheus Integration**
   ```yaml
   # values.yaml
   monitoring:
     enabled: true
     prometheus:
       enabled: true
       serviceMonitor:
         enabled: true
   ```

2. **Grafana Dashboards**
   ```yaml
   # values.yaml
   monitoring:
     grafana:
       enabled: true
       dashboards:
         enabled: true
   ```

### Cost Optimization

1. **Spot Instances** (Cloud deployments)
   ```yaml
   # values.yaml
   vllm:
     phi:
       tolerations:
       - key: "spot-instance"
         operator: "Equal"
         value: "true"
         effect: "NoSchedule"
   ```

2. **Resource Limits**
   ```yaml
   # values.yaml
   ray:
     worker:
       autoscaling:
         enabled: true
         minReplicas: 0  # Scale to zero when idle
         maxReplicas: 10
   ```

---

## 📞 Support

For issues and questions:
- 📖 [Documentation](https://github.com/your-org/vllm-local-swarm/docs)
- 🐛 [Issue Tracker](https://github.com/your-org/vllm-local-swarm/issues)
- 💬 [Community Forum](https://github.com/your-org/vllm-local-swarm/discussions)

---

**Next Steps**: After successful deployment, see the [Usage Guide](USAGE.md) for information on using the CLI and APIs.