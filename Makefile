# vLLM Local Swarm - Deployment Makefile

.PHONY: help build up down logs clean install-deps compose-up compose-down k8s-install k8s-uninstall

# Default help target
help:
	@echo "vLLM Local Swarm - Deployment Commands"
	@echo "======================================"
	@echo ""
	@echo "Docker Compose Commands:"
	@echo "  make compose-up        - Start all services with Docker Compose"
	@echo "  make compose-down      - Stop all services"
	@echo "  make compose-logs      - View logs from all services"
	@echo "  make compose-build     - Build custom Docker images"
	@echo "  make compose-clean     - Clean up volumes and images"
	@echo ""
	@echo "Service-specific Commands:"
	@echo "  make build-ray-head    - Build only Ray head service"
	@echo "  make build-ray-worker  - Build only Ray worker service"
	@echo "  make build-ray         - Build all Ray services"
	@echo "  make build-proxy       - Build OpenAI proxy service"
	@echo "  make up-ray-head       - Start Ray head service"
	@echo "  make up-ray-worker     - Start Ray worker service"
	@echo "  make up-basic          - Start basic services (Redis, Qdrant, Langfuse)"
	@echo "  make logs-ray-head     - View Ray head logs"
	@echo "  make logs-ray-worker   - View Ray worker logs"
	@echo "  make logs-langfuse     - View Langfuse logs"
	@echo "  make logs-clickhouse   - View ClickHouse logs"
	@echo ""
	@echo "Health Check Commands:"
	@echo "  make health-check      - Check all service health"
	@echo "  make health-basic      - Check basic services health"
	@echo "  make health-ray        - Check Ray services health"
	@echo "  make health-clickhouse - Check ClickHouse health"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev-setup         - Complete development setup"
	@echo "  make dev-reset         - Reset development environment"
	@echo "  make dev-logs          - Tail logs from all dev services"
	@echo "  make restart-ray       - Restart Ray services"
	@echo "  make restart-basic     - Restart basic services"
	@echo "  make status-detailed   - Show detailed service status"
	@echo ""
	@echo "Maintenance Commands:"
	@echo "  make maintenance       - Run maintenance tasks"
	@echo "  make backup-volumes    - Backup Docker volumes"
	@echo ""
	@echo "Kubernetes Commands:"
	@echo "  make k8s-install       - Install with Helm on Kubernetes"
	@echo "  make k8s-uninstall     - Uninstall from Kubernetes"
	@echo "  make k8s-upgrade       - Upgrade Helm deployment"
	@echo "  make k8s-status        - Check deployment status"
	@echo ""
	@echo "Development Commands:"
	@echo "  make install-deps      - Install development dependencies"
	@echo "  make test             - Run tests"
	@echo "  make lint             - Run linting"
	@echo ""
	@echo "Profiles (add to compose commands):"
	@echo "  PROFILES=proxy         - Include OpenAI proxy"
	@echo "  PROFILES=webui         - Include Open WebUI"
	@echo "  PROFILES=langflow      - Include Langflow"
	@echo "  PROFILES=large-model   - Include large model service"
	@echo "  PROFILES=clickhouse    - Include ClickHouse (high memory)"
	@echo "  SERVICE=<name>         - Target specific service (build/up/down/logs)"
	@echo ""
	@echo "Examples:"
	@echo "  make compose-up PROFILES=proxy,webui"
	@echo "  make compose-up PROFILES=clickhouse"
	@echo "  make compose-build SERVICE=ray-head"
	@echo "  make compose-up SERVICE=ray-worker"
	@echo "  make compose-logs SERVICE=langfuse-web"
	@echo "  make k8s-install NAMESPACE=vllm-swarm"

# Variables
COMPOSE_FILE := docker-compose.yml
PROFILES ?= 
NAMESPACE ?= default
RELEASE_NAME ?= vllm-local-swarm

# Docker Compose Commands
compose-up:
	@echo "Starting vLLM Local Swarm with Docker Compose..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env file from .env.example"; fi
	@if [ -n "$(SERVICE)" ]; then \
		echo "Starting service: $(SERVICE)"; \
		docker-compose up -d $(SERVICE); \
	elif [ -n "$(PROFILES)" ]; then \
		docker-compose --profile $(shell echo $(PROFILES) | tr ',' ' --profile ') up -d; \
	else \
		docker-compose up -d; \
	fi
	@echo "Services started! Access points:"
	@echo "  - Langfuse Dashboard: http://localhost:3000"
	@echo "  - Ray Dashboard: http://localhost:8265"
	@echo "  - vLLM API: http://localhost:8000"
	@echo "  - Qdrant UI: http://localhost:6333/dashboard"
	@if echo "$(PROFILES)" | grep -q "webui"; then \
		echo "  - Open WebUI: http://localhost:8080"; \
	fi
	@if echo "$(PROFILES)" | grep -q "langflow"; then \
		echo "  - Langflow: http://localhost:7860"; \
	fi

compose-down:
	@echo "Stopping vLLM Local Swarm..."
	@if [ -n "$(SERVICE)" ]; then \
		echo "Stopping service: $(SERVICE)"; \
		docker-compose stop $(SERVICE); \
	else \
		docker-compose down; \
	fi

compose-logs:
	@echo "Showing logs from services..."
	@if [ -n "$(SERVICE)" ]; then \
		echo "Showing logs for service: $(SERVICE)"; \
		docker-compose logs -f $(SERVICE); \
	else \
		docker-compose logs -f; \
	fi

compose-build:
	@echo "Building custom Docker images..."
	@if [ -n "$(SERVICE)" ]; then \
		echo "Building service: $(SERVICE)"; \
		docker-compose build --no-cache $(SERVICE); \
	else \
		docker-compose build --no-cache; \
	fi

compose-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

# Kubernetes Commands
k8s-install:
	@echo "Installing vLLM Local Swarm on Kubernetes..."
	@if ! helm version > /dev/null 2>&1; then \
		echo "Error: Helm is not installed. Please install Helm first."; \
		exit 1; \
	fi
	@if ! kubectl cluster-info > /dev/null 2>&1; then \
		echo "Error: kubectl is not configured or cluster is not accessible."; \
		exit 1; \
	fi
	helm dependency update ./helm
	helm install $(RELEASE_NAME) ./helm \
		--namespace $(NAMESPACE) \
		--create-namespace \
		--wait \
		--timeout 10m
	@echo "Installation complete!"
	@echo "Check status with: make k8s-status"

k8s-uninstall:
	@echo "Uninstalling vLLM Local Swarm from Kubernetes..."
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE)
	@echo "Uninstall complete!"

k8s-upgrade:
	@echo "Upgrading vLLM Local Swarm deployment..."
	helm dependency update ./helm
	helm upgrade $(RELEASE_NAME) ./helm \
		--namespace $(NAMESPACE) \
		--wait \
		--timeout 10m
	@echo "Upgrade complete!"

k8s-status:
	@echo "Checking vLLM Local Swarm deployment status..."
	@echo "Helm releases:"
	helm list --namespace $(NAMESPACE)
	@echo ""
	@echo "Pod status:"
	kubectl get pods --namespace $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME)
	@echo ""
	@echo "Service status:"
	kubectl get services --namespace $(NAMESPACE) -l app.kubernetes.io/instance=$(RELEASE_NAME)

# Development Commands
install-deps:
	@echo "Installing development dependencies..."
	@if command -v python3 > /dev/null 2>&1; then \
		pip install -r docker/ray/requirements.txt; \
	else \
		echo "Python 3 not found. Please install Python 3 first."; \
	fi
	@if command -v node > /dev/null 2>&1; then \
		echo "Node.js found. Installing additional tools..."; \
	else \
		echo "Node.js not found. Some development tools may not be available."; \
	fi

test:
	@echo "Running tests..."
	@echo "TODO: Implement test suite"

lint:
	@echo "Running linting..."
	@if command -v black > /dev/null 2>&1; then \
		black --check .; \
	else \
		echo "black not installed. Run 'pip install black' to enable linting."; \
	fi

# Utility Commands
check-gpu:
	@echo "Checking GPU availability..."
	@if command -v nvidia-smi > /dev/null 2>&1; then \
		nvidia-smi; \
	else \
		echo "nvidia-smi not found. GPU support may not be available."; \
	fi

check-deps:
	@echo "Checking dependencies..."
	@echo -n "Docker: "
	@if command -v docker > /dev/null 2>&1; then echo "✓ Installed"; else echo "✗ Not found"; fi
	@echo -n "Docker Compose: "
	@if command -v docker-compose > /dev/null 2>&1; then echo "✓ Installed"; else echo "✗ Not found"; fi
	@echo -n "Kubectl: "
	@if command -v kubectl > /dev/null 2>&1; then echo "✓ Installed"; else echo "✗ Not found"; fi
	@echo -n "Helm: "
	@if command -v helm > /dev/null 2>&1; then echo "✓ Installed"; else echo "✗ Not found"; fi
	@echo -n "Python 3: "
	@if command -v python3 > /dev/null 2>&1; then echo "✓ Installed"; else echo "✗ Not found"; fi

# Quick start commands
quick-start: check-deps compose-up
	@echo "Quick start complete!"
	@echo "Visit http://localhost:3000 for Langfuse dashboard"

dev-start: install-deps compose-up
	@echo "Development environment started!"

# Service-specific build targets
build-ray-head:
	@echo "Building Ray head service..."
	docker-compose build --no-cache ray-head

build-ray-worker:
	@echo "Building Ray worker service..."
	docker-compose build --no-cache ray-worker

build-ray: build-ray-head build-ray-worker
	@echo "Built all Ray services"

build-proxy:
	@echo "Building OpenAI proxy service..."
	docker-compose build --no-cache openai-proxy

build-all-custom: build-ray build-proxy
	@echo "Built all custom services"

# Service-specific start targets
up-ray-head:
	@echo "Starting Ray head service..."
	docker-compose up -d ray-head

up-ray-worker:
	@echo "Starting Ray worker service..."
	docker-compose up -d ray-worker

up-ray: up-ray-head up-ray-worker
	@echo "Started all Ray services"

up-basic:
	@echo "Starting basic services (Redis, Qdrant, Langfuse)..."
	docker-compose up -d redis qdrant langfuse-db langfuse-web

# Service-specific logs
logs-ray-head:
	@echo "Showing Ray head logs..."
	docker-compose logs -f ray-head

logs-ray-worker:
	@echo "Showing Ray worker logs..."
	docker-compose logs -f ray-worker

logs-langfuse:
	@echo "Showing Langfuse logs..."
	docker-compose logs -f langfuse-web

logs-clickhouse:
	@echo "Showing ClickHouse logs..."
	docker-compose logs -f clickhouse

logs-redis:
	@echo "Showing Redis logs..."
	docker-compose logs -f redis

logs-qdrant:
	@echo "Showing Qdrant logs..."
	docker-compose logs -f qdrant

# Health check system
health-check:
	@echo "Checking service health..."
	@echo "================================"
	@echo -n "Redis: "
	@if docker exec vllm-redis redis-cli ping >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Qdrant: "
	@if curl -sf http://localhost:6333/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "ClickHouse: "
	@if curl -sf http://localhost:8123/ping >/dev/null 2>&1; then echo "✅ Healthy"; else echo "🔄 Optional (use --profile clickhouse)"; fi
	@echo -n "Langfuse: "
	@if curl -sf http://localhost:3000/api/public/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Ray Dashboard: "
	@if curl -sf http://localhost:8265 >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi

health-basic:
	@echo "Checking basic services health..."
	@echo "================================"
	@echo -n "Redis: "
	@if docker exec vllm-redis redis-cli ping >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Qdrant: "
	@if curl -sf http://localhost:6333/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Langfuse DB: "
	@if docker exec vllm-langfuse-db pg_isready -U langfuse >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Langfuse Web: "
	@if curl -sf http://localhost:3000/api/public/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi

health-ray:
	@echo "Checking Ray services health..."
	@echo "=============================="
	@echo -n "Ray Head: "
	@if docker exec vllm-ray-head ray status >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Ray Dashboard: "
	@if curl -sf http://localhost:8265 >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Ray Workers: "
	@if docker exec vllm-ray-head ray status | grep -q "1 nodes"; then echo "✅ Connected"; else echo "❌ Not Connected"; fi

# Additional service management targets
restart-ray:
	@echo "Restarting Ray services..."
	make compose-down SERVICE=ray-head
	make compose-down SERVICE=ray-worker
	make up-ray-head
	make up-ray-worker

restart-basic:
	@echo "Restarting basic services..."
	make compose-down SERVICE=redis
	make compose-down SERVICE=qdrant
	make compose-down SERVICE=langfuse-db
	make compose-down SERVICE=langfuse-web
	make up-basic

restart-all:
	@echo "Restarting all services..."
	make compose-down
	make compose-up

# Development workflow targets
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env file"; fi
	make up-basic
	make build-ray
	make up-ray-head
	@echo "Development environment ready!"
	@echo "Access points:"
	@echo "  - Ray Dashboard: http://localhost:8265"
	@echo "  - Langfuse: http://localhost:3000"
	@echo "  - Qdrant: http://localhost:6333/dashboard"

dev-reset:
	@echo "Resetting development environment..."
	make compose-down
	make compose-clean
	make dev-setup

dev-logs:
	@echo "Tailing logs from all development services..."
	docker-compose logs -f redis qdrant langfuse-db langfuse-web ray-head ray-worker

# Build specific service groups
build-langfuse:
	@echo "Building Langfuse services..."
	@echo "Langfuse uses pre-built images, no build needed"

build-basic:
	@echo "Building basic services..."
	@echo "Basic services use pre-built images, no build needed"

build-vllm:
	@echo "Building vLLM services..."
	@echo "vLLM uses pre-built images, no build needed"

build-clickhouse:
	@echo "Building ClickHouse service..."
	@echo "ClickHouse uses pre-built images, no build needed"

up-clickhouse:
	@echo "Starting ClickHouse service..."
	docker-compose --profile clickhouse up -d clickhouse

restart-clickhouse:
	@echo "Restarting ClickHouse service..."
	make compose-down SERVICE=clickhouse
	make up-clickhouse

health-clickhouse:
	@echo "Checking ClickHouse health..."
	@echo "============================"
	@echo -n "ClickHouse: "
	@if curl -sf http://localhost:8123/ping >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "ClickHouse Status: "
	@if docker exec vllm-clickhouse clickhouse-client --query "SELECT 1" >/dev/null 2>&1; then echo "✅ Responding"; else echo "❌ Not Responding"; fi

# Status and monitoring
status-detailed:
	@echo "Detailed service status..."
	@echo "========================="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "Resource usage:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Maintenance commands
maintenance:
	@echo "Running maintenance tasks..."
	@echo "Pruning unused Docker resources..."
	docker system prune -f
	@echo "Checking for updates..."
	docker-compose pull

# Backup commands
backup-volumes:
	@echo "Backing up Docker volumes..."
	mkdir -p backups
	docker run --rm -v vllm-local-swarm_redis_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/redis_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	docker run --rm -v vllm-local-swarm_qdrant_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/qdrant_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	docker run --rm -v vllm-local-swarm_langfuse_db_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/langfuse_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "Backups created in ./backups/"

# Aliases for convenience
up: compose-up
down: compose-down
logs: compose-logs
build: compose-build
clean: compose-clean
install: k8s-install
uninstall: k8s-uninstall
status: k8s-status
health: health-check
restart: restart-all