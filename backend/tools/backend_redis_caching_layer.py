"""
Redis caching layer for Darwin System.

Provides caching functionality for frequently accessed data including metrics,
agent stats, and dream history to improve API response times and reduce database load.
"""

import json
import logging
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisCacheManager:
    """
    Manages Redis caching operations for the Darwin System.
    
    Provides methods for caching metrics, agent statistics, and dream history
    with automatic serialization, TTL management, and error handling.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True,
        max_connections: int = 50,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize Redis cache manager.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password if authentication is required
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            decode_responses: Whether to decode responses to strings
            max_connections: Maximum number of connections in the pool
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        
        try:
            self.connection_pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=decode_responses,
                max_connections=max_connections
            )
            self.client = redis.Redis(connection_pool=self.connection_pool)
            self.client.ping()
            logger.info(f"Redis cache manager initialized successfully at {host}:{port}")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {e}")
            self.client = None
    
    def is_available(self, top_k: int = None, **kwargs) -> bool:
        """
        Check if Redis connection is available.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if Redis is available, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            self.client.ping()
            return True
        except (RedisError, ConnectionError, TimeoutError):
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking Redis availability: {e}")
            return False
    
    def _serialize_value(self, value: Any, top_k: int = None, **kwargs) -> str:
        """
        Serialize Python object to JSON string.
        
        Args:
            value: Value to serialize
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            JSON serialized string
        """
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value: {e}")
            return json.dumps({"error": "serialization_failed"})
    
    def _deserialize_value(self, value: str, top_k: int = None, **kwargs) -> Any:
        """
        Deserialize JSON string to Python object.
        
        Args:
            value: JSON string to deserialize
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Deserialized Python object
        """
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize value: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        top_k: int = None,
        **kwargs
    ) -> bool:
        """
        Set a value in Redis cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None for no expiration)
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache set")
            return False
        
        try:
            serialized_value = self._serialize_value(value)
            if ttl:
                self.client.setex(key, ttl, serialized_value)
            else:
                self.client.set(key, serialized_value)
            return True
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting cache key {key}: {e}")
            return False
    
    def get(self, key: str, top_k: int = None, **kwargs) -> Optional[Any]:
        """
        Get a value from Redis cache.
        
        Args:
            key: Cache key
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Cached value or None if not found or error occurred
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache get")
            return None
        
        try:
            value = self.client.get(key)
            return self._deserialize_value(value)
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting cache key {key}: {e}")
            return None
    
    def delete(self, key: str, top_k: int = None, **kwargs) -> bool:
        """
        Delete a key from Redis cache.
        
        Args:
            key: Cache key to delete
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache delete")
            return False
        
        try:
            self.client.delete(key)
            return True
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting cache key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str, top_k: int = None, **kwargs) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (e.g., "metrics:*")
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache delete pattern")
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to delete cache pattern {pattern}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error deleting cache pattern {pattern}: {e}")
            return 0
    
    def clear_all(self, top_k: int = None, **kwargs) -> bool:
        """
        Clear all keys in the current database.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache clear")
            return False
        
        try:
            self.client.flushdb()
            logger.info("Redis cache cleared successfully")
            return True
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error clearing cache: {e}")
            return False
    
    def exists(self, key: str, top_k: int = None, **kwargs) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            return bool(self.client.exists(key))
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to check key existence {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking key existence {key}: {e}")
            return False
    
    def set_multiple(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        top_k: int = None,
        **kwargs
    ) -> bool:
        """
        Set multiple key-value pairs in Redis cache.
        
        Args:
            mapping: Dictionary of key-value pairs to cache
            ttl: Time to live in seconds (None for no expiration)
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache set multiple")
            return False
        
        try:
            serialized_mapping = {
                key: self._serialize_value(value)
                for key, value in mapping.items()
            }
            
            pipe = self.client.pipeline()
            pipe.mset(serialized_mapping)
            
            if ttl:
                for key in serialized_mapping.keys():
                    pipe.expire(key, ttl)
            
            pipe.execute()
            return True
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to set multiple cache keys: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting multiple cache keys: {e}")
            return False
    
    def get_multiple(
        self,
        keys: List[str],
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get multiple values from Redis cache.
        
        Args:
            keys: List of cache keys to retrieve
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Dictionary of key-value pairs
        """
        if not self.is_available():
            logger.warning("Redis not available, skipping cache get multiple")
            return {}
        
        try:
            values = self.client.mget(keys)
            return {
                key: self._deserialize_value(value)
                for key, value in zip(keys, values)
                if value is not None
            }
        except (RedisError, ConnectionError, TimeoutError) as e:
            logger.error(f"Failed to get multiple cache keys: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting multiple cache keys: {e}")
            return {}
    
    def close(self, top_k: int = None, **kwargs) -> None:
        """
        Close Redis connection pool.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        if self.client:
            try:
                self.connection_pool.disconnect()
                logger.info("Redis connection pool closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection pool: {e}")


def cache_result(
    key_prefix: str,
    ttl: int = 300,
    cache_manager: Optional[RedisCacheManager] = None
) -> Callable:
    """
    Decorator to cache function results in Redis.
    
    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        cache_manager: RedisCacheManager instance (if None, creates new instance)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal cache_manager
            
            if cache_manager is None:
                cache_manager = RedisCacheManager()
            
            if not cache_manager.is_available():
                return func(*args, **kwargs)
            
            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            if args:
                key_parts.append(str(args))
            if kwargs:
                key_parts.append(str(sorted(kwargs.items())))
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl=ttl)
            logger.debug(f"Cache miss for {cache_key}, result cached")
            
            return result
        
        return wrapper
    return decorator