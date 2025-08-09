# 🔐 GitHub Actions Secrets Configuration

This document outlines the required GitHub Actions secrets for the vLLM Local Swarm CI/CD pipeline with enterprise authentication.

## 📋 Required Secrets

### Core Authentication Secrets

| Secret Name | Description | Required For | Example/Format |
|-------------|-------------|--------------|----------------|
| `JWT_SECRET_KEY` | JWT token signing key (min 32 chars) | All workflows | `your-super-secure-jwt-signing-key-32chars` |
| `LANGFUSE_DB_PASSWORD` | PostgreSQL database password | CI/CD, Deployment | `SecureDbPassword123!` |
| `LANGFUSE_SECRET` | Langfuse application secret | CI/CD, Deployment | `langfuse-secret-key` |

### Docker Registry Secrets

| Secret Name | Description | Required For | Example/Format |
|-------------|-------------|--------------|----------------|
| `DOCKER_REGISTRY` | Docker registry URL | Docker build/push | `ghcr.io` |
| `DOCKER_REGISTRY_USERNAME` | Registry username | Docker build/push | `your-github-username` |
| `DOCKER_REGISTRY_PASSWORD` | Registry password/token | Docker build/push | `ghp_xxxxxxxxxxxxx` |

### Deployment Secrets

| Secret Name | Description | Required For | Example/Format |
|-------------|-------------|--------------|----------------|
| `KUBECONFIG` | Kubernetes cluster config | Deployment | `apiVersion: v1...` (base64) |
| `HELM_REGISTRY_USERNAME` | Helm registry username | Helm deployment | `your-username` |
| `HELM_REGISTRY_PASSWORD` | Helm registry password | Helm deployment | `your-password` |

### Optional Security & Monitoring Secrets

| Secret Name | Description | Required For | Example/Format |
|-------------|-------------|--------------|----------------|
| `SLACK_WEBHOOK_URL` | Slack notification webhook | Notifications | `https://hooks.slack.com/...` |
| `SECURITY_EMAIL` | Email for security alerts | Security scanning | `security@yourcompany.com` |
| `SONARCLOUD_TOKEN` | SonarCloud analysis token | Code quality | `sqp_xxxxxxxxxxxxx` |

## 🔧 Setting Up Secrets

### 1. Navigate to Repository Settings

```
https://github.com/YOUR_USERNAME/vllm-local-swarm/settings/secrets/actions
```

### 2. Add Repository Secrets

Click "New repository secret" and add each required secret:

#### JWT Secret Key Generation
```bash
# Generate a secure JWT secret (32+ characters)
openssl rand -base64 32

# Or use Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Database Password Generation
```bash
# Generate a secure database password
openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
```

### 3. Docker Registry Setup (GitHub Container Registry)

1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Create token with `write:packages` permission
3. Use your GitHub username as `DOCKER_REGISTRY_USERNAME`
4. Use the token as `DOCKER_REGISTRY_PASSWORD`

## 🌍 Environment-Specific Secrets

### Staging Environment

Create additional secrets for staging deployment:

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `STAGING_JWT_SECRET_KEY` | Staging JWT secret | Different from production |
| `STAGING_DB_PASSWORD` | Staging database password | `StagingDb123!` |
| `STAGING_KUBECONFIG` | Staging cluster config | Base64 encoded kubeconfig |
| `STAGING_ADMIN_PASSWORD` | Default admin password | `Admin123!Staging` |

### Production Environment

Create production-specific secrets:

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `PRODUCTION_JWT_SECRET_KEY` | Production JWT secret | High entropy, rotated regularly |
| `PRODUCTION_DB_PASSWORD` | Production database password | Complex, unique password |
| `PRODUCTION_KUBECONFIG` | Production cluster config | Base64 encoded kubeconfig |
| `PRODUCTION_ADMIN_EMAIL` | Production admin email | `admin@yourcompany.com` |

## 🔄 Secret Rotation Schedule

### High Priority (Monthly)
- `JWT_SECRET_KEY` / `PRODUCTION_JWT_SECRET_KEY`
- `DOCKER_REGISTRY_PASSWORD`
- `KUBECONFIG` (if cluster certificates expire)

### Medium Priority (Quarterly)
- `LANGFUSE_DB_PASSWORD`
- `LANGFUSE_SECRET`
- Admin passwords

### Low Priority (Annually)
- `STAGING_*` secrets
- Monitoring/notification tokens

## 📝 Secret Validation Commands

### Test JWT Secret
```bash
# Validate JWT secret length
export JWT_SECRET_KEY="your-secret-here"
if [ ${#JWT_SECRET_KEY} -ge 32 ]; then 
  echo "✅ JWT secret is valid length"; 
else 
  echo "❌ JWT secret too short"; 
fi
```

### Test Docker Registry Access
```bash
# Test Docker registry login
echo $DOCKER_REGISTRY_PASSWORD | docker login ghcr.io -u $DOCKER_REGISTRY_USERNAME --password-stdin
```

### Test Database Connection
```bash
# Test PostgreSQL connection
psql "postgresql://vllm_user:$LANGFUSE_DB_PASSWORD@localhost:5432/vllm_auth" -c "SELECT 1;"
```

## 🚨 Security Best Practices

### 1. Secret Management
- ✅ Use minimum required permissions
- ✅ Rotate secrets regularly
- ✅ Use different secrets for different environments
- ✅ Never commit secrets to git (use `.env.example` with placeholders)
- ❌ Don't share secrets via email/chat
- ❌ Don't use production secrets in development

### 2. Access Control
- ✅ Limit repository access to necessary team members
- ✅ Use branch protection rules
- ✅ Require code review for workflow changes
- ✅ Enable secret scanning on repository

### 3. Monitoring
- ✅ Monitor secret usage in workflow logs
- ✅ Set up alerts for failed authentication
- ✅ Audit secret access regularly
- ✅ Review and rotate unused secrets

## 🔍 Troubleshooting Secrets

### Common Issues

#### "Invalid JWT Secret" Error
```bash
# Check secret exists and has correct name
gh secret list

# Check secret length (should be 32+ chars)
echo "Your secret here" | wc -c
```

#### Docker Push Permission Denied
```bash
# Verify registry URL
echo $DOCKER_REGISTRY  # Should be ghcr.io

# Check token permissions
curl -H "Authorization: token $DOCKER_REGISTRY_PASSWORD" \
  https://api.github.com/user/packages?package_type=container
```

#### Kubernetes Connection Failed
```bash
# Test kubeconfig
kubectl --kubeconfig=<(echo $KUBECONFIG | base64 -d) get nodes

# Verify cluster access
kubectl --kubeconfig=<(echo $KUBECONFIG | base64 -d) auth can-i create pods
```

### Debug Mode

Enable debug logging in workflows by adding:
```yaml
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true
```

## 🔄 Secret Rotation Procedure

### 1. Generate New Secret
```bash
# Generate new JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 32)
echo "New JWT Secret: $NEW_JWT_SECRET"
```

### 2. Update GitHub Secret
- Go to repository settings
- Edit the secret
- Paste new value
- Save

### 3. Update Deployed Applications
```bash
# Update Kubernetes secret
kubectl create secret generic vllm-auth-secrets \
  --namespace=vllm-swarm \
  --from-literal=jwt-secret-key="$NEW_JWT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart services to pick up new secret
kubectl rollout restart deployment/auth-service -n vllm-swarm
```

### 4. Verify Rotation
```bash
# Test authentication with new secret
curl -X POST http://localhost:8005/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-admin-password"}'
```

## 📊 Secret Usage Monitoring

### GitHub Actions Usage
```yaml
# In workflow file - log secret usage (don't expose values)
- name: Verify secrets
  run: |
    echo "JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
    echo "Docker registry: $DOCKER_REGISTRY"
    echo "Kubeconfig size: $(echo $KUBECONFIG | base64 -d | wc -c)"
```

### Audit Script
```bash
#!/bin/bash
# audit-secrets.sh - Check secret freshness

echo "🔍 Secret Audit Report - $(date)"
echo

# Check JWT secret age (implement based on your tracking method)
echo "📊 Secret Status:"
echo "- JWT Secret: Last rotated $(date -d '30 days ago' '+%Y-%m-%d') ⚠️"
echo "- DB Password: Last rotated $(date -d '90 days ago' '+%Y-%m-%d') ✅"
echo "- Docker Token: Last rotated $(date -d '60 days ago' '+%Y-%m-%d') ✅"

echo
echo "🔄 Rotation Recommendations:"
echo "- Rotate JWT secret immediately (overdue)"
echo "- DB password rotation due in 60 days"
echo "- All other secrets current"
```

## 📞 Support & Emergency Contacts

### Secret Compromise Response
1. **Immediately** revoke compromised secret in GitHub
2. **Rotate** secret in all environments
3. **Audit** recent activity for unauthorized usage
4. **Notify** security team: security@yourcompany.com

### Emergency Secret Reset
```bash
# Emergency JWT secret reset
EMERGENCY_JWT_SECRET=$(openssl rand -base64 32)

# Update all environments
kubectl create secret generic emergency-auth-secrets \
  --from-literal=jwt-secret-key="$EMERGENCY_JWT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -
```

---

## 📚 Additional Resources

- [GitHub Actions Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Kubernetes Secret Management](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Docker Registry Authentication](https://docs.docker.com/registry/spec/auth/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**🔐 Remember**: Secrets are the keys to your kingdom. Protect them accordingly!