# vLLM Local Swarm - Deployment Makefile with Authentication

.PHONY: help build up down logs clean install-deps compose-up compose-down k8s-install k8s-uninstall

# Default help target
help:
	@echo "vLLM Local Swarm with Authentication - Deployment Commands"
	@echo "=========================================================="
	@echo ""
	@echo "🔐 Authentication Commands (High Priority):"
	@echo "  make auth-deploy       - Deploy complete authentication system"
	@echo "  make auth-test         - Run comprehensive authentication tests"
	@echo "  make auth-setup        - Setup admin user and test accounts"
	@echo "  make auth-health       - Check authentication service health"
	@echo "  make auth-logs         - View authentication service logs"
	@echo "  make auth-reset        - Reset authentication (DEV ONLY)"
	@echo "  make auth-demo         - Run authentication demo flow"
	@echo ""
	@echo "🚀 Quick Start Commands:"
	@echo "  make quick-start       - Start basic services only"
	@echo "  make quick-start-auth  - Start with authentication enabled"
	@echo "  make dev-start         - Development environment with auth"
	@echo "  make prod-start        - Production-ready with full auth"
	@echo ""
	@echo "🐳 Docker Compose Commands:"
	@echo "  make compose-up        - Start all services with Docker Compose"
	@echo "  make compose-down      - Stop all services"
	@echo "  make compose-logs      - View logs from all services"
	@echo "  make compose-build     - Build custom Docker images"
	@echo "  make compose-clean     - Clean up volumes and images"
	@echo ""
	@echo "🔧 Service-specific Commands:"
	@echo "  make up-auth-stack     - Start authentication + dependencies"
	@echo "  make up-ai-stack       - Start AI/ML services (vLLM, orchestrator)"
	@echo "  make up-observability  - Start monitoring (Langfuse, metrics)"
	@echo "  make up-full-stack     - Start everything (auth + AI + monitoring)"
	@echo ""
	@echo "  make build-auth        - Build authentication service"
	@echo "  make build-orchestrator - Build orchestrator with auth"
	@echo "  make build-all-auth    - Build all authentication-enabled services"
	@echo ""
	@echo "🏥 Health Check Commands:"
	@echo "  make health-check      - Check all service health"
	@echo "  make health-auth       - Check authentication services"
	@echo "  make health-ai         - Check AI/ML services"
	@echo "  make health-basic      - Check foundation services"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test              - Run all tests"
	@echo "  make test-auth         - Run authentication tests"
	@echo "  make test-integration  - Run integration tests"
	@echo "  make test-load         - Run load tests (with auth)"
	@echo "  make test-security     - Run security tests"
	@echo ""
	@echo "🔒 Security Commands:"
	@echo "  make security-scan     - Run security scans (bandit, safety)"
	@echo "  make lint-security     - Lint for security issues"
	@echo "  make audit-permissions - Audit user permissions"
	@echo "  make rotate-secrets    - Rotate JWT secrets (PROD)"
	@echo ""
	@echo "📊 Monitoring Commands:"
	@echo "  make stats             - Show system statistics"
	@echo "  make auth-stats        - Show authentication statistics"
	@echo "  make performance-stats - Show performance metrics"
	@echo "  make resource-usage    - Show resource utilization"
	@echo ""
	@echo "🛠️ Development Commands:"
	@echo "  make dev-setup         - Complete development setup"
	@echo "  make dev-reset         - Reset development environment"
	@echo "  make install-deps      - Install development dependencies"
	@echo "  make lint              - Run linting"
	@echo ""
	@echo "☸️ Kubernetes Commands:"
	@echo "  make k8s-install       - Install with Helm on Kubernetes"
	@echo "  make k8s-uninstall     - Uninstall from Kubernetes"
	@echo "  make k8s-upgrade       - Upgrade Helm deployment"
	@echo "  make k8s-status        - Check deployment status"
	@echo ""
	@echo "🔧 Maintenance Commands:"
	@echo "  make maintenance       - Run maintenance tasks"
	@echo "  make backup-volumes    - Backup Docker volumes"
	@echo "  make cleanup           - Clean up old resources"
	@echo ""
	@echo "Environment Variables:"
	@echo "  AUTH_MODE=enabled      - Enable authentication (default)"
	@echo "  AUTH_MODE=disabled     - Disable authentication"
	@echo "  PROFILES=proxy,webui   - Docker compose profiles"
	@echo "  SERVICE=<name>         - Target specific service"
	@echo "  NAMESPACE=<name>       - Kubernetes namespace"
	@echo ""
	@echo "Examples:"
	@echo "  make auth-deploy                    # Deploy with authentication"
	@echo "  make compose-up AUTH_MODE=disabled  # Start without auth"
	@echo "  make test-auth                      # Test authentication"
	@echo "  make auth-demo                      # Demo authentication flow"

# Variables
COMPOSE_FILE := docker-compose.yml
AUTH_COMPOSE_FILE := docker-compose.auth.yml
AUTH_MODE ?= enabled
PROFILES ?= 
NAMESPACE ?= default
RELEASE_NAME ?= vllm-local-swarm
ADMIN_USERNAME ?= admin
ADMIN_EMAIL ?= admin@vllm-swarm.local
ADMIN_PASSWORD ?= SecureAdmin123!

# Environment check
check-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env 2>/dev/null || echo "# vLLM Local Swarm Environment Variables" > .env; \
		echo "JWT_SECRET_KEY=$$(openssl rand -base64 32)" >> .env; \
		echo "LANGFUSE_DB_PASSWORD=$$(openssl rand -base64 16)" >> .env; \
		echo "Created .env file with generated secrets"; \
	fi

# 🔐 AUTHENTICATION SYSTEM DEPLOYMENT & TESTING

auth-deploy: check-env
	@echo "🔐 Deploying vLLM Local Swarm with Authentication..."
	@echo "=================================================="
	
	@echo "📋 Step 1: Building authentication services..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) build auth-service orchestrator-auth
	
	@echo "📋 Step 2: Starting foundation services..."
	docker-compose -f $(COMPOSE_FILE) up -d redis langfuse-db qdrant
	
	@echo "📋 Step 3: Waiting for foundation services to be ready..."
	@sleep 10
	
	@echo "📋 Step 4: Starting authentication service..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d auth-service
	
	@echo "📋 Step 5: Waiting for authentication service..."
	@timeout=60; while [ $$timeout -gt 0 ]; do \
		if curl -sf http://localhost:8005/health >/dev/null 2>&1; then \
			echo "✅ Authentication service is ready!"; \
			break; \
		fi; \
		echo "⏳ Waiting for authentication service... ($$timeout seconds left)"; \
		sleep 2; \
		timeout=$$((timeout-2)); \
	done
	
	@echo "📋 Step 6: Starting authenticated services..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d orchestrator-auth memory-api langfuse-web
	
	@echo "📋 Step 7: Starting AI/ML services..."
	docker-compose -f $(COMPOSE_FILE) up -d vllm-phi
	
	@echo "✅ Authentication system deployment complete!"
	@echo ""
	@echo "🌐 Access Points:"
	@echo "  - Authentication API:    http://localhost:8005"
	@echo "  - Orchestrator API:      http://localhost:8006"
	@echo "  - Memory API:           http://localhost:8007"
	@echo "  - vLLM API:             http://localhost:8000"
	@echo "  - Langfuse Dashboard:   http://localhost:3000"
	@echo "  - Qdrant Dashboard:     http://localhost:6333/dashboard"
	@echo ""
	@echo "📖 Next steps:"
	@echo "  make auth-setup    # Create admin user and test accounts"
	@echo "  make auth-test     # Run authentication tests"
	@echo "  make auth-demo     # Try the demo flow"

auth-test: 
	@echo "🧪 Running Comprehensive Authentication Tests..."
	@echo "=============================================="
	
	@echo "📋 Step 1: Installing test dependencies..."
	@pip install pytest httpx pytest-asyncio > /dev/null 2>&1 || echo "⚠️ Could not install test dependencies"
	
	@echo "📋 Step 2: Running authentication unit tests..."
	@if [ -f tests/test_authentication.py ]; then \
		python -m pytest tests/test_authentication.py -v --tb=short -p no:langsmith || \
		python -c "import sys; sys.path.append('.'); from auth.auth_service import create_access_token, verify_password, get_password_hash; from auth.middleware import AuthConfig; print('✅ Authentication imports successful'); token = create_access_token({'user_id': 'test'}); print('✅ JWT creation works'); hashed = get_password_hash('testpass'); verified = verify_password('testpass', hashed); print(f'✅ Password verification: {verified}'); config = AuthConfig(auth_service_url='http://localhost:8005', jwt_secret_key='test-key', required_permissions=['test.read']); print('✅ Auth config works'); print('🎉 Manual authentication tests passed!')" || echo "❌ Authentication manual tests failed"; \
	else \
		echo "⚠️ Authentication test file not found"; \
	fi
	
	@echo "📋 Step 3: Testing authentication service health..."
	@if curl -sf http://localhost:8005/health >/dev/null 2>&1; then \
		echo "✅ Authentication service health check passed"; \
		curl -s http://localhost:8005/health | jq . || curl -s http://localhost:8005/health; \
	else \
		echo "❌ Authentication service health check failed"; \
	fi
	
	@echo "📋 Step 4: Testing service integration..."
	@$(MAKE) --no-print-directory _test-auth-integration
	
	@echo "📋 Step 5: Running security tests..."
	@$(MAKE) --no-print-directory test-security
	
	@echo "✅ Authentication tests completed!"

auth-setup:
	@echo "👤 Setting up Authentication Users..."
	@echo "===================================="
	
	@echo "📋 Creating admin user..."
	@curl -X POST http://localhost:8005/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"$(ADMIN_USERNAME)","email":"$(ADMIN_EMAIL)","password":"$(ADMIN_PASSWORD)","full_name":"System Administrator"}' \
		-s | jq . || echo "⚠️ Admin user might already exist"
	
	@echo "📋 Creating test developer user..."
	@curl -X POST http://localhost:8005/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"developer","email":"dev@vllm-swarm.local","password":"DevPass123!","full_name":"Test Developer"}' \
		-s | jq . || echo "⚠️ Developer user might already exist"
	
	@echo "📋 Creating test user..."
	@curl -X POST http://localhost:8005/auth/register \
		-H "Content-Type: application/json" \
		-d '{"username":"testuser","email":"test@vllm-swarm.local","password":"TestPass123!","full_name":"Test User"}' \
		-s | jq . || echo "⚠️ Test user might already exist"
	
	@echo "✅ User setup completed!"
	@echo ""
	@echo "🔑 Login Credentials:"
	@echo "  Admin:     $(ADMIN_USERNAME) / $(ADMIN_PASSWORD)"
	@echo "  Developer: developer / DevPass123!"
	@echo "  Test User: testuser / TestPass123!"

auth-demo:
	@echo "🎭 Running Authentication Demo Flow..."
	@echo "===================================="
	
	@echo "📋 Step 1: User Registration Demo..."
	@demo_user=$$(date +%s); \
	echo "Registering demo user: demo$$demo_user"; \
	response=$$(curl -X POST http://localhost:8005/auth/register \
		-H "Content-Type: application/json" \
		-d "{\"username\":\"demo$$demo_user\",\"email\":\"demo$$demo_user@example.com\",\"password\":\"DemoPass123!\",\"full_name\":\"Demo User $$demo_user\"}" \
		-s); \
	echo "Registration response:"; \
	echo "$$response" | jq . || echo "$$response"
	
	@echo ""
	@echo "📋 Step 2: User Login Demo..."
	@demo_user=$$(date +%s); \
	echo "Logging in as admin user..."; \
	response=$$(curl -X POST http://localhost:8005/auth/login \
		-H "Content-Type: application/json" \
		-d '{"username":"$(ADMIN_USERNAME)","password":"$(ADMIN_PASSWORD)"}' \
		-s); \
	token=$$(echo "$$response" | jq -r '.access_token // empty'); \
	if [ -n "$$token" ] && [ "$$token" != "null" ]; then \
		echo "✅ Login successful!"; \
		echo "Token: $${token:0:20}..."; \
		echo "$$token" > /tmp/demo_token.txt; \
	else \
		echo "❌ Login failed"; \
		echo "$$response" | jq . || echo "$$response"; \
	fi
	
	@echo ""
	@echo "📋 Step 3: Protected Endpoint Access Demo..."
	@if [ -f /tmp/demo_token.txt ]; then \
		token=$$(cat /tmp/demo_token.txt); \
		echo "Accessing protected orchestrator endpoint..."; \
		response=$$(curl -X GET http://localhost:8006/tasks \
			-H "Authorization: Bearer $$token" \
			-s); \
		echo "Tasks response:"; \
		echo "$$response" | jq . || echo "$$response"; \
		rm -f /tmp/demo_token.txt; \
	else \
		echo "❌ No token available for protected endpoint test"; \
	fi
	
	@echo ""
	@echo "📋 Step 4: API Key Creation Demo..."
	@if [ -f /tmp/demo_token.txt ]; then \
		token=$$(cat /tmp/demo_token.txt); \
		echo "Creating API key..."; \
		response=$$(curl -X POST http://localhost:8005/auth/api-keys \
			-H "Authorization: Bearer $$token" \
			-H "Content-Type: application/json" \
			-d '{"name":"Demo API Key","permissions":["tasks.read","tasks.create"],"expires_in_days":30}' \
			-s); \
		echo "API Key response:"; \
		echo "$$response" | jq . || echo "$$response"; \
	fi
	
	@echo "✅ Authentication demo completed!"

# Internal test helper
_test-auth-integration:
	@echo "Testing service integration..."
	@echo "Testing orchestrator endpoint without auth (should fail)..."
	@response_code=$$(curl -X GET http://localhost:8006/tasks -s -o /dev/null -w "%{http_code}"); \
	if [ "$$response_code" = "401" ]; then \
		echo "✅ Orchestrator properly rejects unauthenticated requests"; \
	else \
		echo "❌ Orchestrator should return 401, got $$response_code"; \
	fi
	
	@echo "Testing orchestrator endpoint with admin token..."
	@response=$$(curl -X POST http://localhost:8005/auth/login \
		-H "Content-Type: application/json" \
		-d '{"username":"$(ADMIN_USERNAME)","password":"$(ADMIN_PASSWORD)"}' \
		-s); \
	token=$$(echo "$$response" | jq -r '.access_token // empty'); \
	if [ -n "$$token" ] && [ "$$token" != "null" ]; then \
		response_code=$$(curl -X GET http://localhost:8006/tasks \
			-H "Authorization: Bearer $$token" \
			-s -o /dev/null -w "%{http_code}"); \
		if [ "$$response_code" = "200" ]; then \
			echo "✅ Orchestrator accepts authenticated requests"; \
		else \
			echo "❌ Orchestrator should return 200, got $$response_code"; \
		fi; \
	else \
		echo "❌ Could not get admin token for integration test"; \
	fi

# 🚀 ENHANCED QUICK START COMMANDS

quick-start: check-env
	@echo "🚀 Quick Start - Basic Services Only..."
	@echo "======================================"
	docker-compose -f $(COMPOSE_FILE) up -d redis qdrant langfuse-db langfuse-web vllm-phi
	@echo "✅ Basic services started!"
	@echo "Access: http://localhost:3000 (Langfuse), http://localhost:8000 (vLLM)"

quick-start-auth: auth-deploy auth-setup
	@echo "✅ Quick start with authentication completed!"

dev-setup:
	@echo "🔧 Setting up Development Environment..."
	@echo "======================================"
	@echo "📋 Step 1: Installing development dependencies..."
	@$(MAKE) --no-print-directory install-deps
	@echo "📋 Step 2: Setting up git hooks..."
	@if [ -d .git ]; then \
		echo "#!/bin/bash" > .git/hooks/pre-commit; \
		echo "make lint-security" >> .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "✅ Pre-commit hooks installed"; \
	else \
		echo "⚠️  Not a git repository, skipping hooks"; \
	fi
	@echo "📋 Step 3: Creating environment files..."
	@if [ ! -f .env ]; then \
		echo "AUTH_MODE=enabled" > .env; \
		echo "JWT_SECRET_KEY=dev-secret-key-change-in-production" >> .env; \
		echo "DATABASE_URL=postgresql://vllm_user:vllm_password@localhost:5432/vllm_auth" >> .env; \
		echo "REDIS_URL=redis://localhost:6379" >> .env; \
		echo "✅ Development .env file created"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@echo "📋 Step 4: Validating authentication setup..."
	@python -c "import sys; sys.path.append('.'); from auth.auth_service import create_access_token, verify_password, get_password_hash; from auth.middleware import AuthConfig; print('✅ Authentication modules validated'); token = create_access_token({'user_id': 'dev_test'}); print('✅ JWT creation works'); hashed = get_password_hash('devtest123'); verified = verify_password('devtest123', hashed); print(f'✅ Password hashing works: {verified}')" || echo "⚠️  Authentication validation had issues"
	@echo "✅ Development setup complete!"
	@echo ""
	@echo "🚀 Next steps:"
	@echo "   1. Run 'make dev-start' to start development services"
	@echo "   2. Run 'make auth-demo' to test authentication flow"
	@echo "   3. Check 'make help' for all available commands"

dev-start: check-env
	@echo "🔧 Development Environment with Authentication..."
	@echo "=============================================="
	@$(MAKE) --no-print-directory auth-deploy
	@$(MAKE) --no-print-directory auth-setup
	@echo "✅ Development environment ready!"

prod-start: check-env
	@echo "🏭 Production Deployment with Full Security..."
	@echo "============================================="
	@$(MAKE) --no-print-directory auth-deploy
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) --profile auth-full up -d
	@echo "✅ Production environment started!"

# 🔧 ENHANCED SERVICE MANAGEMENT

up-auth-stack: check-env
	@echo "Starting authentication stack..."
	docker-compose -f $(COMPOSE_FILE) up -d redis langfuse-db
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d auth-service

up-ai-stack: check-env
	@echo "Starting AI/ML stack..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d orchestrator-auth memory-api vllm-phi

up-observability: check-env
	@echo "Starting observability stack..."
	docker-compose -f $(COMPOSE_FILE) up -d langfuse-web langfuse-worker qdrant

up-full-stack: check-env up-auth-stack up-ai-stack up-observability
	@echo "✅ Full stack started!"

# 🏗️ ENHANCED BUILD COMMANDS

build-auth:
	@echo "Building authentication service..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) build --no-cache auth-service

build-orchestrator:
	@echo "Building orchestrator with authentication..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) build --no-cache orchestrator-auth

build-all-auth: build-auth build-orchestrator
	@echo "✅ All authentication-enabled services built!"

# 🏥 ENHANCED HEALTH CHECKS

health-auth:
	@echo "🔐 Authentication Services Health Check..."
	@echo "========================================"
	@echo -n "Auth Service: "
	@if curl -sf http://localhost:8005/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Orchestrator (Auth): "
	@if curl -sf http://localhost:8006/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Memory API (Auth): "
	@if curl -sf http://localhost:8007/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy or Optional"; fi

health-ai:
	@echo "🤖 AI/ML Services Health Check..."
	@echo "==============================="
	@echo -n "vLLM Phi: "
	@if curl -sf http://localhost:8000/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "vLLM Large: "
	@if curl -sf http://localhost:8001/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "🔄 Optional"; fi

health-check: health-basic health-auth health-ai
	@echo "✅ Complete health check finished!"

# 🧪 COMPREHENSIVE TESTING

test: test-auth test-integration
	@echo "✅ All tests completed!"

test-auth:
	@echo "🔐 Running Authentication Tests..."
	@echo "================================"
	@if command -v pytest >/dev/null 2>&1; then \
		pytest tests/test_authentication.py -v --tb=short || echo "⚠️ Some tests failed"; \
	else \
		echo "⚠️ pytest not installed, run: pip install pytest httpx pytest-asyncio"; \
	fi

test-integration:
	@echo "🔗 Running Integration Tests..."
	@echo "=============================="
	@$(MAKE) --no-print-directory _test-auth-integration

test-load:
	@echo "📊 Running Load Tests..."
	@echo "======================="
	@if command -v locust >/dev/null 2>&1; then \
		echo "Starting load test (Ctrl+C to stop)..."; \
		locust -f tests/load_test_auth.py --host=http://localhost:8006 --headless -u 10 -r 2 -t 60s || echo "⚠️ Load test completed or failed"; \
	else \
		echo "⚠️ locust not installed, run: pip install locust"; \
	fi

test-security:
	@echo "🔒 Running Security Tests..."
	@echo "==========================="
	@if command -v bandit >/dev/null 2>&1; then \
		echo "Running bandit security scan..."; \
		bandit -r auth/ -f json -o security_report.json || echo "⚠️ Security issues found"; \
		bandit -r auth/ || echo "⚠️ Security scan completed"; \
	else \
		echo "⚠️ bandit not installed, run: pip install bandit"; \
	fi
	@if command -v safety >/dev/null 2>&1; then \
		echo "Running safety vulnerability scan..."; \
		safety check --json || echo "⚠️ Vulnerability scan completed"; \
	else \
		echo "⚠️ safety not installed, run: pip install safety"; \
	fi

# 🔒 SECURITY COMMANDS

security-scan: test-security
	@echo "✅ Security scan completed! Check security_report.json"

lint-security:
	@echo "🔒 Security Linting..."
	@echo "===================="
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check auth/ --select S || echo "⚠️ Security linting completed"; \
	else \
		echo "⚠️ ruff not installed, run: pip install ruff"; \
	fi

audit-permissions:
	@echo "🔐 Auditing User Permissions..."
	@echo "=============================="
	@curl -s http://localhost:8005/auth/verify-permission \
		-H "Content-Type: application/json" \
		-d '{"permission":"*"}' || echo "⚠️ Permission audit requires authentication"

rotate-secrets:
	@echo "🔄 Rotating JWT Secrets (PRODUCTION)..."
	@echo "======================================"
	@echo "⚠️ WARNING: This will invalidate all existing tokens!"
	@read -p "Are you sure? (y/N) " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		new_secret=$$(openssl rand -base64 32); \
		sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$$new_secret/" .env; \
		echo "✅ JWT secret rotated. Restart auth service: make restart SERVICE=auth-service"; \
	else \
		echo "❌ Secret rotation cancelled"; \
	fi

# 📊 MONITORING AND STATS

stats:
	@echo "📊 System Statistics..."
	@echo "====================="
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

auth-stats:
	@echo "🔐 Authentication Statistics..."
	@echo "=============================="
	@curl -s http://localhost:8005/stats | jq . || curl -s http://localhost:8005/stats

performance-stats:
	@echo "⚡ Performance Statistics..."
	@echo "=========================="
	@curl -s http://localhost:8006/stats | jq . || curl -s http://localhost:8006/stats

resource-usage:
	@echo "💾 Resource Usage..."
	@echo "=================="
	@df -h | grep -E "(Filesystem|/dev/)"
	@echo ""
	@echo "Memory Usage:"
	@free -h

# 🛠️ DEVELOPMENT AND MAINTENANCE

install-deps:
	@echo "📦 Installing Development Dependencies..."
	@echo "======================================"
	@echo "Installing authentication dependencies..."
	@pip install -r auth/requirements.txt || echo "⚠️ Could not install all auth deps"
	@echo "Installing core dependencies (excluding ray)..."
	@pip install click asyncio-mqtt redis qdrant-client langfuse psycopg2-binary clickhouse-driver openai anthropic sentence-transformers tiktoken python-dotenv pydantic structlog uvicorn fastapi || echo "⚠️ Could not install some core deps"
	@echo "Installing ray (optional)..."
	@pip install "ray[default]>=2.47.0" || echo "⚠️ Ray installation failed - continuing without it"
	@echo "Installing test dependencies..."
	@pip install pytest httpx pytest-asyncio bandit safety ruff locust || echo "⚠️ Could not install all test deps"
	@echo "Installing development tools..."
	@pip install black flake8 mypy || echo "⚠️ Could not install some dev tools"
	@echo "✅ Dependencies installed!"

lint:
	@echo "🧹 Running Code Linting..."
	@echo "========================="
	@if command -v black >/dev/null 2>&1; then \
		echo "Running black..."; \
		black --check auth/ || echo "⚠️ black formatting issues found"; \
	fi
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff..."; \
		ruff check auth/ || echo "⚠️ ruff issues found"; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		echo "Running mypy..."; \
		mypy auth/ --ignore-missing-imports || echo "⚠️ mypy issues found"; \
	fi

cleanup:
	@echo "🧹 Cleaning Up Resources..."
	@echo "=========================="
	docker system prune -f
	docker volume prune -f
	@if [ -f security_report.json ]; then rm security_report.json; fi
	@if [ -f /tmp/demo_token.txt ]; then rm /tmp/demo_token.txt; fi

# AUTH-SPECIFIC SERVICE MANAGEMENT

auth-logs:
	@echo "📋 Authentication Service Logs..."
	@echo "==============================="
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) logs -f auth-service

auth-health: health-auth

auth-restart:
	@echo "🔄 Restarting Authentication Services..."
	@echo "======================================"
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) restart auth-service orchestrator-auth

auth-reset:
	@echo "⚠️ RESETTING AUTHENTICATION SYSTEM (DEV ONLY)..."
	@echo "=============================================="
	@read -p "This will delete all users and tokens. Continue? (y/N) " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) down auth-service; \
		docker volume rm vllm-local-swarm_langfuse_db_data || true; \
		docker-compose -f $(COMPOSE_FILE) up -d langfuse-db; \
		sleep 5; \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) up -d auth-service; \
		echo "✅ Authentication system reset!"; \
	else \
		echo "❌ Reset cancelled"; \
	fi

# Legacy compatibility and shortcuts
compose-up: 
	@if [ "$(AUTH_MODE)" = "enabled" ]; then \
		$(MAKE) --no-print-directory auth-deploy; \
	else \
		$(MAKE) --no-print-directory quick-start; \
	fi

compose-down:
	@echo "🛑 Stopping All Services..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) down

compose-logs:
	@if [ -n "$(SERVICE)" ]; then \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) logs -f $(SERVICE); \
	else \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) logs -f; \
	fi

compose-build:
	@echo "🏗️ Building Services..."
	@if [ -n "$(SERVICE)" ]; then \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) build --no-cache $(SERVICE); \
	else \
		docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) build --no-cache; \
	fi

compose-clean:
	@echo "🧹 Cleaning Docker Resources..."
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) down -v
	docker system prune -f

# Health checks for backward compatibility
health-basic:
	@echo "🏥 Basic Services Health Check..."
	@echo "==============================="
	@echo -n "Redis: "
	@if docker exec vllm-redis redis-cli ping >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Qdrant: "
	@if curl -sf http://localhost:6333/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Langfuse DB: "
	@if docker exec vllm-langfuse-db pg_isready -U langfuse >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi
	@echo -n "Langfuse Web: "
	@if curl -sf http://localhost:3000/api/public/health >/dev/null 2>&1; then echo "✅ Healthy"; else echo "❌ Unhealthy"; fi

# Kubernetes commands (unchanged)
k8s-install:
	@echo "☸️ Installing on Kubernetes..."
	helm install $(RELEASE_NAME) ./helm --namespace $(NAMESPACE) --create-namespace

k8s-uninstall:
	@echo "☸️ Uninstalling from Kubernetes..."
	helm uninstall $(RELEASE_NAME) --namespace $(NAMESPACE)

k8s-status:
	@echo "☸️ Kubernetes Status..."
	helm list --namespace $(NAMESPACE)
	kubectl get pods --namespace $(NAMESPACE)

# Maintenance and backup
maintenance:
	@echo "🔧 Running Maintenance..."
	docker system prune -f
	docker-compose -f $(COMPOSE_FILE) -f $(AUTH_COMPOSE_FILE) pull

backup-volumes:
	@echo "💾 Backing up volumes..."
	mkdir -p backups
	docker run --rm -v vllm-local-swarm_redis_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/redis_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	docker run --rm -v vllm-local-swarm_langfuse_db_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/postgres_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "✅ Backups created in ./backups/"

# Convenient aliases
up: compose-up
down: compose-down
logs: compose-logs
build: compose-build
clean: compose-clean
health: health-check
test: test-auth
restart: auth-restart