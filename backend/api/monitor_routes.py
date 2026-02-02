"""
Monitor API Routes - Real-time activity monitoring for Darwin.

Provides endpoints for:
- Activity log streaming
- Aggregated statistics
- Error tracking
- Moltbook statistics
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from consciousness.activity_monitor import (
    get_activity_monitor,
    ActivityCategory,
    ActivityStatus
)
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/monitor", tags=["monitor"])


class ActivityLogResponse(BaseModel):
    id: str
    category: str
    action: str
    description: str
    status: str
    timestamp: str
    duration_ms: Optional[int] = None
    details: dict = {}
    error: Optional[str] = None


class StatsResponse(BaseModel):
    total_activities: int
    successful: int
    failed: int
    by_category: dict
    errors_last_hour: int
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    pending_activities: int
    moltbook: dict


@router.get("/logs")
async def get_activity_logs(
    limit: int = Query(100, ge=1, le=500),
    category: Optional[str] = None,
    status: Optional[str] = None,
    since_minutes: Optional[int] = None
):
    """
    Get recent activity logs.

    Args:
        limit: Maximum number of logs to return (1-500)
        category: Filter by category (moltbook, internet, thinking, creating, executing, system)
        status: Filter by status (started, success, failed, partial)
        since_minutes: Only show logs from last N minutes
    """
    monitor = get_activity_monitor()

    # Parse category filter
    cat_filter = None
    if category:
        try:
            cat_filter = ActivityCategory(category.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid category: {category}")

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = ActivityStatus(status.lower())
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")

    # Parse time filter
    since = None
    if since_minutes:
        since = datetime.now() - timedelta(minutes=since_minutes)

    logs = monitor.get_logs(
        limit=limit,
        category=cat_filter,
        status=status_filter,
        since=since
    )

    return {
        "logs": logs,
        "total": len(logs),
        "filters": {
            "category": category,
            "status": status,
            "since_minutes": since_minutes
        }
    }


@router.get("/errors")
async def get_error_logs(limit: int = Query(50, ge=1, le=200)):
    """Get recent error logs"""
    monitor = get_activity_monitor()
    errors = monitor.get_errors(limit=limit)

    return {
        "errors": errors,
        "total": len(errors),
        "errors_last_hour": monitor.stats.get("errors_last_hour", 0)
    }


@router.get("/stats")
async def get_monitor_stats():
    """Get aggregated activity statistics"""
    monitor = get_activity_monitor()
    stats = monitor.get_stats()

    return stats


@router.get("/moltbook")
async def get_moltbook_stats():
    """Get Moltbook-specific statistics"""
    monitor = get_activity_monitor()

    return {
        "stats": monitor.moltbook_stats.to_dict(),
        "recent_activity": monitor.get_logs(
            limit=20,
            category=ActivityCategory.MOLTBOOK
        )
    }


@router.get("/categories")
async def get_category_breakdown():
    """Get activity breakdown by category"""
    monitor = get_activity_monitor()
    stats = monitor.get_stats()

    # Get recent logs for each category
    categories = {}
    for cat in ActivityCategory:
        cat_logs = monitor.get_logs(limit=10, category=cat)
        categories[cat.value] = {
            "count": stats["by_category"].get(cat.value, 0),
            "recent": cat_logs
        }

    return {
        "categories": categories,
        "total": stats["total_activities"]
    }


@router.get("/live")
async def get_live_status():
    """Get current live status for real-time monitoring"""
    monitor = get_activity_monitor()
    stats = monitor.get_stats()

    # Get very recent logs (last 5 minutes)
    recent = monitor.get_logs(limit=20, since=datetime.now() - timedelta(minutes=5))

    # Get pending activities
    pending = [
        {
            "id": log.id,
            "category": log.category.value,
            "action": log.action,
            "description": log.description,
            "started_at": log.timestamp.isoformat(),
            "elapsed_ms": int((datetime.now() - log.timestamp).total_seconds() * 1000)
        }
        for log in monitor.pending.values()
    ]

    return {
        "status": "healthy" if stats["errors_last_hour"] < 10 else "degraded",
        "pending_activities": pending,
        "recent_logs": recent,
        "stats_summary": {
            "total": stats["total_activities"],
            "successful": stats["successful"],
            "failed": stats["failed"],
            "errors_last_hour": stats["errors_last_hour"]
        },
        "last_error": stats.get("last_error"),
        "last_error_time": stats.get("last_error_time"),
        "timestamp": datetime.now().isoformat()
    }


# Initialize monitor (called from main app setup)
def initialize_monitor(websocket_manager=None):
    """Initialize the activity monitor with WebSocket support"""
    from consciousness.activity_monitor import init_activity_monitor
    monitor = init_activity_monitor(websocket_manager)
    logger.info("Activity monitor initialized for API routes")
    return monitor
