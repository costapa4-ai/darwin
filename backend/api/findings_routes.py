"""
Findings API Routes - REST endpoints for Darwin's Findings Inbox

Provides endpoints for:
- Listing findings (active, unread, by type)
- Getting finding details
- Marking findings as read
- Dismissing findings
- Statistics
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from consciousness.findings_inbox import (
    get_findings_inbox,
    FindingType,
    FindingPriority
)
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


class DismissRequest(BaseModel):
    """Request body for dismissing a finding."""
    reason: Optional[str] = None


class CreateFindingRequest(BaseModel):
    """Request body for creating a finding manually (for testing)."""
    type: str
    title: str
    description: str
    source: str = "manual"
    priority: str = "medium"
    expires_in_days: int = 7
    metadata: Optional[dict] = None


@router.get("")
async def list_findings(
    limit: int = 50,
    type: Optional[str] = None,
    unread_only: bool = False,
    min_priority: Optional[str] = None
):
    """
    List findings with optional filters.

    Query params:
    - limit: Maximum number of findings (default 50)
    - type: Filter by finding type (discovery, insight, anomaly, suggestion, curiosity)
    - unread_only: Only show unread findings
    - min_priority: Minimum priority (low, medium, high, urgent)
    """
    inbox = get_findings_inbox()

    try:
        if unread_only:
            findings = inbox.get_unread(limit=limit)
        elif type:
            finding_type = FindingType(type.lower())
            findings = inbox.get_by_type(finding_type, include_viewed=True, limit=limit)
        elif min_priority:
            priority = FindingPriority[min_priority.upper()]
            findings = inbox.get_by_priority(min_priority=priority, limit=limit)
        else:
            findings = inbox.get_all_active(limit=limit)

        return {
            "findings": findings,
            "count": len(findings),
            "unread_count": inbox.get_unread_count()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filter value: {e}")


@router.get("/unread")
async def get_unread_findings(limit: int = 20):
    """Get unread findings sorted by priority."""
    inbox = get_findings_inbox()

    findings = inbox.get_unread(limit=limit)

    return {
        "findings": findings,
        "count": len(findings),
        "total_unread": inbox.get_unread_count()
    }


@router.get("/count")
async def get_findings_count():
    """Get quick count of unread findings (for badge display)."""
    inbox = get_findings_inbox()

    return {
        "unread_count": inbox.get_unread_count(),
        "total_active": inbox.get_statistics()["total_active"]
    }


@router.get("/statistics")
async def get_findings_statistics():
    """Get detailed inbox statistics."""
    inbox = get_findings_inbox()

    return inbox.get_statistics()


@router.get("/{finding_id}")
async def get_finding(finding_id: str):
    """Get a specific finding by ID."""
    inbox = get_findings_inbox()

    finding = inbox.get_finding(finding_id)

    if not finding:
        raise HTTPException(status_code=404, detail=f"Finding not found: {finding_id}")

    return finding


@router.post("/{finding_id}/read")
async def mark_finding_read(finding_id: str):
    """Mark a finding as read/viewed."""
    inbox = get_findings_inbox()

    success = inbox.mark_as_read(finding_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Finding not found: {finding_id}")

    return {
        "success": True,
        "message": f"Finding {finding_id} marked as read"
    }


@router.post("/{finding_id}/dismiss")
async def dismiss_finding(finding_id: str, request: Optional[DismissRequest] = None):
    """Dismiss a finding (remove from active list)."""
    inbox = get_findings_inbox()

    success = inbox.dismiss(finding_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Finding not found: {finding_id}")

    return {
        "success": True,
        "message": f"Finding {finding_id} dismissed",
        "reason": request.reason if request else None
    }


@router.delete("/{finding_id}")
async def delete_finding(finding_id: str):
    """Delete a finding (alias for dismiss)."""
    return await dismiss_finding(finding_id)


@router.post("/cleanup")
async def trigger_cleanup(max_age_days: int = 7):
    """Manually trigger cleanup of expired findings."""
    inbox = get_findings_inbox()

    removed = inbox.auto_cleanup(max_age_days=max_age_days)

    return {
        "success": True,
        "removed_count": removed,
        "message": f"Cleaned up {removed} expired findings"
    }


@router.post("")
async def create_finding(request: CreateFindingRequest):
    """
    Create a finding manually (primarily for testing).

    In production, findings are created by proactive actions.
    """
    inbox = get_findings_inbox()

    try:
        finding_type = FindingType(request.type.lower())
        priority = FindingPriority[request.priority.upper()]

        finding_id = inbox.add_finding(
            type=finding_type,
            title=request.title,
            description=request.description,
            source=request.source,
            priority=priority,
            expires_in_days=request.expires_in_days,
            metadata=request.metadata
        )

        return {
            "success": True,
            "finding_id": finding_id,
            "message": f"Finding created: {request.title}"
        }

    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}")


@router.post("/mark-all-read")
async def mark_all_read():
    """Mark all active findings as read."""
    inbox = get_findings_inbox()

    count = 0
    for finding in inbox.findings:
        if finding.is_active() and not finding.is_viewed():
            finding.viewed_at = __import__('datetime').datetime.now().isoformat()
            count += 1

    if count > 0:
        inbox._save_state()

    return {
        "success": True,
        "marked_count": count,
        "message": f"Marked {count} findings as read"
    }
