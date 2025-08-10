"""
Authentication Middleware for vLLM Local Swarm Services

Provides authentication and authorization middleware for FastAPI applications.
"""

import logging
from functools import wraps
from typing import Callable, List, Optional

import httpx
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthConfig:
    """Configuration for authentication middleware"""

    def __init__(
        self,
        auth_service_url: str = "http://auth-service:8005",
        jwt_secret_key: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        required_permissions: Optional[List[str]] = None,
        allow_anonymous: bool = False,
        api_key_header: str = "X-API-Key",
    ):
        self.auth_service_url = auth_service_url
        self.jwt_secret_key = jwt_secret_key
        self.jwt_algorithm = jwt_algorithm
        self.required_permissions = required_permissions or []
        self.allow_anonymous = allow_anonymous
        self.api_key_header = api_key_header


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authenticating requests using JWT tokens or API keys
    """

    def __init__(self, app, config: AuthConfig):
        super().__init__(app)
        self.config = config
        self.security = HTTPBearer(auto_error=False)

        # Paths that don't require authentication
        self.public_paths = {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/auth/login",
            "/auth/register",
        }

    async def dispatch(self, request: Request, call_next):
        """Process each request for authentication"""

        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Allow anonymous access if configured
        if self.config.allow_anonymous:
            return await call_next(request)

        try:
            # Try to authenticate the request
            auth_info = await self.authenticate_request(request)

            if not auth_info:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication required"},
                )

            # Add auth info to request state
            request.state.auth = auth_info

            # Check permissions if required
            if self.config.required_permissions:
                if not await self.check_permissions(
                    auth_info, self.config.required_permissions
                ):
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "Insufficient permissions"},
                    )

            # Continue processing the request
            response = await call_next(request)
            return response

        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.error(f"Authentication middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )

    async def authenticate_request(self, request: Request) -> Optional[dict]:
        """Authenticate a request using JWT or API key"""

        # Try JWT authentication first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            auth_info = await self.verify_jwt_token(token)
            if auth_info:
                return auth_info

        # Try API key authentication
        api_key = request.headers.get(self.config.api_key_header)
        if api_key:
            auth_info = await self.verify_api_key(api_key)
            if auth_info:
                return auth_info

        return None

    async def verify_jwt_token(self, token: str) -> Optional[dict]:
        """Verify a JWT token"""

        # If we have the secret key, verify locally
        if self.config.jwt_secret_key:
            try:
                payload = jwt.decode(
                    token,
                    self.config.jwt_secret_key,
                    algorithms=[self.config.jwt_algorithm],
                )
                return {
                    "type": "jwt",
                    "user_id": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role"),
                    "token": token,
                }
            except jwt.ExpiredSignatureError:
                logger.warning("Expired JWT token")
                return None
            except jwt.JWTError as e:
                logger.warning(f"Invalid JWT token: {e}")
                return None

        # Otherwise, verify with auth service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.auth_service_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "type": "jwt",
                        "user_id": user_data.get("id"),
                        "username": user_data.get("username"),
                        "role": user_data.get("role"),
                        "token": token,
                    }
        except Exception as e:
            logger.error(f"Error verifying token with auth service: {e}")

        return None

    async def verify_api_key(self, api_key: str) -> Optional[dict]:
        """Verify an API key with the auth service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.auth_service_url}/auth/verify-api-key",
                    headers={self.config.api_key_header: api_key},
                )

                if response.status_code == 200:
                    key_data = response.json()
                    return {
                        "type": "api_key",
                        "key_id": key_data.get("key_id"),
                        "user_id": key_data.get("user_id"),
                        "permissions": key_data.get("permissions", []),
                    }
        except Exception as e:
            logger.error(f"Error verifying API key: {e}")

        return None

    async def check_permissions(
        self, auth_info: dict, required_permissions: List[str]
    ) -> bool:
        """Check if the authenticated user has required permissions"""

        # Admin role has all permissions
        if auth_info.get("role") == "admin":
            return True

        # For API keys, check stored permissions
        if auth_info.get("type") == "api_key":
            user_permissions = auth_info.get("permissions", [])
            return any(
                self.has_permission(perm, user_permissions)
                for perm in required_permissions
            )

        # For JWT tokens, check with auth service
        if auth_info.get("type") == "jwt":
            try:
                async with httpx.AsyncClient() as client:
                    for permission in required_permissions:
                        response = await client.post(
                            f"{self.config.auth_service_url}/auth/verify-permission",
                            json={"permission": permission},
                            headers={
                                "Authorization": f"Bearer {auth_info.get('token')}"
                            },
                        )

                        if response.status_code == 200:
                            result = response.json()
                            if result.get("has_permission"):
                                return True
            except Exception as e:
                logger.error(f"Error checking permissions: {e}")

        return False

    def has_permission(self, required: str, user_permissions: List[str]) -> bool:
        """Check if a required permission is in user permissions"""
        for perm in user_permissions:
            if perm == required or perm == "*":
                return True
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if required.startswith(prefix):
                    return True
        return False


def require_auth(permissions: Optional[List[str]] = None):
    """
    Decorator for protecting individual endpoints

    Usage:
        @app.get("/protected")
        @require_auth(["tasks.read"])
        async def protected_endpoint(request: Request):
            auth_info = request.state.auth
            return {"user": auth_info.get("username")}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Check if auth info exists in request state
            if not hasattr(request.state, "auth") or not request.state.auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check permissions if specified
            if permissions:
                auth_info = request.state.auth
                has_permission = False

                # Check each required permission
                for permission in permissions:
                    if auth_info.get("role") == "admin":
                        has_permission = True
                        break

                    user_permissions = auth_info.get("permissions", [])
                    if any(
                        p == permission
                        or p == "*"
                        or (p.endswith(".*") and permission.startswith(p[:-2]))
                        for p in user_permissions
                    ):
                        has_permission = True
                        break

                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions",
                    )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def get_current_user(request: Request) -> dict:
    """
    Helper function to get current authenticated user from request

    Usage:
        @app.get("/me")
        async def get_me(request: Request):
            user = get_current_user(request)
            return {"user": user}
    """
    if not hasattr(request.state, "auth") or not request.state.auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    return request.state.auth


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API endpoints
    """

    def __init__(
        self,
        app,
        redis_url: str = "redis://redis:6379",
        default_limit: int = 100,
        window_seconds: int = 60,
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.redis_client = None

    async def dispatch(self, request: Request, call_next):
        """Check rate limits for authenticated users"""

        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        # Get user identifier
        user_id = None
        if hasattr(request.state, "auth"):
            auth_info = request.state.auth
            user_id = auth_info.get("user_id") or auth_info.get("key_id")

        if not user_id:
            # Use IP address for unauthenticated requests
            user_id = request.client.host if request.client else "unknown"

        # Check rate limit
        if not await self.check_rate_limit(user_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
            )

        return await call_next(request)

    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        try:
            if not self.redis_client:
                import redis.asyncio as redis

                self.redis_client = await redis.from_url(self.redis_url)

            key = f"rate_limit:{user_id}"

            # Increment counter
            count = await self.redis_client.incr(key)

            # Set expiration on first request
            if count == 1:
                await self.redis_client.expire(key, self.window_seconds)

            return count <= self.default_limit

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Allow request if rate limiting fails
            return True
