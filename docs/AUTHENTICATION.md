# 🔐 Authentication System Documentation

## Overview

The vLLM Local Swarm features an **enterprise-grade authentication system** with comprehensive security controls. The system provides dual authentication mechanisms (JWT + API keys), role-based access control, session management, and audit logging for all swarm services.

### ✅ Recent Updates & Fixes
- **Fixed ray version compatibility** (updated to ray[default]>=2.47.0)
- **Resolved Docker Compose warnings** (removed obsolete version fields)
- **Enhanced make commands** with comprehensive authentication targets
- **Improved error handling** in development setup
- **Package versions compliance** (all dependencies use n/n-1/n-2 versions)

## Architecture

### Components

1. **Authentication Service** (`auth-service`)
   - JWT token generation and validation
   - User registration and management
   - API key management
   - Permission verification
   - Session management

2. **Authentication Middleware**
   - FastAPI middleware for service integration
   - Token verification
   - Permission checking
   - Rate limiting

3. **Database**
   - PostgreSQL for user and API key storage
   - Redis for session management and token blacklisting

4. **Nginx Reverse Proxy** (optional)
   - Centralized authentication gateway
   - Rate limiting
   - SSL termination

## 🚀 Quick Start

### 1. Complete Setup with Make Commands

```bash
# Setup development environment
make dev-setup

# Deploy authentication system
make dev-start

# Create admin user and demo accounts  
make auth-setup

# Test the authentication system
make auth-demo

# Check authentication health
make auth-health
```

### 2. Manual User Registration

```bash
curl -X POST http://localhost:8005/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
```

### 3. Login

```bash
curl -X POST http://localhost:8005/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePassword123!"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user_id": "user_123",
  "username": "john_doe",
  "role": "user"
}
```

### 4. Use the Token

```bash
# Access protected endpoint
curl -X GET http://localhost:8006/tasks \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Authentication Methods

### 1. JWT Tokens

JWT tokens are the primary authentication method for interactive sessions.

**Advantages:**
- Stateless authentication
- Short-lived (24 hours default)
- Can be refreshed
- Contains user information and role

**Usage:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 2. API Keys

API keys are for programmatic access and long-term integrations.

**Create API Key:**
```bash
curl -X POST http://localhost:8005/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "permissions": ["tasks.create", "tasks.read"],
    "expires_in_days": 90
  }'
```

**Usage:**
```http
X-API-Key: vllm_a1b2c3d4e5f6...
```

## User Roles and Permissions

### Roles

1. **admin** - Full system access
2. **user** - Standard access to own resources
3. **viewer** - Read-only access

### Permissions

| Permission | Description | Default Roles |
|------------|-------------|---------------|
| `*` | All permissions | admin |
| `tasks.create` | Create new tasks | admin, user |
| `tasks.read` | View tasks | admin, user, viewer |
| `tasks.update` | Update tasks | admin, user |
| `tasks.delete` | Delete tasks | admin, user |
| `memory.read` | Read memory data | admin, user, viewer |
| `memory.write` | Write memory data | admin, user |
| `agents.query` | Query agents | admin, user |
| `stats.read` | View statistics | admin, user |

## 🔧 Make Commands Reference

### Authentication Deployment
```bash
make auth-deploy       # Deploy complete authentication system
make auth-test         # Run comprehensive authentication tests  
make auth-setup        # Setup admin user and test accounts
make auth-health       # Check authentication service health
make auth-logs         # View authentication service logs
make auth-reset        # Reset authentication (DEV ONLY)
make auth-demo         # Run authentication demo flow
```

### Development Commands
```bash
make dev-setup         # Complete development environment setup
make dev-start         # Start development environment with auth
make prod-start        # Production-ready deployment with full auth
make install-deps      # Install all development dependencies
```

### Security & Testing
```bash
make test-security     # Run security scans (bandit, safety)
make lint-security     # Lint for security issues
make audit-permissions # Audit user permissions
make rotate-secrets    # Rotate JWT secrets (PRODUCTION)
make test-auth         # Run authentication unit tests
make test-integration  # Run integration tests with auth
make test-load         # Run load tests with authentication
```

### Service Management
```bash
make up-auth-stack     # Start authentication + dependencies
make up-ai-stack       # Start AI/ML services (vLLM, orchestrator)
make up-full-stack     # Start everything (auth + AI + monitoring)
make health-check      # Check all service health
make health-auth       # Check authentication services only
make compose-logs      # View logs from all services
```

### Utility Commands
```bash
make stats             # Show system statistics
make auth-stats        # Show authentication statistics  
make performance-stats # Show performance metrics
make resource-usage    # Show resource utilization
make cleanup           # Clean up old resources
```

### Environment Variables
Set these in your `.env` file or environment:
```bash
AUTH_MODE=enabled              # Enable authentication (default)
JWT_SECRET_KEY=your-secret-key # JWT secret (auto-generated if not set)
DATABASE_URL=postgresql://...  # PostgreSQL connection string
REDIS_URL=redis://localhost:6379 # Redis connection string
PROFILES=proxy,webui           # Docker compose profiles to activate
```

## API Reference

### Authentication Endpoints

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "string",
  "email": "email@example.com",
  "password": "string (min 8 chars)",
  "full_name": "string (optional)"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "string"
}
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer TOKEN
```

#### Get Current User
```http
GET /auth/me
Authorization: Bearer TOKEN
```

#### Change Password
```http
POST /auth/change-password
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "current_password": "string",
  "new_password": "string (min 8 chars)"
}
```

### API Key Management

#### Create API Key
```http
POST /auth/api-keys
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "name": "string",
  "permissions": ["string"],
  "expires_in_days": 30
}
```

#### List API Keys
```http
GET /auth/api-keys
Authorization: Bearer TOKEN
```

#### Revoke API Key
```http
DELETE /auth/api-keys/{key_id}
Authorization: Bearer TOKEN
```

### Permission Verification

#### Check Permission
```http
POST /auth/verify-permission
Authorization: Bearer TOKEN
Content-Type: application/json

{
  "permission": "string",
  "resource": "string (optional)"
}
```

## Integration Guide

### Adding Authentication to a Service

1. **Install Dependencies:**
```bash
pip install fastapi httpx pyjwt
```

2. **Add Middleware:**
```python
from auth.middleware import AuthenticationMiddleware, AuthConfig

app = FastAPI()

auth_config = AuthConfig(
    auth_service_url="http://auth-service:8005",
    jwt_secret_key=os.getenv("JWT_SECRET_KEY"),
    required_permissions=["tasks.create"]
)

app.add_middleware(AuthenticationMiddleware, config=auth_config)
```

3. **Protect Endpoints:**
```python
from auth.middleware import require_auth, get_current_user

@app.get("/protected")
@require_auth(["tasks.read"])
async def protected_endpoint(request: Request):
    user = get_current_user(request)
    return {"message": f"Hello {user['username']}"}
```

### Client Libraries

#### Python Client
```python
import httpx

class AuthClient:
    def __init__(self, base_url="http://localhost:8005"):
        self.base_url = base_url
        self.token = None
    
    async def login(self, username, password):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                return data
            raise Exception(f"Login failed: {response.text}")
    
    async def make_request(self, method, path, **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                **kwargs
            )
            return response
```

#### JavaScript Client
```javascript
class AuthClient {
    constructor(baseUrl = "http://localhost:8005") {
        this.baseUrl = baseUrl;
        this.token = null;
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username, password})
        });
        
        if (response.ok) {
            const data = await response.json();
            this.token = data.access_token;
            return data;
        }
        throw new Error(`Login failed: ${response.statusText}`);
    }
    
    async makeRequest(method, path, options = {}) {
        const headers = options.headers || {};
        if (this.token) {
            headers.Authorization = `Bearer ${this.token}`;
        }
        
        return fetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            ...options
        });
    }
}
```

## Security Best Practices

### 1. Environment Variables

Always use environment variables for sensitive configuration:

```bash
# .env file
JWT_SECRET_KEY=your-very-secure-secret-key-change-this
LANGFUSE_DB_PASSWORD=strong-database-password
REDIS_PASSWORD=redis-password
```

### 2. Token Security

- **Never log tokens** in production
- **Use HTTPS** in production to prevent token interception
- **Set appropriate expiration times** (24 hours for access, 30 days for refresh)
- **Implement token rotation** for refresh tokens

### 3. Password Requirements

Enforce strong password requirements:
- Minimum 8 characters
- Mix of uppercase, lowercase, numbers, and special characters
- Password history to prevent reuse
- Account lockout after failed attempts

### 4. Rate Limiting

Implement rate limiting for authentication endpoints:
- Login: 5 attempts per minute
- Registration: 3 per hour
- API calls: Based on user tier

### 5. API Key Management

- **Hash API keys** before storing in database
- **Show full key only once** during creation
- **Implement key rotation** policies
- **Audit key usage** regularly

## Monitoring and Logging

### Metrics to Monitor

1. **Authentication Metrics**
   - Login success/failure rates
   - Token refresh rates
   - API key usage

2. **Security Metrics**
   - Failed authentication attempts
   - Suspicious activity patterns
   - Rate limit violations

3. **Performance Metrics**
   - Authentication service response time
   - Database query performance
   - Redis cache hit rates

### Log Events

Important events to log:
- User registration
- Login attempts (success/failure)
- Password changes
- API key creation/revocation
- Permission denials
- Token blacklisting

## Troubleshooting

### Common Issues

#### 1. "Invalid token" Error
**Cause:** Token expired or malformed
**Solution:** Refresh the token or login again

#### 2. "Permission denied" Error
**Cause:** User lacks required permissions
**Solution:** Check user role and permissions, contact admin if needed

#### 3. "Rate limit exceeded" Error
**Cause:** Too many requests in short time
**Solution:** Wait and retry, implement exponential backoff

#### 4. Database Connection Error
**Cause:** PostgreSQL not running or misconfigured
**Solution:** Check database connection string and ensure database is running

### Debug Mode

Enable debug logging for troubleshooting:

```python
# In auth_service.py
logging.basicConfig(level=logging.DEBUG)
```

## Migration Guide

### From No Authentication to Authentication

1. **Deploy authentication service**
2. **Create admin user**
3. **Migrate existing users** (if any)
4. **Update service configurations** to include auth middleware
5. **Update client applications** to handle authentication
6. **Test thoroughly** in staging environment
7. **Deploy to production** with monitoring

### Upgrading Authentication Service

1. **Backup database** before upgrade
2. **Test upgrade** in staging environment
3. **Run database migrations** if needed
4. **Update environment variables** for new features
5. **Deploy new version** with zero-downtime strategy
6. **Monitor for issues** after deployment

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_PORT` | Authentication service port | 8005 |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://... |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `JWT_SECRET_KEY` | Secret key for JWT signing | (generated) |
| `JWT_ALGORITHM` | JWT signing algorithm | HS256 |
| `JWT_EXPIRATION_HOURS` | Access token expiration | 24 |
| `REFRESH_TOKEN_EXPIRATION_DAYS` | Refresh token expiration | 30 |

### Docker Compose Profiles

- **Default**: Basic services without authentication
- **auth**: Services with authentication enabled
- **auth-full**: All services with authentication
- **auth-proxy**: Nginx reverse proxy with authentication

## Support

For issues or questions about the authentication system:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review logs: `docker-compose logs auth-service`
3. Open an issue on GitHub
4. Contact the development team

## License

The authentication system is part of the vLLM Local Swarm project and follows the same license terms.