"""
vLLM Local Swarm Authentication Package

Enterprise-grade authentication system with JWT + API key support,
role-based access control, and comprehensive security features.
"""

__version__ = "1.0.0"
__author__ = "vLLM Local Swarm Team"

# Import core authentication components
from .auth_service import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_password,
    get_password_hash,
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
)

from .middleware import (
    AuthConfig,
    AuthenticationMiddleware,
    RateLimitMiddleware,
    require_auth,
    get_current_user,
)

__all__ = [
    # Authentication service functions
    "create_access_token",
    "create_refresh_token", 
    "verify_token",
    "verify_password",
    "get_password_hash",
    
    # Models
    "UserRegisterRequest",
    "UserLoginRequest", 
    "TokenResponse",
    "UserResponse",
    "ApiKeyCreateRequest",
    "ApiKeyResponse",
    
    # Middleware components
    "AuthConfig",
    "AuthenticationMiddleware",
    "RateLimitMiddleware",
    "require_auth",
    "get_current_user",
]