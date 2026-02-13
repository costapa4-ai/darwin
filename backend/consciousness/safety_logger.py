"""
Safety Event Logger — Persistent tracking of all safety mechanism activations.

Logs every time a safety constraint fires: rollbacks, protected file redirects,
tool rejections, validation failures, model fallbacks, early stops.

This data feeds directly into alignment research publications — measuring
how often and why safety mechanisms activate in a self-modifying AI system.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)

_local = threading.local()
_instance = None


class SafetyLogger:
    """Logs safety events to SQLite for research analysis."""

    EVENT_TYPES = {
        'prompt_rollback',          # Prompt variant rolled back for underperformance
        'prompt_promoted',          # Prompt variant promoted (evolution working)
        'protected_file_redirect',  # Code gen redirected away from critical file
        'code_validation_fail',     # Generated code failed validation
        'code_validation_corrected',# Code needed correction attempts to pass
        'tool_rejected',            # Autonomous loop rejected disallowed tool
        'model_fallback',           # Router fell back to different model
        'routing_decision',         # Model routing decision (for analysis)
        'early_stop',               # Autonomous loop stopped early
        'truncation_retry',         # Response truncated, retrying with more tokens
    }

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self._init_table()
        logger.info("SafetyLogger initialized")

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(_local, 'safety_conn') or _local.safety_conn is None:
            _local.safety_conn = sqlite3.connect(self.db_path)
            _local.safety_conn.row_factory = sqlite3.Row
            _local.safety_conn.execute("PRAGMA journal_mode=WAL")
        return _local.safety_conn

    def _init_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS safety_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                details TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_safety_type
            ON safety_events(event_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_safety_time
            ON safety_events(timestamp)
        """)
        conn.commit()

    def log(self, event_type: str, source: str, details: dict = None,
            severity: str = 'info'):
        """Log a safety event. Fire-and-forget, never raises."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO safety_events (timestamp, event_type, source, severity, details) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    datetime.utcnow().isoformat(),
                    event_type,
                    source,
                    severity,
                    json.dumps(details or {}, default=str),
                )
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"SafetyLogger.log failed: {e}")

    def get_events(self, event_type: str = None, since_hours: int = 24,
                   limit: int = 100) -> List[dict]:
        """Query recent safety events."""
        try:
            conn = self._get_conn()
            since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
            if event_type:
                rows = conn.execute(
                    "SELECT * FROM safety_events WHERE event_type = ? AND timestamp > ? "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (event_type, since, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM safety_events WHERE timestamp > ? "
                    "ORDER BY timestamp DESC LIMIT ?",
                    (since, limit)
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_summary(self, since_hours: int = 24) -> dict:
        """Get aggregate counts by event type."""
        try:
            conn = self._get_conn()
            since = (datetime.utcnow() - timedelta(hours=since_hours)).isoformat()
            rows = conn.execute(
                "SELECT event_type, COUNT(*) as count FROM safety_events "
                "WHERE timestamp > ? GROUP BY event_type ORDER BY count DESC",
                (since,)
            ).fetchall()
            return {r['event_type']: r['count'] for r in rows}
        except Exception:
            return {}

    def get_total_count(self) -> int:
        """Total safety events ever logged."""
        try:
            conn = self._get_conn()
            row = conn.execute("SELECT COUNT(*) as n FROM safety_events").fetchone()
            return row['n'] if row else 0
        except Exception:
            return 0


def get_safety_logger() -> SafetyLogger:
    """Get or create the singleton SafetyLogger."""
    global _instance
    if _instance is None:
        _instance = SafetyLogger()
    return _instance
