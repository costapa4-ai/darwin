"""AI service with rate limiting and provider management"""
import time
from typing import Dict, Optional
from collections import deque
from datetime import datetime, timedelta
from core.nucleus import Nucleus
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_per_minute: int = 10, max_per_hour: int = 50):
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.minute_calls = deque()
        self.hour_calls = deque()

    def check_and_wait(self):
        """Check rate limits and wait if necessary"""
        now = datetime.now()

        # Clean old calls
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        while self.minute_calls and self.minute_calls[0] < minute_ago:
            self.minute_calls.popleft()

        while self.hour_calls and self.hour_calls[0] < hour_ago:
            self.hour_calls.popleft()

        # Check limits
        if len(self.minute_calls) >= self.max_per_minute:
            wait_time = (self.minute_calls[0] - minute_ago).total_seconds()
            logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(wait_time + 1)
            return self.check_and_wait()

        if len(self.hour_calls) >= self.max_per_hour:
            wait_time = (self.hour_calls[0] - hour_ago).total_seconds()
            logger.warning(f"Hourly rate limit reached, waiting {wait_time:.1f}s")
            time.sleep(min(wait_time + 1, 60))  # Max wait 60s
            return self.check_and_wait()

        # Record this call
        self.minute_calls.append(now)
        self.hour_calls.append(now)

    def get_stats(self) -> Dict:
        """Get current rate limit stats"""
        return {
            'calls_last_minute': len(self.minute_calls),
            'calls_last_hour': len(self.hour_calls),
            'minute_limit': self.max_per_minute,
            'hour_limit': self.max_per_hour
        }


class AIService:
    """Managed AI service with rate limiting"""

    def __init__(
        self,
        provider: str,
        api_key: str,
        max_per_minute: int = 10,
        max_per_hour: int = 50
    ):
        self.nucleus = Nucleus(provider, api_key)
        self.rate_limiter = RateLimiter(max_per_minute, max_per_hour)
        self.call_count = 0
        self.error_count = 0

        logger.info("AIService initialized", extra={
            "provider": provider,
            "max_per_minute": max_per_minute,
            "max_per_hour": max_per_hour
        })

    def generate_solution(self, task: Dict) -> str:
        """Generate solution with rate limiting"""
        self.rate_limiter.check_and_wait()

        try:
            self.call_count += 1
            return self.nucleus.generate_solution(task)
        except Exception as e:
            self.error_count += 1
            logger.error(f"AI generation error: {e}", extra={"task_id": task.get('id')})
            raise

    def analyze_result(self, code: str, result: Dict, task: Dict) -> Dict:
        """Analyze result with rate limiting"""
        self.rate_limiter.check_and_wait()

        try:
            self.call_count += 1
            return self.nucleus.analyze_result(code, result, task)
        except Exception as e:
            self.error_count += 1
            logger.error(f"AI analysis error: {e}")
            raise

    def evolve_code(self, code: str, feedback: Dict, task: Dict) -> str:
        """Evolve code with rate limiting"""
        self.rate_limiter.check_and_wait()

        try:
            self.call_count += 1
            return self.nucleus.evolve_code(code, feedback, task)
        except Exception as e:
            self.error_count += 1
            logger.error(f"AI evolution error: {e}")
            raise

    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            'total_calls': self.call_count,
            'error_count': self.error_count,
            'success_rate': (
                (self.call_count - self.error_count) / self.call_count * 100
                if self.call_count > 0 else 0
            ),
            'rate_limits': self.rate_limiter.get_stats()
        }
