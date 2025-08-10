#!/bin/bash

# 🔐 Generate Secrets for vLLM Local Swarm CI/CD Pipeline
# This script generates cryptographically secure secrets for GitHub Actions

set -euo pipefail

echo "🔐 vLLM Local Swarm - Secret Generator"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to generate secure random string
generate_secret() {
    local length=$1
    local name=$2
    
    if command -v openssl &> /dev/null; then
        secret=$(openssl rand -base64 $length | tr -d '\n')
    elif command -v python3 &> /dev/null; then
        secret=$(python3 -c "import secrets; print(secrets.token_urlsafe($length))" | tr -d '\n')
    else
        echo -e "${RED}❌ Error: Neither openssl nor python3 found. Please install one of them.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Generated $name (${#secret} characters)${NC}"
    echo "$secret"
}

echo -e "${BLUE}📝 Generating required secrets...${NC}"
echo ""

# Generate JWT Secret Key (minimum 32 characters)
echo -e "${YELLOW}🔑 JWT_SECRET_KEY:${NC}"
JWT_SECRET=$(generate_secret 48 "JWT Secret Key")
echo ""

# Generate Langfuse DB Password
echo -e "${YELLOW}🗄️ LANGFUSE_DB_PASSWORD:${NC}"
DB_PASSWORD=$(generate_secret 32 "Database Password")
echo ""

# Generate Langfuse Secret
echo -e "${YELLOW}📊 LANGFUSE_SECRET:${NC}"
LANGFUSE_SECRET=$(generate_secret 32 "Langfuse Secret")
echo ""

echo -e "${BLUE}📋 Summary - Copy these values to GitHub Secrets:${NC}"
echo "=================================================="
echo ""
echo -e "${YELLOW}Secret Name:${NC} JWT_SECRET_KEY"
echo -e "${GREEN}Value:${NC} $JWT_SECRET"
echo ""
echo -e "${YELLOW}Secret Name:${NC} LANGFUSE_DB_PASSWORD"
echo -e "${GREEN}Value:${NC} $DB_PASSWORD"
echo ""
echo -e "${YELLOW}Secret Name:${NC} LANGFUSE_SECRET"
echo -e "${GREEN}Value:${NC} $LANGFUSE_SECRET"
echo ""

echo -e "${BLUE}🔗 Next Steps:${NC}"
echo "1. Go to: https://github.com/YOUR_USERNAME/vllm-local-swarm/settings/secrets/actions"
echo "2. Click 'New repository secret'"
echo "3. Add each secret above (copy the Value, not including 'Value:')"
echo "4. Ensure secret names match exactly (case-sensitive)"
echo ""

# Optional: Save to file for reference (WITHOUT exposing in git)
if [[ "${SAVE_TO_FILE:-}" == "true" ]]; then
    SECRETS_FILE="./.secrets-$(date +%Y%m%d-%H%M%S).txt"
    echo "# Generated secrets for vLLM Local Swarm - $(date)" > "$SECRETS_FILE"
    echo "# DO NOT COMMIT THIS FILE TO VERSION CONTROL" >> "$SECRETS_FILE"
    echo "" >> "$SECRETS_FILE"
    echo "JWT_SECRET_KEY=$JWT_SECRET" >> "$SECRETS_FILE"
    echo "LANGFUSE_DB_PASSWORD=$DB_PASSWORD" >> "$SECRETS_FILE"
    echo "LANGFUSE_SECRET=$LANGFUSE_SECRET" >> "$SECRETS_FILE"
    
    echo -e "${GREEN}💾 Secrets saved to: $SECRETS_FILE${NC}"
    echo -e "${RED}⚠️ WARNING: Delete this file after adding secrets to GitHub!${NC}"
    echo ""
fi

echo -e "${GREEN}✅ Secret generation complete!${NC}"
echo ""
echo -e "${BLUE}📖 For detailed setup instructions, see:${NC}"
echo "   docs/GITHUB_ACTIONS_SECRETS.md"
echo ""
echo -e "${YELLOW}🔒 Security Reminder:${NC}"
echo "   - Never share these secrets via chat, email, or unsecured channels"
echo "   - Only add them to GitHub repository secrets"
echo "   - Rotate secrets every 90 days for maximum security"