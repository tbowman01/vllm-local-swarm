# Troubleshooting Guide

This guide helps you diagnose and fix common issues in the vLLM Local Swarm project.

## 🔍 Quick Diagnosis

### Check System Status
```bash
# View all services
make compose-ps

# Check service health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Check resource usage
docker stats --no-stream
```

### View Logs
```bash
# All services
make compose-logs

# Specific service
make logs-ray-head
make logs-langfuse
make logs-redis
```

## 🚨 Common Issues

### 1. Services Won't Start

#### Symptoms
- `docker-compose up` fails
- Services show "exited" status
- "Port already in use" errors

#### Solutions
```bash
# Check for port conflicts
sudo netstat -tulpn | grep :6379
sudo netstat -tulpn | grep :3000

# Kill conflicting processes
sudo kill -9 $(lsof -ti:6379)

# Restart Docker daemon
sudo systemctl restart docker

# Clean up Docker state
docker system prune -f
make compose-clean
```

### 2. Ray Services Failing

#### Symptoms
- Ray head/worker containers exit immediately
- "Ray cluster not found" errors
- Ray dashboard not accessible

#### Solutions
```bash
# Check Ray head logs
make logs-ray-head

# Common fixes
make compose-down SERVICE=ray-head
make build-ray-head
make compose-up SERVICE=redis  # Ensure Redis is running first
make up-ray-head

# Check Ray status inside container
docker exec vllm-ray-head ray status
```

### 3. Memory Issues

#### Symptoms
- Services killed with exit code 137
- "Out of memory" errors
- System becomes unresponsive

#### Solutions
```bash
# Check memory usage
free -h
docker stats

# Reduce memory allocation
echo "RAY_OBJECT_STORE_MEMORY=500000000" >> .env

# Start fewer services
make up-basic  # Only start essential services
```

### 4. Build Failures

#### Symptoms
- `make compose-build` fails
- "No such file or directory" errors
- Dependency conflicts

#### Solutions
```bash
# Clear build cache
docker builder prune -f

# Build without cache
docker-compose build --no-cache ray-head

# Check disk space
df -h

# Fix missing directories
mkdir -p ray coordination
```

### 5. ClickHouse Issues

#### Symptoms
- Langfuse web service fails to start
- "ClickHouse connection failed" errors
- Exit code 137 from ClickHouse

#### Solutions
```bash
# Temporary fix: Disable ClickHouse dependency
# Already implemented in current configuration

# Check ClickHouse logs
docker-compose logs clickhouse

# Increase memory limits
echo "CLICKHOUSE_MAX_MEMORY=2000000000" >> .env
```

### 6. Network Connectivity Issues

#### Symptoms
- Services can't reach each other
- "Connection refused" errors
- Timeouts between services

#### Solutions
```bash
# Check Docker networks
docker network ls
docker network inspect vllm-local-swarm_vllm-network

# Restart networking
make compose-down
docker network prune -f
make compose-up
```

## 🔧 Service-Specific Troubleshooting

### Redis Issues
```bash
# Check Redis connectivity
docker exec vllm-redis redis-cli ping

# View Redis logs
make logs-redis

# Common fixes
make compose-down SERVICE=redis
make compose-up SERVICE=redis
```

### Qdrant Issues
```bash
# Test Qdrant API
curl http://localhost:6333/health

# Check Qdrant logs
make logs-qdrant

# Reset Qdrant data
make compose-down SERVICE=qdrant
docker volume rm vllm-local-swarm_qdrant_data
make compose-up SERVICE=qdrant
```

### Langfuse Issues
```bash
# Check database connection
docker exec vllm-langfuse-db pg_isready -U langfuse

# View Langfuse logs
make logs-langfuse

# Reset Langfuse database
make compose-down SERVICE=langfuse-db
docker volume rm vllm-local-swarm_langfuse_db_data
make compose-up SERVICE=langfuse-db
make compose-up SERVICE=langfuse-web
```

### Ray Cluster Issues
```bash
# Check Ray cluster status
docker exec vllm-ray-head ray status

# View Ray logs
make logs-ray-head
make logs-ray-worker

# Reset Ray cluster
make compose-down SERVICE=ray-head SERVICE=ray-worker
make build-ray
make up-ray
```

## 🐛 Debugging Tips

### Enable Debug Logging
```bash
# Add to .env
RAY_LOG_LEVEL=DEBUG
LANGFUSE_LOG_LEVEL=DEBUG

# Restart services
make compose-down
make compose-up
```

### Interactive Debugging
```bash
# Access service shells
docker exec -it vllm-ray-head bash
docker exec -it vllm-redis redis-cli
docker exec -it vllm-langfuse-db psql -U langfuse

# Check service processes
docker exec vllm-ray-head ps aux
docker exec vllm-ray-head netstat -tulpn
```

### Performance Debugging
```bash
# Monitor resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check disk usage
docker system df

# Analyze logs for performance issues
make logs-ray-head | grep -i "slow\|timeout\|error"
```

## 📊 Environment-Specific Issues

### macOS Issues
```bash
# Increase Docker memory allocation
# Docker Desktop > Settings > Resources > Memory: 8GB+

# Fix file sharing permissions
# Docker Desktop > Settings > Resources > File Sharing
```

### Windows/WSL2 Issues
```bash
# Increase WSL2 memory
echo '[wsl2]
memory=8GB' >> ~/.wslconfig

# Restart WSL2
wsl --shutdown
```

### Linux Issues
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Increase file descriptor limits
echo "fs.file-max = 65536" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## 🛠️ Recovery Procedures

### Complete Reset
```bash
# Nuclear option: Reset everything
make compose-down
make compose-clean
docker system prune -af
docker volume prune -f

# Rebuild from scratch
make compose-build
make compose-up
```

### Partial Reset
```bash
# Reset specific service
make compose-down SERVICE=ray-head
docker volume rm vllm-local-swarm_ray_logs
make build-ray-head
make up-ray-head
```

### Configuration Reset
```bash
# Reset environment
cp .env.example .env

# Reset to default configuration
git checkout -- docker-compose.yml
```

## 📋 Health Check Commands

### Service Health Checks
```bash
# Redis
redis-cli -h localhost -p 6379 ping

# Qdrant
curl -f http://localhost:6333/health

# Langfuse
curl -f http://localhost:3000/api/public/health

# Ray
curl -f http://localhost:8265/api/nodes
```

### Automated Health Check
```bash
#!/bin/bash
# Save as check_health.sh

services=("redis:6379" "qdrant:6333" "langfuse:3000" "ray:8265")

for service in "${services[@]}"; do
    name=${service%:*}
    port=${service#*:}
    
    if nc -z localhost $port; then
        echo "✅ $name: OK"
    else
        echo "❌ $name: FAIL"
    fi
done
```

## 📞 Getting Help

### Before Reporting Issues
1. Check this troubleshooting guide
2. Review recent changes to your setup
3. Collect relevant logs and error messages
4. Note your system configuration

### Information to Include
- Operating system and version
- Docker and Docker Compose versions
- Service logs (relevant portions)
- Steps to reproduce the issue
- Expected vs actual behavior

### Support Channels
- GitHub Issues: https://github.com/tbowman01/vllm-local-swarm/issues
- Documentation: Check `docs/` directory
- Community: Docker and Ray community forums

## 🔄 Maintenance Tips

### Regular Maintenance
```bash
# Clean up unused resources (weekly)
docker system prune -f

# Update images (monthly)
docker-compose pull

# Backup important data
docker volume ls | grep vllm-local-swarm
```

### Performance Optimization
```bash
# Monitor resource usage
docker stats --no-stream

# Optimize memory allocation
# Edit .env with appropriate values for your system

# Use faster storage
# Consider SSD for Docker volumes
```

### Security Considerations
```bash
# Regular updates
git pull origin main
docker-compose pull

# Check for vulnerabilities
docker scout quickview

# Secure environment variables
chmod 600 .env
```

---

**Remember**: Most issues can be resolved by restarting services, checking logs, and ensuring proper resource allocation. Start with the simplest solutions first!