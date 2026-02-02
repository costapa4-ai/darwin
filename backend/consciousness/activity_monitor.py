"""
Darwin Activity Monitor - Centralized logging and monitoring system.

Tracks all Darwin activities including:
- Moltbook interactions (read, post, comment, vote)
- Internet/Web activity (searches, fetches)
- Thinking/Analysis (AI calls, reasoning)
- Creating (code generation, tool creation)
- Executing (tool runs, commands)
- Errors and failures

Provides:
- Persistent storage of activity logs
- Real-time streaming via WebSocket
- Aggregated statistics
- Error tracking and alerting
"""

import json
import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ActivityCategory(Enum):
    """Categories of Darwin activities"""
    MOLTBOOK = "moltbook"
    INTERNET = "internet"
    THINKING = "thinking"
    CREATING = "creating"
    EXECUTING = "executing"
    SYSTEM = "system"


class ActivityStatus(Enum):
    """Status of an activity"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class ActivityLog:
    """A single activity log entry"""
    id: str
    category: ActivityCategory
    action: str  # e.g., "read_post", "web_search", "generate_code"
    description: str
    status: ActivityStatus
    timestamp: datetime
    duration_ms: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "action": self.action,
            "description": self.description,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "details": self.details,
            "error": self.error
        }


@dataclass
class MoltbookStats:
    """Moltbook-specific statistics"""
    posts_read: int = 0
    posts_created: int = 0
    comments_made: int = 0
    upvotes_given: int = 0
    downvotes_given: int = 0
    karma: int = 0
    last_activity: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "posts_read": self.posts_read,
            "posts_created": self.posts_created,
            "comments_made": self.comments_made,
            "upvotes_given": self.upvotes_given,
            "downvotes_given": self.downvotes_given,
            "karma": self.karma,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None
        }


class ActivityMonitor:
    """
    Centralized activity monitoring system for Darwin.

    Usage:
        monitor = get_activity_monitor()

        # Log an activity
        activity_id = monitor.start_activity(
            category=ActivityCategory.MOLTBOOK,
            action="read_post",
            description="Reading post about AI consciousness"
        )

        # ... do the work ...

        monitor.complete_activity(activity_id, status=ActivityStatus.SUCCESS, details={...})

        # Or for quick logs:
        monitor.log_activity(
            category=ActivityCategory.INTERNET,
            action="web_search",
            description="Searching for Python optimization tips",
            status=ActivityStatus.SUCCESS
        )
    """

    def __init__(self, data_dir: str = "./data/monitor"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Activity logs (keep last 1000 in memory)
        self.logs: List[ActivityLog] = []
        self.max_logs_in_memory = 1000

        # Pending activities (started but not completed)
        self.pending: Dict[str, ActivityLog] = {}

        # Statistics
        self.stats = {
            "total_activities": 0,
            "successful": 0,
            "failed": 0,
            "by_category": defaultdict(int),
            "errors_last_hour": 0,
            "last_error": None,
            "last_error_time": None
        }

        # Moltbook-specific stats
        self.moltbook_stats = MoltbookStats()

        # WebSocket manager for real-time updates
        self.websocket_manager = None

        # Activity counter for IDs
        self._activity_counter = 0

        # Load persisted data
        self._load_state()

        logger.info("ActivityMonitor initialized")

    def _generate_id(self) -> str:
        """Generate a unique activity ID"""
        self._activity_counter += 1
        return f"act_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._activity_counter}"

    def start_activity(
        self,
        category: ActivityCategory,
        action: str,
        description: str,
        details: Dict[str, Any] = None
    ) -> str:
        """
        Start tracking an activity. Returns activity ID for later completion.
        """
        activity_id = self._generate_id()

        log = ActivityLog(
            id=activity_id,
            category=category,
            action=action,
            description=description,
            status=ActivityStatus.STARTED,
            timestamp=datetime.now(),
            details=details or {}
        )

        self.pending[activity_id] = log
        self._add_log(log)

        logger.info(f"[{category.value.upper()}] Started: {action} - {description}")

        return activity_id

    def complete_activity(
        self,
        activity_id: str,
        status: ActivityStatus = ActivityStatus.SUCCESS,
        details: Dict[str, Any] = None,
        error: Optional[str] = None
    ):
        """Complete a previously started activity"""
        if activity_id not in self.pending:
            logger.warning(f"Activity {activity_id} not found in pending")
            return

        log = self.pending.pop(activity_id)
        log.status = status
        log.duration_ms = int((datetime.now() - log.timestamp).total_seconds() * 1000)

        if details:
            log.details.update(details)

        if error:
            log.error = error
            self._record_error(log)

        # Update stats
        self.stats["total_activities"] += 1
        self.stats["by_category"][log.category.value] += 1

        if status == ActivityStatus.SUCCESS:
            self.stats["successful"] += 1
        elif status == ActivityStatus.FAILED:
            self.stats["failed"] += 1

        # Update Moltbook stats if applicable
        if log.category == ActivityCategory.MOLTBOOK:
            self._update_moltbook_stats(log)

        # Broadcast update
        self._broadcast_log(log)

        status_emoji = "✅" if status == ActivityStatus.SUCCESS else "❌" if status == ActivityStatus.FAILED else "⚠️"
        logger.info(f"[{log.category.value.upper()}] {status_emoji} {log.action}: {log.description} ({log.duration_ms}ms)")

    def log_activity(
        self,
        category: ActivityCategory,
        action: str,
        description: str,
        status: ActivityStatus = ActivityStatus.SUCCESS,
        details: Dict[str, Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None
    ):
        """Log a completed activity in one call"""
        log = ActivityLog(
            id=self._generate_id(),
            category=category,
            action=action,
            description=description,
            status=status,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            details=details or {},
            error=error
        )

        self._add_log(log)

        # Update stats
        self.stats["total_activities"] += 1
        self.stats["by_category"][category.value] += 1

        if status == ActivityStatus.SUCCESS:
            self.stats["successful"] += 1
        elif status == ActivityStatus.FAILED:
            self.stats["failed"] += 1
            self._record_error(log)

        # Update Moltbook stats if applicable
        if category == ActivityCategory.MOLTBOOK:
            self._update_moltbook_stats(log)

        # Broadcast update
        self._broadcast_log(log)

        status_emoji = "✅" if status == ActivityStatus.SUCCESS else "❌" if status == ActivityStatus.FAILED else "⚠️"
        logger.info(f"[{category.value.upper()}] {status_emoji} {action}: {description}")

    def log_error(
        self,
        category: ActivityCategory,
        action: str,
        error: str,
        details: Dict[str, Any] = None
    ):
        """Convenience method to log an error"""
        self.log_activity(
            category=category,
            action=action,
            description=f"Error: {error[:100]}",
            status=ActivityStatus.FAILED,
            error=error,
            details=details
        )

    def _add_log(self, log: ActivityLog):
        """Add log to memory and persist"""
        self.logs.append(log)

        # Trim if too many
        if len(self.logs) > self.max_logs_in_memory:
            self.logs = self.logs[-self.max_logs_in_memory:]

        # Persist periodically (every 10 logs)
        if len(self.logs) % 10 == 0:
            self._save_state()

    def _record_error(self, log: ActivityLog):
        """Record error for tracking"""
        self.stats["last_error"] = log.error
        self.stats["last_error_time"] = log.timestamp.isoformat()

        # Count errors in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.stats["errors_last_hour"] = sum(
            1 for l in self.logs
            if l.status == ActivityStatus.FAILED and l.timestamp > one_hour_ago
        )

    def _update_moltbook_stats(self, log: ActivityLog):
        """Update Moltbook-specific statistics based on actual results"""
        self.moltbook_stats.last_activity = log.timestamp

        # Only count successful actions
        if log.status != ActivityStatus.SUCCESS:
            return

        action = log.action.lower()
        details = log.details or {}

        # Try to parse actual counts from output_summary
        output_str = str(details.get("output_summary", ""))

        if "read" in action:
            # Try to extract posts_read count from output
            # Format: "{'success': True, 'posts_read': 5, ...}"
            match = re.search(r"'posts_read':\s*(\d+)", output_str)
            if match:
                self.moltbook_stats.posts_read += int(match.group(1))
            else:
                self.moltbook_stats.posts_read += 1

        elif "share" in action or "post" in action or "create_post" in action:
            # Check if post was actually created
            if "'success': True" in output_str or '"success": true' in output_str.lower():
                self.moltbook_stats.posts_created += 1

        elif "comment" in action:
            # Check if comment was actually made
            if "'success': True" in output_str or '"success": true' in output_str.lower():
                match = re.search(r"'comments_made':\s*(\d+)", output_str)
                if match:
                    self.moltbook_stats.comments_made += int(match.group(1))
                else:
                    self.moltbook_stats.comments_made += 1

        elif "upvote" in action:
            if "'success': True" in output_str or '"success": true' in output_str.lower():
                self.moltbook_stats.upvotes_given += 1

        elif "downvote" in action:
            if "'success': True" in output_str or '"success": true' in output_str.lower():
                self.moltbook_stats.downvotes_given += 1

    def _broadcast_log(self, log: ActivityLog):
        """Broadcast log to WebSocket clients"""
        if self.websocket_manager:
            try:
                asyncio.create_task(
                    self.websocket_manager.broadcast({
                        "type": "activity_log",
                        "data": log.to_dict()
                    })
                )
            except Exception as e:
                logger.debug(f"Could not broadcast log: {e}")

    def get_logs(
        self,
        limit: int = 100,
        category: Optional[ActivityCategory] = None,
        status: Optional[ActivityStatus] = None,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get recent activity logs with optional filtering"""
        logs = self.logs

        if category:
            logs = [l for l in logs if l.category == category]

        if status:
            logs = [l for l in logs if l.status == status]

        if since:
            logs = [l for l in logs if l.timestamp > since]

        # Return in chronological order (oldest first, newest last)
        return [l.to_dict() for l in logs[-limit:]]

    def get_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error logs"""
        errors = [l for l in self.logs if l.status == ActivityStatus.FAILED]
        return [l.to_dict() for l in errors[-limit:][::-1]]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics"""
        # Recalculate errors in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.stats["errors_last_hour"] = sum(
            1 for l in self.logs
            if l.status == ActivityStatus.FAILED and l.timestamp > one_hour_ago
        )

        return {
            **self.stats,
            "by_category": dict(self.stats["by_category"]),
            "pending_activities": len(self.pending),
            "moltbook": self.moltbook_stats.to_dict()
        }

    def _save_state(self):
        """Persist state to disk"""
        try:
            state = {
                "stats": {
                    **self.stats,
                    "by_category": dict(self.stats["by_category"])
                },
                "moltbook_stats": self.moltbook_stats.to_dict(),
                "recent_logs": [l.to_dict() for l in self.logs[-200:]],  # Save last 200
                "saved_at": datetime.now().isoformat()
            }

            state_file = self.data_dir / "activity_monitor_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to save monitor state: {e}")

    def _load_state(self):
        """Load state from disk"""
        try:
            state_file = self.data_dir / "activity_monitor_state.json"
            if not state_file.exists():
                return

            with open(state_file, 'r') as f:
                state = json.load(f)

            # Restore stats
            if "stats" in state:
                self.stats.update(state["stats"])
                self.stats["by_category"] = defaultdict(int, state["stats"].get("by_category", {}))

            # Restore Moltbook stats
            if "moltbook_stats" in state:
                ms = state["moltbook_stats"]
                self.moltbook_stats.posts_read = ms.get("posts_read", 0)
                self.moltbook_stats.posts_created = ms.get("posts_created", 0)
                self.moltbook_stats.comments_made = ms.get("comments_made", 0)
                self.moltbook_stats.upvotes_given = ms.get("upvotes_given", 0)
                self.moltbook_stats.downvotes_given = ms.get("downvotes_given", 0)
                self.moltbook_stats.karma = ms.get("karma", 0)
                if ms.get("last_activity"):
                    self.moltbook_stats.last_activity = datetime.fromisoformat(ms["last_activity"])

            logger.info(f"Loaded monitor state: {self.stats['total_activities']} activities tracked")

        except Exception as e:
            logger.error(f"Failed to load monitor state: {e}")


# Singleton instance
_activity_monitor: Optional[ActivityMonitor] = None


def get_activity_monitor() -> ActivityMonitor:
    """Get the global activity monitor instance"""
    global _activity_monitor
    if _activity_monitor is None:
        _activity_monitor = ActivityMonitor()
    return _activity_monitor


def init_activity_monitor(websocket_manager=None) -> ActivityMonitor:
    """Initialize the activity monitor with optional WebSocket manager"""
    global _activity_monitor
    _activity_monitor = ActivityMonitor()
    if websocket_manager:
        _activity_monitor.websocket_manager = websocket_manager
    return _activity_monitor
