#!/usr/bin/env python3
"""
Generate secure secrets for vLLM Local Swarm environments
"""
import secrets
import string
import base64

def generate_jwt_secret(length=64):
    """Generate JWT secret key"""
    return secrets.token_urlsafe(length)

def generate_api_key(prefix="sk", length=48):
    """Generate API key with prefix"""
    return f"{prefix}-{secrets.token_urlsafe(length)}"

def generate_password(length=32):
    """Generate secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_hex_key(length=64):
    """Generate hex encryption key"""
    return secrets.token_hex(length)

def generate_langfuse_encryption_key():
    """Generate Langfuse-compatible 64-character hex key"""
    return secrets.token_hex(32)  # 32 bytes = 64 hex chars

if __name__ == "__main__":
    print("=== vLLM Local Swarm Secret Generator ===\n")
    
    print("DEVELOPMENT SECRETS:")
    print(f"DEV_JWT_SECRET_KEY: {generate_jwt_secret(32)}")
    print(f"DEV_API_SECRET_KEY: {generate_api_key('dev', 32)}")
    print(f"DEV_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("STAGING SECRETS:")
    print(f"STAGING_JWT_SECRET_KEY: {generate_jwt_secret(48)}")
    print(f"STAGING_API_SECRET_KEY: {generate_api_key('staging', 48)}")
    print(f"STAGING_REDIS_PASSWORD: {generate_password(32)}")
    print(f"STAGING_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("PRODUCTION SECRETS:")
    print(f"PROD_JWT_SECRET_KEY: {generate_jwt_secret(64)}")
    print(f"PROD_API_SECRET_KEY: {generate_api_key('prod', 64)}")
    print(f"PROD_REDIS_PASSWORD: {generate_password(64)}")
    print(f"PROD_DB_ENCRYPTION_KEY: {generate_hex_key(32)}")
    print(f"PROD_ENCRYPTION_KEY: {generate_hex_key(64)}")
    print(f"PROD_LANGFUSE_ENCRYPTION_KEY: {generate_langfuse_encryption_key()}")
    print()
    
    print("NOTE: Store these secrets securely and never commit to version control!")