"""
Task Queue System for Darwin System
Provides async task processing with Celery and Redis backend.
"""

import os
import logging
import functools
import time
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

try:
    from celery import Celery, Task, states
    from celery.result import AsyncResult
    from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
    from kombu import serialization
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Provide stubs so the module loads without celery
    Celery = None
    Task = object
    states = None
    AsyncResult = None
    SoftTimeLimitExceeded = Exception
    TimeLimitExceeded = Exception

try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 15


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskQueueConfig:
    """Configuration for task queue system."""
    
    def __init__(
        self,
        broker_url: Optional[str] = None,
        result_backend: Optional[str] = None,
        task_serializer: str = "json",
        result_serializer: str = "json",
        accept_content: List[str] = None,
        timezone: str = "UTC",
        enable_utc: bool = True,
        task_track_started: bool = True,
        task_time_limit: int = 3600,
        task_soft_time_limit: int = 3000,
        worker_prefetch_multiplier: int = 4,
        worker_max_tasks_per_child: int = 1000,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize task queue configuration.
        
        Args:
            broker_url: Redis broker URL
            result_backend: Redis result backend URL
            task_serializer: Serialization format for tasks
            result_serializer: Serialization format for results
            accept_content: List of accepted content types
            timezone: Timezone for task scheduling
            enable_utc: Enable UTC timezone
            task_track_started: Track when tasks start
            task_time_limit: Hard time limit for tasks (seconds)
            task_soft_time_limit: Soft time limit for tasks (seconds)
            worker_prefetch_multiplier: Number of tasks to prefetch
            worker_max_tasks_per_child: Max tasks per worker process
            top_k: For compatibility with tool registry
            **kwargs: Additional configuration parameters
        """
        self.broker_url = broker_url or os.getenv(
            "CELERY_BROKER_URL", "redis://localhost:6379/0"
        )
        self.result_backend = result_backend or os.getenv(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
        )
        self.task_serializer = task_serializer
        self.result_serializer = result_serializer
        self.accept_content = accept_content or ["json", "pickle"]
        self.timezone = timezone
        self.enable_utc = enable_utc
        self.task_track_started = task_track_started
        self.task_time_limit = task_time_limit
        self.task_soft_time_limit = task_soft_time_limit
        self.worker_prefetch_multiplier = worker_prefetch_multiplier
        self.worker_max_tasks_per_child = worker_max_tasks_per_child
        
    def to_dict(self, top_k: int = None, **kwargs) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            Configuration dictionary
        """
        return {
            "broker_url": self.broker_url,
            "result_backend": self.result_backend,
            "task_serializer": self.task_serializer,
            "result_serializer": self.result_serializer,
            "accept_content": self.accept_content,
            "timezone": self.timezone,
            "enable_utc": self.enable_utc,
            "task_track_started": self.task_track_started,
            "task_time_limit": self.task_time_limit,
            "task_soft_time_limit": self.task_soft_time_limit,
            "worker_prefetch_multiplier": self.worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.worker_max_tasks_per_child,
        }


class DarwinTask(Task):
    """Base task class with retry logic and error handling."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
        top_k: int = None,
        **extra_kwargs
    ) -> None:
        """
        Handle task failure.
        
        Args:
            exc: Exception that caused failure
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info
            top_k: For compatibility with tool registry
            **extra_kwargs: Additional parameters
        """
        logger.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            exc_info=True,
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
            }
        )
        
    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
        top_k: int = None,
        **extra_kwargs
    ) -> None:
        """
        Handle task retry.
        
        Args:
            exc: Exception that caused retry
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            einfo: Exception info
            top_k: For compatibility with tool registry
            **extra_kwargs: Additional parameters
        """
        logger.warning(
            f"Task {self.name}[{task_id}] retrying: {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retry_count": self.request.retries,
            }
        )
        
    def on_success(
        self,
        retval: Any,
        task_id: str,
        args: tuple,
        kwargs: dict,
        top_k: int = None,
        **extra_kwargs
    ) -> None:
        """
        Handle task success.
        
        Args:
            retval: Task return value
            task_id: Unique task identifier
            args: Task positional arguments
            kwargs: Task keyword arguments
            top_k: For compatibility with tool registry
            **extra_kwargs: Additional parameters
        """
        logger.info(
            f"Task {self.name}[{task_id}] succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
            }
        )


class TaskQueueManager:
    """Manages Celery task queue operations."""
    
    def __init__(
        self,
        config: Optional[TaskQueueConfig] = None,
        app_name: str = "darwin_tasks",
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize task queue manager.
        
        Args:
            config: Task queue configuration
            app_name: Name of the Celery application
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
        """
        if not CELERY_AVAILABLE:
            raise ImportError(
                "Celery is not installed. Install with: pip install celery[redis]"
            )
        self.config = config or TaskQueueConfig()
        self.app_name = app_name
        self.app = self._create_app()
        self.redis_client = self._create_redis_client()
        
    def _create_app(self) -> Celery:
        """Create and configure Celery application."""
        app = Celery(self.app_name)
        app.config_from_object(self.config.to_dict())
        app.Task = DarwinTask
        return app
        
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client for direct operations."""
        try:
            client = redis.from_url(self.config.broker_url)
            client.ping()
            return client
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
            
    def task(
        self,
        name: Optional[str] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        **options
    ) -> Callable:
        """
        Decorator to register a task.
        
        Args:
            name: Task name
            priority: Task priority level
            **options: Additional task options
            
        Returns:
            Decorated task function
        """
        def decorator(func: Callable) -> Callable:
            task_name = name or f"{self.app_name}.{func.__name__}"
            return self.app.task(
                name=task_name,
                bind=True,
                priority=priority.value,
                **options
            )(func)
        return decorator
        
    def submit_task(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        countdown: Optional[int] = None,
        eta: Optional[datetime] = None,
        top_k: int = None,
        **options
    ) -> AsyncResult:
        """
        Submit a task for execution.
        
        Args:
            task_name: Name of the task to execute
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            priority: Task priority level
            countdown: Delay in seconds before execution
            eta: Specific time for execution
            top_k: For compatibility with tool registry
            **options: Additional task options
            
        Returns:
            AsyncResult object for tracking task
        """
        kwargs = kwargs or {}
        task = self.app.send_task(
            task_name,
            args=args,
            kwargs=kwargs,
            priority=priority.value,
            countdown=countdown,
            eta=eta,
            **options
        )
        logger.info(f"Submitted task {task_name} with ID {task.id}")
        return task
        
    def get_task_status(
        self,
        task_id: str,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get status of a task.
        
        Args:
            task_id: Unique task identifier
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with task status information
        """
        result = AsyncResult(task_id, app=self.app)
        return {
            "task_id": task_id,
            "status": result.state,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback,
            "info": result.info,
        }
        
    def cancel_task(
        self,
        task_id: str,
        terminate: bool = False,
        top_k: int = None,
        **kwargs
    ) -> bool:
        """
        Cancel a task.
        
        Args:
            task_id: Unique task identifier
            terminate: Whether to terminate the task forcefully
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            True if task was cancelled successfully
        """
        result = AsyncResult(task_id, app=self.app)
        result.revoke(terminate=terminate)
        logger.info(f"Cancelled task {task_id}")
        return True
        
    def get_active_tasks(
        self,
        top_k: int = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get list of active tasks.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            List of active task information
        """
        inspect = self.app.control.inspect()
        active = inspect.active()
        if not active:
            return []
            
        tasks = []
        for worker, worker_tasks in active.items():
            for task in worker_tasks:
                tasks.append({
                    "worker": worker,
                    "task_id": task.get("id"),
                    "name": task.get("name"),
                    "args": task.get("args"),
                    "kwargs": task.get("kwargs"),
                })
        return tasks
        
    def purge_queue(
        self,
        queue_name: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> int:
        """
        Purge all tasks from a queue.
        
        Args:
            queue_name: Name of the queue to purge (None for default)
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            Number of tasks purged
        """
        count = self.app.control.purge()
        logger.info(f"Purged {count} tasks from queue")
        return count
        
    def get_queue_length(
        self,
        queue_name: str = "celery",
        top_k: int = None,
        **kwargs
    ) -> int:
        """
        Get number of tasks in queue.
        
        Args:
            queue_name: Name of the queue
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            Number of tasks in queue
        """
        try:
            length = self.redis_client.llen(queue_name)
            return length
        except RedisError as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0