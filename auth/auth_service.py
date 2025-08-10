#!/usr/bin/env python3
"""
Authentication Service for vLLM Local Swarm

Provides JWT-based authentication and authorization for all swarm services.
"""

import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

import redis.asyncio as redis
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
AUTH_PORT = int(os.getenv("AUTH_PORT", "8005"))
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://langfuse:langfuse123@langfuse-db:5432/auth"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
REFRESH_TOKEN_EXPIRATION_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=lambda: secrets.token_urlsafe(16))
    key = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    permissions = Column(Text)  # JSON array of permissions
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)


# FastAPI app
app = FastAPI(title="Authentication Service", version="1.0.0")
security = HTTPBearer()

# Redis client for session/token management
redis_client = None

# Database session
async_engine = None
AsyncSessionLocal = None


# Request/Response models
class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    role: str


class ApiKeyCreateRequest(BaseModel):
    name: str
    permissions: List[str] = []
    expires_in_days: Optional[int] = None


class ApiKeyResponse(BaseModel):
    api_key: str
    key_id: str
    name: str
    permissions: List[str]
    expires_at: Optional[str] = None
    created_at: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: str
    last_login: Optional[str]


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class PermissionCheckRequest(BaseModel):
    permission: str
    resource: Optional[str] = None


# Dependency functions
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Verify and decode a JWT token"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Check if token is blacklisted
        if redis_client:
            is_blacklisted = await redis_client.get(f"blacklist:{token}")
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


async def verify_api_key(api_key: str = Header(alias="X-API-Key")) -> dict:
    """Verify an API key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
        )

    async with AsyncSessionLocal() as db:
        # Hash the API key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        result = await db.execute(
            "SELECT * FROM api_keys WHERE key = :key AND is_active = true",
            {"key": key_hash},
        )
        api_key_record = result.first()

        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
            )

        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired"
            )

        # Update last used timestamp
        await db.execute(
            "UPDATE api_keys SET last_used = :now WHERE id = :id",
            {"now": datetime.utcnow(), "id": api_key_record.id},
        )
        await db.commit()

        return {
            "key_id": api_key_record.id,
            "user_id": api_key_record.user_id,
            "permissions": json.loads(api_key_record.permissions or "[]"),
        }


def check_permission(required_permission: str, user_permissions: List[str]) -> bool:
    """Check if a user has a required permission"""
    # Check for exact match or wildcard permissions
    for perm in user_permissions:
        if perm == required_permission or perm == "*":
            return True
        # Check for partial wildcard (e.g., "tasks.*" matches "tasks.create")
        if perm.endswith(".*"):
            prefix = perm[:-2]
            if required_permission.startswith(prefix):
                return True
    return False


# API Endpoints


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global redis_client, async_engine, AsyncSessionLocal

    try:
        # Initialize Redis
        redis_client = await redis.from_url(REDIS_URL)
        logger.info("Redis client initialized")

        # Initialize database
        async_engine = create_async_engine(DATABASE_URL, echo=False)
        AsyncSessionLocal = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized")

        # Create default admin user if not exists
        async with AsyncSessionLocal() as db:
            result = await db.execute("SELECT * FROM users WHERE username = 'admin'")
            if not result.first():
                admin_user = User(
                    username="admin",
                    email="admin@vllm-swarm.local",
                    password_hash=get_password_hash("admin123"),
                    full_name="System Administrator",
                    role="admin",
                    is_active=True,
                    is_verified=True,
                )
                db.add(admin_user)
                await db.commit()
                logger.info("Default admin user created")

    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    if async_engine:
        await async_engine.dispose()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "authentication",
    }


@app.post("/auth/register", response_model=UserResponse)
async def register(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    # Check if username or email already exists
    result = await db.execute(
        "SELECT * FROM users WHERE username = :username OR email = :email",
        {"username": request.username, "email": request.email},
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    # Create new user
    user = User(
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        full_name=request.full_name,
        role="user",
        is_active=True,
        is_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and receive JWT tokens"""
    # Find user
    result = await db.execute(
        "SELECT * FROM users WHERE username = :username", {"username": request.username}
    )
    user = result.first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    # Update last login
    await db.execute(
        "UPDATE users SET last_login = :now WHERE id = :id",
        {"now": datetime.utcnow(), "id": user.id},
    )
    await db.commit()

    # Create tokens
    token_data = {"sub": user.id, "username": user.username, "role": user.role}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token in Redis
    if redis_client:
        await redis_client.setex(
            f"refresh:{user.id}:{refresh_token[:10]}",
            timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS),
            refresh_token,
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=JWT_EXPIRATION_HOURS * 3600,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@app.post("/auth/logout")
async def logout(token_data: dict = Depends(verify_token)):
    """Logout and invalidate token"""
    # Add token to blacklist
    if redis_client:
        token = token_data.get("token")
        if token:
            # Calculate remaining TTL
            exp = token_data.get("exp")
            if exp:
                ttl = exp - datetime.utcnow().timestamp()
                if ttl > 0:
                    await redis_client.setex(f"blacklist:{token}", int(ttl), "1")

    return {"message": "Logged out successfully"}


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token"""
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

        user_id = payload.get("sub")

        # Verify refresh token in Redis
        if redis_client:
            stored_token = await redis_client.get(
                f"refresh:{user_id}:{refresh_token[:10]}"
            )
            if not stored_token or stored_token.decode() != refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

        # Get user
        result = await db.execute(
            "SELECT * FROM users WHERE id = :id AND is_active = true", {"id": user_id}
        )
        user = result.first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Create new tokens
        token_data = {"sub": user.id, "username": user.username, "role": user.role}

        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        # Update refresh token in Redis
        if redis_client:
            # Delete old refresh token
            await redis_client.delete(f"refresh:{user_id}:{refresh_token[:10]}")
            # Store new refresh token
            await redis_client.setex(
                f"refresh:{user_id}:{new_refresh_token[:10]}",
                timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS),
                new_refresh_token,
            )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user_id=user.id,
            username=user.username,
            role=user.role,
        )

    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user(
    token_data: dict = Depends(verify_token), db: AsyncSession = Depends(get_db)
):
    """Get current user information"""
    user_id = token_data.get("sub")

    result = await db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@app.post("/auth/change-password")
async def change_password(
    request: PasswordChangeRequest,
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    """Change user password"""
    user_id = token_data.get("sub")

    result = await db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not verify_password(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    new_hash = get_password_hash(request.new_password)
    await db.execute(
        "UPDATE users SET password_hash = :hash, updated_at = :now WHERE id = :id",
        {"hash": new_hash, "now": datetime.utcnow(), "id": user_id},
    )
    await db.commit()

    return {"message": "Password changed successfully"}


@app.post("/auth/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key"""
    user_id = token_data.get("sub")

    # Generate API key
    raw_key = f"vllm_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)

    # Create API key record
    api_key = ApiKey(
        key=key_hash,
        name=request.name,
        user_id=user_id,
        permissions=json.dumps(request.permissions),
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyResponse(
        api_key=raw_key,  # Return raw key only once
        key_id=api_key.id,
        name=api_key.name,
        permissions=request.permissions,
        expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
        created_at=api_key.created_at.isoformat(),
    )


@app.get("/auth/api-keys")
async def list_api_keys(
    token_data: dict = Depends(verify_token), db: AsyncSession = Depends(get_db)
):
    """List user's API keys"""
    user_id = token_data.get("sub")

    result = await db.execute(
        "SELECT * FROM api_keys WHERE user_id = :user_id AND is_active = true",
        {"user_id": user_id},
    )
    keys = result.fetchall()

    return {
        "api_keys": [
            {
                "key_id": key.id,
                "name": key.name,
                "permissions": json.loads(key.permissions or "[]"),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "created_at": key.created_at.isoformat(),
                "last_used": key.last_used.isoformat() if key.last_used else None,
            }
            for key in keys
        ]
    }


@app.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    token_data: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key"""
    user_id = token_data.get("sub")

    result = await db.execute(
        "UPDATE api_keys SET is_active = false WHERE id = :id AND user_id = :user_id",
        {"id": key_id, "user_id": user_id},
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await db.commit()

    return {"message": "API key revoked successfully"}


@app.post("/auth/verify-permission")
async def verify_permission(
    request: PermissionCheckRequest, token_data: dict = Depends(verify_token)
):
    """Check if user has a specific permission"""
    role = token_data.get("role", "user")

    # Define role-based permissions
    role_permissions = {
        "admin": ["*"],  # Admin has all permissions
        "user": [
            "tasks.create",
            "tasks.read",
            "tasks.update",
            "memory.read",
            "memory.write",
            "agents.query",
        ],
        "viewer": ["tasks.read", "memory.read"],
    }

    permissions = role_permissions.get(role, [])
    has_permission = check_permission(request.permission, permissions)

    return {
        "has_permission": has_permission,
        "permission": request.permission,
        "role": role,
    }


if __name__ == "__main__":
    logger.info(f"Starting Authentication Service on port {AUTH_PORT}")
    logger.info(f"Database: {DATABASE_URL}")
    logger.info(f"Redis: {REDIS_URL}")

    uvicorn.run(
        app,
        host="0.0.0.0",  # nosec B104 - Required for containerized service
        port=AUTH_PORT,
        log_level="info",
    )
