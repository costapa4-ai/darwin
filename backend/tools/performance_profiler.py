"""
Performance Profiler Module for Darwin System

This module provides comprehensive performance profiling capabilities including
execution time tracking, memory usage monitoring, function call analysis, and
performance bottleneck identification.
"""

import time
import functools
import logging
import json
import os
import sys
import tracemalloc
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import statistics


@dataclass
class ProfileRecord:
    """Record of a single profiling measurement."""
    function_name: str
    module_name: str
    start_time: float
    end_time: float
    duration: float
    memory_start: float
    memory_end: float
    memory_delta: float
    call_count: int
    thread_id: int
    timestamp: str
    args_repr: str = ""
    kwargs_repr: str = ""
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary."""
        return asdict(self)


@dataclass
class AggregatedStats:
    """Aggregated statistics for a profiled function."""
    function_name: str
    total_calls: int
    total_duration: float
    avg_duration: float
    min_duration: float
    max_duration: float
    median_duration: float
    std_duration: float
    total_memory_delta: float
    avg_memory_delta: float
    max_memory_delta: float
    error_count: int
    durations: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary, excluding raw durations."""
        data = asdict(self)
        data.pop('durations', None)
        return data


class PerformanceProfiler:
    """
    Comprehensive performance profiler for the Darwin System.
    
    Features:
    - Function execution time tracking
    - Memory usage monitoring
    - Call count statistics
    - Bottleneck identification
    - Thread-safe operation
    - Export to multiple formats (JSON, CSV, HTML)
    """
    
    def __init__(
        self,
        enabled: bool = True,
        track_memory: bool = True,
        log_level: int = logging.INFO,
        output_dir: Optional[str] = None
    ):
        """
        Initialize the performance profiler.
        
        Args:
            enabled: Whether profiling is enabled
            track_memory: Whether to track memory usage
            log_level: Logging level
            output_dir: Directory for profiling output files
        """
        self.enabled = enabled
        self.track_memory = track_memory
        self.records: List[ProfileRecord] = []
        self.aggregated_stats: Dict[str, AggregatedStats] = {}
        self._lock = threading.Lock()
        self._memory_tracking_started = False
        
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.output_dir = Path("profiling_results")
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        if self.track_memory and self.enabled:
            try:
                tracemalloc.start()
                self._memory_tracking_started = True
            except Exception as e:
                self.logger.warning(f"Failed to start memory tracking: {e}")
                self.track_memory = False
    
    def profile(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        track_args: bool = False
    ) -> Callable:
        """
        Decorator to profile a function.
        
        Args:
            func: Function to profile
            name: Custom name for the profiled function
            track_args: Whether to track function arguments
            
        Returns:
            Decorated function
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not self.enabled:
                    return f(*args, **kwargs)
                
                func_name = name or f.__name__
                module_name = f.__module__
                thread_id = threading.get_ident()
                timestamp = datetime.now().isoformat()
                
                args_repr = ""
                kwargs_repr = ""
                if track_args:
                    try:
                        args_repr = str(args)[:100]
                        kwargs_repr = str(kwargs)[:100]
                    except Exception:
                        args_repr = "<unable to represent>"
                        kwargs_repr = "<unable to represent>"
                
                memory_start = 0.0
                memory_end = 0.0
                if self.track_memory and self._memory_tracking_started:
                    try:
                        current, peak = tracemalloc.get_traced_memory()
                        memory_start = current / 1024 / 1024
                    except Exception:
                        pass
                
                start_time = time.perf_counter()
                exception_info = None
                
                try:
                    result = f(*args, **kwargs)
                    return result
                except Exception as e:
                    exception_info = f"{type(e).__name__}: {str(e)}"
                    raise
                finally:
                    end_time = time.perf_counter()
                    duration = end_time - start_time
                    
                    if self.track_memory and self._memory_tracking_started:
                        try:
                            current, peak = tracemalloc.get_traced_memory()
                            memory_end = current / 1024 / 1024
                        except Exception:
                            pass
                    
                    memory_delta = memory_end - memory_start
                    
                    record = ProfileRecord(
                        function_name=func_name,
                        module_name=module_name,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        memory_start=memory_start,
                        memory_end=memory_end,
                        memory_delta=memory_delta,
                        call_count=1,
                        thread_id=thread_id,
                        timestamp=timestamp,
                        args_repr=args_repr,
                        kwargs_repr=kwargs_repr,
                        exception=exception_info
                    )
                    
                    with self._lock:
                        self.records.append(record)
                        self._update_aggregated_stats(record)
            
            return wrapper
        
        if func is None:
            return decorator
        else:
            return decorator(func)
    
    def _update_aggregated_stats(self, record: ProfileRecord) -> None:
        """Update aggregated statistics with a new record."""
        func_key = f"{record.module_name}.{record.function_name}"
        
        if func_key not in self.aggregated_stats:
            self.aggregated_stats[func_key] = AggregatedStats(
                function_name=func_key,
                total_calls=0,
                total_duration=0.0,
                avg_duration=0.0,
                min_duration=float('inf'),
                max_duration=0.0,
                median_duration=0.0,
                std_duration=0.0,
                total_memory_delta=0.0,
                avg_memory_delta=0.0,
                max_memory_delta=0.0,
                error_count=0,
                durations=[]
            )