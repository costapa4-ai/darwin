"""
Centralized Error Tracking System
Stores and analyzes all system errors for later inspection
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque
import threading


class ErrorLogStore:
    """
    Centralized error log storage for analysis
    Thread-safe in-memory storage of all errors
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.errors = deque(maxlen=1000)  # Keep last 1000 errors
        self.error_counts = {}  # Count errors by type
        self.log_file = Path("/app/logs/errors.log")
        self.log_file.parent.mkdir(exist_ok=True, parents=True)

    def log_error(self, error_data: Dict):
        """
        Log an error to the central store

        Args:
            error_data: Dictionary with error information
        """
        with self._lock:
            # Add timestamp if not present
            if 'timestamp' not in error_data:
                error_data['timestamp'] = datetime.utcnow().isoformat()

            # Store in memory
            self.errors.append(error_data)

            # Count by type
            error_type = error_data.get('type', 'unknown')
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

            # Persist to file
            try:
                with open(self.log_file, 'a') as f:
                    f.write(json.dumps(error_data) + '\n')
            except Exception as e:
                print(f"Failed to write error log: {e}")

    def get_recent_errors(self, limit: int = 100, level: Optional[str] = None,
                         component: Optional[str] = None) -> List[Dict]:
        """Get recent errors with optional filtering"""
        with self._lock:
            errors = list(self.errors)

            # Filter by level if specified
            if level:
                errors = [e for e in errors if e.get('level') == level]

            # Filter by component if specified
            if component:
                errors = [e for e in errors if e.get('component') == component]

            return errors[-limit:]

    def get_error_summary(self) -> Dict:
        """Get summary statistics about errors"""
        with self._lock:
            total_errors = len(self.errors)

            # Count by level
            by_level = {}
            by_component = {}

            for error in self.errors:
                level = error.get('level', 'unknown')
                by_level[level] = by_level.get(level, 0) + 1

                component = error.get('component', 'unknown')
                by_component[component] = by_component.get(component, 0) + 1

            # Recent errors (last 10)
            recent = list(self.errors)[-10:]

            return {
                'total_errors': total_errors,
                'by_type': dict(self.error_counts),
                'by_level': by_level,
                'by_component': by_component,
                'recent_errors': recent,
                'log_file': str(self.log_file)
            }

    def get_errors_by_component(self, component: str) -> List[Dict]:
        """Get all errors for a specific component"""
        with self._lock:
            return [e for e in self.errors if e.get('component') == component]

    def get_critical_errors(self) -> List[Dict]:
        """Get all ERROR and CRITICAL level errors"""
        with self._lock:
            return [e for e in self.errors if e.get('level') in ['ERROR', 'CRITICAL']]

    def clear_errors(self):
        """Clear all stored errors"""
        with self._lock:
            self.errors.clear()
            self.error_counts.clear()


# Global instance
error_store = ErrorLogStore()
