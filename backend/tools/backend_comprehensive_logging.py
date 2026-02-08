"""
Comprehensive structured logging system with correlation IDs and context tracking.

This module provides a production-ready logging infrastructure with:
- Structured JSON logging
- Request/correlation ID tracking
- Contextual information
- Thread-safe context management
- Performance monitoring
- Audit trail capabilities
"""

import json
import logging
import threading
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

# Context variables for tracking request context across async boundaries
request_context: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class StructuredLogger:
    """
    Thread-safe structured logger with correlation ID support.
    
    Provides JSON-formatted logging with automatic context enrichment,
    correlation ID tracking, and performance monitoring capabilities.
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        enable_console: bool = True,
        enable_file: bool = False,
        log_file: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name (typically module name)
            level: Logging level (default: INFO)
            enable_console: Enable console output
            enable_file: Enable file output
            log_file: Path to log file if file output enabled
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for tool registry compatibility
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.handlers.clear()
        
        # Create formatters
        self.json_formatter = JSONFormatter()
        
        # Add console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(self.json_formatter)
            self.logger.addHandler(console_handler)
        
        # Add file handler
        if enable_file and log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(level)
                file_handler.setFormatter(self.json_formatter)
                self.logger.addHandler(file_handler)
            except (IOError, OSError) as e:
                self.logger.error(f"Failed to create file handler: {e}")
        
        self._local = threading.local()
    
    def _get_context(self) -> Dict[str, Any]:
        """
        Get current logging context.
        
        Returns:
            Dictionary containing current context information
        """
        try:
            ctx = request_context.get()
        except LookupError:
            ctx = {}
        
        # Merge with thread-local context
        thread_ctx = getattr(self._local, 'context', {})
        return {**ctx, **thread_ctx}
    
    def set_context(
        self,
        **context_data: Any
    ) -> None:
        """
        Set context data for subsequent log entries.
        
        Args:
            **context_data: Key-value pairs to add to context
        """
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        self._local.context.update(context_data)
    
    def clear_context(self) -> None:
        """Clear thread-local context data."""
        if hasattr(self._local, 'context'):
            self._local.context.clear()
    
    def _log(
        self,
        level: int,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Internal logging method with context enrichment.
        
        Args:
            level: Log level
            message: Log message
            extra_data: Additional data to include
            exc_info: Exception information
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for tool registry compatibility
        """
        try:
            context = self._get_context()
            log_data = {
                'message': message,
                'context': context,
            }
            
            if extra_data:
                log_data['data'] = extra_data
            
            self.logger.log(
                level,
                json.dumps(log_data),
                exc_info=exc_info,
                extra={'structured_data': log_data}
            )
        except Exception as e:
            # Fallback to basic logging if structured logging fails
            self.logger.error(f"Logging error: {e}. Original message: {message}")
    
    def debug(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, extra_data, **kwargs)
    
    def info(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """Log info message."""
        self._log(logging.INFO, message, extra_data, **kwargs)
    
    def warning(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, extra_data, **kwargs)
    
    def error(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, extra_data, exc_info, **kwargs)
    
    def critical(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None,
        top_k: int = None,
        **kwargs
    ) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, extra_data, exc_info, **kwargs)


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Formats log records as JSON with timestamp, level, message,
    and contextual information.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        try:
            log_data = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'level': record.levelname,
                'logger': record.name,
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno,
            }
            
            # Add structured data if available
            if hasattr(record, 'structured_data'):
                log_data.update(record.structured_data)
            else:
                log_data['message'] = record.getMessage()
            
            # Add exception info if present
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data, default=str)
        except Exception as e:
            # Fallback to basic format if JSON serialization fails
            return f'{{"timestamp": "{datetime.utcnow().isoformat()}Z", "level": "ERROR", "message": "Logging error: {e}"}}'


class CorrelationIDManager:
    """
    Manages correlation IDs for request tracking.
    
    Provides utilities for generating and managing correlation IDs
    that can be used to trace requests across service boundaries.
    """
    
    @staticmethod
    def generate_id() -> str:
        """
        Generate a new correlation ID.
        
        Returns:
            UUID-based correlation ID
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def set_correlation_id(correlation_id: Optional[str] = None) -> str:
        """
        Set correlation ID in context.
        
        Args:
            correlation_id: Correlation ID to set (generates new if None)
            
        Returns:
            The correlation ID that was set
        """
        if correlation_id is None:
            correlation_id = CorrelationIDManager.generate_id()
        
        ctx = request_context.get().copy() if request_context.get() else {}
        ctx['correlation_id'] = correlation_id
        request_context.set(ctx)
        
        return correlation_id
    
    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """
        Get current correlation ID from context.
        
        Returns:
            Current correlation ID or None
        """
        try:
            ctx = request_context.get()
            return ctx.get('correlation_id')
        except LookupError:
            return None
    
    @staticmethod
    def clear_correlation_id() -> None:
        """Clear correlation ID from context."""
        try:
            ctx = request_context.get().copy()
            ctx.pop('correlation_id', None)
            request_context.set(ctx)
        except LookupError:
            pass


def with_correlation_id(func: Callable) -> Callable:
    """
    Decorator to automatically manage correlation IDs.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with correlation ID management
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Generate or use existing correlation ID
        existing_id = CorrelationIDManager.get_correlation_id()
        if not existing_id:
            CorrelationIDManager.set_correlation_id()
        
        try:
            return func(*args, **kwargs)
        finally:
            # Clean up if we created the ID
            if not existing_id:
                CorrelationIDManager.clear_correlation_id()
    
    return wrapper


def log_performance(logger: StructuredLogger, operation: str) -> Callable:
    """
    Decorator to log function performance metrics.
    
    Args:
        logger: StructuredLogger instance
        operation: Name of the operation being measured
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                duration = time.time() - start_time
                
                log_data = {
                    'operation': operation,
                    'duration_seconds': duration,
                    'success': error is None,
                }
                
                if error:
                    log_data['error'] = str(error)
                    logger.error(f"Operation '{operation}' failed", extra_data=log_data, exc_info=error)
                else:
                    logger.info(f"Operation '{operation}' completed", extra_data=log_data)
        
        return wrapper
    return decorator


def create_logger(
    name: str,
    level: int = logging.INFO,
    enable_console: bool = True,
    enable_file: bool = False,
    log_file: Optional[str] = None
) -> StructuredLogger:
    """
    Factory function to create a structured logger.
    
    Args:
        name: Logger name
        level: Logging level
        enable_console: Enable console output
        enable_file: Enable file output
        log_file: Path to log file
        
    Returns:
        Configured StructuredLogger instance
    """
    return StructuredLogger(
        name=name,
        level=level,
        enable_console=enable_console,
        enable_file=enable_file,
        log_file=log_file
    )