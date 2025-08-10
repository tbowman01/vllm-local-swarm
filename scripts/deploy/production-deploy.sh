#!/bin/bash

# 🏭 Production Deployment Script for vLLM Local Swarm
# Enterprise-grade deployment with security, monitoring, and high availability
# 
# Usage: ./scripts/deploy/production-deploy.sh [command] [options]
# Commands: deploy, update, rollback, status, logs, backup, restore

set -euo pipefail

# 🎨 Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 📁 Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILES=(
    "$PROJECT_ROOT/docker-compose.yml"
    "$PROJECT_ROOT/docker-compose.production.yml"
)
ENV_FILE="$PROJECT_ROOT/.env.production"
BACKUP_DIR="$PROJECT_ROOT/backups/production"
LOG_DIR="$PROJECT_ROOT/logs/production"

# 🔧 Default configuration
DEPLOYMENT_NAME="vllm-prod"
NETWORK_NAME="vllm-production"
HEALTH_CHECK_TIMEOUT=300
ROLLBACK_TIMEOUT=120

# 📝 Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC}  [$timestamp] $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC}  [$timestamp] $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} [$timestamp] $message" ;;
        "DEBUG") echo -e "${CYAN}[DEBUG]${NC} [$timestamp] $message" ;;
        *)       echo -e "${BLUE}[LOG]${NC}   [$timestamp] $message" ;;
    esac
    
    # Also log to file
    mkdir -p "$LOG_DIR"
    echo "[$level] [$timestamp] $message" >> "$LOG_DIR/deployment.log"
}

# 🔍 Pre-flight checks
preflight_checks() {
    log "INFO" "🔍 Running pre-flight checks..."
    
    # Check if running as root (should not be)
    if [[ $EUID -eq 0 ]]; then
        log "ERROR" "❌ Do not run this script as root for security reasons"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "jq")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log "ERROR" "❌ Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log "ERROR" "❌ Docker daemon not running or accessible"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        log "ERROR" "❌ Production environment file not found: $ENV_FILE"
        log "INFO" "💡 Copy .env.production.example to .env.production and configure"
        exit 1
    fi
    
    # Validate critical environment variables
    source "$ENV_FILE"
    local critical_vars=(
        "JWT_SECRET_KEY_PROD" 
        "POSTGRES_PASSWORD_PROD" 
        "REDIS_PASSWORD_PROD"
    )
    
    for var in "${critical_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log "ERROR" "❌ Critical environment variable $var is not set"
            exit 1
        fi
        
        # Check minimum length for security
        if [[ ${#!var} -lt 32 ]]; then
            log "ERROR" "❌ $var must be at least 32 characters for security"
            exit 1
        fi
    done
    
    # Check available disk space (minimum 10GB)
    local available_space=$(df -BG "$PROJECT_ROOT" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [[ $available_space -lt 10 ]]; then
        log "WARN" "⚠️  Low disk space: ${available_space}GB available (minimum 10GB recommended)"
    fi
    
    # Check available memory (minimum 4GB)
    local available_memory=$(free -g | awk 'NR==2{print $7}')
    if [[ $available_memory -lt 4 ]]; then
        log "WARN" "⚠️  Low memory: ${available_memory}GB available (minimum 4GB recommended)"
    fi
    
    log "INFO" "✅ Pre-flight checks completed successfully"
}

# 🔐 Security hardening
security_hardening() {
    log "INFO" "🔐 Applying security hardening..."
    
    # Create secure directories with proper permissions
    mkdir -p "$BACKUP_DIR" "$LOG_DIR"
    chmod 750 "$BACKUP_DIR" "$LOG_DIR"
    
    # Set secure permissions on environment file
    chmod 600 "$ENV_FILE"
    
    # Create Docker secrets (if supported)
    if docker swarm ca &> /dev/null; then
        log "INFO" "🐳 Docker Swarm detected, using secrets"
        # Implementation for Docker secrets would go here
    else
        log "INFO" "🐳 Using environment variables for secrets"
    fi
    
    # Configure firewall rules (if ufw is available)
    if command -v ufw &> /dev/null; then
        log "INFO" "🔥 Configuring firewall rules"
        sudo ufw --force reset
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        sudo ufw allow ssh
        sudo ufw allow 80/tcp   # HTTP
        sudo ufw allow 443/tcp  # HTTPS
        sudo ufw --force enable
    fi
    
    log "INFO" "✅ Security hardening completed"
}

# 🚀 Deploy services
deploy_services() {
    log "INFO" "🚀 Deploying vLLM Local Swarm to production..."
    
    # Pull latest images
    log "INFO" "📥 Pulling latest container images..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" pull
    
    # Start infrastructure services first
    log "INFO" "🏗️  Starting infrastructure services..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        up -d postgres-prod redis-prod qdrant-prod
    
    # Wait for infrastructure to be ready
    log "INFO" "⏱️  Waiting for infrastructure services..."
    sleep 30
    
    # Start application services
    log "INFO" "🎯 Starting application services..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        up -d auth-service memory-api orchestrator
    
    # Start monitoring services
    log "INFO" "📊 Starting monitoring services..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        up -d prometheus grafana
    
    # Start reverse proxy
    log "INFO" "🔄 Starting reverse proxy..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        up -d nginx-prod
    
    # Wait for all services to be healthy
    wait_for_health
    
    log "INFO" "✅ Deployment completed successfully!"
}

# 🏥 Health checks
wait_for_health() {
    log "INFO" "🏥 Waiting for all services to be healthy..."
    
    local services=(
        "http://localhost:8005/health:Auth Service"
        "http://localhost:8003/health:Memory API" 
        "http://localhost:8004/health:Orchestrator"
        "http://localhost:9090/-/healthy:Prometheus"
    )
    
    local timeout=$HEALTH_CHECK_TIMEOUT
    local elapsed=0
    local all_healthy=false
    
    while [[ $elapsed -lt $timeout ]] && [[ $all_healthy == false ]]; do
        all_healthy=true
        
        for service_info in "${services[@]}"; do
            local url="${service_info%:*}"
            local name="${service_info#*:}"
            
            if ! curl -f -s --max-time 5 "$url" &> /dev/null; then
                log "DEBUG" "⏳ $name not ready yet..."
                all_healthy=false
            else
                log "DEBUG" "✅ $name is healthy"
            fi
        done
        
        if [[ $all_healthy == false ]]; then
            sleep 10
            elapsed=$((elapsed + 10))
        fi
    done
    
    if [[ $all_healthy == true ]]; then
        log "INFO" "✅ All services are healthy!"
    else
        log "ERROR" "❌ Some services failed to become healthy within ${timeout}s"
        show_service_status
        exit 1
    fi
}

# 📊 Show service status
show_service_status() {
    log "INFO" "📊 Current service status:"
    
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" ps
    
    log "INFO" "🏥 Health check results:"
    local services=(
        "http://localhost:8005/health:Auth Service"
        "http://localhost:8003/health:Memory API"
        "http://localhost:8004/health:Orchestrator"  
        "http://localhost:9090/-/healthy:Prometheus"
    )
    
    for service_info in "${services[@]}"; do
        local url="${service_info%:*}"
        local name="${service_info#*:}"
        
        if curl -f -s --max-time 5 "$url" &> /dev/null; then
            log "INFO" "✅ $name: Healthy"
        else
            log "ERROR" "❌ $name: Unhealthy"
        fi
    done
}

# 🔄 Update deployment
update_deployment() {
    log "INFO" "🔄 Updating deployment..."
    
    # Create backup before update
    create_backup
    
    # Pull latest images
    log "INFO" "📥 Pulling latest images..."
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" pull
    
    # Rolling update (recreate containers one by one)
    local services=("auth-service" "memory-api" "orchestrator")
    
    for service in "${services[@]}"; do
        log "INFO" "🔄 Updating $service..."
        docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
            up -d --no-deps "$service"
        
        # Wait for service to be healthy
        sleep 15
        
        # Basic health check
        case "$service" in
            "auth-service")
                if ! curl -f -s http://localhost:8005/health &> /dev/null; then
                    log "ERROR" "❌ $service failed health check after update"
                    rollback_deployment
                    exit 1
                fi
                ;;
            "memory-api")
                if ! curl -f -s http://localhost:8003/health &> /dev/null; then
                    log "ERROR" "❌ $service failed health check after update"
                    rollback_deployment  
                    exit 1
                fi
                ;;
            "orchestrator")
                if ! curl -f -s http://localhost:8004/health &> /dev/null; then
                    log "ERROR" "❌ $service failed health check after update"
                    rollback_deployment
                    exit 1
                fi
                ;;
        esac
        
        log "INFO" "✅ $service updated successfully"
    done
    
    log "INFO" "✅ Update completed successfully!"
}

# ⏪ Rollback deployment
rollback_deployment() {
    log "WARN" "⏪ Rolling back deployment..."
    
    # Stop current containers
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        stop auth-service memory-api orchestrator
    
    # Start previous versions (implementation depends on backup strategy)
    log "WARN" "🔄 This is a simplified rollback - implement full rollback strategy for production"
    
    # Restart services
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        up -d auth-service memory-api orchestrator
    
    log "WARN" "⏪ Rollback completed - verify system status"
}

# 💾 Create backup
create_backup() {
    log "INFO" "💾 Creating backup..."
    
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/backup_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup databases
    log "INFO" "🗄️  Backing up PostgreSQL..."
    docker exec vllm-postgres-prod pg_dumpall -U "$POSTGRES_USER_PROD" > "$backup_path/postgres_backup.sql"
    
    # Backup Redis
    log "INFO" "📊 Backing up Redis..."
    docker exec vllm-redis-prod redis-cli --rdb - > "$backup_path/redis_backup.rdb"
    
    # Backup Qdrant
    log "INFO" "🔍 Backing up Qdrant..."
    docker exec vllm-qdrant-prod tar czf - /qdrant/storage > "$backup_path/qdrant_backup.tar.gz"
    
    # Backup configuration
    log "INFO" "⚙️  Backing up configuration..."
    cp "$ENV_FILE" "$backup_path/"
    
    # Create backup manifest
    cat > "$backup_path/manifest.json" << EOF
{
    "timestamp": "$backup_timestamp",
    "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "services": [
        "postgres", "redis", "qdrant"
    ],
    "files": [
        "postgres_backup.sql",
        "redis_backup.rdb", 
        "qdrant_backup.tar.gz",
        ".env.production"
    ]
}
EOF
    
    # Compress backup
    tar czf "$BACKUP_DIR/backup_$backup_timestamp.tar.gz" -C "$BACKUP_DIR" "backup_$backup_timestamp"
    rm -rf "$backup_path"
    
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/backup_*.tar.gz | tail -n +11 | xargs -r rm
    
    log "INFO" "✅ Backup created: backup_$backup_timestamp.tar.gz"
}

# 🔧 Show logs
show_logs() {
    local service="${1:-}"
    local lines="${2:-100}"
    
    if [[ -n "$service" ]]; then
        log "INFO" "📋 Showing last $lines lines of logs for $service:"
        docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
            logs --tail="$lines" "$service"
    else
        log "INFO" "📋 Showing last $lines lines of logs for all services:"
        docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
            logs --tail="$lines"
    fi
}

# 🛑 Stop services
stop_services() {
    log "INFO" "🛑 Stopping production services..."
    
    docker-compose --env-file "$ENV_FILE" -f "${COMPOSE_FILES[0]}" -f "${COMPOSE_FILES[1]}" \
        down --remove-orphans
    
    log "INFO" "✅ All services stopped"
}

# 📋 Show usage
show_usage() {
    echo -e "${BLUE}🏭 vLLM Local Swarm Production Deployment${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  deploy           Deploy services to production"
    echo "  update           Update running deployment"
    echo "  rollback         Rollback to previous version"
    echo "  status           Show service status and health"
    echo "  logs [service]   Show logs (all services or specific service)"
    echo "  backup           Create backup of all data"
    echo "  stop             Stop all services"
    echo "  help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Deploy to production"
    echo "  $0 status                    # Check service status"
    echo "  $0 logs auth-service         # Show auth service logs"
    echo "  $0 backup                    # Create backup"
    echo ""
    echo "Environment:"
    echo "  Configuration: $ENV_FILE"
    echo "  Logs:         $LOG_DIR"
    echo "  Backups:      $BACKUP_DIR"
}

# 🚀 Main execution
main() {
    local command="${1:-help}"
    
    case "$command" in
        "deploy")
            preflight_checks
            security_hardening
            deploy_services
            ;;
        "update")
            preflight_checks
            update_deployment
            ;;
        "rollback")
            preflight_checks
            rollback_deployment
            ;;
        "status")
            show_service_status
            ;;
        "logs")
            show_logs "${2:-}" "${3:-100}"
            ;;
        "backup")
            preflight_checks
            create_backup
            ;;
        "stop")
            stop_services
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log "ERROR" "❌ Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function with all arguments
main "$@"