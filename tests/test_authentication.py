#!/usr/bin/env python3
"""
Test suite for Authentication Service
"""

import pytest
import pytest_asyncio
import asyncio
import httpx
from jose import jwt
from datetime import datetime, timedelta
import json
import os

# Test configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8005")
TEST_JWT_SECRET = "test-secret-key"
TEST_JWT_ALGORITHM = "HS256"

@pytest_asyncio.fixture
async def async_client():
    """Create an async HTTP client"""
    async with httpx.AsyncClient() as client:
        yield client

@pytest_asyncio.fixture
async def test_user():
    """Create a test user"""
    return {
        "username": f"testuser_{datetime.now().timestamp()}",
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }

@pytest_asyncio.fixture
async def admin_token(async_client):
    """Get admin authentication token"""
    response = await async_client.post(
        f"{AUTH_SERVICE_URL}/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

class TestUserRegistration:
    """Test user registration functionality"""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, async_client, test_user):
        """Test registering a new user"""
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]
        assert data["role"] == "user"
        assert data["is_active"] is True
        assert data["is_verified"] is False
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, async_client, test_user):
        """Test registering with duplicate username"""
        # Register first time
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        # Try to register again with same username
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client):
        """Test registering with invalid email"""
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "TestPassword123!"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_register_weak_password(self, async_client):
        """Test registering with weak password"""
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 422  # Validation error

class TestAuthentication:
    """Test authentication functionality"""
    
    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, async_client, test_user):
        """Test login with valid credentials"""
        # Register user first
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        # Login
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == test_user["username"]
        assert data["role"] == "user"
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client, test_user):
        """Test login with invalid password"""
        # Register user first
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        # Try to login with wrong password
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client):
        """Test login with non-existent user"""
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": "nonexistentuser",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, async_client, test_user):
        """Test refreshing access token"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Use refresh token to get new access token
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        new_tokens = response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]

class TestAuthorization:
    """Test authorization functionality"""
    
    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_token(self, async_client, test_user):
        """Test accessing protected endpoint with valid token"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = await async_client.get(
            f"{AUTH_SERVICE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user["username"]
        assert data["email"] == test_user["email"]
    
    @pytest.mark.asyncio
    async def test_access_protected_endpoint_without_token(self, async_client):
        """Test accessing protected endpoint without token"""
        response = await async_client.get(f"{AUTH_SERVICE_URL}/auth/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_access_protected_endpoint_with_invalid_token(self, async_client):
        """Test accessing protected endpoint with invalid token"""
        response = await async_client.get(
            f"{AUTH_SERVICE_URL}/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_logout(self, async_client, test_user):
        """Test logout functionality"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Logout
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

class TestApiKeys:
    """Test API key functionality"""
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, async_client, test_user):
        """Test creating an API key"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Create API key
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/api-keys",
            json={
                "name": "Test API Key",
                "permissions": ["tasks.read", "tasks.create"],
                "expires_in_days": 30
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["name"] == "Test API Key"
        assert data["permissions"] == ["tasks.read", "tasks.create"]
        assert data["api_key"].startswith("vllm_")
    
    @pytest.mark.asyncio
    async def test_list_api_keys(self, async_client, test_user):
        """Test listing user's API keys"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Create an API key
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/api-keys",
            json={"name": "Test Key", "permissions": []},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # List API keys
        response = await async_client.get(
            f"{AUTH_SERVICE_URL}/auth/api-keys",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_keys" in data
        assert len(data["api_keys"]) > 0
    
    @pytest.mark.asyncio
    async def test_revoke_api_key(self, async_client, test_user):
        """Test revoking an API key"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Create an API key
        create_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/api-keys",
            json={"name": "Test Key", "permissions": []},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        key_id = create_response.json()["key_id"]
        
        # Revoke the API key
        response = await async_client.delete(
            f"{AUTH_SERVICE_URL}/auth/api-keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "revoked successfully" in response.json()["message"]

class TestPasswordManagement:
    """Test password management functionality"""
    
    @pytest.mark.asyncio
    async def test_change_password(self, async_client, test_user):
        """Test changing user password"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Change password
        new_password = "NewPassword123!"
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/change-password",
            json={
                "current_password": test_user["password"],
                "new_password": new_password
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Password changed successfully" in response.json()["message"]
        
        # Try to login with new password
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": new_password
            }
        )
        
        assert login_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, async_client, test_user):
        """Test changing password with wrong current password"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Try to change password with wrong current password
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewPassword123!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "Current password is incorrect" in response.json()["detail"]

class TestPermissions:
    """Test permission checking functionality"""
    
    @pytest.mark.asyncio
    async def test_check_permission_user_role(self, async_client, test_user):
        """Test permission checking for user role"""
        # Register and login
        await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/register",
            json=test_user
        )
        
        login_response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Check allowed permission
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/verify-permission",
            json={"permission": "tasks.read"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["has_permission"] is True
        
        # Check denied permission
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/verify-permission",
            json={"permission": "admin.delete"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["has_permission"] is False
    
    @pytest.mark.asyncio
    async def test_check_permission_admin_role(self, async_client, admin_token):
        """Test permission checking for admin role"""
        if not admin_token:
            pytest.skip("Admin token not available")
        
        # Check any permission (admin has all)
        response = await async_client.post(
            f"{AUTH_SERVICE_URL}/auth/verify-permission",
            json={"permission": "admin.delete"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["has_permission"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])