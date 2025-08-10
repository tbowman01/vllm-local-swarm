# 🚀 vLLM Local Swarm - Comprehensive Makefile
# Supports both local builds and GHCR container deployments

# ===================================================================
# Configuration
# ===================================================================

# Project settings
PROJECT_NAME := vllm-local-swarm
GITHUB_REPO := tbowman01/vllm-local-swarm
GHCR_REGISTRY := ghcr.io/$(GITHUB_REPO)

# Service configuration
SERVICES := auth-service orchestrator memory-api
COMPOSE_FILE := docker-compose.yml
AUTH_COMPOSE_FILE := docker-compose.auth.yml
GHCR_COMPOSE_FILE := docker-compose.ghcr.yml

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# Default target
.DEFAULT_GOAL := help

# ===================================================================
# Help and Information
# ===================================================================

.PHONY: help
help: ## Show this help message
	@echo "$(BLUE)🚀 vLLM Local Swarm - Development & Deployment Makefile$(NC)"
	@echo "================================================================"
	@echo ""
	@echo "$(YELLOW)📋 Available Commands:$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)💡 Quick Start Examples:$(NC)"
	@echo "  make dev-up              # Development with local builds"
	@echo "  make ghcr-up             # Development with GHCR containers"
	@echo "  make auth-up             # With authentication enabled"
	@echo "  make test                # Run all tests"
	@echo "  make clean               # Clean everything"

# ===================================================================
# Docker Prerequisites
# ===================================================================

.PHONY: docker-check
docker-check:
	@if ! command -v docker > /dev/null 2>&1; then \
		echo "$(RED)❌ Docker is not installed$(NC)"; \
		exit 1; \
	fi
	@if ! command -v docker-compose > /dev/null 2>&1; then \
		echo "$(RED)❌ Docker Compose is not installed$(NC)"; \
		exit 1; \
	fi

# ===================================================================
# Local Development (Build from Source)
# ===================================================================

.PHONY: dev-build
dev-build: docker-check ## Build all services locally
	@echo "$(YELLOW)🔨 Building all services locally...$(NC)"
	docker-compose build
	@echo "$(GREEN)✅ Local build complete$(NC)"

.PHONY: dev-up
dev-up: dev-build ## Start development environment with local builds
	@echo "$(YELLOW)🚀 Starting development environment (local builds)...$(NC)"
	docker-compose up -d
	@$(MAKE) --no-print-directory show-endpoints

.PHONY: dev-down
dev-down: ## Stop development environment
	@echo "$(YELLOW)⏹️  Stopping development environment...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ Development environment stopped$(NC)"

# ===================================================================
# GHCR Container Deployment
# ===================================================================

.PHONY: ghcr-pull
ghcr-pull: ## Pull latest images from GitHub Container Registry
	@echo "$(YELLOW)📦 Pulling latest GHCR images...$(NC)"
	@for service in $(SERVICES); do \
		echo "  Pulling $(GHCR_REGISTRY)/$$service:latest"; \
		docker pull $(GHCR_REGISTRY)/$$service:latest || echo "  ⚠️  Could not pull $$service"; \
	done
	@echo "  Pulling $(GHCR_REGISTRY)/vllm-swarm:latest"
	@docker pull $(GHCR_REGISTRY)/vllm-swarm:latest || echo "  ⚠️  Could not pull composite image"
	@echo "$(GREEN)✅ GHCR images pulled$(NC)"

.PHONY: ghcr-up
ghcr-up: ghcr-pull ## Start environment using GHCR containers
	@echo "$(YELLOW)🚀 Starting environment with GHCR containers...$(NC)"
	docker-compose -f $(COMPOSE_FILE) -f $(GHCR_COMPOSE_FILE) up -d
	@$(MAKE) --no-print-directory show-endpoints

.PHONY: ghcr-down
ghcr-down: ## Stop GHCR container environment
	@echo "$(YELLOW)⏹️  Stopping GHCR environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) -f $(GHCR_COMPOSE_FILE) down
	@echo "$(GREEN)✅ GHCR environment stopped$(NC)"

# ===================================================================
# Authentication & Security
# ===================================================================

.PHONY: auth-up
auth-up: dev-build ## Start with authentication enabled (local builds)
	@echo "$(YELLOW)🚀 Starting authenticated environment (local builds)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d
	@$(MAKE) --no-print-directory show-auth-endpoints

.PHONY: auth-ghcr-up
auth-ghcr-up: ghcr-pull ## Start with authentication enabled (GHCR containers)
	@echo "$(YELLOW)🚀 Starting authenticated environment (GHCR containers)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) -f $(GHCR_COMPOSE_FILE) up -d
	@$(MAKE) --no-print-directory show-auth-endpoints

.PHONY: auth-down
auth-down: ## Stop authenticated environment
	@echo "$(YELLOW)⏹️  Stopping authenticated environment...$(NC)"
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) down
	@echo "$(GREEN)✅ Authenticated environment stopped$(NC)"

# ===================================================================
# Environment-Specific Deployments
# ===================================================================

.PHONY: deploy-dev
deploy-dev: ## Deploy development environment using deployment script
	@echo "$(YELLOW)🚀 Deploying development environment...$(NC)"
	./scripts/deploy/deploy-dev.sh

.PHONY: deploy-staging
deploy-staging: ## Deploy staging environment using deployment script
	@echo "$(YELLOW)🚀 Deploying staging environment...$(NC)"
	./scripts/deploy/deploy-staging.sh

.PHONY: deploy-production
deploy-production: ## Deploy production environment using deployment script
	@echo "$(RED)⚠️  PRODUCTION DEPLOYMENT$(NC)"
	./scripts/deploy/deploy-production.sh

# ===================================================================
# Testing
# ===================================================================

.PHONY: test
test: ## Run all tests
	@echo "$(YELLOW)🧪 Running all tests...$(NC)"
	@if command -v pytest > /dev/null 2>&1; then \
		pytest tests/ --cov=. --cov-report=html --cov-report=term-missing; \
	elif [ -f "scripts/dev/run-tests.sh" ]; then \
		./scripts/dev/run-tests.sh; \
	else \
		echo "$(RED)❌ No test runner found$(NC)"; \
	fi

.PHONY: test-security
test-security: ## Run security tests
	@echo "$(YELLOW)🔐 Running security tests...$(NC)"
	pytest tests/security/ tests/auth/ -v
	@if command -v bandit > /dev/null 2>&1; then \
		bandit -r auth/ orchestrator/ memory/ -f json; \
	fi

# ===================================================================
# Code Quality
# ===================================================================

.PHONY: quality
quality: ## Run all code quality checks
	@echo "$(YELLOW)🔍 Running code quality checks...$(NC)"
	@if [ -f "scripts/dev/quality-check.sh" ]; then \
		./scripts/dev/quality-check.sh; \
	else \
		$(MAKE) --no-print-directory lint; \
	fi

.PHONY: lint
lint: ## Run linting
	@echo "$(YELLOW)🔍 Running linting...$(NC)"
	@if command -v ruff > /dev/null 2>&1; then \
		ruff check .; \
	fi
	@if command -v black > /dev/null 2>&1; then \
		black . --check; \
	fi

.PHONY: format
format: ## Format code
	@echo "$(YELLOW)🎨 Formatting code...$(NC)"
	@if command -v black > /dev/null 2>&1; then \
		black .; \
	fi

# ===================================================================
# Health & Monitoring
# ===================================================================

.PHONY: health
health: ## Check service health
	@echo "$(YELLOW)🔍 Checking service health...$(NC)"
	@if [ -f "scripts/dev/health-check.sh" ]; then \
		./scripts/dev/health-check.sh; \
	else \
		$(MAKE) --no-print-directory health-manual; \
	fi

.PHONY: health-manual
health-manual: ## Manual health check
	@echo "$(YELLOW)🔍 Manual health checks...$(NC)"
	@services="redis:6379 langfuse-db:5432 qdrant:6333 auth-service:8005 orchestrator:8006 memory-api:8003"; \
	for service in $$services; do \
		name=$$(echo $$service | cut -d: -f1); \
		port=$$(echo $$service | cut -d: -f2); \
		if nc -z localhost $$port 2>/dev/null; then \
			echo "$(GREEN)✅ $$name is running on port $$port$(NC)"; \
		else \
			echo "$(RED)❌ $$name is not accessible on port $$port$(NC)"; \
		fi; \
	done

.PHONY: status
status: ## Show service status
	@echo "$(YELLOW)📊 Service Status$(NC)"
	@docker-compose ps

.PHONY: logs
logs: ## Show all service logs
	docker-compose logs -f

# ===================================================================
# Database Operations
# ===================================================================

.PHONY: db-setup
db-setup: ## Set up development database
	@echo "$(YELLOW)💾 Setting up development database...$(NC)"
	@docker exec -it vllm-langfuse-db psql -U langfuse -c "CREATE DATABASE auth;" 2>/dev/null || true
	@echo "$(GREEN)✅ Database setup complete$(NC)"

.PHONY: db-reset
db-reset: ## Reset development database
	@echo "$(YELLOW)💾 Resetting development database...$(NC)"
	@docker exec -it vllm-langfuse-db psql -U langfuse -c "DROP DATABASE IF EXISTS auth;"
	@docker exec -it vllm-langfuse-db psql -U langfuse -c "CREATE DATABASE auth;"
	@echo "$(GREEN)✅ Database reset complete$(NC)"

# ===================================================================
# Container Management
# ===================================================================

.PHONY: build
build: docker-check ## Build all containers locally
	@echo "$(YELLOW)🔨 Building all containers...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)✅ Build complete$(NC)"

.PHONY: pull
pull: ## Pull all base images
	@echo "$(YELLOW)📦 Pulling base images...$(NC)"
	docker-compose pull
	@echo "$(GREEN)✅ Images pulled$(NC)"

# ===================================================================
# Cleanup Operations
# ===================================================================

.PHONY: clean
clean: ## Clean all containers, volumes, and networks
	@echo "$(YELLOW)🧹 Cleaning all containers and volumes...$(NC)"
	docker-compose down --volumes --remove-orphans 2>/dev/null || true
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) down --volumes --remove-orphans 2>/dev/null || true
	docker-compose -f $(COMPOSE_FILE) -f $(GHCR_COMPOSE_FILE) down --volumes --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(NC)"

.PHONY: clean-system
clean-system: clean ## Clean everything including Docker system
	@echo "$(YELLOW)🧹 Cleaning Docker system...$(NC)"
	docker system prune -af --volumes
	@echo "$(GREEN)✅ System cleanup complete$(NC)"

# ===================================================================
# Development Utilities
# ===================================================================

.PHONY: generate-secrets
generate-secrets: ## Generate secure secrets for all environments
	@echo "$(YELLOW)🔑 Generating secure secrets...$(NC)"
	@if [ -f "scripts/generate-secrets.py" ]; then \
		python scripts/generate-secrets.py; \
	else \
		echo "$(RED)❌ Secret generator not found$(NC)"; \
	fi

.PHONY: info
info: ## Show project information and status
	@echo "$(BLUE)📊 Project Information$(NC)"
	@echo "=================================="
	@echo "Project: $(PROJECT_NAME)"
	@echo "GitHub: https://github.com/$(GITHUB_REPO)"
	@echo "Registry: $(GHCR_REGISTRY)"
	@echo ""
	@echo "$(YELLOW)🐳 Available Images:$(NC)"
	@for service in $(SERVICES); do \
		echo "  • $(GHCR_REGISTRY)/$$service:latest"; \
	done
	@echo "  • $(GHCR_REGISTRY)/vllm-swarm:latest (composite)"

# ===================================================================
# Utility Functions
# ===================================================================

.PHONY: show-endpoints
show-endpoints:
	@echo ""
	@echo "$(GREEN)🎉 Services are running!$(NC)"
	@echo "=================================="
	@echo "$(BLUE)📊 Service Endpoints:$(NC)"
	@echo "  • Orchestrator:     http://localhost:8006"
	@echo "  • Memory API:       http://localhost:8003"
	@echo "  • Redis:            localhost:6379"
	@echo "  • PostgreSQL:       localhost:5432"
	@echo "  • Qdrant:           http://localhost:6333"
	@echo "  • Langfuse:         http://localhost:3000"

.PHONY: show-auth-endpoints
show-auth-endpoints:
	@echo ""
	@echo "$(GREEN)🎉 Authenticated services are running!$(NC)"
	@echo "============================================"
	@echo "$(BLUE)📊 Service Endpoints:$(NC)"
	@echo "  • Auth Service:     http://localhost:8005"
	@echo "  • Orchestrator:     http://localhost:8006"
	@echo "  • Memory API:       http://localhost:8003"
	@echo "  • Langfuse:         http://localhost:3000"
	@echo ""
	@echo "$(YELLOW)🔐 Authentication:$(NC)"
	@echo "  • Test health:      curl http://localhost:8005/health"

# ===================================================================
# Ensure make doesn't delete intermediate files and disable built-ins
# ===================================================================

.SECONDARY:
.SUFFIXES: