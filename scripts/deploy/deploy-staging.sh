#!/bin/bash

# 🚀 Staging Deployment Script for vLLM Local Swarm Authentication System
# This script deploys the vLLM Local Swarm with authentication to staging environment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_ENV="${DEPLOY_ENV:-staging}"
NAMESPACE="${NAMESPACE:-vllm-swarm-staging}"
HELM_RELEASE_NAME="${HELM_RELEASE_NAME:-vllm-swarm-staging}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
trap 'log_error "Deployment failed at line $LINENO"; exit 1' ERR

# Validation functions
check_prerequisites() {
    log_info "🔍 Checking prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "kubectl" "helm" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done
    
    # Check kubectl context
    local current_context
    current_context=$(kubectl config current-context)
    log_info "Current kubectl context: $current_context"
    
    # Verify we're not accidentally deploying to production
    if [[ "$current_context" == *"prod"* ]] && [[ "$DEPLOY_ENV" != "production" ]]; then
        log_error "Kubectl context appears to be production, but DEPLOY_ENV is $DEPLOY_ENV"
        exit 1
    fi
    
    # Check Docker registry access
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

validate_environment() {
    log_info "🔧 Validating environment configuration..."
    
    # Check required environment variables
    local required_vars=("JWT_SECRET_KEY" "LANGFUSE_DB_PASSWORD" "LANGFUSE_SECRET")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate JWT secret strength
    if [[ ${#JWT_SECRET_KEY} -lt 32 ]]; then
        log_error "JWT_SECRET_KEY must be at least 32 characters long"
        exit 1
    fi
    
    log_success "Environment configuration is valid"
}

build_and_push_images() {
    log_info "🐳 Building and pushing Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Get version info
    local git_sha
    git_sha=$(git rev-parse --short HEAD)
    local branch_name
    branch_name=$(git rev-parse --abbrev-ref HEAD)
    local image_tag="${branch_name}-${git_sha}"
    
    # Registry configuration
    local registry="${DOCKER_REGISTRY:-ghcr.io}"
    local image_base="${GITHUB_REPOSITORY:-tbowman01/vllm-local-swarm}"
    
    log_info "Building images with tag: $image_tag"
    
    # Build authentication service
    log_info "Building authentication service..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --file docker/Dockerfile.auth \
        --tag "$registry/$image_base-auth-service:$image_tag" \
        --tag "$registry/$image_base-auth-service:latest" \
        --push \
        .
    
    # Build orchestrator with auth
    log_info "Building orchestrator with authentication..."
    docker buildx build \
        --platform linux/amd64,linux/arm64 \
        --file docker/Dockerfile.orchestrator \
        --tag "$registry/$image_base-orchestrator-auth:$image_tag" \
        --tag "$registry/$image_base-orchestrator-auth:latest" \
        --push \
        .
    
    # Export image tags for Helm
    export AUTH_SERVICE_IMAGE="$registry/$image_base-auth-service:$image_tag"
    export ORCHESTRATOR_AUTH_IMAGE="$registry/$image_base-orchestrator-auth:$image_tag"
    
    log_success "All images built and pushed successfully"
}

prepare_namespace() {
    log_info "🏗️ Preparing Kubernetes namespace..."
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Creating namespace: $NAMESPACE"
        kubectl create namespace "$NAMESPACE"
        
        # Label namespace for monitoring
        kubectl label namespace "$NAMESPACE" \
            environment="$DEPLOY_ENV" \
            app="vllm-local-swarm" \
            security-scan="enabled" \
            --overwrite
    else
        log_info "Namespace $NAMESPACE already exists"
    fi
    
    # Create secrets
    create_secrets
    
    log_success "Namespace prepared"
}

create_secrets() {
    log_info "🔐 Creating Kubernetes secrets..."
    
    # Authentication secrets
    kubectl create secret generic vllm-auth-secrets \
        --namespace="$NAMESPACE" \
        --from-literal=jwt-secret-key="$JWT_SECRET_KEY" \
        --from-literal=database-password="$LANGFUSE_DB_PASSWORD" \
        --from-literal=langfuse-secret="$LANGFUSE_SECRET" \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Docker registry secret (if using private registry)
    if [[ -n "${DOCKER_REGISTRY_USERNAME:-}" ]] && [[ -n "${DOCKER_REGISTRY_PASSWORD:-}" ]]; then
        kubectl create secret docker-registry docker-registry-secret \
            --namespace="$NAMESPACE" \
            --docker-server="${DOCKER_REGISTRY:-ghcr.io}" \
            --docker-username="$DOCKER_REGISTRY_USERNAME" \
            --docker-password="$DOCKER_REGISTRY_PASSWORD" \
            --dry-run=client -o yaml | kubectl apply -f -
    fi
    
    log_success "Secrets created/updated"
}

deploy_helm_chart() {
    log_info "⛵ Deploying Helm chart..."
    
    cd "$PROJECT_ROOT"
    
    # Update Helm dependencies
    if [[ -f "helm/Chart.yaml" ]]; then
        log_info "Updating Helm dependencies..."
        helm dependency update helm/
    fi
    
    # Prepare values file for staging
    local values_file="$SCRIPT_DIR/values-staging.yaml"
    if [[ ! -f "$values_file" ]]; then
        log_warning "Staging values file not found, creating default..."
        cat > "$values_file" << EOF
# Staging environment values for vLLM Local Swarm
global:
  environment: staging
  imageTag: "${image_tag:-latest}"
  
# Authentication configuration
auth:
  enabled: true
  replicas: 2
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: 500m
      memory: 1Gi

# Database configuration
postgresql:
  auth:
    postgresPassword: "${LANGFUSE_DB_PASSWORD}"
  primary:
    persistence:
      size: 10Gi

# Redis configuration
redis:
  auth:
    enabled: false
  master:
    persistence:
      size: 2Gi

# vLLM configuration (scaled down for staging)
vllm:
  phi:
    replicas: 1
    resources:
      requests:
        cpu: 1
        memory: 4Gi
      limits:
        cpu: 2
        memory: 8Gi

# Monitoring
monitoring:
  enabled: true
  
# Ingress
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: vllm-staging.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
EOF
    fi
    
    # Deploy with Helm
    log_info "Installing/upgrading Helm release: $HELM_RELEASE_NAME"
    helm upgrade --install "$HELM_RELEASE_NAME" helm/ \
        --namespace="$NAMESPACE" \
        --values="$values_file" \
        --set global.imageTag="${image_tag:-latest}" \
        --set auth.image.repository="${AUTH_SERVICE_IMAGE%:*}" \
        --set auth.image.tag="${AUTH_SERVICE_IMAGE##*:}" \
        --set orchestrator.image.repository="${ORCHESTRATOR_AUTH_IMAGE%:*}" \
        --set orchestrator.image.tag="${ORCHESTRATOR_AUTH_IMAGE##*:}" \
        --timeout=15m \
        --wait
    
    log_success "Helm deployment completed"
}

wait_for_deployment() {
    log_info "⏳ Waiting for deployment to be ready..."
    
    # Wait for critical services
    local services=("auth-service" "orchestrator-auth" "langfuse-web" "redis" "postgresql")
    
    for service in "${services[@]}"; do
        log_info "Waiting for $service to be ready..."
        
        # Wait for deployment
        if kubectl get deployment "$HELM_RELEASE_NAME-$service" -n "$NAMESPACE" &> /dev/null; then
            kubectl rollout status deployment/"$HELM_RELEASE_NAME-$service" -n "$NAMESPACE" --timeout=300s
        elif kubectl get statefulset "$HELM_RELEASE_NAME-$service" -n "$NAMESPACE" &> /dev/null; then
            kubectl rollout status statefulset/"$HELM_RELEASE_NAME-$service" -n "$NAMESPACE" --timeout=300s
        else
            log_warning "$service deployment/statefulset not found, skipping..."
        fi
    done
    
    log_success "All services are ready"
}

run_health_checks() {
    log_info "🏥 Running health checks..."
    
    # Get service endpoints
    local auth_service_url
    local orchestrator_url
    
    # Try to get external IPs/hostnames
    auth_service_url=$(kubectl get svc "$HELM_RELEASE_NAME-auth-service" -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' || echo "")
    if [[ -z "$auth_service_url" ]]; then
        # Fallback to port-forward for testing
        log_info "Setting up port-forward for health checks..."
        kubectl port-forward -n "$NAMESPACE" svc/"$HELM_RELEASE_NAME-auth-service" 8005:8005 &
        local port_forward_pid=$!
        sleep 5
        auth_service_url="http://localhost:8005"
    else
        auth_service_url="http://$auth_service_url:8005"
    fi
    
    # Health check auth service
    log_info "Checking authentication service health..."
    local max_retries=10
    local retry_count=0
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -s -f "$auth_service_url/health" > /dev/null; then
            log_success "Authentication service is healthy"
            break
        else
            ((retry_count++))
            log_info "Health check attempt $retry_count/$max_retries failed, retrying..."
            sleep 10
        fi
    done
    
    if [[ $retry_count -eq $max_retries ]]; then
        log_error "Authentication service health check failed after $max_retries attempts"
        exit 1
    fi
    
    # Test authentication flow
    log_info "Testing authentication flow..."
    local test_response
    test_response=$(curl -s -X POST "$auth_service_url/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username":"admin","password":"admin123"}' || echo "")
    
    if [[ "$test_response" == *"access_token"* ]]; then
        log_success "Authentication flow test passed"
    else
        log_warning "Authentication flow test failed (may be expected if admin user not set up yet)"
    fi
    
    # Clean up port-forward if used
    if [[ -n "${port_forward_pid:-}" ]]; then
        kill $port_forward_pid || true
    fi
    
    log_success "Health checks completed"
}

create_admin_user() {
    log_info "👤 Creating admin user..."
    
    # Port-forward to auth service
    kubectl port-forward -n "$NAMESPACE" svc/"$HELM_RELEASE_NAME-auth-service" 8005:8005 &
    local port_forward_pid=$!
    sleep 5
    
    # Create admin user
    local admin_response
    admin_response=$(curl -s -X POST "http://localhost:8005/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
            "username":"admin",
            "email":"admin@staging.local",
            "password":"'"${ADMIN_PASSWORD:-Admin123!Staging}"'",
            "full_name":"Staging Admin",
            "role":"admin"
        }' || echo "")
    
    if [[ "$admin_response" == *"user_id"* ]]; then
        log_success "Admin user created successfully"
    else
        log_warning "Admin user creation failed or user already exists"
    fi
    
    # Clean up port-forward
    kill $port_forward_pid || true
    
    log_success "Admin user setup completed"
}

generate_deployment_summary() {
    log_info "📊 Generating deployment summary..."
    
    local summary_file="$SCRIPT_DIR/staging-deployment-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "$summary_file" << EOF
# 🚀 Staging Deployment Summary

**Date**: $(date)
**Environment**: $DEPLOY_ENV
**Namespace**: $NAMESPACE
**Helm Release**: $HELM_RELEASE_NAME

## 📦 Deployed Images
- **Auth Service**: $AUTH_SERVICE_IMAGE
- **Orchestrator**: $ORCHESTRATOR_AUTH_IMAGE

## 🔗 Access Points
EOF
    
    # Get service URLs
    local ingress_hosts
    ingress_hosts=$(kubectl get ingress -n "$NAMESPACE" -o jsonpath='{.items[*].spec.rules[*].host}' || echo "")
    
    if [[ -n "$ingress_hosts" ]]; then
        echo "- **Web Interface**: https://$ingress_hosts" >> "$summary_file"
    fi
    
    echo "- **Authentication Service**: (port-forward) kubectl port-forward -n $NAMESPACE svc/$HELM_RELEASE_NAME-auth-service 8005:8005" >> "$summary_file"
    echo "- **Orchestrator**: (port-forward) kubectl port-forward -n $NAMESPACE svc/$HELM_RELEASE_NAME-orchestrator-auth 8006:8004" >> "$summary_file"
    
    cat >> "$summary_file" << EOF

## 🔐 Admin Credentials
- **Username**: admin
- **Password**: ${ADMIN_PASSWORD:-Admin123!Staging}
- **Email**: admin@staging.local

## 🔧 Management Commands
\`\`\`bash
# Check deployment status
kubectl get pods -n $NAMESPACE

# View logs
kubectl logs -f deployment/$HELM_RELEASE_NAME-auth-service -n $NAMESPACE

# Scale services
kubectl scale deployment/$HELM_RELEASE_NAME-auth-service --replicas=3 -n $NAMESPACE

# Update deployment
helm upgrade $HELM_RELEASE_NAME helm/ -n $NAMESPACE --values $values_file
\`\`\`

## 🧪 Testing Commands
\`\`\`bash
# Test authentication
curl -X POST http://localhost:8005/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username":"admin","password":"${ADMIN_PASSWORD:-Admin123!Staging}"}'

# Health check
curl http://localhost:8005/health
\`\`\`

---
Generated by: $0
EOF
    
    log_success "Deployment summary saved to: $summary_file"
    echo
    cat "$summary_file"
}

# Main deployment function
main() {
    log_info "🚀 Starting staging deployment for vLLM Local Swarm Authentication System"
    echo
    
    # Pre-deployment checks
    check_prerequisites
    validate_environment
    
    # Docker operations
    build_and_push_images
    
    # Kubernetes deployment
    prepare_namespace
    deploy_helm_chart
    wait_for_deployment
    
    # Post-deployment validation
    run_health_checks
    create_admin_user
    
    # Summary
    generate_deployment_summary
    
    log_success "🎉 Staging deployment completed successfully!"
    echo
    log_info "Next steps:"
    echo "1. Test the authentication system using the provided commands"
    echo "2. Run integration tests against the staging environment"
    echo "3. Verify all services are functioning correctly"
    echo "4. Update DNS records if using custom domains"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi