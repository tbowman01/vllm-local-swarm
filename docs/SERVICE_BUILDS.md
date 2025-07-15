# Service-Specific Build Guide

This document explains how to build and manage individual services in the vLLM Local Swarm project.

## Quick Reference

### Build Commands

```bash
# Build specific service using SERVICE parameter
make compose-build SERVICE=ray-head
make compose-build SERVICE=ray-worker
make compose-build SERVICE=openai-proxy

# Build using dedicated targets
make build-ray-head          # Build Ray head service
make build-ray-worker        # Build Ray worker service
make build-ray               # Build both Ray services
make build-proxy             # Build OpenAI proxy service
make build-all-custom        # Build all custom services
```

### Service Management

```bash
# Start specific services
make compose-up SERVICE=ray-head
make compose-up SERVICE=ray-worker
make up-ray-head             # Dedicated target
make up-ray-worker           # Dedicated target
make up-ray                  # Start all Ray services
make up-basic                # Start basic services (Redis, Qdrant, Langfuse)

# View logs for specific services
make compose-logs SERVICE=ray-head
make compose-logs SERVICE=langfuse-web
make logs-ray-head           # Dedicated target
make logs-ray-worker         # Dedicated target
make logs-langfuse           # Dedicated target

# Stop specific services
make compose-down SERVICE=ray-head
make compose-down SERVICE=ray-worker
```

## Available Services

### Core Services (Pre-built Images)
- `redis` - Redis cache and message queue
- `qdrant` - Vector database
- `langfuse-db` - PostgreSQL database for Langfuse
- `langfuse-web` - Langfuse web interface
- `langfuse-worker` - Langfuse background worker
- `vllm-phi` - vLLM model server (Phi-3.5)
- `vllm-large` - vLLM large model server (configurable)

### Custom Services (Built from Source)
- `ray-head` - Ray head node (orchestration coordinator)
- `ray-worker` - Ray worker nodes
- `openai-proxy` - OpenAI API proxy service

### Optional Services (Profile-based)
- `open-webui` - Web UI for model interaction (profile: webui)
- `langflow` - Visual workflow builder (profile: langflow)

## Usage Examples

### Development Workflow

1. **Build and start Ray services only:**
   ```bash
   make build-ray
   make up-ray
   ```

2. **Build specific service and view logs:**
   ```bash
   make build-ray-head
   make up-ray-head
   make logs-ray-head
   ```

3. **Quick basic setup:**
   ```bash
   make up-basic          # Start Redis, Qdrant, Langfuse
   make build-ray-head    # Build Ray head
   make up-ray-head       # Start Ray head
   ```

### Testing Individual Components

```bash
# Test Ray head service
make compose-build SERVICE=ray-head
make compose-up SERVICE=ray-head
make compose-logs SERVICE=ray-head

# Test with dependencies
make up-basic                    # Start dependencies first
make compose-up SERVICE=ray-head # Then start Ray head
```

### Debugging Build Issues

```bash
# Build without cache for troubleshooting
docker-compose build --no-cache ray-head

# Build with verbose output
docker-compose build --progress=plain ray-head

# Check service dependencies
docker-compose config ray-head
```

## Build Context and Performance

### Build Times (Approximate)
- `ray-head`: ~1-2 minutes (2.44GB image)
- `ray-worker`: ~1-2 minutes (similar to head)
- `openai-proxy`: ~30 seconds (lightweight)

### Build Optimization
- Docker layer caching is enabled
- Dependencies are cached between builds
- Use `--no-cache` flag sparingly for debugging

### Resource Requirements
- Ray services require ~2GB RAM minimum
- Build process needs ~4GB available disk space
- GPU support optional but recommended for vLLM services

## Configuration

### Environment Variables
Services can be configured via environment variables in `.env`:

```bash
# Ray configuration
RAY_WORKER_REPLICAS=2
RAY_OBJECT_STORE_MEMORY=1000000000

# Model configuration
LARGE_MODEL=microsoft/DialoGPT-large
LARGE_MODEL_TP=2
LARGE_MODEL_GPU_COUNT=2

# Proxy configuration
OPENAI_API_KEY=your-key-here
PROXY_RATE_LIMIT=100
```

### Service Dependencies
- `ray-head` depends on: `redis`, `vllm-phi`
- `ray-worker` depends on: `ray-head`
- `langfuse-web` depends on: `langfuse-db`

## Troubleshooting

### Common Build Issues

1. **Missing directories:**
   ```bash
   mkdir -p ray coordination
   ```

2. **Dependency conflicts:**
   ```bash
   # Check requirements.txt compatibility
   cat docker/ray/requirements.txt
   ```

3. **Build context issues:**
   ```bash
   # Ensure correct build context
   docker-compose config ray-head
   ```

### Service Health Checks

```bash
# Check service status
docker-compose ps

# Check service logs
make logs-ray-head

# Test service endpoints
curl http://localhost:8265  # Ray Dashboard
curl http://localhost:3000  # Langfuse
curl http://localhost:6333  # Qdrant
```

## Integration with Profiles

Service-specific builds work with profiles:

```bash
# Build and start with proxy profile
make build-proxy
make compose-up PROFILES=proxy SERVICE=openai-proxy

# Build all custom services with profiles
make build-all-custom
make compose-up PROFILES=webui,langflow
```

## Best Practices

1. **Start dependencies first:** Always start `up-basic` before Ray services
2. **Use dedicated targets:** Prefer `build-ray-head` over `compose-build SERVICE=ray-head`
3. **Monitor logs:** Use dedicated log targets for better debugging
4. **Clean builds:** Use `make compose-clean` between major changes
5. **Resource monitoring:** Monitor system resources during builds

## Performance Tips

- Use `make build-ray` to build both Ray services in parallel
- Start basic services first to avoid dependency issues
- Use `docker system prune` periodically to clean up build cache
- Monitor memory usage during builds in resource-constrained environments