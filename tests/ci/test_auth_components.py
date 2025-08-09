import pytest
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from auth.auth_service import create_access_token, verify_password, get_password_hash
from auth.middleware import AuthConfig

def test_authentication_imports():
    """Test that all authentication components can be imported."""
    assert create_access_token is not None
    assert verify_password is not None
    assert get_password_hash is not None
    assert AuthConfig is not None

def test_jwt_token_creation():
    """Test JWT token creation functionality."""
    token = create_access_token({'user_id': 'test_user', 'username': 'test'})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are typically longer

def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123\!"
    hashed = get_password_hash(password)
    assert hashed is not None
    assert hashed \!= password  # Should be hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_auth_config_creation():
    """Test authentication configuration creation."""
    config = AuthConfig(
        auth_service_url="http://localhost:8005",
        jwt_secret_key="test-secret-key",
        required_permissions=["test.read"]
    )
    assert config is not None
    assert config.auth_service_url == "http://localhost:8005"
    assert config.jwt_secret_key == "test-secret-key"
    assert "test.read" in config.required_permissions

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
EOF < /dev/null
