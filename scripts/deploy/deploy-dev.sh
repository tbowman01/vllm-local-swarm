#!/bin/bash
set -e

# 🚀 Development Environment Deployment Script
# Uses GHCR containers with development configuration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="development"
GHCR_REGISTRY="ghcr.io/tbowman01/vllm-local-swarm"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.ghcr.yml"

echo -e "${BLUE}🚀 vLLM Local Swarm - Development Deployment${NC}"
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
            echo -e "${YELLOW}⚠️  Could not pull $image, will use local build${NC}"
        }
    done
    
    echo -e "${GREEN}✅ Image pull completed${NC}"
}

# Function to create development environment file
create_dev_env() {
    echo -e "${YELLOW}🔧 Creating development environment...${NC}"
    
    cat > .env.development << 'EOF'
# Development Environment Configuration
NODE_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Authentication
JWT_SECRET_KEY=dev-jwt-secret-key-change-this-in-production-min32chars
API_SECRET_KEY=dev-api-secret-key-for-service-communication

# Database URLs
DATABASE_URL=postgresql+asyncpg://langfuse:langfuse123@langfuse-db:5432/auth
REDIS_URL=redis://redis:6379
QDRANT_URL=http://qdrant:6333

# Observability
LANGFUSE_SECRET_KEY=sk-lf-development-key
LANGFUSE_PUBLIC_KEY=pk-lf-development-key
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_ENCRYPTION_KEY=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ123456789abc

# AI/ML Configuration
VLLM_GPU_MEMORY_UTILIZATION=0.90
VLLM_MAX_MODEL_LEN=16384

# Development Settings
ENABLE_CORS=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT_ENABLED=false

# Container Images
AUTH_SERVICE_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/auth-service:latest
ORCHESTRATOR_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/orchestrator:latest
MEMORY_API_IMAGE=ghcr.io/tbowman01/vllm-local-swarm/memory-api:latest
EOF

    echo -e "${GREEN}✅ Development environment configured${NC}"
}

# Function to start infrastructure services
start_infrastructure() {
    echo -e "${YELLOW}🏗️  Starting infrastructure services...${NC}"
    
    # Start foundation services first
    docker-compose up -d redis langfuse-db qdrant
    
    # Wait for services to be ready
    echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
    sleep 10
    
    # Check service health
    check_service_health "Redis" "localhost:6379" "redis-cli ping"
    check_service_health "PostgreSQL" "localhost:5432" "pg_isready -h localhost -p 5432"
    check_service_health "Qdrant" "localhost:6333" "curl -s http://localhost:6333/"
    
    echo -e "${GREEN}✅ Infrastructure services ready${NC}"
}

# Function to check service health
check_service_health() {
    local service_name="$1"
    local endpoint="$2"
    local health_command="$3"
    
    echo -e "${BLUE}  Checking $service_name health...${NC}"
    
    for i in {1..30}; do
        if eval "$health_command" &>/dev/null; then
            echo -e "${GREEN}    ✅ $service_name is healthy${NC}"
            return 0
        fi
        sleep 2
    done
    
    echo -e "${RED}    ❌ $service_name health check failed${NC}"
    return 1
}

# Function to setup database
setup_database() {
    echo -e "${YELLOW}💾 Setting up development database...${NC}"
    
    # Wait for PostgreSQL to be ready
    sleep 5
    
    # Create auth database if it doesn't exist
    docker exec vllm-langfuse-db psql -U langfuse -c "CREATE DATABASE auth;" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Database setup completed${NC}"
}

# Function to start application services
start_application() {
    echo -e "${YELLOW}🚀 Starting application services with GHCR images...${NC}"
    
    # Start Langfuse first
    docker-compose up -d langfuse-web
    sleep 10
    
    # Start application services
    docker-compose $COMPOSE_FILES up -d auth-service orchestrator memory-api
    
    echo -e "${GREEN}✅ Application services started${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
    
    # Wait for services to start
    sleep 15
    
    # Check service endpoints
    services=(
        "Auth Service:http://localhost:8005/health"
        "Orchestrator:http://localhost:8006/health"  
        "Memory API:http://localhost:8003/health"
        "Langfuse:http://localhost:3000"
    )
    
    for service_info in "${services[@]}"; do
        IFS=':' read -r name url <<< "$service_info"
        echo -e "${BLUE}  Checking $name at $url${NC}"
        
        for i in {1..10}; do
            if curl -s -f "$url" >/dev/null; then
                echo -e "${GREEN}    ✅ $name is responding${NC}"
                break
            fi
            if [ $i -eq 10 ]; then
                echo -e "${RED}    ❌ $name is not responding${NC}"
            fi
            sleep 3
        done
    done
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo -e "${GREEN}🎉 Development deployment completed successfully!${NC}"
    echo "======================================================="
    echo ""
    echo -e "${BLUE}📊 Service Endpoints:${NC}"
    echo "  • Auth Service:     http://localhost:8005"
    echo "  • Orchestrator:     http://localhost:8006"
    echo "  • Memory API:       http://localhost:8003"
    echo "  • Langfuse:         http://localhost:3000"
    echo "  • Redis:            localhost:6379"
    echo "  • PostgreSQL:       localhost:5432"
    echo "  • Qdrant:           http://localhost:6333"
    echo ""
    echo -e "${BLUE}🔧 Management Commands:${NC}"
    echo "  • View logs:        docker-compose logs -f"
    echo "  • Stop services:    docker-compose down"
    echo "  • Restart:          ./scripts/deploy/deploy-dev.sh"
    echo ""
    echo -e "${BLUE}🧪 Testing:${NC}"
    echo "  • Health checks:    ./scripts/dev/health-check.sh"
    echo "  • Run tests:        ./scripts/dev/run-tests.sh"
    echo ""
    echo -e "${YELLOW}💡 Next Steps:${NC}"
    echo "  1. Test authentication: curl http://localhost:8005/health"
    echo "  2. View dashboard: open http://localhost:3000"
    echo "  3. Check logs: docker-compose logs -f auth-service"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Deployment failed${NC}"
        echo -e "${YELLOW}📋 Troubleshooting:${NC}"
        echo "  • Check logs: docker-compose logs"
        echo "  • Check services: docker-compose ps"
        echo "  • Clean up: docker-compose down --volumes"
    fi
}

# Main deployment flow
main() {
    trap cleanup EXIT
    
    check_prerequisites
    pull_images
    create_dev_env
    start_infrastructure
    setup_database
    start_application
    verify_deployment
    show_summary
}

# Handle script arguments
case "${1:-}" in
    --clean)
        echo -e "${YELLOW}🧹 Cleaning up existing deployment...${NC}"
        docker-compose down --volumes --remove-orphans
        docker system prune -f
        ;;
    --logs)
        docker-compose logs -f
        exit 0
        ;;
    --status)
        docker-compose ps
        exit 0
        ;;
    --help|-h)
        echo "vLLM Local Swarm Development Deployment"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --clean    Clean up existing deployment"
        echo "  --logs     Show service logs"
        echo "  --status   Show service status"
        echo "  --help     Show this help message"
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