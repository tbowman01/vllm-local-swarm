#!/bin/bash
set -e

# 🚀 Staging Environment Deployment Script
# Uses GHCR containers with staging configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="staging"
GHCR_REGISTRY="ghcr.io/tbowman01/vllm-local-swarm"

echo -e "${BLUE}🚀 vLLM Local Swarm - Staging Deployment${NC}"
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
    
    echo -e "${GREEN}✅ Prerequisites OK${NC}"
}

# Function to pull latest images
pull_images() {
    echo -e "${YELLOW}📦 Pulling latest GHCR images...${NC}"
    
    images=(
        "$GHCR_REGISTRY/auth-service:latest"
        "$GHCR_REGISTRY/orchestrator:latest"
        "$GHCR_REGISTRY/memory-api:latest"
        "$GHCR_REGISTRY/vllm-swarm:latest"
    )
    
    for image in "${images[@]}"; do
        echo -e "${BLUE}  Pulling $image${NC}"
        docker pull "$image" || {
            echo -e "${YELLOW}⚠️  Could not pull $image${NC}"
        }
    done
    
    echo -e "${GREEN}✅ Image pull completed${NC}"
}

# Function to create staging environment
create_staging_env() {
    echo -e "${YELLOW}🔧 Creating staging environment...${NC}"
    
    cat > .env.staging << 'EOF'
# Staging Environment Configuration
NODE_ENV=staging
DEBUG=false
LOG_LEVEL=INFO

# Authentication (use environment variables or GitHub secrets)
JWT_SECRET_KEY=${STAGING_JWT_SECRET_KEY:-staging-jwt-secret-change-this}
API_SECRET_KEY=${STAGING_API_SECRET_KEY:-staging-api-secret-change-this}

# Database
DATABASE_URL=${STAGING_DATABASE_URL:-postgresql+asyncpg://langfuse:langfuse123@langfuse-db:5432/auth}
REDIS_URL=${STAGING_REDIS_URL:-redis://redis:6379}

# Container Images
AUTH_SERVICE_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest
ORCHESTRATOR_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest
MEMORY_API_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest
EOF
    
    echo -e "${GREEN}✅ Staging environment configured${NC}"
}

# Show summary function
show_staging_summary() {
    echo ""
    echo -e "${GREEN}🎉 Staging deployment setup completed!${NC}"
    echo "======================================================="
    echo ""
    echo -e "${BLUE}📊 Service Endpoints:${NC}"
    echo "  • Auth Service:     http://localhost:8005"
    echo "  • Orchestrator:     http://localhost:8006"
    echo "  • Memory API:       http://localhost:8003"
    echo "  • Langfuse:         http://localhost:3000"
    echo ""
    echo -e "${YELLOW}💡 Configure staging secrets using environment variables${NC}"
}

# Main deployment
main() {
    check_prerequisites
    pull_images
    create_staging_env
    show_staging_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "vLLM Local Swarm Staging Deployment"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Optional Environment Variables:"
        echo "  STAGING_JWT_SECRET_KEY"
        echo "  STAGING_API_SECRET_KEY" 
        echo "  STAGING_DATABASE_URL"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        echo -e "${RED}❌ Unknown option: $1${NC}"
        exit 1
        ;;
esac