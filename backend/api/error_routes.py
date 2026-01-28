"""
Error Tracking API Routes
Endpoints to view and analyze system errors
"""
from fastapi import APIRouter, Query
from typing import Optional
from utils.error_tracker import error_store

router = APIRouter(prefix="/api/v1/errors", tags=["errors"])


@router.get("/summary")
async def get_error_summary():
    """
    📊 Get summary statistics about system errors

    Returns counts by type, level, component and recent errors
    """
    summary = error_store.get_error_summary()

    return {
        'success': True,
        'summary': summary
    }


@router.get("/recent")
async def get_recent_errors(
    limit: int = Query(default=100, le=500),
    level: Optional[str] = Query(default=None, description="Filter by level: WARNING, ERROR, CRITICAL"),
    component: Optional[str] = Query(default=None, description="Filter by component")
):
    """
    🔍 Get recent errors with optional filtering

    Args:
        limit: Maximum number of errors to return (max 500)
        level: Filter by log level (WARNING, ERROR, CRITICAL)
        component: Filter by component name
    """
    errors = error_store.get_recent_errors(limit=limit, level=level, component=component)

    return {
        'success': True,
        'count': len(errors),
        'errors': errors
    }


@router.get("/critical")
async def get_critical_errors():
    """
    🚨 Get all ERROR and CRITICAL level errors

    Returns only the most severe errors that require attention
    """
    critical_errors = error_store.get_critical_errors()

    return {
        'success': True,
        'count': len(critical_errors),
        'errors': critical_errors
    }


@router.get("/component/{component}")
async def get_component_errors(component: str):
    """
    🔧 Get all errors for a specific component

    Components: evolution, executor, nucleus, dream, agents, etc.
    """
    errors = error_store.get_errors_by_component(component)

    return {
        'success': True,
        'component': component,
        'count': len(errors),
        'errors': errors
    }


@router.post("/clear")
async def clear_errors():
    """
    🗑️ Clear all stored errors

    Use this to reset the error log after addressing issues
    """
    error_store.clear_errors()

    return {
        'success': True,
        'message': 'All errors cleared'
    }


@router.get("/status")
async def error_tracking_status():
    """
    ℹ️ Check error tracking system status
    """
    summary = error_store.get_error_summary()

    return {
        'enabled': True,
        'total_errors': summary['total_errors'],
        'by_level': summary['by_level'],
        'log_file': summary['log_file']
    }
