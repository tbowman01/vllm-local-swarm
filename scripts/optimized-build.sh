#!/bin/bash
# 🚀 Optimized Docker Build Script with Advanced Caching
# This script uses BuildKit features for faster, more efficient builds

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CACHE_REGISTRY="${CACHE_REGISTRY:-vllm-swarm/cache}"
BUILD_PARALLEL="${BUILD_PARALLEL:-true}"
USE_INLINE_CACHE="${USE_INLINE_CACHE:-true}"
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
BUILDKIT_PROGRESS="${BUILDKIT_PROGRESS:-auto}"

# Export BuildKit environment variables
export DOCKER_BUILDKIT COMPOSE_DOCKER_CLI_BUILD BUILDKIT_PROGRESS

echo -e "${BLUE}🚀 vLLM Local Swarm - Optimized Build System${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to check if BuildKit is available
check_buildkit() {
    echo -e "${YELLOW}📦 Checking Docker BuildKit...${NC}"
    
    if docker buildx version &>/dev/null; then
        echo -e "${GREEN}✅ Docker BuildKit is available${NC}"
        
        # Create builder instance if it doesn't exist
        if ! docker buildx ls | grep -q vllm-builder; then
            echo -e "${YELLOW}Creating BuildKit builder instance...${NC}"
            docker buildx create --name vllm-builder \
                --driver docker-container \
                --config docker/buildkitd.toml \
                --use
            echo -e "${GREEN}✅ Builder instance created${NC}"
        else
            docker buildx use vllm-builder
            echo -e "${GREEN}✅ Using existing builder instance${NC}"
        fi
    else
        echo -e "${RED}❌ Docker BuildKit not available. Please update Docker.${NC}"
        exit 1
    fi
}

# Function to build with caching
build_with_cache() {
    local dockerfile=$1
    local image_name=$2
    local build_args=$3
    
    echo -e "${YELLOW}🔨 Building ${image_name}...${NC}"
    
    # Build command with all optimizations
    docker buildx build \
        --file "$dockerfile" \
        --tag "$image_name" \
        --cache-from "type=registry,ref=${CACHE_REGISTRY}/${image_name}:cache" \
        --cache-from "type=local,src=/tmp/buildkit-cache" \
        --cache-to "type=local,dest=/tmp/buildkit-cache,mode=max" \
        --build-arg BUILDKIT_INLINE_CACHE=1 \
        $build_args \
        --progress=plain \
        --load \
        .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Successfully built ${image_name}${NC}"
    else
        echo -e "${RED}❌ Failed to build ${image_name}${NC}"
        return 1
    fi
}

# Function to build base images
build_base_images() {
    echo -e "${BLUE}📦 Building Base Images...${NC}"
    
    # Build Python base
    build_with_cache \
        "docker/Dockerfile.base-python" \
        "vllm-swarm/base-python:latest" \
        "--build-arg PYTHON_VERSION=3.11"
    
    # Build ML base (depends on Python base)
    build_with_cache \
        "docker/Dockerfile.base-ml" \
        "vllm-swarm/base-ml:latest" \
        "--build-arg PYTHON_VERSION=3.11"
}

# Function to build service images in parallel
build_services() {
    echo -e "${BLUE}🎯 Building Service Images...${NC}"
    
    if [ "$BUILD_PARALLEL" = "true" ]; then
        echo -e "${YELLOW}⚡ Building services in parallel...${NC}"
        
        # Build services in parallel using background jobs
        build_with_cache "docker/Dockerfile.auth-optimized" "vllm-swarm/auth:optimized" "" &
        local auth_pid=$!
        
        build_with_cache "docker/Dockerfile.memory-optimized" "vllm-swarm/memory:optimized" "" &
        local memory_pid=$!
        
        build_with_cache "docker/Dockerfile.orchestrator-optimized" "vllm-swarm/orchestrator:optimized" "" &
        local orch_pid=$!
        
        # Wait for all builds to complete
        wait $auth_pid && echo -e "${GREEN}✅ Auth service built${NC}" || echo -e "${RED}❌ Auth service failed${NC}"
        wait $memory_pid && echo -e "${GREEN}✅ Memory service built${NC}" || echo -e "${RED}❌ Memory service failed${NC}"
        wait $orch_pid && echo -e "${GREEN}✅ Orchestrator built${NC}" || echo -e "${RED}❌ Orchestrator failed${NC}"
    else
        # Sequential build
        build_with_cache "docker/Dockerfile.auth-optimized" "vllm-swarm/auth:optimized" ""
        build_with_cache "docker/Dockerfile.memory-optimized" "vllm-swarm/memory:optimized" ""
        build_with_cache "docker/Dockerfile.orchestrator-optimized" "vllm-swarm/orchestrator:optimized" ""
    fi
}

# Function to prune old cache
prune_cache() {
    echo -e "${YELLOW}🧹 Pruning old build cache...${NC}"
    
    # Keep only recent cache (last 7 days)
    docker buildx prune --force --filter "until=168h"
    
    # Clean up local cache if it's too large
    if [ -d "/tmp/buildkit-cache" ]; then
        local cache_size=$(du -sh /tmp/buildkit-cache | cut -f1)
        echo -e "${BLUE}Current cache size: ${cache_size}${NC}"
        
        # If cache is larger than 5GB, clean it
        if [ $(du -s /tmp/buildkit-cache | cut -f1) -gt 5242880 ]; then
            echo -e "${YELLOW}Cache too large, cleaning...${NC}"
            rm -rf /tmp/buildkit-cache/*
        fi
    fi
}

# Function to export cache to registry
export_cache() {
    echo -e "${YELLOW}📤 Exporting cache to registry...${NC}"
    
    for image in base-python base-ml auth memory orchestrator; do
        docker tag "vllm-swarm/${image}:optimized" "${CACHE_REGISTRY}/${image}:cache" 2>/dev/null || true
        docker push "${CACHE_REGISTRY}/${image}:cache" 2>/dev/null || \
            echo -e "${YELLOW}⚠️  Could not push cache for ${image} (registry may not be configured)${NC}"
    done
}

# Function to show build statistics
show_stats() {
    echo -e "${BLUE}📊 Build Statistics${NC}"
    echo -e "${BLUE}==================${NC}"
    
    # Show image sizes
    echo -e "${YELLOW}Image Sizes:${NC}"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep vllm-swarm || true
    
    # Show cache usage
    echo -e "\n${YELLOW}Cache Usage:${NC}"
    docker buildx du --verbose 2>/dev/null || docker system df
    
    # Show layer sharing
    echo -e "\n${YELLOW}Shared Layers:${NC}"
    for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep vllm-swarm); do
        layers=$(docker history "$image" --format "{{.ID}}" --no-trunc | wc -l)
        echo "  $image: $layers layers"
    done
}

# Main execution flow
main() {
    local start_time=$(date +%s)
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-cache)
                echo -e "${YELLOW}⚠️  Building without cache${NC}"
                USE_INLINE_CACHE=false
                shift
                ;;
            --sequential)
                BUILD_PARALLEL=false
                shift
                ;;
            --prune)
                prune_cache
                exit 0
                ;;
            --stats)
                show_stats
                exit 0
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-cache     Build without using cache"
                echo "  --sequential   Build services sequentially"
                echo "  --prune        Prune old build cache"
                echo "  --stats        Show build statistics"
                echo "  --help         Show this help message"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
        esac
    done
    
    # Check BuildKit availability
    check_buildkit
    
    # Create cache directory
    mkdir -p /tmp/buildkit-cache
    
    # Build base images first
    build_base_images
    
    # Build service images
    build_services
    
    # Export cache if configured
    if [ "$USE_INLINE_CACHE" = "true" ]; then
        export_cache
    fi
    
    # Show statistics
    show_stats
    
    # Calculate build time
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    echo -e "\n${GREEN}✅ Build completed in ${minutes}m ${seconds}s${NC}"
    echo -e "${BLUE}================================================${NC}"
    
    # Provide next steps
    echo -e "\n${YELLOW}📋 Next Steps:${NC}"
    echo -e "  1. Start services: ${GREEN}docker-compose -f docker-compose.optimized.yml up -d${NC}"
    echo -e "  2. Check health: ${GREEN}docker-compose -f docker-compose.optimized.yml ps${NC}"
    echo -e "  3. View logs: ${GREEN}docker-compose -f docker-compose.optimized.yml logs -f${NC}"
    echo -e "  4. Clean cache: ${GREEN}$0 --prune${NC}"
}

# Run main function
main "$@"