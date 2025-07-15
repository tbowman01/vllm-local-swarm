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
	@echo ""
	@echo "Examples:"
	@echo "  make compose-up PROFILES=proxy,webui"
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
	@if [ -n "$(PROFILES)" ]; then \
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
	docker-compose down

compose-logs:
	@echo "Showing logs from all services..."
	docker-compose logs -f

compose-build:
	@echo "Building custom Docker images..."
	docker-compose build --no-cache

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

# Aliases for convenience
up: compose-up
down: compose-down
logs: compose-logs
build: compose-build
clean: compose-clean
install: k8s-install
uninstall: k8s-uninstall
status: k8s-status