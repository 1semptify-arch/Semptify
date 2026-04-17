"""
Advanced Rate Limiter - Intelligent API Throttling
===============================================

Advanced rate limiting with multiple strategies, user tiers, and adaptive throttling.
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import json
import hashlib
import threading

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

class UserTier(Enum):
    """User access tiers."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_window: int
    window_seconds: int
    burst_size: Optional[int] = None
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_per_window": self.requests_per_window,
            "window_seconds": self.window_seconds,
            "burst_size": self.burst_size,
            "strategy": self.strategy.value
        }

@dataclass
class RateLimitState:
    """Rate limit state for a client."""
    current_requests: int
    window_start: float
    last_request_time: float
    tokens: float
    last_refill_time: float
    violations: int = 0
    blocked_until: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_requests": self.current_requests,
            "window_start": self.window_start,
            "last_request_time": self.last_request_time,
            "tokens": self.tokens,
            "last_refill_time": self.last_refill_time,
            "violations": self.violations,
            "blocked_until": self.blocked_until
        }

class TokenBucketLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
    
    def is_allowed(self, state: RateLimitState, current_time: float) -> Tuple[bool, float]:
        """Check if request is allowed."""
        # Refill tokens
        time_passed = current_time - state.last_refill_time
        state.tokens = min(self.capacity, state.tokens + time_passed * self.refill_rate)
        state.last_refill_time = current_time
        
        if state.tokens >= 1:
            state.tokens -= 1
            return True, state.tokens
        else:
            return False, state.tokens

class SlidingWindowLimiter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, request_history: deque, current_time: float) -> Tuple[bool, deque]:
        """Check if request is allowed."""
        # Remove old requests outside the window
        cutoff_time = current_time - self.window_seconds
        
        while request_history and request_history[0] < cutoff_time:
            request_history.popleft()
        
        # Check if under limit
        if len(request_history) < self.max_requests:
            request_history.append(current_time)
            return True, request_history
        else:
            return False, request_history

class AdvancedRateLimiter:
    """Advanced rate limiting system."""
    
    def __init__(self):
        # Rate limit configurations by tier and endpoint type
        self.tier_configs: Dict[UserTier, Dict[str, RateLimitConfig]] = {
            UserTier.FREE: {
                "read": RateLimitConfig(100, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "write": RateLimitConfig(50, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "upload": RateLimitConfig(10, 60, strategy=RateLimitStrategy.TOKEN_BUCKET),
                "auth": RateLimitConfig(5, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "ai": RateLimitConfig(20, 60, strategy=RateLimitStrategy.TOKEN_BUCKET)
            },
            UserTier.BASIC: {
                "read": RateLimitConfig(500, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "write": RateLimitConfig(200, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "upload": RateLimitConfig(50, 60, strategy=RateLimitStrategy.TOKEN_BUCKET),
                "auth": RateLimitConfig(10, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "ai": RateLimitConfig(100, 60, strategy=RateLimitStrategy.TOKEN_BUCKET)
            },
            UserTier.PREMIUM: {
                "read": RateLimitConfig(2000, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "write": RateLimitConfig(1000, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "upload": RateLimitConfig(200, 60, strategy=RateLimitStrategy.TOKEN_BUCKET),
                "auth": RateLimitConfig(20, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "ai": RateLimitConfig(500, 60, strategy=RateLimitStrategy.TOKEN_BUCKET)
            },
            UserTier.ENTERPRISE: {
                "read": RateLimitConfig(10000, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "write": RateLimitConfig(5000, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "upload": RateLimitConfig(1000, 60, strategy=RateLimitStrategy.TOKEN_BUCKET),
                "auth": RateLimitConfig(100, 60, strategy=RateLimitStrategy.SLIDING_WINDOW),
                "ai": RateLimitConfig(2000, 60, strategy=RateLimitStrategy.TOKEN_BUCKET)
            }
        }
        
        # Client states
        self.client_states: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.sliding_windows: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        
        # Token bucket limiters
        self.token_buckets: Dict[str, TokenBucketLimiter] = {}
        
        # Violation tracking
        self.violations: Dict[str, List[float]] = defaultdict(list)
        
        # Adaptive throttling
        self.global_load_factor = 1.0
        self.endpoint_load_factors: Dict[str, float] = defaultdict(lambda: 1.0)
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "violations_by_tier": defaultdict(int),
            "violations_by_endpoint": defaultdict(int)
        }
    
    def get_user_tier(self, user_id: str) -> UserTier:
        """Get user tier (simplified for demo)."""
        # In a real system, this would check user subscription
        # For now, default to BASIC tier
        return UserTier.BASIC
    
    def classify_endpoint(self, method: str, path: str) -> str:
        """Classify endpoint type for rate limiting."""
        path_lower = path.lower()
        
        if method.upper() == "GET":
            return "read"
        elif method.upper() in ["POST", "PUT", "PATCH"]:
            if "upload" in path_lower or "file" in path_lower:
                return "upload"
            elif "auth" in path_lower or "login" in path_lower:
                return "auth"
            elif "ai" in path_lower or "copilot" in path_lower:
                return "ai"
            else:
                return "write"
        else:
            return "write"
    
    def get_client_key(self, user_id: str, ip_address: str, endpoint_type: str) -> str:
        """Generate client key for rate limiting."""
        key_data = f"{user_id}:{ip_address}:{endpoint_type}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def is_allowed(self, user_id: str, ip_address: str, method: str, path: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed."""
        with self.lock:
            self.stats["total_requests"] += 1
            
            # Get user tier
            tier = self.get_user_tier(user_id)
            
            # Classify endpoint
            endpoint_type = self.classify_endpoint(method, path)
            
            # Get rate limit config
            config = self.tier_configs[tier][endpoint_type]
            
            # Get client key
            client_key = self.get_client_key(user_id, ip_address, endpoint_type)
            
            # Check if client is blocked
            if self._is_client_blocked(client_key):
                self.stats["blocked_requests"] += 1
                return False, {
                    "allowed": False,
                    "reason": "client_blocked",
                    "retry_after": self._get_block_duration(client_key),
                    "tier": tier.value,
                    "endpoint_type": endpoint_type
                }
            
            # Apply rate limiting based on strategy
            allowed, details = self._apply_rate_limit(
                client_key, config, endpoint_type
            )
            
            if allowed:
                self.stats["allowed_requests"] += 1
                return True, {
                    "allowed": True,
                    "tier": tier.value,
                    "endpoint_type": endpoint_type,
                    "remaining": details.get("remaining", 0),
                    "reset_time": details.get("reset_time", 0)
                }
            else:
                self.stats["blocked_requests"] += 1
                self._record_violation(client_key, tier, endpoint_type)
                
                return False, {
                    "allowed": False,
                    "reason": "rate_limit_exceeded",
                    "retry_after": details.get("retry_after", 60),
                    "tier": tier.value,
                    "endpoint_type": endpoint_type,
                    "limit": config.requests_per_window,
                    "window": config.window_seconds
                }
    
    def _apply_rate_limit(self, client_key: str, config: RateLimitConfig, 
                         endpoint_type: str) -> Tuple[bool, Dict[str, Any]]:
        """Apply rate limiting based on strategy."""
        current_time = time.time()
        
        # Apply adaptive throttling
        effective_limit = int(config.requests_per_window * 
                              self.global_load_factor * 
                              self.endpoint_load_factors[endpoint_type])
        
        if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._sliding_window_check(client_key, effective_limit, 
                                             config.window_seconds, current_time)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._token_bucket_check(client_key, effective_limit, 
                                           config.window_seconds, current_time)
        else:
            # Default to sliding window
            return self._sliding_window_check(client_key, effective_limit, 
                                             config.window_seconds, current_time)
    
    def _sliding_window_check(self, client_key: str, max_requests: int, 
                              window_seconds: int, current_time: float) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limit check."""
        if client_key not in self.sliding_windows:
            self.sliding_windows[client_key] = defaultdict(deque)
        
        window = self.sliding_windows[client_key]["default"]
        
        # Remove old requests
        cutoff_time = current_time - window_seconds
        while window and window[0] < cutoff_time:
            window.popleft()
        
        # Check if under limit
        if len(window) < max_requests:
            window.append(current_time)
            return True, {
                "remaining": max_requests - len(window),
                "reset_time": current_time + window_seconds
            }
        else:
            # Calculate retry after
            oldest_request = window[0]
            retry_after = int(oldest_request + window_seconds - current_time)
            
            return False, {
                "retry_after": max(retry_after, 1),
                "window_start": oldest_request,
                "current_count": len(window)
            }
    
    def _token_bucket_check(self, client_key: str, capacity: int, 
                           refill_time: int, current_time: float) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket rate limit check."""
        # Get or create token bucket
        bucket_key = f"bucket:{client_key}"
        if bucket_key not in self.token_buckets:
            refill_rate = capacity / refill_time
            self.token_buckets[bucket_key] = TokenBucketLimiter(capacity, refill_rate)
        
        # Get or create state
        if client_key not in self.client_states:
            self.client_states[client_key]["token_bucket"] = RateLimitState(
                current_requests=0,
                window_start=current_time,
                last_request_time=current_time,
                tokens=capacity,
                last_refill_time=current_time
            )
        
        state = self.client_states[client_key]["token_bucket"]
        bucket = self.token_buckets[bucket_key]
        
        allowed, remaining_tokens = bucket.is_allowed(state, current_time)
        
        if allowed:
            return True, {
                "remaining": int(remaining_tokens),
                "reset_time": current_time + (capacity - remaining_tokens) / bucket.refill_rate
            }
        else:
            retry_after = int((1 - remaining_tokens) / bucket.refill_rate)
            return False, {
                "retry_after": max(retry_after, 1),
                "tokens_available": remaining_tokens
            }
    
    def _is_client_blocked(self, client_key: str) -> bool:
        """Check if client is temporarily blocked."""
        if client_key not in self.client_states:
            return False
        
        state = self.client_states[client_key].get("block_state")
        if not state:
            return False
        
        current_time = time.time()
        if state.blocked_until and current_time < state.blocked_until:
            return True
        
        return False
    
    def _get_block_duration(self, client_key: str) -> int:
        """Get remaining block duration."""
        if client_key not in self.client_states:
            return 0
        
        state = self.client_states[client_key].get("block_state")
        if not state or not state.blocked_until:
            return 0
        
        remaining = int(state.blocked_until - time.time())
        return max(remaining, 1)
    
    def _record_violation(self, client_key: str, tier: UserTier, endpoint_type: str):
        """Record rate limit violation."""
        current_time = time.time()
        
        # Add to violations list
        self.violations[client_key].append(current_time)
        
        # Keep only recent violations (last hour)
        cutoff_time = current_time - 3600
        self.violations[client_key] = [
            v for v in self.violations[client_key] if v > cutoff_time
        ]
        
        # Update statistics
        self.stats["violations_by_tier"][tier.value] += 1
        self.stats["violations_by_endpoint"][endpoint_type] += 1
        
        # Check if client should be blocked
        if len(self.violations[client_key]) >= 10:  # 10 violations in last hour
            block_duration = min(300, len(self.violations[client_key]) * 30)  # Up to 5 minutes
            
            if client_key not in self.client_states:
                self.client_states[client_key] = {}
            
            self.client_states[client_key]["block_state"] = RateLimitState(
                current_requests=0,
                window_start=current_time,
                last_request_time=current_time,
                tokens=0,
                last_refill_time=current_time,
                violations=len(self.violations[client_key]),
                blocked_until=current_time + block_duration
            )
    
    def update_load_factors(self, global_load: float = None, 
                          endpoint_loads: Dict[str, float] = None):
        """Update adaptive load factors."""
        with self.lock:
            if global_load is not None:
                self.global_load_factor = max(0.1, min(2.0, global_load))
            
            if endpoint_loads:
                for endpoint, load in endpoint_loads.items():
                    self.endpoint_load_factors[endpoint] = max(0.1, min(2.0, load))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        with self.lock:
            total = self.stats["total_requests"]
            allowed = self.stats["allowed_requests"]
            blocked = self.stats["blocked_requests"]
            
            return {
                "total_requests": total,
                "allowed_requests": allowed,
                "blocked_requests": blocked,
                "allow_rate": (allowed / total) if total > 0 else 0,
                "block_rate": (blocked / total) if total > 0 else 0,
                "violations_by_tier": dict(self.stats["violations_by_tier"]),
                "violations_by_endpoint": dict(self.stats["violations_by_endpoint"]),
                "active_clients": len(self.client_states),
                "blocked_clients": len([
                    key for key, states in self.client_states.items()
                    if "block_state" in states and states["block_state"].blocked_until
                ]),
                "global_load_factor": self.global_load_factor,
                "endpoint_load_factors": dict(self.endpoint_load_factors)
            }
    
    def get_client_status(self, user_id: str, ip_address: str) -> Dict[str, Any]:
        """Get rate limit status for a client."""
        client_info = {}
        
        for endpoint_type in ["read", "write", "upload", "auth", "ai"]:
            client_key = self.get_client_key(user_id, ip_address, endpoint_type)
            
            if client_key in self.client_states:
                tier = self.get_user_tier(user_id)
                config = self.tier_configs[tier][endpoint_type]
                
                client_info[endpoint_type] = {
                    "tier": tier.value,
                    "limit": config.requests_per_window,
                    "window": config.window_seconds,
                    "violations": len(self.violations.get(client_key, [])),
                    "blocked": self._is_client_blocked(client_key)
                }
        
        return client_info
    
    def reset_client(self, user_id: str, ip_address: str):
        """Reset rate limit state for a client."""
        with self.lock:
            for endpoint_type in ["read", "write", "upload", "auth", "ai"]:
                client_key = self.get_client_key(user_id, ip_address, endpoint_type)
                
                if client_key in self.client_states:
                    del self.client_states[client_key]
                
                if client_key in self.sliding_windows:
                    del self.sliding_windows[client_key]
                
                if client_key in self.violations:
                    del self.violations[client_key]
                
                bucket_key = f"bucket:{client_key}"
                if bucket_key in self.token_buckets:
                    del self.token_buckets[bucket_key]

# Global rate limiter instance
_rate_limiter: Optional[AdvancedRateLimiter] = None

def get_advanced_rate_limiter() -> AdvancedRateLimiter:
    """Get the global advanced rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        _rate_limiter = AdvancedRateLimiter()
    
    return _rate_limiter

# Helper functions
def check_rate_limit(user_id: str, ip_address: str, method: str, path: str) -> Tuple[bool, Dict[str, Any]]:
    """Check if request is allowed."""
    limiter = get_advanced_rate_limiter()
    return limiter.is_allowed(user_id, ip_address, method, path)

def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limiting statistics."""
    limiter = get_advanced_rate_limiter()
    return limiter.get_stats()

def update_rate_limit_load_factors(global_load: float = None, 
                                 endpoint_loads: Dict[str, float] = None):
    """Update adaptive load factors."""
    limiter = get_advanced_rate_limiter()
    limiter.update_load_factors(global_load, endpoint_loads)

def reset_client_rate_limits(user_id: str, ip_address: str):
    """Reset rate limit state for a client."""
    limiter = get_advanced_rate_limiter()
    limiter.reset_client(user_id, ip_address)

# FastAPI dependency
async def rate_limit_dependency(request):
    """FastAPI dependency for rate limiting."""
    # Extract user info (this would come from authentication)
    user_id = getattr(request.state, 'user_id', 'anonymous')
    ip_address = request.client.host if request.client else 'unknown'
    
    # Check rate limit
    allowed, details = check_rate_limit(user_id, ip_address, request.method, request.url.path)
    
    if not allowed:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(details.get("retry_after", 60)),
                "X-RateLimit-Limit": str(details.get("limit", 0)),
                "X-RateLimit-Remaining": str(details.get("remaining", 0)),
                "X-RateLimit-Reset": str(details.get("reset_time", 0))
            }
        )
    
    # Add rate limit headers to response
    return details
