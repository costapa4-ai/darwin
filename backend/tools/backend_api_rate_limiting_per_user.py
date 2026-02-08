"""
API Rate Limiting System with Per-User Token Bucket Implementation

This module provides a comprehensive rate limiting system that supports per-user
rate limiting using the token bucket algorithm. It includes Redis-backed storage
for distributed systems and in-memory fallback for single-instance deployments.
"""

import time
import threading
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
from enum import Enum


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, user_id: str, retry_after: float, limit: int):
        self.user_id = user_id
        self.retry_after = retry_after
        self.limit = limit
        super().__init__(
            f"Rate limit exceeded for user {user_id}. "
            f"Retry after {retry_after:.2f} seconds. Limit: {limit} requests."
        )


class RateLimitTier(Enum):
    """Rate limit tiers for different user types."""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.requests_per_hour <= 0:
            raise ValueError("requests_per_hour must be positive")
        if self.requests_per_day <= 0:
            raise ValueError("requests_per_day must be positive")
        if self.burst_size <= 0:
            raise ValueError("burst_size must be positive")


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)
    
    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (success, retry_after_seconds)
        """
        self.refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, 0.0
        
        tokens_needed = tokens - self.tokens
        retry_after = tokens_needed / self.refill_rate
        return False, retry_after


class RateLimitStore:
    """Abstract base class for rate limit storage backends."""
    
    def get_bucket(self, key: str) -> Optional[Dict[str, Any]]:
        """Get bucket data for a key."""
        raise NotImplementedError
    
    def set_bucket(self, key: str, bucket_data: Dict[str, Any], ttl: int = 86400) -> None:
        """Set bucket data for a key with optional TTL."""
        raise NotImplementedError
    
    def increment_counter(self, key: str, window: int) -> int:
        """Increment a counter with a time window."""
        raise NotImplementedError


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory storage for rate limiting (single instance)."""
    
    def __init__(self):
        """Initialize in-memory store."""
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._counters: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.RLock()
    
    def get_bucket(self, key: str) -> Optional[Dict[str, Any]]:
        """Get bucket data for a key."""
        with self._lock:
            return self._buckets.get(key)
    
    def set_bucket(self, key: str, bucket_data: Dict[str, Any], ttl: int = 86400) -> None:
        """Set bucket data for a key."""
        with self._lock:
            self._buckets[key] = bucket_data
    
    def increment_counter(self, key: str, window: int) -> int:
        """Increment a counter with a time window."""
        with self._lock:
            now = time.time()
            if key in self._counters:
                count, timestamp = self._counters[key]
                if now - timestamp > window:
                    count = 0
                    timestamp = now
            else:
                count = 0
                timestamp = now
            
            count += 1
            self._counters[key] = (count, timestamp)
            return count
    
    def cleanup_expired(self) -> None:
        """Clean up expired entries."""
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._counters.items()
                if now - timestamp > 86400
            ]
            for key in expired_keys:
                del self._counters[key]


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed storage for distributed rate limiting."""
    
    def __init__(self, redis_client: Any):
        """
        Initialize Redis store.
        
        Args:
            redis_client: Redis client instance (redis.Redis or compatible)
        """
        self._redis = redis_client
    
    def get_bucket(self, key: str) -> Optional[Dict[str, Any]]:
        """Get bucket data for a key."""
        try:
            data = self._redis.get(f"ratelimit:bucket:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to get bucket from Redis: {e}")
    
    def set_bucket(self, key: str, bucket_data: Dict[str, Any], ttl: int = 86400) -> None:
        """Set bucket data for a key with TTL."""
        try:
            self._redis.setex(
                f"ratelimit:bucket:{key}",
                ttl,
                json.dumps(bucket_data)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to set bucket in Redis: {e}")
    
    def increment_counter(self, key: str, window: int) -> int:
        """Increment a counter with a time window."""
        try:
            counter_key = f"ratelimit:counter:{key}"
            pipeline = self._redis.pipeline()
            pipeline.incr(counter_key)
            pipeline.expire(counter_key, window)
            result = pipeline.execute()
            return result[0]
        except Exception as e:
            raise RuntimeError(f"Failed to increment counter in Redis: {e}")


class PerUserRateLimiter:
    """
    Per-user rate limiter using token bucket algorithm.
    
    Supports multiple time windows (minute, hour, day) and configurable
    rate limits per user tier.
    """
    
    def __init__(
        self,
        store: Optional[RateLimitStore] = None,
        default_config: Optional[RateLimitConfig] = None,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize the rate limiter.
        
        Args:
            store: Storage backend for rate limit data
            default_config: Default rate limit configuration
            top_k: For compatibility with other systems
            **kwargs: Additional configuration options
        """
        self.store = store if store is not None else InMemoryRateLimitStore()
        self.default_config = default_config if default_config is not None else RateLimitConfig()
        self.tier_configs: Dict[RateLimitTier, RateLimitConfig] = {
            RateLimitTier.FREE: RateLimitConfig(
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=1000,
                burst_size=5
            ),
            RateLimitTier.BASIC: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=10000,
                burst_size=10
            ),
            RateLimitTier.PREMIUM: RateLimitConfig(
                requests_per_minute=300,
                requests_per_hour=5000,
                requests_per_day=50000,
                burst_size=50
            ),
            RateLimitTier.ENTERPRISE: RateLimitConfig(
                requests_per_minute=1000,
                requests_per_hour=20000,
                requests_per_day=200000,
                burst_size=100
            )
        }
        self._lock = threading.RLock()
    
    def _get_user_key(self, user_id: str, window: str) -> str:
        """Generate a unique key for a user and time window."""
        return f"{user_id}:{window}"
    
    def _get_config(self, tier: RateLimitTier) -> RateLimitConfig:
        """Get configuration for a specific tier."""
        return self.tier_configs.get(tier, self.default_config)
    
    def _create_bucket(self, config: RateLimitConfig, window: str) -> TokenBucket:
        """Create a new token bucket for a time window."""
        if window == "minute":
            capacity = config.requests_per_minute
            refill_rate = capacity / 60.0
        elif window == "hour":
            capacity = config.requests_per_hour
            refill_rate = capacity / 3600.0
        elif window == "day":
            capacity = config.requests_per_day
            refill_rate = capacity / 86400.0
        else:
            raise ValueError(f"Invalid window: {window}")
        
        return TokenBucket(
            capacity=capacity,
            tokens=float(capacity),
            refill_rate=refill_rate
        )
    
    def _load_bucket(self, user_id: str, window: str, config: RateLimitConfig) -> TokenBucket:
        """Load or create a token bucket for a user and window."""
        key = self._get_user_key(user_id, window)
        bucket_data = self.store.get_bucket(key)
        
        if bucket_data:
            return TokenBucket(
                capacity=bucket_data["capacity"],
                tokens=bucket_data["tokens"],
                refill_rate=bucket_data["refill_rate"],
                last_refill=bucket_data["last_refill"]
            )
        else:
            return self._create_bucket(config, window)
    
    def _save_bucket(self, user_id: str, window: str, bucket: TokenBucket) -> None:
        """Save a token bucket to storage."""
        key = self._get_user_key(user_id, window)
        bucket_data = {
            "capacity": bucket.capacity,
            "tokens": bucket.tokens,
            "refill_rate": bucket.refill_rate,
            "last_refill": bucket.last_refill
        }
        self.store.set_bucket(key, bucket_data)
    
    def check_rate_limit(
        self,
        user_id: str,
        tier: RateLimitTier = RateLimitTier.FREE,
        tokens: int = 1
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if a request is allowed under rate limits.
        
        Args:
            user_id: Unique identifier for the user
            tier: Rate limit tier for the user
            tokens: Number of tokens to consume (default 1)
            
        Returns:
            Tuple of (allowed, retry_after_seconds)
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        with self._lock:
            config = self._get_config(tier)
            windows = ["minute", "hour", "day"]
            
            max_retry_after = 0.0
            
            for window in windows:
                bucket = self._load_bucket(user_id, window, config)
                allowed, retry_after = bucket.consume(tokens)
                
                if not allowed:
                    max_retry_after = max(max_retry_after, retry_after)
                    limit = bucket.capacity
                    raise RateLimitExceeded(user_id, retry_after, limit)
                
                self._save_bucket(user_id, window, bucket)
            
            return True, None
    
    def get_remaining_quota(
        self,
        user_id: str,
        tier: RateLimitTier = RateLimitTier.FREE
    ) -> Dict[str, int]:
        """
        Get remaining quota for a user across all time windows.
        
        Args:
            user_id: Unique identifier for the user
            tier: Rate limit tier for the user
            
        Returns:
            Dictionary with remaining tokens per window
        """
        with self._lock:
            config = self._get_config(tier)
            windows = ["minute", "hour", "day"]
            remaining = {}
            
            for window in windows:
                bucket = self._load_bucket(user_id, window, config)
                bucket.refill()
                remaining[window] = int(bucket.tokens)
                self._save_bucket(user_id, window, bucket)
            
            return remaining
    
    def reset_user_limits(self, user_id: str) -> None:
        """
        Reset rate limits for a specific user.
        
        Args:
            user_id: Unique identifier for the user
        """
        with self._lock:
            windows = ["minute", "hour", "day"]
            for window in windows:
                key = self._get_user_key(user_id, window)
                # Remove bucket data to force recreation
                self.store.set_bucket(key, {}, ttl=1)