import time
import threading
from typing import Callable, Dict, Tuple, Union

class RateLimiter:
    """
    A generic rate limiter class that can be used to limit the rate of any function call.

    Supports multiple keys for independent rate limiting.
    Uses a thread-safe mechanism for concurrent access.
    """

    def __init__(self, rate: int, period: int) -> None:
        """
        Initializes the RateLimiter.

        Args:
            rate: The maximum number of calls allowed within the period.
            period: The time period (in seconds) during which the rate applies.
        """
        if rate <= 0:
            raise ValueError("Rate must be a positive integer.")
        if period <= 0:
            raise ValueError("Period must be a positive integer.")

        self.rate: int = rate
        self.period: int = period
        self.calls: Dict[str, list[float]] = {}  # key: [timestamp1, timestamp2, ...]
        self.lock: threading.Lock = threading.Lock()  # Ensure thread safety

    def __call__(self, key: str) -> bool:
        """
        Checks if a call with the given key is allowed based on the rate limit.

        Args:
            key: The key to identify the rate limit for a specific resource or user.

        Returns:
            True if the call is allowed, False otherwise.
        """
        with self.lock:
            now: float = time.time()
            if key not in self.calls:
                self.calls[key] = []

            # Remove outdated timestamps
            self.calls[key] = [t for t in self.calls[key] if t > now - self.period]

            if len(self.calls[key]) < self.rate:
                self.calls[key].append(now)
                return True
            else:
                return False

    def get_remaining_calls(self, key: str) -> int:
        """
        Returns the number of remaining calls within the current period for a given key.

        Args:
            key: The key to identify the rate limit.

        Returns:
            The number of remaining calls.
        """
        with self.lock:
            now: float = time.time()
            if key not in self.calls:
                return self.rate  # No calls made yet, all calls remaining

            # Remove outdated timestamps
            self.calls[key] = [t for t in self.calls[key] if t > now - self.period]
            return max(0, self.rate - len(self.calls[key]))

    def reset_key(self, key: str) -> None:
        """
        Resets the rate limit for a given key, effectively allowing a full set of new calls.

        Args:
            key: The key to reset.
        """
        with self.lock:
            self.calls[key] = []

    def decorate(self, key_func: Callable[[...], str]) -> Callable[[Callable[..., Union[str, bytes, int, float, list, dict, tuple]]], Callable[..., Union[str, bytes, int, float, list, dict, tuple]]]:
        """
        A decorator factory that returns a decorator to rate limit a function based on a dynamic key.

        Args:
            key_func: A function that takes the same arguments as the decorated function and returns the rate limiting key (string).

        Returns:
            A decorator that wraps the function with rate limiting logic.
        """
        def decorator(func: Callable[..., Union[str, bytes, int, float, list, dict, tuple]]) -> Callable[..., Union[str, bytes, int, float, list, dict, tuple]]:
            """
            The actual decorator that wraps the function.

            Args:
                func: The function to be decorated.

            Returns:
                The wrapped function.
            """
            def wrapper(*args, **kwargs) -> Union[str, bytes, int, float, list, dict, tuple]:
                """
                The wrapper function that executes before the decorated function.

                Args:
                    *args: Positional arguments passed to the decorated function.
                    **kwargs: Keyword arguments passed to the decorated function.

                Returns:
                    The result of the decorated function, or None if rate limited.

                Raises:
                    RateLimitExceeded: If the rate limit is exceeded.
                """
                key: str = key_func(*args, **kwargs)
                if self(key):
                    return func(*args, **kwargs)
                else:
                    raise RateLimitExceeded(f"Rate limit exceeded for key: {key}")
            return wrapper
        return decorator

class RateLimitExceeded(Exception):
    """
    Custom exception raised when the rate limit is exceeded.
    """
    pass

def get_user_id(user_id: int) -> str:
    """
    A function used to extract user_id as a key
    """
    return str(user_id)

if __name__ == '__main__':
    # Example Usage
    rate_limiter = RateLimiter(rate=5, period=1)  # 5 calls per second

    # Basic Usage
    for i in range(10):
        if rate_limiter("test_key"):
            print(f"Call {i+1} allowed")
        else:
            print(f"Call {i+1} rate limited")
        time.sleep(0.1)

    print(f"Remaining calls for test_key: {rate_limiter.get_remaining_calls('test_key')}")

    rate_limiter.reset_key("test_key")
    print(f"Remaining calls for test_key after reset: {rate_limiter.get_remaining_calls('test_key')}")


    # Usage with decorator
    rate_limiter_decorator = RateLimiter(rate=2, period=2)

    @rate_limiter_decorator.decorate(key_func=get_user_id)
    def my_api_call(user_id: int, data: str) -> str:
        """
        A dummy API call function.
        """
        print(f"API call with user_id {user_id} and data: {data}")
        return "API call successful"

    for i in range(3):
        try:
            result = my_api_call(user_id=1, data=f"Data {i}")
            print(f"Result: {result}")
        except RateLimitExceeded as e:
            print(e)
        time.sleep(1)

    for i in range(3):
        try:
            result = my_api_call(user_id=2, data=f"Data {i}") # Different user, different rate limit
            print(f"Result: {result}")
        except RateLimitExceeded as e:
            print(e)
        time.sleep(1)