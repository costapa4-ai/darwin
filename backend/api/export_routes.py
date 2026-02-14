"""
Data Export API Routes — Download Darwin's collected data as CSV/JSON for graphing.

Endpoints:
- GET /api/v1/export/activities    — Activity log (CSV or JSON)
- GET /api/v1/export/costs         — Cost snapshots over time
- GET /api/v1/export/cycles        — Wake/sleep cycle history
- GET /api/v1/export/genome        — Genome mutation changelog
- GET /api/v1/export/routing       — Per-model routing stats
- GET /api/v1/export/all           — All datasets bundled as JSON
"""

import csv
import io
import json
from datetime import datetime
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/export", tags=["export"])


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _to_csv(rows: list, fieldnames: list) -> str:
    """Convert list of dicts to CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def _csv_response(content: str, filename: str):
    """Return a streaming CSV response with download headers."""
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _json_response(data, filename: str):
    """Return a streaming JSON response with download headers."""
    content = json.dumps(data, indent=2, default=str, ensure_ascii=False)
    return StreamingResponse(
        io.BytesIO(content.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== Activities ====================

@router.get("/activities")
async def export_activities(
    format: str = Query("csv", regex="^(csv|json)$"),
    limit: int = Query(1000, ge=1, le=5000)
):
    """Export activity log data."""
    from consciousness.activity_monitor import get_activity_monitor

    monitor = _safe(get_activity_monitor)
    if not monitor:
        return {"error": "Activity monitor not available"}

    logs = monitor.get_logs(limit=limit)  # Returns List[Dict]
    rows = []
    for log in logs:
        rows.append({
            "timestamp": str(log.get("timestamp", "")),
            "category": str(log.get("category", "")),
            "action": log.get("action", ""),
            "description": str(log.get("description", ""))[:200],
            "status": str(log.get("status", "")),
            "duration_ms": log.get("duration_ms") or 0,
            "error": log.get("error") or ""
        })

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    if format == "json":
        return _json_response(rows, f"darwin_activities_{ts}.json")

    fields = ["timestamp", "category", "action", "description", "status", "duration_ms", "error"]
    return _csv_response(_to_csv(rows, fields), f"darwin_activities_{ts}.csv")


# ==================== Costs ====================

@router.get("/costs")
async def export_costs(
    format: str = Query("csv", regex="^(csv|json)$")
):
    """Export cost tracking data."""
    from app.lifespan import get_service

    fin = _safe(lambda: get_service('financial_consciousness'))
    rows = []

    if fin:
        # Get cost history snapshots
        history = getattr(fin, 'cost_history', [])
        for snap in history:
            rows.append({
                "timestamp": str(getattr(snap, 'timestamp', '')),
                "total_cost": getattr(snap, 'total_cost', 0),
                "requests_count": getattr(snap, 'requests_count', 0),
                "haiku_cost": getattr(snap, 'breakdown', {}).get('haiku', 0),
                "gemini_cost": getattr(snap, 'breakdown', {}).get('gemini', 0),
                "claude_cost": getattr(snap, 'breakdown', {}).get('claude', 0),
                "ollama_cost": getattr(snap, 'breakdown', {}).get('ollama', 0),
            })

    # Also get current session from router
    from app.lifespan import get_service
    router_svc = _safe(lambda: get_service('multi_model_router'))
    if router_svc:
        stats = _safe(lambda: router_svc.get_router_stats(), {})
        perf = stats.get('performance_stats', {})
        if perf:
            rows.append({
                "timestamp": datetime.utcnow().isoformat(),
                "total_cost": sum(m.get('total_cost_estimate', 0) for m in perf.values()),
                "requests_count": sum(m.get('total_requests', 0) for m in perf.values()),
                "haiku_cost": perf.get('haiku', {}).get('total_cost_estimate', 0),
                "gemini_cost": perf.get('gemini', {}).get('total_cost_estimate', 0),
                "claude_cost": perf.get('claude', {}).get('total_cost_estimate', 0),
                "ollama_cost": perf.get('ollama', {}).get('total_cost_estimate', 0),
            })

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    if format == "json":
        return _json_response(rows, f"darwin_costs_{ts}.json")

    fields = ["timestamp", "total_cost", "requests_count", "haiku_cost", "gemini_cost", "claude_cost", "ollama_cost"]
    return _csv_response(_to_csv(rows, fields), f"darwin_costs_{ts}.csv")


# ==================== Cycles ====================

@router.get("/cycles")
async def export_cycles(
    format: str = Query("csv", regex="^(csv|json)$"),
    limit: int = Query(200, ge=1, le=1000)
):
    """Export wake/sleep cycle data with activity and dream counts."""
    from app.lifespan import get_service

    engine = _safe(lambda: get_service('consciousness_engine'))
    rows = []

    if engine:
        # Wake activities
        activities = getattr(engine, 'wake_activities', [])[-limit:]
        for a in activities:
            rows.append({
                "timestamp": str(a.started_at),
                "type": "activity",
                "category": a.type,
                "description": a.description[:150],
                "success": a.result.get('success', True) if isinstance(a.result, dict) else True,
                "insights_count": len(a.insights) if a.insights else 0,
                "duration_ms": (a.completed_at - a.started_at).total_seconds() * 1000 if a.completed_at and a.started_at else 0
            })

        # Sleep dreams
        dreams = getattr(engine, 'sleep_dreams', [])[-limit:]
        for d in dreams:
            rows.append({
                "timestamp": str(d.started_at),
                "type": "dream",
                "category": d.topic[:50] if d.topic else "",
                "description": d.description[:150],
                "success": d.success,
                "insights_count": len(d.insights) if d.insights else 0,
                "duration_ms": (d.completed_at - d.started_at).total_seconds() * 1000 if d.completed_at and d.started_at else 0
            })

    # Sort by timestamp
    rows.sort(key=lambda r: r.get("timestamp", ""))

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    if format == "json":
        return _json_response(rows, f"darwin_cycles_{ts}.json")

    fields = ["timestamp", "type", "category", "description", "success", "insights_count", "duration_ms"]
    return _csv_response(_to_csv(rows, fields), f"darwin_cycles_{ts}.csv")


# ==================== Genome ====================

@router.get("/genome")
async def export_genome(
    format: str = Query("csv", regex="^(csv|json)$")
):
    """Export genome mutation history."""
    from consciousness.genome_manager import get_genome

    genome = _safe(get_genome)
    rows = []

    if genome:
        changelog = genome._version.get("changelog", [])
        for entry in changelog:
            rows.append({
                "timestamp": entry.get("timestamp", ""),
                "version": entry.get("version", 0),
                "domain": entry.get("domain", ""),
                "key": entry.get("key", ""),
                "old_value": json.dumps(entry.get("old_value"), default=str),
                "new_value": json.dumps(entry.get("new_value"), default=str),
                "reason": entry.get("reason", ""),
                "status": entry.get("status", "applied")
            })

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    if format == "json":
        return _json_response(rows, f"darwin_genome_{ts}.json")

    fields = ["timestamp", "version", "domain", "key", "old_value", "new_value", "reason", "status"]
    return _csv_response(_to_csv(rows, fields), f"darwin_genome_{ts}.csv")


# ==================== Routing ====================

@router.get("/routing")
async def export_routing(
    format: str = Query("csv", regex="^(csv|json)$")
):
    """Export model routing statistics."""
    from app.lifespan import get_service

    router_svc = _safe(lambda: get_service('multi_model_router'))
    rows = []

    if router_svc:
        stats = _safe(lambda: router_svc.get_router_stats(), {})
        perf = stats.get('performance_stats', {})
        for model_name, model_stats in perf.items():
            rows.append({
                "timestamp": datetime.utcnow().isoformat(),
                "model": model_name,
                "total_requests": model_stats.get('total_requests', 0),
                "total_cost": model_stats.get('total_cost_estimate', 0),
                "avg_latency_ms": model_stats.get('avg_response_time_ms', 0),
                "success_rate": model_stats.get('success_rate', 0),
            })

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

    if format == "json":
        return _json_response(rows, f"darwin_routing_{ts}.json")

    fields = ["timestamp", "model", "total_requests", "total_cost", "avg_latency_ms", "success_rate"]
    return _csv_response(_to_csv(rows, fields), f"darwin_routing_{ts}.csv")


# ==================== All (bundled) ====================

@router.get("/all")
async def export_all():
    """Export all datasets bundled as a single JSON file."""
    from consciousness.activity_monitor import get_activity_monitor
    from consciousness.genome_manager import get_genome
    from app.lifespan import get_service

    bundle = {
        "exported_at": datetime.utcnow().isoformat(),
        "activities": [],
        "costs": [],
        "cycles": [],
        "genome_mutations": [],
        "routing": [],
        "genome_status": {},
        "consciousness_stats": {}
    }

    # Activities
    monitor = _safe(get_activity_monitor)
    if monitor:
        logs = monitor.get_logs(limit=1000)  # Returns List[Dict]
        bundle["activities"] = [
            {
                "timestamp": str(l.get("timestamp", "")),
                "category": str(l.get("category", "")),
                "action": l.get("action", ""),
                "status": str(l.get("status", "")),
                "duration_ms": l.get("duration_ms") or 0,
            }
            for l in logs
        ]

    # Genome
    genome = _safe(get_genome)
    if genome:
        bundle["genome_mutations"] = genome._version.get("changelog", [])
        bundle["genome_status"] = genome.get_stats()

    # Routing
    router_svc = _safe(lambda: get_service('multi_model_router'))
    if router_svc:
        stats = _safe(lambda: router_svc.get_router_stats(), {})
        bundle["routing"] = stats.get('performance_stats', {})

    # Consciousness stats
    engine = _safe(lambda: get_service('consciousness_engine'))
    if engine:
        bundle["consciousness_stats"] = {
            "wake_cycles": getattr(engine, 'wake_cycles_completed', 0),
            "sleep_cycles": getattr(engine, 'sleep_cycles_completed', 0),
            "total_activities": getattr(engine, 'total_activities_completed', 0),
            "total_discoveries": getattr(engine, 'total_discoveries_made', 0),
        }

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
    return _json_response(bundle, f"darwin_export_{ts}.json")
