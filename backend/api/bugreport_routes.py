"""
Bug Report Routes — Human-managed bug tracking system.

Simple CRUD for bug reports stored in SQLite. These are for Paulo
to track issues, NOT for Darwin to process autonomously.
"""

import sqlite3
import threading
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/bugreports", tags=["bugreports"])

# Thread-local SQLite connections
_local = threading.local()
_DB_PATH = "./data/darwin.db"


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, 'bug_conn') or _local.bug_conn is None:
        _local.bug_conn = sqlite3.connect(_DB_PATH)
        _local.bug_conn.row_factory = sqlite3.Row
        _local.bug_conn.execute("PRAGMA journal_mode=WAL")
    return _local.bug_conn


def _init_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bug_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            severity TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'general',
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()


# Initialize table on import
_init_table()


class BugReportCreate(BaseModel):
    title: str
    description: str
    severity: str = "medium"
    category: str = "general"


class BugReportStatusUpdate(BaseModel):
    status: str


@router.post("")
async def create_bug_report(report: BugReportCreate):
    """Create a new bug report."""
    if not report.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    if not report.description.strip():
        raise HTTPException(status_code=400, detail="Description is required")

    valid_severities = {"low", "medium", "high", "critical"}
    if report.severity not in valid_severities:
        raise HTTPException(status_code=400, detail=f"Severity must be one of: {valid_severities}")

    valid_categories = {"general", "frontend", "backend", "consciousness", "integration"}
    if report.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {valid_categories}")

    now = datetime.now().isoformat()
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO bug_reports (title, description, severity, category, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'open', ?, ?)""",
        (report.title.strip(), report.description.strip(), report.severity, report.category, now, now)
    )
    conn.commit()

    logger.info(f"Bug report created: #{cursor.lastrowid} - {report.title}")

    return {
        "id": cursor.lastrowid,
        "title": report.title.strip(),
        "description": report.description.strip(),
        "severity": report.severity,
        "category": report.category,
        "status": "open",
        "created_at": now,
        "updated_at": now
    }


@router.get("")
async def list_bug_reports(status: Optional[str] = None):
    """List all bug reports, optionally filtered by status."""
    conn = _get_conn()

    if status:
        rows = conn.execute(
            "SELECT * FROM bug_reports WHERE status = ? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM bug_reports ORDER BY created_at DESC"
        ).fetchall()

    reports = [dict(row) for row in rows]

    # Count by status
    counts = {}
    all_rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM bug_reports GROUP BY status"
    ).fetchall()
    for row in all_rows:
        counts[row["status"]] = row["count"]

    return {
        "reports": reports,
        "total": len(reports),
        "counts": counts
    }


@router.patch("/{report_id}/status")
async def update_bug_report_status(report_id: int, update: BugReportStatusUpdate):
    """Update the status of a bug report."""
    valid_statuses = {"open", "in_progress", "resolved", "closed"}
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    conn = _get_conn()
    row = conn.execute("SELECT * FROM bug_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Bug report not found")

    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE bug_reports SET status = ?, updated_at = ? WHERE id = ?",
        (update.status, now, report_id)
    )
    conn.commit()

    logger.info(f"Bug report #{report_id} status → {update.status}")

    return {"id": report_id, "status": update.status, "updated_at": now}


@router.delete("/{report_id}")
async def delete_bug_report(report_id: int):
    """Delete a bug report."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM bug_reports WHERE id = ?", (report_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Bug report not found")

    conn.execute("DELETE FROM bug_reports WHERE id = ?", (report_id,))
    conn.commit()

    logger.info(f"Bug report #{report_id} deleted")

    return {"deleted": True, "id": report_id}
