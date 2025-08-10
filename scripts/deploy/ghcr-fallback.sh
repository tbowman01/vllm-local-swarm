#!/bin/bash
set -e

# 🐳 GHCR Container Fallback Deployment
# Uses composite container when individual containers aren't available

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

GHCR_REGISTRY="ghcr.io/tbowman01/vllm-local-swarm"

echo -e "${BLUE}🐳 GHCR Container Deployment with Fallback${NC}"
echo "======================================================="

cd "$PROJECT_ROOT"

# Function to check if individual containers are available
check_individual_containers() {
    echo -e "${YELLOW}🔍 Checking individual container availability...${NC}"
    
    services=("auth-service" "orchestrator" "memory-api")
    available_services=()
    unavailable_services=()
    
    for service in "${services[@]}"; do
        if docker pull "$GHCR_REGISTRY/$service:latest" >/dev/null 2>&1; then
            available_services+=("$service")
            echo -e "${GREEN}  ✅ $service:latest available${NC}"
        else
            unavailable_services+=("$service")
            echo -e "${YELLOW}  ⚠️  $service:latest not available${NC}"
        fi
    done
    
    echo ""
    if [ ${#unavailable_services[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All individual containers available${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Some individual containers unavailable: ${unavailable_services[*]}${NC}"
        return 1
    fi
}

# Function to deploy using composite container
deploy_composite() {
    echo -e "${YELLOW}🚀 Deploying with composite container...${NC}"
    
    # Pull composite container
    echo -e "${BLUE}📦 Pulling composite container...${NC}"
    docker pull "$GHCR_REGISTRY/vllm-swarm:latest"
    
    # Start infrastructure first
    echo -e "${BLUE}🏗️  Starting infrastructure services...${NC}"
    docker-compose up -d redis langfuse-db qdrant langfuse-web
    
    # Wait for infrastructure
    sleep 15
    
    # Start composite container only
    echo -e "${BLUE}🚀 Starting composite container...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml --profile all-in-one up -d vllm-swarm-composite
    
    echo -e "${GREEN}✅ Composite deployment complete${NC}"
}

# Function to deploy using individual containers
deploy_individual() {
    echo -e "${YELLOW}🚀 Deploying with individual containers...${NC}"
    
    # Start infrastructure first
    echo -e "${BLUE}🏗️  Starting infrastructure services...${NC}"
    docker-compose up -d redis langfuse-db qdrant langfuse-web
    
    # Wait for infrastructure
    sleep 15
    
    # Start individual services
    echo -e "${BLUE}🚀 Starting individual services...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d auth-service orchestrator memory-api
    
    echo -e "${GREEN}✅ Individual service deployment complete${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
    
    # Wait for services to start
    sleep 30
    
    # Check endpoints
    services=(
        "Auth Service:http://localhost:8005/health"
        "Memory API:http://localhost:8003/health"
    )
    
    all_healthy=true
    for service_info in "${services[@]}"; do
        IFS=':' read -r name url <<< "$service_info"
        echo -e "${BLUE}  Checking $name...${NC}"
        
        for i in {1..10}; do
            if curl -s -f "$url" >/dev/null 2>&1; then
                echo -e "${GREEN}    ✅ $name is responding${NC}"
                break
            fi
            if [ $i -eq 10 ]; then
                echo -e "${RED}    ❌ $name is not responding after 10 attempts${NC}"
                all_healthy=false
            else
                sleep 3
            fi
        done
    done
    
    if [ "$all_healthy" = true ]; then
        echo -e "${GREEN}✅ All services are healthy${NC}"
    else
        echo -e "${YELLOW}⚠️  Some services may still be starting up${NC}"
    fi
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo -e "${GREEN}🎉 GHCR deployment completed!${NC}"
    echo "======================================================="
    echo ""
    echo -e "${BLUE}📊 Service Endpoints:${NC}"
    echo "  • Auth Service:     http://localhost:8005"
    echo "  • Memory API:       http://localhost:8003"
    echo "  • Langfuse:         http://localhost:3000"
    echo ""
    echo -e "${YELLOW}💡 Note:${NC}"
    echo "  This deployment uses GHCR containers with automatic fallback"
    echo "  to composite container when individual services aren't available"
    echo ""
    echo -e "${BLUE}🔧 Management:${NC}"
    echo "  • View logs:        docker-compose logs -f"
    echo "  • Stop services:    docker-compose down"
}

# Main deployment logic
main() {
    if check_individual_containers; then
        deploy_individual
    else
        echo -e "${YELLOW}📦 Falling back to composite container deployment${NC}"
        deploy_composite
    fi
    
    verify_deployment
    show_summary
}

# Handle script arguments
case "${1:-}" in
    --composite)
        echo -e "${BLUE}🐳 Force using composite container${NC}"
        docker pull "$GHCR_REGISTRY/vllm-swarm:latest"
        deploy_composite
        verify_deployment
        show_summary
        ;;
    --individual)
        echo -e "${BLUE}🔧 Force using individual containers${NC}"
        deploy_individual
        verify_deployment
        show_summary
        ;;
    --help|-h)
        echo "GHCR Container Deployment with Fallback"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --composite   Force use composite container"
        echo "  --individual  Force use individual containers"
        echo "  --help        Show this help message"
        echo ""
        echo "Default: Auto-detect and fallback to composite if needed"
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