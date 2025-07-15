#!/bin/bash

# vLLM Local Swarm Deployment Script
# Supports both Docker Compose and Kubernetes deployments

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_FILE="${PROJECT_DIR}/deployment.log"

# Default values
DEPLOYMENT_TYPE="docker"
PROFILES=""
NAMESPACE="default"
RELEASE_NAME="vllm-local-swarm"
GPU_ENABLED="false"
ENABLE_MONITORING="false"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}INFO: $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
vLLM Local Swarm Deployment Script

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Deployment type: docker or k8s (default: docker)
    -p, --profiles PROFILES Comma-separated profiles for Docker Compose
    -n, --namespace NS      Kubernetes namespace (default: default)
    -r, --release NAME      Helm release name (default: vllm-local-swarm)
    -g, --gpu              Enable GPU support
    -m, --monitoring       Enable monitoring stack
    -h, --help             Show this help message

Profiles:
    proxy                  Include OpenAI proxy service
    webui                  Include Open WebUI interface
    langflow               Include Langflow visual builder
    large-model            Include large model service

Examples:
    $0 --type docker --profiles proxy,webui --gpu
    $0 --type k8s --namespace vllm-swarm --monitoring
    $0 --type docker --profiles proxy,webui,langflow

Environment Variables:
    VLLM_GPU_COUNT         Number of GPUs to use (default: 1)
    VLLM_MODEL_SIZE        Model size: small, medium, large (default: small)
    LANGFUSE_ADMIN_EMAIL   Admin email for Langfuse
    OPENAI_API_KEY         OpenAI API key for proxy
EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                DEPLOYMENT_TYPE="$2"
                shift 2
                ;;
            -p|--profiles)
                PROFILES="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            -g|--gpu)
                GPU_ENABLED="true"
                shift
                ;;
            -m|--monitoring)
                ENABLE_MONITORING="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."
    
    case $DEPLOYMENT_TYPE in
        docker)
            command -v docker >/dev/null 2>&1 || error "Docker is not installed"
            command -v docker-compose >/dev/null 2>&1 || error "Docker Compose is not installed"
            ;;
        k8s)
            command -v kubectl >/dev/null 2>&1 || error "kubectl is not installed"
            command -v helm >/dev/null 2>&1 || error "Helm is not installed"
            kubectl cluster-info >/dev/null 2>&1 || error "Unable to connect to Kubernetes cluster"
            ;;
        *)
            error "Invalid deployment type: $DEPLOYMENT_TYPE"
            ;;
    esac
    
    if [[ "$GPU_ENABLED" == "true" ]]; then
        if command -v nvidia-smi >/dev/null 2>&1; then
            nvidia-smi >/dev/null 2>&1 || warn "GPU support requested but nvidia-smi failed"
        else
            warn "GPU support requested but nvidia-smi not found"
        fi
    fi
    
    success "Prerequisites check completed"
}

# Setup environment
setup_environment() {
    info "Setting up environment..."
    
    cd "$PROJECT_DIR"
    
    if [[ ! -f .env ]]; then
        cp .env.example .env
        info "Created .env file from .env.example"
        warn "Please review and update .env file with your configuration"
    fi
    
    # Update .env based on options
    if [[ "$GPU_ENABLED" == "true" ]]; then
        sed -i 's/NVIDIA_VISIBLE_DEVICES=all/NVIDIA_VISIBLE_DEVICES=all/' .env || true
        GPU_COUNT=${VLLM_GPU_COUNT:-1}
        sed -i "s/LARGE_MODEL_GPU_COUNT=2/LARGE_MODEL_GPU_COUNT=${GPU_COUNT}/" .env || true
    fi
    
    if [[ -n "$PROFILES" ]]; then
        sed -i "s/COMPOSE_PROFILES=/COMPOSE_PROFILES=${PROFILES}/" .env || true
    fi
    
    success "Environment setup completed"
}

# Deploy with Docker Compose
deploy_docker() {
    info "Deploying with Docker Compose..."
    
    cd "$PROJECT_DIR"
    
    # Build custom images
    info "Building custom Docker images..."
    docker-compose build
    
    # Start services
    info "Starting services..."
    if [[ -n "$PROFILES" ]]; then
        PROFILE_ARGS=""
        IFS=',' read -ra PROFILE_ARRAY <<< "$PROFILES"
        for profile in "${PROFILE_ARRAY[@]}"; do
            PROFILE_ARGS="$PROFILE_ARGS --profile $profile"
        done
        docker-compose $PROFILE_ARGS up -d
    else
        docker-compose up -d
    fi
    
    # Wait for services to be ready
    info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_docker_health
    
    success "Docker Compose deployment completed"
    show_docker_endpoints
}

# Deploy with Kubernetes
deploy_k8s() {
    info "Deploying with Kubernetes..."
    
    cd "$PROJECT_DIR/helm"
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
    
    # Update Helm dependencies
    info "Updating Helm dependencies..."
    helm dependency update
    
    # Prepare values
    VALUES_FILE="values-deploy.yaml"
    cp values.yaml "$VALUES_FILE"
    
    if [[ "$GPU_ENABLED" == "true" ]]; then
        cat >> "$VALUES_FILE" << EOF

# GPU configuration
vllm:
  phi:
    resources:
      requests:
        nvidia.com/gpu: 1
      limits:
        nvidia.com/gpu: 1
EOF
    fi
    
    if [[ "$ENABLE_MONITORING" == "true" ]]; then
        cat >> "$VALUES_FILE" << EOF

# Monitoring configuration
monitoring:
  enabled: true
  prometheus:
    enabled: true
  grafana:
    enabled: true
EOF
    fi
    
    # Install with Helm
    info "Installing with Helm..."
    helm install "$RELEASE_NAME" . \
        --namespace "$NAMESPACE" \
        --values "$VALUES_FILE" \
        --wait \
        --timeout 10m
    
    # Check deployment health
    check_k8s_health
    
    success "Kubernetes deployment completed"
    show_k8s_endpoints
}

# Check Docker service health
check_docker_health() {
    info "Checking service health..."
    
    services=("redis" "clickhouse" "qdrant" "langfuse-web" "vllm-phi" "ray-head")
    
    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            success "$service is running"
        else
            warn "$service is not running properly"
        fi
    done
}

# Check Kubernetes deployment health
check_k8s_health() {
    info "Checking deployment health..."
    
    kubectl wait --for=condition=ready pod \
        --selector=app.kubernetes.io/instance="$RELEASE_NAME" \
        --namespace="$NAMESPACE" \
        --timeout=300s
    
    success "All pods are ready"
}

# Show Docker endpoints
show_docker_endpoints() {
    cat << EOF

=================================
vLLM Local Swarm - Access Points
=================================

Core Services:
  🎯 Langfuse Dashboard: http://localhost:3000
  📊 Ray Dashboard:      http://localhost:8265
  🤖 vLLM API:          http://localhost:8000
  🔍 Qdrant UI:         http://localhost:6333/dashboard

EOF

    if echo "$PROFILES" | grep -q "webui"; then
        echo "  💬 Open WebUI:        http://localhost:8080"
    fi
    
    if echo "$PROFILES" | grep -q "langflow"; then
        echo "  🔄 Langflow:          http://localhost:7860"
    fi
    
    if echo "$PROFILES" | grep -q "proxy"; then
        echo "  🔗 OpenAI Proxy:      http://localhost:8002"
    fi
    
    cat << EOF

Management:
  📋 View logs:         make compose-logs
  🛑 Stop services:     make compose-down
  🔄 Restart:           make compose-up

EOF
}

# Show Kubernetes endpoints
show_k8s_endpoints() {
    cat << EOF

=================================
vLLM Local Swarm - K8s Deployment
=================================

Namespace: $NAMESPACE
Release:   $RELEASE_NAME

To access services, use port forwarding:

kubectl port-forward svc/$RELEASE_NAME-langfuse-web 3000:3000 -n $NAMESPACE
kubectl port-forward svc/$RELEASE_NAME-ray-head 8265:8265 -n $NAMESPACE
kubectl port-forward svc/$RELEASE_NAME-vllm-phi 8000:8000 -n $NAMESPACE

Management:
  📊 Check status:      make k8s-status NAMESPACE=$NAMESPACE
  🔄 Upgrade:           make k8s-upgrade NAMESPACE=$NAMESPACE
  🗑️  Uninstall:        make k8s-uninstall NAMESPACE=$NAMESPACE

EOF
}

# Main function
main() {
    log "Starting vLLM Local Swarm deployment"
    
    parse_args "$@"
    check_prerequisites
    setup_environment
    
    case $DEPLOYMENT_TYPE in
        docker)
            deploy_docker
            ;;
        k8s)
            deploy_k8s
            ;;
    esac
    
    success "Deployment completed successfully!"
}

# Run main function with all arguments
main "$@"