import pytest
import sys
import os
import json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('.'))

# Import all authentication components for comprehensive testing
from auth.auth_service import (
    create_access_token, create_refresh_token, verify_password, get_password_hash,
    check_permission, UserRegisterRequest, UserLoginRequest, TokenResponse,
    UserResponse, ApiKeyCreateRequest, ApiKeyResponse, PasswordChangeRequest,
    PermissionCheckRequest
)
from auth.middleware import (
    AuthConfig, require_auth, get_current_user, 
    RateLimitMiddleware
)

def test_authentication_imports():
    """Test that all authentication components can be imported."""
    assert create_access_token is not None
    assert create_refresh_token is not None
    assert verify_password is not None
    assert get_password_hash is not None
    assert check_permission is not None
    assert AuthConfig is not None

def test_jwt_token_creation():
    """Test JWT token creation functionality."""
    test_data = {'user_id': 'test_user', 'username': 'test', 'role': 'user'}
    
    # Test access token
    access_token = create_access_token(test_data)
    assert access_token is not None
    assert isinstance(access_token, str)
    assert len(access_token) > 50  # JWT tokens are typically longer
    
    # Test refresh token
    refresh_token = create_refresh_token(test_data)
    assert refresh_token is not None
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 50
    
    # Tokens should be different
    assert access_token != refresh_token

def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123!"
    hashed = get_password_hash(password)
    assert hashed is not None
    assert hashed != password  # Should be hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_permission_system():
    """Test permission checking functionality."""
    # Test exact permission match
    assert check_permission("tasks.read", ["tasks.read", "tasks.write"]) is True
    assert check_permission("tasks.delete", ["tasks.read", "tasks.write"]) is False
    
    # Test wildcard permissions
    assert check_permission("tasks.read", ["*"]) is True
    assert check_permission("anything", ["*"]) is True
    
    # Test partial wildcard
    assert check_permission("tasks.read", ["tasks.*"]) is True
    assert check_permission("tasks.write", ["tasks.*"]) is True
    assert check_permission("memory.read", ["tasks.*"]) is False

def test_auth_config_creation():
    """Test authentication configuration creation."""
    config = AuthConfig(
        auth_service_url="http://localhost:8005",
        jwt_secret_key="test-secret-key",
        required_permissions=["test.read"],
        allow_anonymous=False,
        api_key_header="X-API-Key"
    )
    assert config is not None
    assert config.auth_service_url == "http://localhost:8005"
    assert config.jwt_secret_key == "test-secret-key"
    assert "test.read" in config.required_permissions
    assert config.allow_anonymous is False
    assert config.api_key_header == "X-API-Key"

def test_pydantic_models():
    """Test that all Pydantic models can be instantiated."""
    # Test UserRegisterRequest
    user_reg = UserRegisterRequest(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        full_name="Test User"
    )
    assert user_reg.username == "testuser"
    assert user_reg.email == "test@example.com"
    
    # Test UserLoginRequest  
    user_login = UserLoginRequest(username="testuser", password="SecurePass123!")
    assert user_login.username == "testuser"
    
    # Test TokenResponse
    token_response = TokenResponse(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_type="bearer",
        expires_in=3600,
        user_id="user_123",
        username="testuser",
        role="user"
    )
    assert token_response.access_token == "test_access_token"
    assert token_response.expires_in == 3600
    
    # Test UserResponse
    user_response = UserResponse(
        id="user_123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        role="user",
        is_active=True,
        is_verified=False,
        created_at=datetime.utcnow().isoformat(),
        last_login=None
    )
    assert user_response.username == "testuser"
    assert user_response.is_active is True

def test_api_key_models():
    """Test API key related models."""
    # Test ApiKeyCreateRequest
    api_key_req = ApiKeyCreateRequest(
        name="test-key",
        permissions=["tasks.read", "tasks.write"],
        expires_in_days=30
    )
    assert api_key_req.name == "test-key"
    assert len(api_key_req.permissions) == 2
    assert api_key_req.expires_in_days == 30
    
    # Test ApiKeyResponse
    api_key_resp = ApiKeyResponse(
        api_key="vllm_test_key_12345",
        key_id="key_123",
        name="test-key",
        permissions=["tasks.read"],
        expires_at=None,
        created_at=datetime.utcnow().isoformat()
    )
    assert api_key_resp.api_key.startswith("vllm_")
    assert api_key_resp.name == "test-key"

def test_auth_validation_models():
    """Test authentication validation models."""
    # Test PasswordChangeRequest
    pwd_change = PasswordChangeRequest(
        current_password="OldPass123!",
        new_password="NewPass123!"
    )
    assert pwd_change.current_password == "OldPass123!"
    assert pwd_change.new_password == "NewPass123!"
    
    # Test PermissionCheckRequest
    perm_check = PermissionCheckRequest(
        permission="tasks.read",
        resource="task_123"
    )
    assert perm_check.permission == "tasks.read"
    assert perm_check.resource == "task_123"

def test_middleware_functionality():
    """Test middleware configuration and basic functionality."""
    # Test default configuration
    default_config = AuthConfig()
    assert default_config.auth_service_url == "http://auth-service:8005"
    assert default_config.jwt_algorithm == "HS256"
    assert default_config.allow_anonymous is False
    
    # Test custom configuration
    custom_config = AuthConfig(
        auth_service_url="http://custom-auth:8080",
        jwt_secret_key="custom-secret",
        required_permissions=["custom.read", "custom.write"],
        allow_anonymous=True
    )
    assert custom_config.auth_service_url == "http://custom-auth:8080"
    assert custom_config.jwt_secret_key == "custom-secret"
    assert len(custom_config.required_permissions) == 2
    assert custom_config.allow_anonymous is True

def test_comprehensive_coverage():
    """Test to ensure comprehensive coverage of authentication system."""
    # Test that we can import all expected components
    from auth import (
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
        AuthConfig,
        AuthenticationMiddleware,
        RateLimitMiddleware,
        require_auth,
        get_current_user,
    )
    
    # Verify all components are callable or instantiable
    assert callable(create_access_token)
    assert callable(create_refresh_token)
    assert callable(verify_password)
    assert callable(get_password_hash)
    assert callable(require_auth)
    assert callable(get_current_user)
    
    # Test JWT token with expiration
    token_data = {"sub": "user123", "username": "testuser", "role": "user"}
    custom_expiry = timedelta(hours=2)
    token_with_expiry = create_access_token(token_data, custom_expiry)
    assert token_with_expiry is not None
    assert isinstance(token_with_expiry, str)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
