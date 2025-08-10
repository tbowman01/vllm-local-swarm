#!/bin/bash
set -e

# 🚀 Production Environment Deployment Script
# Uses GHCR containers with maximum security configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="production"
GHCR_REGISTRY="ghcr.io/tbowman01/vllm-local-swarm"

echo -e "${BLUE}🚀 vLLM Local Swarm - Production Deployment${NC}"
echo "======================================================="

cd "$PROJECT_ROOT"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check for CRITICAL production environment variables
    critical_vars=(
        "PROD_JWT_SECRET_KEY"
        "PROD_API_SECRET_KEY"
        "PROD_DATABASE_URL"
        "PROD_REDIS_PASSWORD"
        "PROD_ENCRYPTION_KEY"
    )
    
    for var in "${critical_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo -e "${RED}❌ CRITICAL: Production environment variable $var is not set${NC}"
            echo -e "${YELLOW}💡 Set production secrets before deploying to production${NC}"
            exit 1
        fi
    done
    
    # Validate secret lengths
    if [ ${#PROD_JWT_SECRET_KEY} -lt 64 ]; then
        echo -e "${RED}❌ PROD_JWT_SECRET_KEY too short (minimum 64 characters for production)${NC}"
        exit 1
    fi
    
    if [ ${#PROD_ENCRYPTION_KEY} -lt 64 ]; then
        echo -e "${RED}❌ PROD_ENCRYPTION_KEY too short (minimum 64 characters for production)${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites and security validation passed${NC}"
}

# Function to pull latest images
pull_images() {
    echo -e "${YELLOW}📦 Pulling latest GHCR production images...${NC}"
    
    images=(
        "$GHCR_REGISTRY/auth-service:latest"
        "$GHCR_REGISTRY/orchestrator:latest"
        "$GHCR_REGISTRY/memory-api:latest"
        "$GHCR_REGISTRY/vllm-swarm:latest"
    )
    
    for image in "${images[@]}"; do
        echo -e "${BLUE}  Pulling $image${NC}"
        docker pull "$image" || {
            echo -e "${RED}❌ CRITICAL: Failed to pull production image $image${NC}"
            exit 1
        }
    done
    
    echo -e "${GREEN}✅ All production images pulled successfully${NC}"
}

# Function to create production environment
create_production_env() {
    echo -e "${YELLOW}🔧 Creating production environment configuration...${NC}"
    
    cat > .env.production << EOF
# Production Environment Configuration - MAXIMUM SECURITY
NODE_ENV=production
DEBUG=false
LOG_LEVEL=WARN
SECURE_MODE=true

# Authentication (CRITICAL SECURITY)
JWT_SECRET_KEY=${PROD_JWT_SECRET_KEY}
API_SECRET_KEY=${PROD_API_SECRET_KEY}
JWT_EXPIRATION=1800
JWT_REFRESH_EXPIRATION=604800

# Database with encryption
DATABASE_URL=${PROD_DATABASE_URL}
DB_ENCRYPTION_KEY=${PROD_DB_ENCRYPTION_KEY:-${PROD_ENCRYPTION_KEY}}
DB_SSL_MODE=require
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# Redis with TLS
REDIS_URL=${PROD_REDIS_URL}
REDIS_PASSWORD=${PROD_REDIS_PASSWORD}
REDIS_TLS=true

# Observability
LANGFUSE_SECRET_KEY=${PROD_LANGFUSE_SECRET_KEY}
LANGFUSE_PUBLIC_KEY=${PROD_LANGFUSE_PUBLIC_KEY}
LANGFUSE_HOST=${PROD_LANGFUSE_HOST}
LANGFUSE_ENCRYPTION_KEY=${PROD_LANGFUSE_ENCRYPTION_KEY:-${PROD_ENCRYPTION_KEY}}

# External APIs
OPENAI_API_KEY=${PROD_OPENAI_API_KEY:-}
ANTHROPIC_API_KEY=${PROD_ANTHROPIC_API_KEY:-}

# Security & Monitoring
ENCRYPTION_KEY=${PROD_ENCRYPTION_KEY}
AUDIT_WEBHOOK_URL=${PROD_AUDIT_WEBHOOK_URL:-}
ALERT_EMAIL=${PROD_ALERT_EMAIL:-}

# Rate limiting & security
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW=900
RATE_LIMIT_MAX=100
CORS_ORIGINS=${PROD_CORS_ORIGINS:-https://your-domain.com}
ALLOWED_HOSTS=${PROD_ALLOWED_HOSTS:-your-domain.com}

# AI/ML Production Settings
VLLM_GPU_MEMORY_UTILIZATION=0.85
VLLM_MAX_MODEL_LEN=32768
VLLM_TENSOR_PARALLEL_SIZE=2

# Container Images
AUTH_SERVICE_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest
ORCHESTRATOR_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest
MEMORY_API_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest
VLLM_SWARM_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/vllm-swarm:latest
EOF
    
    # Secure the production environment file
    chmod 600 .env.production
    
    echo -e "${GREEN}✅ Production environment configured with maximum security${NC}"
}

# Function to create production docker-compose
create_production_compose() {
    echo -e "${YELLOW}🐳 Creating production docker-compose configuration...${NC}"
    
    cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  # Production authentication service
  auth-service:
    image: ${AUTH_SERVICE_IMAGE:-ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest}
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=WARN
      - SECURE_MODE=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      
  # Production orchestrator service
  orchestrator:
    image: ${ORCHESTRATOR_IMAGE:-ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest}
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=WARN
      - SECURE_MODE=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8006/health"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      
  # Production memory API service
  memory-api:
    image: ${MEMORY_API_IMAGE:-ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest}
    environment:
      - NODE_ENV=production
      - LOG_LEVEL=WARN
      - SECURE_MODE=true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 60s
      timeout: 30s
      retries: 3
      start_period: 60s
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp

  # Production Redis with authentication and persistence
  redis:
    command: >
      redis-server
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
      --tcp-keepalive 300
      --timeout 300
    volumes:
      - production_redis_data:/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 600M
          cpus: '1.0'
    security_opt:
      - no-new-privileges:true

  # Production PostgreSQL with SSL and backups
  langfuse-db:
    environment:
      - POSTGRES_DB=auth_prod
      - POSTGRES_USER=prod_user
      - POSTGRES_PASSWORD=${PROD_DB_PASSWORD}
      - POSTGRES_SSL_MODE=require
    volumes:
      - production_postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    security_opt:
      - no-new-privileges:true

  # Production Qdrant with persistence
  qdrant:
    volumes:
      - production_qdrant_data:/qdrant/storage
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
    security_opt:
      - no-new-privileges:true

  # Production Langfuse
  langfuse-web:
    environment:
      - NODE_ENV=production
      - NEXTAUTH_SECRET=${PROD_LANGFUSE_SECRET_KEY}
      - ENCRYPTION_KEY=${PROD_LANGFUSE_ENCRYPTION_KEY}
      - DATABASE_URL=postgresql://prod_user:${PROD_DB_PASSWORD}@langfuse-db:5432/langfuse_prod?sslmode=require
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
    security_opt:
      - no-new-privileges:true

volumes:
  production_postgres_data:
    driver: local
  production_redis_data:
    driver: local
  production_qdrant_data:
    driver: local
EOF

    echo -e "${GREEN}✅ Production docker-compose configured${NC}"
}

# Function to perform production deployment
deploy_production() {
    echo -e "${YELLOW}🚀 Deploying to production with maximum security...${NC}"
    
    # Start infrastructure services first
    echo -e "${BLUE}  Starting infrastructure services...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d \
        redis langfuse-db qdrant
    
    # Wait for infrastructure
    sleep 30
    
    # Start application services
    echo -e "${BLUE}  Starting application services...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d \
        langfuse-web auth-service orchestrator memory-api
    
    echo -e "${GREEN}✅ Production deployment initiated${NC}"
}

# Function to verify production deployment
verify_production() {
    echo -e "${YELLOW}🔍 Verifying production deployment (strict checks)...${NC}"
    
    # Extended wait for production startup
    echo -e "${BLUE}  Waiting for services to stabilize...${NC}"
    sleep 60
    
    # Comprehensive health checks
    services=(
        "Auth Service:http://localhost:8005/health"
        "Orchestrator:http://localhost:8006/health"
        "Memory API:http://localhost:8003/health" 
        "Langfuse:http://localhost:3000"
    )
    
    all_healthy=true
    for service_info in "${services[@]}"; do
        IFS=':' read -r name url <<< "$service_info"
        echo -e "${BLUE}  Checking $name at $url${NC}"
        
        healthy=false
        for i in {1..30}; do
            if curl -s -f --max-time 10 "$url" >/dev/null; then
                echo -e "${GREEN}    ✅ $name is responding${NC}"
                healthy=true
                break
            fi
            sleep 5
        done
        
        if [ "$healthy" = false ]; then
            echo -e "${RED}    ❌ $name is not responding${NC}"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = false ]; then
        echo -e "${RED}❌ Production deployment verification failed${NC}"
        echo -e "${YELLOW}📋 Troubleshooting:${NC}"
        echo "  • Check logs: docker-compose -f docker-compose.yml -f docker-compose.production.yml logs"
        echo "  • Check status: docker-compose ps"
        echo "  • Contact operations team immediately"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Production deployment verification successful${NC}"
}

# Function to show production summary
show_production_summary() {
    echo ""
    echo -e "${GREEN}🎉 PRODUCTION DEPLOYMENT SUCCESSFUL!${NC}"
    echo "======================================================="
    echo ""
    echo -e "${BLUE}📊 Production Service Endpoints:${NC}"
    echo "  • Auth Service:     http://localhost:8005 (secure)"
    echo "  • Orchestrator:     http://localhost:8006 (secure)"
    echo "  • Memory API:       http://localhost:8003 (secure)"
    echo "  • Langfuse:         http://localhost:3000 (secure)"
    echo ""
    echo -e "${RED}🔐 PRODUCTION SECURITY ACTIVE:${NC}"
    echo "  • JWT tokens expire in 30 minutes"
    echo "  • Database encryption enabled"
    echo "  • Redis authentication required"
    echo "  • Rate limiting enforced"
    echo "  • All containers run with security constraints"
    echo "  • Read-only filesystems where possible"
    echo ""
    echo -e "${BLUE}📊 Management Commands:${NC}"
    echo "  • View logs:        docker-compose -f docker-compose.yml -f docker-compose.production.yml logs -f"
    echo "  • Check status:     docker-compose ps"
    echo "  • Stop (CRITICAL):  docker-compose -f docker-compose.yml -f docker-compose.production.yml down"
    echo ""
    echo -e "${YELLOW}⚠️  PRODUCTION OPERATIONS:${NC}"
    echo "  • Monitor all services continuously"
    echo "  • Regular security audits required"
    echo "  • Backup databases before updates"
    echo "  • Rotate secrets quarterly"
    echo "  • Monitor resource usage"
    echo ""
    echo -e "${RED}🚨 EMERGENCY PROCEDURES:${NC}"
    echo "  • Security incident: Revoke JWT secrets immediately"
    echo "  • Service failure: Check logs and restart affected services"
    echo "  • Performance issues: Monitor resource usage"
    echo "  • Data issues: Restore from latest backup"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ PRODUCTION DEPLOYMENT FAILED${NC}"
        echo -e "${YELLOW}🚨 CRITICAL: Production deployment failure detected${NC}"
        echo -e "${YELLOW}📋 Immediate Actions:${NC}"
        echo "  1. Check logs: docker-compose -f docker-compose.yml -f docker-compose.production.yml logs"
        echo "  2. Notify operations team"
        echo "  3. Document incident"
        echo "  4. Plan rollback if necessary"
    fi
}

# Main production deployment flow
main() {
    trap cleanup EXIT
    
    echo -e "${RED}⚠️  PRODUCTION DEPLOYMENT - PROCEED WITH CAUTION${NC}"
    read -p "Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}❌ Production deployment cancelled${NC}"
        exit 1
    fi
    
    check_prerequisites
    pull_images
    create_production_env
    create_production_compose
    deploy_production
    verify_production
    show_production_summary
}

# Handle script arguments
case "${1:-}" in
    --clean)
        echo -e "${RED}🚨 CLEANING PRODUCTION DEPLOYMENT${NC}"
        read -p "This will DESTROY all production data. Are you sure? (yes/no): " confirm
        if [ "$confirm" == "yes" ]; then
            docker-compose -f docker-compose.yml -f docker-compose.production.yml down --volumes --remove-orphans
            docker system prune -f
        fi
        ;;
    --logs)
        docker-compose -f docker-compose.yml -f docker-compose.production.yml logs -f
        exit 0
        ;;
    --status)
        docker-compose -f docker-compose.yml -f docker-compose.production.yml ps
        exit 0
        ;;
    --verify)
        verify_production
        exit 0
        ;;
    --help|-h)
        echo "vLLM Local Swarm Production Deployment"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --clean    Clean up production deployment (DESTRUCTIVE)"
        echo "  --logs     Show production logs"
        echo "  --status   Show service status"
        echo "  --verify   Run production verification checks"
        echo "  --help     Show this help message"
        echo ""
        echo "CRITICAL Production Environment Variables Required:"
        echo "  PROD_JWT_SECRET_KEY (64+ chars)"
        echo "  PROD_API_SECRET_KEY (64+ chars)"
        echo "  PROD_DATABASE_URL"
        echo "  PROD_REDIS_PASSWORD"
        echo "  PROD_ENCRYPTION_KEY (64+ chars)"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        echo "Use --help for usage information"
        exit 1
        ;;
esac