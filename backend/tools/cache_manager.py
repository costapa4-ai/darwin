import functools
import json
import os
import threading
from typing import Any, Callable, Dict, Optional, Tuple, Union

class CacheManager:
    """
    A versatile cache manager for storing and retrieving data, supporting different storage backends
    (in-memory, file-based).  Provides thread-safe operations and automatic cache invalidation based on
    time-to-live (TTL).
    """

    def __init__(self, cache_type: str = "memory", cache_path: Optional[str] = None, default_ttl: int = 3600):
        """
        Initializes the CacheManager.

        Args:
            cache_type: The type of cache to use ("memory" or "file"). Defaults to "memory".
            cache_path: The path to the cache file if using file-based caching. Required if cache_type is "file".
            default_ttl: The default time-to-live (in seconds) for cached items. Defaults to 3600 seconds (1 hour).

        Raises:
            ValueError: If an invalid cache_type is provided or if cache_path is not provided when cache_type is "file".
        """
        self.cache_type: str = cache_type.lower()
        self.cache_path: Optional[str] = cache_path
        self.default_ttl: int = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = {}  # key: {value, expiry}
        self._lock: threading.Lock = threading.Lock()

        if self.cache_type not in ("memory", "file"):
            raise ValueError("Invalid cache_type. Must be 'memory' or 'file'.")

        if self.cache_type == "file":
            if not self.cache_path:
                raise ValueError("cache_path must be specified when using file-based caching.")
            self._load_cache_from_file()

    def _load_cache_from_file(self) -> None:
        """Loads the cache from a file, handling potential errors."""
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r") as f:
                    self.cache = json.load(f)
        except FileNotFoundError:
            # Handle the case where the file doesn't exist (first run).
            self.cache = {}
        except json.JSONDecodeError:
            # Handle the case where the JSON is corrupted.
            print("Warning: Cache file is corrupted. Starting with an empty cache.")
            self.cache = {}
        except Exception as e:
            print(f"Error loading cache from file: {e}. Starting with an empty cache.")
            self.cache = {}

    def _save_cache_to_file(self) -> None:
        """Saves the cache to a file, handling potential errors."""
        try:
            with self._lock:
                with open(self.cache_path, "w") as f:
                    json.dump(self.cache, f, indent=4)
        except Exception as e:
            print(f"Error saving cache to file: {e}")

    def get(self, key: str) -> Any:
        """
        Retrieves a value from the cache.

        Args:
            key: The key of the value to retrieve.

        Returns:
            The cached value if it exists and is not expired, otherwise None.
        """
        with self._lock:
            if key in self.cache:
                if self.cache[key]["expiry"] > time.time():
                    return self.cache[key]["value"]
                else:
                    del self.cache[key]  # Remove expired entry
                    if self.cache_type == "file":
                        self._save_cache_to_file()
                    return None
            else:
                return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Stores a value in the cache.

        Args:
            key: The key of the value to store.
            value: The value to store.
            ttl: The time-to-live (in seconds) for the cached item. If None, the default_ttl is used.
        """
        expiry: float = time.time() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self.cache[key] = {"value": value, "expiry": expiry}
            if self.cache_type == "file":
                self._save_cache_to_file()

    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.

        Args:
            key: The key of the value to delete.
        """
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                if self.cache_type == "file":
                    self._save_cache_to_file()

    def clear(self) -> None:
        """Clears the entire cache."""
        with self._lock:
            self.cache.clear()
            if self.cache_type == "file":
                self._save_cache_to_file()

    def cache_result(self, ttl: Optional[int] = None, key_prefix: str = "") -> Callable:
        """
        A decorator to cache the result of a function.

        Args:
            ttl: The time-to-live (in seconds) for the cached result. If None, the default_ttl is used.
            key_prefix: A prefix to add to the cache key.

        Returns:
            A decorator function.
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                key = f"{key_prefix}{func.__name__}_{args}_{kwargs}"
                cached_result = self.get(key)
                if cached_result is not None:
                    return cached_result
                else:
                    result = func(*args, **kwargs)
                    self.set(key, result, ttl)
                    return result

            return wrapper

        return decorator

import time  # Import the time module

if __name__ == '__main__':
    # Example Usage
    # In-memory cache
    memory_cache = CacheManager(cache_type="memory")

    @memory_cache.cache_result(ttl=10)
    def expensive_calculation(x: int, y: int) -> int:
        """A function that performs an expensive calculation."""
        print("Performing expensive calculation...")
        time.sleep(2)  # Simulate a time-consuming operation
        return x * y

    print(f"First calculation: {expensive_calculation(5, 10)}")  # Output: Performing expensive calculation..., 50
    print(f"Second calculation: {expensive_calculation(5, 10)}") # Output: 50 (from cache)
    time.sleep(11)
    print(f"Third calculation: {expensive_calculation(5, 10)}") # Output: Performing expensive calculation..., 50 (cache expired)

    # File-based cache
    file_cache = CacheManager(cache_type="file", cache_path="my_cache.json", default_ttl=60)

    @file_cache.cache_result(ttl=20)
    def another_expensive_calculation(a: int) -> int:
        """Another expensive calculation."""
        print("Performing another expensive calculation...")
        time.sleep(1)
        return a ** 2

    print(f"First file-based calculation: {another_expensive_calculation(7)}")
    print(f"Second file-based calculation: {another_expensive_calculation(7)}")
    time.sleep(21)
    print(f"Third file-based calculation: {another_expensive_calculation(7)}")

    # Demonstrating cache deletion
    file_cache.delete("another_expensive_calculation_(7,)_{}")
    print(f"Calculation after deletion: {another_expensive_calculation(7)}") # Will recalculate

    #Demonstrates clearing the cache
    file_cache.clear()
    print(f"Calculation after clear: {another_expensive_calculation(7)}") # Will recalculate