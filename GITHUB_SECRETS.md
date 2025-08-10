# 🔐 GitHub Secrets Configuration Guide

## 📋 Overview

This guide provides comprehensive instructions for configuring GitHub repository secrets to support development, staging, and production environments for the vLLM Local Swarm project.

---

## 🏗️ **Environment Structure**

### **Development Environment**
- **Purpose**: Local development and testing
- **Infrastructure**: Docker Compose with local containers
- **Security**: Development credentials, non-production secrets

### **Staging Environment** 
- **Purpose**: Pre-production testing and validation
- **Infrastructure**: GHCR containers with staging configurations
- **Security**: Production-like security with staging credentials

### **Production Environment**
- **Purpose**: Live production deployment
- **Infrastructure**: GHCR containers with production configurations  
- **Security**: Maximum security, encrypted secrets, audit logging

---

## 🔑 **Required GitHub Secrets**

### **🛠️ Development Environment Secrets**

#### **Repository Settings > Secrets and variables > Actions > Repository secrets**

```bash
# Authentication
DEV_JWT_SECRET_KEY
# Value: "dev-jwt-secret-key-change-this-in-production-min32chars"
# Description: JWT signing key for development

DEV_API_SECRET_KEY  
# Value: "dev-api-secret-key-for-service-communication-change-this"
# Description: API key for service-to-service communication

# Database
DEV_DATABASE_URL
# Value: "postgresql+asyncpg://langfuse:langfuse123@localhost:5432/auth"
# Description: Development database connection string

DEV_REDIS_URL
# Value: "redis://localhost:6379"
# Description: Development Redis connection

# Observability
DEV_LANGFUSE_SECRET_KEY
# Value: "sk-lf-development-key-replace-with-actual"
# Description: Langfuse secret key for development

DEV_LANGFUSE_PUBLIC_KEY
# Value: "pk-lf-development-key-replace-with-actual"  
# Description: Langfuse public key for development

DEV_LANGFUSE_HOST
# Value: "http://localhost:3000"
# Description: Langfuse host URL for development
```

### **🚀 Staging Environment Secrets**

```bash
# Authentication
STAGING_JWT_SECRET_KEY
# Value: [Generate 32+ character secure key]
# Command: python -c "import secrets; print(secrets.token_urlsafe(32))"
# Description: JWT signing key for staging

STAGING_API_SECRET_KEY
# Value: [Generate secure API key]
# Command: python -c "import secrets; print('sk-' + secrets.token_urlsafe(48))"
# Description: API key for staging service communication

# Database
STAGING_DATABASE_URL
# Value: "postgresql+asyncpg://username:password@staging-db:5432/auth"
# Description: Staging database connection string

STAGING_REDIS_URL
# Value: "redis://username:password@staging-redis:6379"
# Description: Staging Redis connection with auth

STAGING_REDIS_PASSWORD
# Value: [Secure Redis password]
# Description: Redis authentication password

# Observability
STAGING_LANGFUSE_SECRET_KEY
# Value: "sk-lf-[secure-staging-key]"
# Description: Langfuse secret key for staging

STAGING_LANGFUSE_PUBLIC_KEY
# Value: "pk-lf-[staging-public-key]"
# Description: Langfuse public key for staging

STAGING_LANGFUSE_HOST
# Value: "https://staging-langfuse.your-domain.com"
# Description: Staging Langfuse host URL

# External APIs (Staging)
STAGING_OPENAI_API_KEY
# Value: [OpenAI API key for staging]
# Description: OpenAI API key for AI model access

STAGING_ANTHROPIC_API_KEY
# Value: [Anthropic API key for staging]
# Description: Anthropic Claude API key
```

### **🏭 Production Environment Secrets**

```bash
# Authentication (CRITICAL SECURITY)
PROD_JWT_SECRET_KEY
# Value: [Generate 64+ character secure key]
# Command: python -c "import secrets; print(secrets.token_urlsafe(64))"
# Description: PRODUCTION JWT signing key - NEVER SHARE

PROD_API_SECRET_KEY
# Value: [Generate 64+ character API key]
# Command: python -c "import secrets; print('sk-prod-' + secrets.token_urlsafe(64))"
# Description: Production API key for service communication

# Database (Production)
PROD_DATABASE_URL
# Value: "postgresql+asyncpg://prod_user:secure_password@prod-db:5432/auth_prod?sslmode=require"
# Description: Production database with SSL required

PROD_DB_ENCRYPTION_KEY
# Value: [32-byte encryption key]
# Command: python -c "import secrets; print(secrets.token_hex(32))"
# Description: Database field-level encryption key

# Caching & Sessions
PROD_REDIS_URL
# Value: "rediss://username:password@prod-redis:6380/0"  
# Description: Production Redis with TLS

PROD_REDIS_PASSWORD
# Value: [64-character secure password]
# Command: python -c "import secrets; print(secrets.token_urlsafe(64))"
# Description: Production Redis authentication

# Observability (Production)
PROD_LANGFUSE_SECRET_KEY
# Value: "sk-lf-[production-secret-key]"
# Description: Production Langfuse secret key

PROD_LANGFUSE_PUBLIC_KEY
# Value: "pk-lf-[production-public-key]"
# Description: Production Langfuse public key

PROD_LANGFUSE_HOST
# Value: "https://langfuse.your-domain.com"
# Description: Production Langfuse host URL

# External APIs (Production)
PROD_OPENAI_API_KEY
# Value: [Production OpenAI API key]
# Description: OpenAI API key for production

PROD_ANTHROPIC_API_KEY
# Value: [Production Anthropic API key]
# Description: Anthropic Claude API key for production

# Security & Monitoring
PROD_ENCRYPTION_KEY
# Value: [64-character hex string]
# Command: python -c "import secrets; print(secrets.token_hex(64))"
# Description: General encryption key for sensitive data

PROD_AUDIT_WEBHOOK_URL
# Value: "https://your-monitoring.com/webhooks/audit"
# Description: Webhook for security audit alerts

PROD_ALERT_EMAIL
# Value: "security-alerts@your-company.com"
# Description: Email for production security alerts

# TLS/SSL Certificates
PROD_SSL_CERT
# Value: [Base64 encoded SSL certificate]
# Description: Production SSL certificate

PROD_SSL_KEY
# Value: [Base64 encoded SSL private key]
# Description: Production SSL private key

# Container Registry (if private)
GHCR_USERNAME
# Value: "your-github-username"
# Description: GitHub Container Registry username

GHCR_TOKEN
# Value: [GitHub Personal Access Token with packages:read scope]
# Description: Token for private container access
```

---

## 🔧 **Setting Up GitHub Secrets**

### **Step 1: Access Repository Settings**
```bash
# Navigate to your GitHub repository
https://github.com/tbowman01/vllm-local-swarm

# Go to Settings > Secrets and variables > Actions
# Click "New repository secret"
```

### **Step 2: Generate Secure Keys**
```bash
# Create a secure key generation script
cat > scripts/generate-secrets.py << 'EOF'
#!/usr/bin/env python3
"""
Generate secure secrets for vLLM Local Swarm environments
"""
import secrets
import string
import base64

def generate_jwt_secret(length=64):
    """Generate JWT secret key"""
    return secrets.token_urlsafe(length)

def generate_api_key(prefix="sk", length=48):
    """Generate API key with prefix"""
    return f"{prefix}-{secrets.token_urlsafe(length)}"

def generate_password(length=32):
    """Generate secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=64):
    """Generate hex encryption key"""
    return secrets.token_hex(length)

def generate_langfuse_encryption_key():
    """Generate Langfuse-compatible 64-character hex key"""
    return secrets.token_hex(32)  # 32 bytes = 64 hex chars

if __name__ == "__main__":
    print("=== vLLM Local Swarm Secret Generator ===\n")
    
    print("DEVELOPMENT SECRETS:")
    print(f"DEV_JWT_SECRET_KEY: {generate_jwt_secret(32)}")
    print(f"DEV_API_SECRET_KEY: {generate_api_key('dev', 32)}")
    print(f"DEV_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("STAGING SECRETS:")
    print(f"STAGING_JWT_SECRET_KEY: {generate_jwt_secret(48)}")
    print(f"STAGING_API_SECRET_KEY: {generate_api_key('staging', 48)}")
    print(f"STAGING_REDIS_PASSWORD: {generate_password(32)}")
    print(f"STAGING_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("PRODUCTION SECRETS:")
    print(f"PROD_JWT_SECRET_KEY: {generate_jwt_secret(64)}")
    print(f"PROD_API_SECRET_KEY: {generate_api_key('prod', 64)}")
    print(f"PROD_REDIS_PASSWORD: {generate_password(64)}")
    print(f"PROD_DB_ENCRYPTION_KEY: {generate_hex_key(32)}")
    print(f"PROD_ENCRYPTION_KEY: {generate_hex_key(64)}")
    print(f"PROD_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("NOTE: Store these secrets securely and never commit to version control!")
EOF

chmod +x scripts/generate-secrets.py

# Generate secrets
python scripts/generate-secrets.py
```

### **Step 3: Add Secrets to GitHub**
```bash
# Example using GitHub CLI
gh secret set DEV_JWT_SECRET_KEY --body "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"

gh secret set STAGING_JWT_SECRET_KEY --body "$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"

gh secret set PROD_JWT_SECRET_KEY --body "$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

# List all secrets to verify
gh secret list
```

---

## 🌍 **Environment-Specific Configurations**

### **Development (.env.development)**
```bash
# Generated automatically from GitHub secrets
NODE_ENV=development
LOG_LEVEL=DEBUG
DEBUG=true

# Authentication
JWT_SECRET_KEY=${{ secrets.DEV_JWT_SECRET_KEY }}
API_SECRET_KEY=${{ secrets.DEV_API_SECRET_KEY }}

# Database  
DATABASE_URL=${{ secrets.DEV_DATABASE_URL }}
REDIS_URL=${{ secrets.DEV_REDIS_URL }}

# Observability
LANGFUSE_SECRET_KEY=${{ secrets.DEV_LANGFUSE_SECRET_KEY }}
LANGFUSE_PUBLIC_KEY=${{ secrets.DEV_LANGFUSE_PUBLIC_KEY }}
LANGFUSE_HOST=${{ secrets.DEV_LANGFUSE_HOST }}

# AI/ML Settings
VLLM_GPU_MEMORY_UTILIZATION=0.90
VLLM_MAX_MODEL_LEN=16384
```

### **Staging (.env.staging)**
```bash
# Production-like configuration
NODE_ENV=staging
LOG_LEVEL=INFO
DEBUG=false

# Authentication
JWT_SECRET_KEY=${{ secrets.STAGING_JWT_SECRET_KEY }}
API_SECRET_KEY=${{ secrets.STAGING_API_SECRET_KEY }}
JWT_EXPIRATION=3600

# Database with connection pooling
DATABASE_URL=${{ secrets.STAGING_DATABASE_URL }}
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis with authentication
REDIS_URL=${{ secrets.STAGING_REDIS_URL }}
REDIS_PASSWORD=${{ secrets.STAGING_REDIS_PASSWORD }}

# Enhanced observability
LANGFUSE_SECRET_KEY=${{ secrets.STAGING_LANGFUSE_SECRET_KEY }}
LANGFUSE_PUBLIC_KEY=${{ secrets.STAGING_LANGFUSE_PUBLIC_KEY }}
LANGFUSE_HOST=${{ secrets.STAGING_LANGFUSE_HOST }}
LANGFUSE_ENCRYPTION_KEY=${{ secrets.STAGING_LANGFUSE_ENCRYPTION_KEY }}

# External APIs
OPENAI_API_KEY=${{ secrets.STAGING_OPENAI_API_KEY }}
ANTHROPIC_API_KEY=${{ secrets.STAGING_ANTHROPIC_API_KEY }}
```

### **Production (.env.production)**
```bash
# Maximum security configuration
NODE_ENV=production
LOG_LEVEL=WARN
DEBUG=false
SECURE_MODE=true

# Authentication with maximum security
JWT_SECRET_KEY=${{ secrets.PROD_JWT_SECRET_KEY }}
API_SECRET_KEY=${{ secrets.PROD_API_SECRET_KEY }}
JWT_EXPIRATION=1800  # 30 minutes
JWT_REFRESH_EXPIRATION=604800  # 7 days

# Database with SSL and encryption
DATABASE_URL=${{ secrets.PROD_DATABASE_URL }}
DB_ENCRYPTION_KEY=${{ secrets.PROD_DB_ENCRYPTION_KEY }}
DB_SSL_MODE=require
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100

# Redis with TLS and authentication
REDIS_URL=${{ secrets.PROD_REDIS_URL }}
REDIS_PASSWORD=${{ secrets.PROD_REDIS_PASSWORD }}
REDIS_TLS=true

# Production observability
LANGFUSE_SECRET_KEY=${{ secrets.PROD_LANGFUSE_SECRET_KEY }}
LANGFUSE_PUBLIC_KEY=${{ secrets.PROD_LANGFUSE_PUBLIC_KEY }}
LANGFUSE_HOST=${{ secrets.PROD_LANGFUSE_HOST }}
LANGFUSE_ENCRYPTION_KEY=${{ secrets.PROD_LANGFUSE_ENCRYPTION_KEY }}

# External APIs
OPENAI_API_KEY=${{ secrets.PROD_OPENAI_API_KEY }}
ANTHROPIC_API_KEY=${{ secrets.PROD_ANTHROPIC_API_KEY }}

# Security & Monitoring
ENCRYPTION_KEY=${{ secrets.PROD_ENCRYPTION_KEY }}
AUDIT_WEBHOOK_URL=${{ secrets.PROD_AUDIT_WEBHOOK_URL }}
ALERT_EMAIL=${{ secrets.PROD_ALERT_EMAIL }}

# TLS/SSL
SSL_CERT_PATH=/app/certs/cert.pem
SSL_KEY_PATH=/app/certs/key.pem

# Rate limiting & security
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW=900  # 15 minutes
RATE_LIMIT_MAX=100  # requests per window
CORS_ORIGINS=https://your-domain.com
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# AI/ML Production Settings
VLLM_GPU_MEMORY_UTILIZATION=0.85  # Conservative for production
VLLM_MAX_MODEL_LEN=32768  # Full context length
VLLM_TENSOR_PARALLEL_SIZE=2  # Multi-GPU if available
```

---

## 🔐 **Security Best Practices**

### **Secret Management**
1. **Never commit secrets to version control**
2. **Use different secrets for each environment**
3. **Rotate secrets regularly (quarterly minimum)**
4. **Use long, randomly generated keys**
5. **Monitor secret usage and access**

### **Access Control**
1. **Limit who can view/edit repository secrets**
2. **Use environment-specific secrets**
3. **Audit secret access regularly**
4. **Implement secret rotation policies**

### **Production Security**
1. **Use TLS/SSL for all connections**
2. **Enable database encryption at rest**
3. **Implement audit logging for all secret usage**
4. **Use separate encryption keys for different data types**
5. **Monitor for unauthorized access attempts**

---

## 🚀 **GitHub Actions Integration**

### **Environment-Specific Workflows**
```yaml
# .github/workflows/deploy-production.yml
name: 🚀 Production Deployment

on:
  release:
    types: [published]

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment: production  # Requires manual approval
    
    steps:
    - name: 🔐 Configure Production Environment
      run: |
        echo "JWT_SECRET_KEY=${{ secrets.PROD_JWT_SECRET_KEY }}" >> .env.production
        echo "DATABASE_URL=${{ secrets.PROD_DATABASE_URL }}" >> .env.production
        echo "REDIS_URL=${{ secrets.PROD_REDIS_URL }}" >> .env.production
        # ... other production secrets
        
    - name: 🐳 Deploy to Production
      run: |
        docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

### **Secret Validation**
```yaml
# Add to workflows to validate secrets
- name: 🔍 Validate Required Secrets
  run: |
    if [ -z "${{ secrets.PROD_JWT_SECRET_KEY }}" ]; then
      echo "ERROR: PROD_JWT_SECRET_KEY is not set"
      exit 1
    fi
    
    if [ ${#JWT_SECRET_KEY} -lt 32 ]; then
      echo "ERROR: JWT_SECRET_KEY too short (minimum 32 characters)"
      exit 1
    fi
  env:
    JWT_SECRET_KEY: ${{ secrets.PROD_JWT_SECRET_KEY }}
```

---

## 📋 **Setup Checklist**

### **Development Environment**
- [ ] DEV_JWT_SECRET_KEY (32+ characters)
- [ ] DEV_API_SECRET_KEY  
- [ ] DEV_DATABASE_URL
- [ ] DEV_REDIS_URL
- [ ] DEV_LANGFUSE_SECRET_KEY
- [ ] DEV_LANGFUSE_PUBLIC_KEY

### **Staging Environment**
- [ ] STAGING_JWT_SECRET_KEY (48+ characters)
- [ ] STAGING_API_SECRET_KEY
- [ ] STAGING_DATABASE_URL
- [ ] STAGING_REDIS_URL
- [ ] STAGING_REDIS_PASSWORD
- [ ] STAGING_LANGFUSE_SECRET_KEY
- [ ] STAGING_LANGFUSE_PUBLIC_KEY
- [ ] STAGING_OPENAI_API_KEY
- [ ] STAGING_ANTHROPIC_API_KEY

### **Production Environment**
- [ ] PROD_JWT_SECRET_KEY (64+ characters)
- [ ] PROD_API_SECRET_KEY
- [ ] PROD_DATABASE_URL (with SSL)
- [ ] PROD_DB_ENCRYPTION_KEY
- [ ] PROD_REDIS_URL (with TLS)
- [ ] PROD_REDIS_PASSWORD
- [ ] PROD_LANGFUSE_SECRET_KEY
- [ ] PROD_LANGFUSE_PUBLIC_KEY
- [ ] PROD_OPENAI_API_KEY
- [ ] PROD_ANTHROPIC_API_KEY
- [ ] PROD_ENCRYPTION_KEY
- [ ] PROD_AUDIT_WEBHOOK_URL
- [ ] PROD_ALERT_EMAIL
- [ ] PROD_SSL_CERT
- [ ] PROD_SSL_KEY

---

**🎊 With these GitHub secrets configured, your vLLM Local Swarm will have enterprise-grade security across all environments!**

*Last Updated: August 10, 2025*  
*Security Standard: Enterprise-Grade*  
*Environment Support: Development, Staging, Production*