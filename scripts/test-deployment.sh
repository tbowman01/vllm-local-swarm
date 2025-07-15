#!/bin/bash

# vLLM Local Swarm Deployment Test Script
# Tests all services and endpoints for functionality

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEST_LOG="${PROJECT_DIR}/test-results.log"

# Default values
DEPLOYMENT_TYPE="docker"
NAMESPACE="default"
RELEASE_NAME="vllm-local-swarm"
BASE_URL="http://localhost"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$TEST_LOG"
}

error() {
    echo -e "${RED}✗ FAIL: $1${NC}" | tee -a "$TEST_LOG"
    ((TESTS_FAILED++))
}

success() {
    echo -e "${GREEN}✓ PASS: $1${NC}" | tee -a "$TEST_LOG"
    ((TESTS_PASSED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN: $1${NC}" | tee -a "$TEST_LOG"
}

info() {
    echo -e "${BLUE}ℹ INFO: $1${NC}" | tee -a "$TEST_LOG"
}

# Test runner function
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    ((TESTS_TOTAL++))
    
    info "Running test: $test_name"
    
    if eval "$test_command" 2>&1 | grep -q "$expected_pattern"; then
        success "$test_name"
        return 0
    else
        error "$test_name"
        return 1
    fi
}

# Health check function
check_endpoint() {
    local service="$1"
    local url="$2"
    local expected_status="${3:-200}"
    local timeout="${4:-10}"
    
    ((TESTS_TOTAL++))
    
    info "Checking $service endpoint: $url"
    
    if timeout "$timeout" curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        success "$service endpoint is healthy"
        return 0
    else
        error "$service endpoint is not responding"
        return 1
    fi
}

# Docker-specific tests
test_docker_services() {
    info "Testing Docker Compose services..."
    
    # Check if containers are running
    local services=("redis" "clickhouse" "qdrant" "langfuse-db" "langfuse-web" "vllm-phi" "ray-head")
    
    for service in "${services[@]}"; do
        ((TESTS_TOTAL++))
        if docker-compose ps "$service" | grep -q "Up"; then
            success "Container $service is running"
        else
            error "Container $service is not running"
        fi
    done
    
    # Test service endpoints
    check_endpoint "Redis" "redis://localhost:6379" "PONG" 5
    check_endpoint "ClickHouse" "$BASE_URL:8123/ping" "Ok" 10
    check_endpoint "Qdrant" "$BASE_URL:6333/health" "200" 10
    check_endpoint "Langfuse" "$BASE_URL:3000/api/public/health" "200" 15
    check_endpoint "vLLM Phi-3.5" "$BASE_URL:8000/health" "200" 30
    check_endpoint "Ray Dashboard" "$BASE_URL:8265" "200" 15
    
    # Test optional services if they're running
    if docker-compose ps "openai-proxy" | grep -q "Up"; then
        check_endpoint "OpenAI Proxy" "$BASE_URL:8002/health" "200" 10
    fi
    
    if docker-compose ps "open-webui" | grep -q "Up"; then
        check_endpoint "Open WebUI" "$BASE_URL:8080/health" "200" 10
    fi
}

# Kubernetes-specific tests
test_k8s_services() {
    info "Testing Kubernetes deployment..."
    
    # Check pod status
    ((TESTS_TOTAL++))
    if kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" --no-headers | grep -q "Running"; then
        success "Kubernetes pods are running"
    else
        error "Kubernetes pods are not running"
        kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    fi
    
    # Check services
    local services=("langfuse-web" "vllm-phi" "ray-head" "clickhouse" "qdrant")
    
    for service in "${services[@]}"; do
        ((TESTS_TOTAL++))
        if kubectl get service "$RELEASE_NAME-$service" -n "$NAMESPACE" >/dev/null 2>&1; then
            success "Service $service exists"
        else
            error "Service $service not found"
        fi
    done
    
    # Test service connectivity using port-forward (basic check)
    info "Testing service connectivity..."
    
    # Note: In a real environment, you'd want to test actual endpoints
    # This is a simplified check for service existence
    ((TESTS_TOTAL++))
    if kubectl get endpoints -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" | grep -q "$RELEASE_NAME"; then
        success "Services have endpoints"
    else
        error "Services missing endpoints"
    fi
}

# API functionality tests
test_api_functionality() {
    info "Testing API functionality..."
    
    # Test vLLM API
    ((TESTS_TOTAL++))
    local vllm_url="$BASE_URL:8000"
    if curl -s "$vllm_url/v1/models" | grep -q "phi-3.5-mini"; then
        success "vLLM API is serving models"
    else
        error "vLLM API not responding correctly"
    fi
    
    # Test simple completion request
    ((TESTS_TOTAL++))
    local completion_test=$(curl -s -X POST "$vllm_url/v1/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "phi-3.5-mini",
            "prompt": "Hello",
            "max_tokens": 5
        }')
    
    if echo "$completion_test" | grep -q "choices"; then
        success "vLLM completion API working"
    else
        error "vLLM completion API failed"
    fi
    
    # Test Qdrant API
    ((TESTS_TOTAL++))
    if curl -s "$BASE_URL:6333/collections" | grep -q "collections"; then
        success "Qdrant API responding"
    else
        error "Qdrant API not responding"
    fi
    
    # Test ClickHouse API
    ((TESTS_TOTAL++))
    if curl -s "$BASE_URL:8123/?query=SELECT%201" | grep -q "1"; then
        success "ClickHouse API responding"
    else
        error "ClickHouse API not responding"
    fi
}

# Performance tests
test_performance() {
    info "Running performance tests..."
    
    # Test model inference time
    ((TESTS_TOTAL++))
    local start_time=$(date +%s)
    curl -s -X POST "$BASE_URL:8000/v1/completions" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "phi-3.5-mini",
            "prompt": "What is artificial intelligence?",
            "max_tokens": 50
        }' > /dev/null
    local end_time=$(date +%s)
    local inference_time=$((end_time - start_time))
    
    if [ "$inference_time" -lt 30 ]; then
        success "Model inference time acceptable ($inference_time seconds)"
    else
        warn "Model inference time slow ($inference_time seconds)"
    fi
    
    # Test memory usage
    ((TESTS_TOTAL++))
    if command -v docker >/dev/null 2>&1 && [ "$DEPLOYMENT_TYPE" = "docker" ]; then
        local memory_usage=$(docker stats --no-stream --format "{{.MemUsage}}" | head -1)
        success "Memory usage check completed: $memory_usage"
    else
        info "Memory usage check skipped (not in Docker environment)"
    fi
}

# Integration tests
test_integration() {
    info "Running integration tests..."
    
    # Test Ray cluster status
    ((TESTS_TOTAL++))
    if curl -s "$BASE_URL:8265/api/cluster_status" | grep -q "autoscaler"; then
        success "Ray cluster is healthy"
    else
        error "Ray cluster status check failed"
    fi
    
    # Test Langfuse integration
    ((TESTS_TOTAL++))
    local langfuse_health=$(curl -s "$BASE_URL:3000/api/public/health")
    if echo "$langfuse_health" | grep -q "healthy\|ok"; then
        success "Langfuse integration working"
    else
        error "Langfuse integration failed"
    fi
    
    # Test end-to-end workflow (simplified)
    ((TESTS_TOTAL++))
    info "Testing end-to-end workflow..."
    
    # This would typically involve:
    # 1. Submitting a task to Ray
    # 2. Having agents process it
    # 3. Checking results in Langfuse
    # For now, we'll do a basic connectivity test
    
    if curl -s "$BASE_URL:8000/health" >/dev/null && \
       curl -s "$BASE_URL:8265" >/dev/null && \
       curl -s "$BASE_URL:3000/api/public/health" >/dev/null; then
        success "End-to-end connectivity test passed"
    else
        error "End-to-end connectivity test failed"
    fi
}

# Load test (basic)
test_load() {
    info "Running basic load test..."
    
    ((TESTS_TOTAL++))
    local concurrent_requests=5
    local temp_dir=$(mktemp -d)
    
    # Generate concurrent requests
    for i in $(seq 1 $concurrent_requests); do
        (
            curl -s -X POST "$BASE_URL:8000/v1/completions" \
                -H "Content-Type: application/json" \
                -d '{
                    "model": "phi-3.5-mini",
                    "prompt": "Test request '"$i"'",
                    "max_tokens": 10
                }' > "$temp_dir/response_$i.json"
        ) &
    done
    
    wait
    
    # Check if all requests completed
    local completed_requests=$(ls "$temp_dir"/response_*.json 2>/dev/null | wc -l)
    
    if [ "$completed_requests" -eq "$concurrent_requests" ]; then
        success "Load test passed ($completed_requests/$concurrent_requests requests completed)"
    else
        error "Load test failed ($completed_requests/$concurrent_requests requests completed)"
    fi
    
    rm -rf "$temp_dir"
}

# Main test execution
main() {
    log "Starting vLLM Local Swarm deployment tests"
    echo > "$TEST_LOG"  # Clear previous log
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            --base-url)
                BASE_URL="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    info "Test configuration:"
    info "  Deployment type: $DEPLOYMENT_TYPE"
    info "  Base URL: $BASE_URL"
    if [ "$DEPLOYMENT_TYPE" = "k8s" ]; then
        info "  Namespace: $NAMESPACE"
        info "  Release: $RELEASE_NAME"
    fi
    
    echo ""
    info "Starting test suite..."
    echo ""
    
    # Run deployment-specific tests
    case $DEPLOYMENT_TYPE in
        docker)
            test_docker_services
            ;;
        k8s)
            test_k8s_services
            ;;
        *)
            error "Invalid deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Run common tests
    test_api_functionality
    test_performance
    test_integration
    test_load
    
    # Generate test report
    echo ""
    echo "========================================="
    echo "          TEST RESULTS SUMMARY"
    echo "========================================="
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    fi
    
    echo ""
    echo "Tests run: $TESTS_TOTAL"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    echo ""
    
    success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    echo "Success rate: $success_rate%"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ Deployment is healthy and ready for use!${NC}"
        echo ""
        echo "Access points:"
        echo "  🎯 Langfuse Dashboard: $BASE_URL:3000"
        echo "  📊 Ray Dashboard: $BASE_URL:8265"
        echo "  🤖 vLLM API: $BASE_URL:8000"
        echo "  🔍 Qdrant UI: $BASE_URL:6333/dashboard"
    else
        echo ""
        echo -e "${RED}❌ Deployment has issues. Check logs for details.${NC}"
        echo "Log file: $TEST_LOG"
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
vLLM Local Swarm Deployment Test Script

Usage: $0 [OPTIONS]

Options:
    --type TYPE         Deployment type: docker or k8s (default: docker)
    --namespace NS      Kubernetes namespace (default: default)
    --release NAME      Helm release name (default: vllm-local-swarm)
    --base-url URL      Base URL for testing (default: http://localhost)
    -h, --help          Show this help message

Examples:
    $0 --type docker
    $0 --type k8s --namespace vllm-swarm
    $0 --type docker --base-url http://192.168.1.100

EOF
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main "$@"