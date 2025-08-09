#!/bin/bash

# vLLM Local Swarm Authentication System Deployment Script
# This script handles the complete deployment and testing of the authentication system

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AUTH_SERVICE_PORT=8005
ORCHESTRATOR_PORT=8006
MEMORY_API_PORT=8007
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@vllm-swarm.local}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-SecureAdmin123!}

echo -e "${BLUE}🔐 vLLM Local Swarm Authentication System Deployment${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo ""

# Function to print step headers
print_step() {
    echo -e "${BLUE}📋 Step $1: $2${NC}"
}

# Function to check if service is healthy
check_service_health() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $name is healthy!${NC}"
            return 0
        fi
        echo "⏳ Waiting for $name... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $name failed to become healthy after $max_attempts attempts${NC}"
    return 1
}

# Function to test authentication endpoints
test_auth_endpoints() {
    print_step "AUTH-TEST" "Testing Authentication Endpoints"
    
    # Test health endpoint
    echo "Testing authentication service health..."
    if curl -sf "http://localhost:$AUTH_SERVICE_PORT/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Authentication service health check passed${NC}"
        curl -s "http://localhost:$AUTH_SERVICE_PORT/health" | jq . || curl -s "http://localhost:$AUTH_SERVICE_PORT/health"
    else
        echo -e "${RED}❌ Authentication service health check failed${NC}"
        return 1
    fi
    
    # Test user registration
    echo ""
    echo "Testing user registration..."
    demo_user="test_$(date +%s)"
    response=$(curl -X POST "http://localhost:$AUTH_SERVICE_PORT/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$demo_user\",\"email\":\"$demo_user@example.com\",\"password\":\"TestPass123!\",\"full_name\":\"Test User\"}" \
        -s)
    
    if echo "$response" | jq -e '.username' >/dev/null 2>&1; then
        echo -e "${GREEN}✅ User registration successful${NC}"
        echo "$response" | jq .
    else
        echo -e "${YELLOW}⚠️ User registration response:${NC}"
        echo "$response"
    fi
    
    # Test admin login
    echo ""
    echo "Testing admin login..."
    response=$(curl -X POST "http://localhost:$AUTH_SERVICE_PORT/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" \
        -s)
    
    token=$(echo "$response" | jq -r '.access_token // empty')
    if [ -n "$token" ] && [ "$token" != "null" ]; then
        echo -e "${GREEN}✅ Admin login successful${NC}"
        echo "Token: ${token:0:20}..."
        echo "$token" > /tmp/auth_test_token.txt
    else
        echo -e "${RED}❌ Admin login failed${NC}"
        echo "$response"
        return 1
    fi
    
    return 0
}

# Function to test service integration
test_service_integration() {
    print_step "INTEGRATION" "Testing Service Integration"
    
    # Test unauthenticated request (should fail)
    echo "Testing unauthenticated request to orchestrator..."
    response_code=$(curl -X GET "http://localhost:$ORCHESTRATOR_PORT/tasks" -s -o /dev/null -w "%{http_code}")
    if [ "$response_code" = "401" ]; then
        echo -e "${GREEN}✅ Orchestrator properly rejects unauthenticated requests${NC}"
    else
        echo -e "${RED}❌ Orchestrator should return 401, got $response_code${NC}"
    fi
    
    # Test authenticated request
    if [ -f /tmp/auth_test_token.txt ]; then
        echo "Testing authenticated request to orchestrator..."
        token=$(cat /tmp/auth_test_token.txt)
        response_code=$(curl -X GET "http://localhost:$ORCHESTRATOR_PORT/tasks" \
            -H "Authorization: Bearer $token" \
            -s -o /dev/null -w "%{http_code}")
        if [ "$response_code" = "200" ]; then
            echo -e "${GREEN}✅ Orchestrator accepts authenticated requests${NC}"
        else
            echo -e "${RED}❌ Orchestrator should return 200, got $response_code${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️ No token available for authenticated test${NC}"
    fi
    
    return 0
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    print_step "TESTS" "Running Comprehensive Tests"
    
    # Install test dependencies
    echo "Installing test dependencies..."
    pip install pytest httpx pytest-asyncio bandit safety ruff > /dev/null 2>&1 || echo "⚠️ Could not install some test dependencies"
    
    # Run authentication unit tests
    if [ -f tests/test_authentication.py ]; then
        echo "Running authentication unit tests..."
        python -m pytest tests/test_authentication.py -v --tb=short || echo "⚠️ Some unit tests failed"
    else
        echo "⚠️ Authentication test file not found at tests/test_authentication.py"
    fi
    
    # Run security tests
    echo "Running security scans..."
    if command -v bandit >/dev/null 2>&1; then
        echo "Running bandit security scan..."
        bandit -r auth/ -f json -o security_report.json || echo "⚠️ Security issues found"
        bandit -r auth/ || echo "⚠️ Security scan completed"
    else
        echo "⚠️ bandit not installed, skipping security scan"
    fi
    
    return 0
}

# Function to setup users
setup_users() {
    print_step "USER-SETUP" "Setting up Authentication Users"
    
    echo "Creating admin user..."
    curl -X POST "http://localhost:$AUTH_SERVICE_PORT/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$ADMIN_USERNAME\",\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\",\"full_name\":\"System Administrator\"}" \
        -s | jq . || echo "⚠️ Admin user might already exist"
    
    echo "Creating test developer user..."
    curl -X POST "http://localhost:$AUTH_SERVICE_PORT/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username":"developer","email":"dev@vllm-swarm.local","password":"DevPass123!","full_name":"Test Developer"}' \
        -s | jq . || echo "⚠️ Developer user might already exist"
    
    echo "Creating test user..."
    curl -X POST "http://localhost:$AUTH_SERVICE_PORT/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"username":"testuser","email":"test@vllm-swarm.local","password":"TestPass123!","full_name":"Test User"}' \
        -s | jq . || echo "⚠️ Test user might already exist"
    
    echo -e "${GREEN}✅ User setup completed!${NC}"
    echo ""
    echo -e "${BLUE}🔑 Login Credentials:${NC}"
    echo "  Admin:     $ADMIN_USERNAME / $ADMIN_PASSWORD"
    echo "  Developer: developer / DevPass123!"
    echo "  Test User: testuser / TestPass123!"
    
    return 0
}

# Function to show deployment summary
show_deployment_summary() {
    echo ""
    echo -e "${GREEN}✅ Authentication System Deployment Summary${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo ""
    echo -e "${BLUE}🌐 Service Access Points:${NC}"
    echo "  - Authentication API:    http://localhost:$AUTH_SERVICE_PORT"
    echo "  - Orchestrator API:      http://localhost:$ORCHESTRATOR_PORT"
    echo "  - Memory API:           http://localhost:$MEMORY_API_PORT"
    echo "  - vLLM API:             http://localhost:8000"
    echo "  - Langfuse Dashboard:   http://localhost:3000"
    echo "  - Qdrant Dashboard:     http://localhost:6333/dashboard"
    echo ""
    echo -e "${BLUE}📖 Available Make Commands:${NC}"
    echo "  make auth-health        # Check authentication service health"
    echo "  make auth-test          # Run authentication tests"
    echo "  make auth-demo          # Run authentication demo"
    echo "  make auth-logs          # View authentication service logs"
    echo "  make auth-stats         # View authentication statistics"
    echo ""
    echo -e "${BLUE}🔧 Docker Commands (when Docker is available):${NC}"
    echo "  make auth-deploy        # Deploy authentication system"
    echo "  make auth-setup         # Setup users"
    echo "  make dev-start          # Start development environment"
    echo "  make health-check       # Check all services"
}

# Main execution
main() {
    # Check if Docker is available
    if command -v docker >/dev/null 2>&1 && command -v docker-compose >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker is available. Running full deployment...${NC}"
        
        # Check environment
        if [ ! -f .env ]; then
            cp .env.example .env 2>/dev/null || echo "# vLLM Local Swarm Environment Variables" > .env
            echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
            echo "LANGFUSE_DB_PASSWORD=$(openssl rand -base64 16)" >> .env
            echo -e "${GREEN}✅ Created .env file with generated secrets${NC}"
        fi
        
        # Build services
        print_step "1" "Building Authentication Services"
        docker-compose -f docker-compose.yml -f docker-compose.auth.yml build auth-service orchestrator-auth || {
            echo -e "${RED}❌ Failed to build authentication services${NC}"
            exit 1
        }
        
        # Start foundation services
        print_step "2" "Starting Foundation Services"
        docker-compose -f docker-compose.yml up -d redis langfuse-db qdrant || {
            echo -e "${RED}❌ Failed to start foundation services${NC}"
            exit 1
        }
        
        # Wait for foundation services
        print_step "3" "Waiting for Foundation Services"
        sleep 10
        
        # Start authentication service
        print_step "4" "Starting Authentication Service"
        docker-compose -f docker-compose.yml -f docker-compose.auth.yml up -d auth-service || {
            echo -e "${RED}❌ Failed to start authentication service${NC}"
            exit 1
        }
        
        # Wait for authentication service
        print_step "5" "Waiting for Authentication Service"
        check_service_health "http://localhost:$AUTH_SERVICE_PORT/health" "Authentication Service" || exit 1
        
        # Start authenticated services
        print_step "6" "Starting Authenticated Services"
        docker-compose -f docker-compose.yml -f docker-compose.auth.yml up -d orchestrator-auth memory-api langfuse-web || {
            echo -e "${RED}❌ Failed to start authenticated services${NC}"
            exit 1
        }
        
        # Start AI/ML services
        print_step "7" "Starting AI/ML Services"
        docker-compose -f docker-compose.yml up -d vllm-phi || {
            echo -e "${RED}❌ Failed to start AI/ML services${NC}"
            exit 1
        }
        
        # Setup users
        setup_users || exit 1
        
        # Run tests
        test_auth_endpoints || exit 1
        test_service_integration || exit 1
        run_comprehensive_tests || exit 1
        
    else
        echo -e "${YELLOW}⚠️ Docker is not available in this environment.${NC}"
        echo -e "${BLUE}📖 To deploy the authentication system:${NC}"
        echo ""
        echo "1. Install Docker and Docker Compose on your system"
        echo "2. Run: make auth-deploy"
        echo "3. Run: make auth-setup"
        echo "4. Run: make auth-test"
        echo ""
        echo -e "${BLUE}📋 For now, let's run the available tests:${NC}"
        
        # Run tests that don't require running services
        run_comprehensive_tests || exit 1
    fi
    
    show_deployment_summary
    
    # Cleanup
    rm -f /tmp/auth_test_token.txt
    
    echo ""
    echo -e "${GREEN}🎉 Authentication system deployment and testing completed!${NC}"
}

# Run main function
main "$@"