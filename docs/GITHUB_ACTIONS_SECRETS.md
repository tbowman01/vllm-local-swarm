# 🔐 GitHub Actions Secrets Configuration

This document provides step-by-step instructions for configuring GitHub Actions secrets required for the vLLM Local Swarm CI/CD pipeline.

## 📋 Required Secrets

### 🔑 Authentication & Security
| Secret Name | Purpose | Example/Format | Required |
|-------------|---------|----------------|----------|
| `JWT_SECRET_KEY` | JWT token signing key | `your-super-secret-jwt-key-32-chars-min` | ✅ **YES** |
| `LANGFUSE_DB_PASSWORD` | PostgreSQL database password | `secure-db-password-123` | ✅ **YES** |
| `LANGFUSE_SECRET` | Langfuse application secret | `langfuse-app-secret-key` | ✅ **YES** |

### 🐳 Container Registry
| Secret Name | Purpose | Example/Format | Required |
|-------------|---------|----------------|----------|
| `GITHUB_TOKEN` | GitHub Container Registry access | *Auto-provided by GitHub* | ✅ **YES** |

### ☁️ Deployment (Optional)
| Secret Name | Purpose | Example/Format | Required |
|-------------|---------|----------------|----------|
| `STAGING_KUBECONFIG` | Kubernetes config for staging | `apiVersion: v1...` | 🔄 **OPTIONAL** |
| `PRODUCTION_KUBECONFIG` | Kubernetes config for production | `apiVersion: v1...` | 🔄 **OPTIONAL** |
| `SLACK_WEBHOOK_URL` | Slack notifications | `https://hooks.slack.com/...` | 🔄 **OPTIONAL** |

## 🛠️ Setup Instructions

### Step 1: Generate JWT Secret Key

```bash
# Generate a secure 32-character JWT secret
openssl rand -base64 32
# OR using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 2: Generate Database Passwords

```bash
# Generate secure database password
openssl rand -base64 24
```

### Step 3: Add Secrets to GitHub Repository

1. Navigate to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each required secret:

#### JWT_SECRET_KEY
- **Name**: `JWT_SECRET_KEY`
- **Value**: Output from Step 1 (minimum 32 characters)
- **Example**: `dGhpc19pc19hX3NlY3VyZV9qd3Rfc2VjcmV0X2tleV8zMmNoYXJz`

#### LANGFUSE_DB_PASSWORD  
- **Name**: `LANGFUSE_DB_PASSWORD`
- **Value**: Output from Step 2
- **Example**: `SecureDBPassword123!`

#### LANGFUSE_SECRET
- **Name**: `LANGFUSE_SECRET`
- **Value**: Another secure random string
- **Example**: `langfuse-application-secret-key-secure-random`

### Step 4: Verify GitHub Token Permissions

The `GITHUB_TOKEN` is automatically provided by GitHub Actions. Ensure your repository has these permissions:

1. Go to **Settings** → **Actions** → **General**
2. Under "Workflow permissions":
   - Select **Read and write permissions**
   - Check **Allow GitHub Actions to create and approve pull requests**

## 🧪 Testing Secrets Configuration

After adding secrets, test the CI/CD pipeline:

```bash
# Push a commit to trigger the pipeline
git commit --allow-empty -m "test: Trigger CI/CD with new secrets"
git push
```

Monitor the pipeline at: `https://github.com/YOUR_USERNAME/vllm-local-swarm/actions`

## 🔍 Validation Commands

To validate secrets are working in CI/CD:

```yaml
# Example step to test secret availability (DO NOT expose actual values)
- name: Validate secrets
  run: |
    echo "JWT_SECRET_KEY length: ${#JWT_SECRET_KEY}"
    echo "LANGFUSE_DB_PASSWORD configured: $([ -n "$LANGFUSE_DB_PASSWORD" ] && echo "✅" || echo "❌")"
    echo "LANGFUSE_SECRET configured: $([ -n "$LANGFUSE_SECRET" ] && echo "✅" || echo "❌")"
  env:
    JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
    LANGFUSE_DB_PASSWORD: ${{ secrets.LANGFUSE_DB_PASSWORD }}
    LANGFUSE_SECRET: ${{ secrets.LANGFUSE_SECRET }}
```

## 🚨 Security Best Practices

### ✅ DO
- Use minimum 32-character secrets for JWT keys
- Generate cryptographically secure random strings
- Rotate secrets periodically (every 90 days)
- Use different secrets for staging and production
- Store secrets in GitHub repository settings only

### ❌ DON'T
- Hardcode secrets in code or configuration files
- Share secrets via chat, email, or unsecured channels
- Use weak or predictable passwords
- Log or expose secret values in CI/CD output
- Commit secrets to version control (even temporarily)

## 🔧 Environment-Specific Configuration

### Staging Environment
For staging deployments, use less complex but still secure secrets:

```bash
# Staging JWT Secret (still 32+ chars but can be simpler)
JWT_SECRET_KEY_STAGING="staging-jwt-secret-key-32-chars-minimum"
```

### Production Environment
For production, use maximum security:

```bash
# Production JWT Secret (complex, random)
JWT_SECRET_KEY_PRODUCTION="$(openssl rand -base64 48)"
```

## 🐛 Troubleshooting

### Issue: Pipeline fails with "Secret not found"
**Solution**: Verify secret names match exactly (case-sensitive)

### Issue: JWT tokens invalid
**Solution**: Ensure JWT_SECRET_KEY is minimum 32 characters

### Issue: Database connection fails
**Solution**: Check LANGFUSE_DB_PASSWORD matches your PostgreSQL configuration

### Issue: Container registry push fails
**Solution**: Verify workflow permissions include "write" access to packages

## 📚 Related Documentation

- [GitHub Actions Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [JWT Secret Key Best Practices](https://auth0.com/blog/a-look-at-the-latest-draft-for-jwt-bcp/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/auth-pg-hba-conf.html)

## 🆘 Support

If you encounter issues:
1. Check the [troubleshooting section](#-troubleshooting) above
2. Review CI/CD pipeline logs for specific error messages
3. Ensure all required secrets are properly configured
4. Verify secret values don't contain special characters that need escaping

---

✅ **After completing this setup, your CI/CD pipeline will have full access to required secrets for authentication, database connections, and container registry operations.**