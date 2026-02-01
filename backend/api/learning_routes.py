"""
Learning System API Routes
Endpoints for Darwin's meta-learning and self-reflection system
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])

# Global references (set by initialization)
meta_learner = None
self_reflection = None


class TrackSessionRequest(BaseModel):
    """Request to track a learning session"""
    source: str
    topic: str
    duration_minutes: float
    knowledge_gained: int
    quality: float  # 0.0 to 1.0


def initialize_learning(learner, reflection_system):
    """Initialize learning routes with service instances"""
    global meta_learner, self_reflection
    meta_learner = learner
    self_reflection = reflection_system
    print("Learning Routes initialized")


@router.get("/status")
async def get_learning_status():
    """
    Get current learning system status

    Returns:
    - Total learning sessions tracked
    - Recent learning stats
    - Current strategy status
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        sessions = meta_learner.learning_sessions
        recent_sessions = sessions[-10:] if sessions else []

        return {
            'success': True,
            'total_sessions': len(sessions),
            'recent_sessions': recent_sessions,
            'current_strategy': meta_learner.get_current_strategy(),
            'optimal_strategies_count': len(meta_learner.optimal_strategies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/report")
async def get_learning_report(days: int = 7):
    """
    Generate learning report for specified period

    Args:
        days: Number of days to include (default 7)
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        report = await meta_learner.generate_learning_report(period_days=days)
        return {
            'success': True,
            'report': report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.get("/effectiveness")
async def analyze_effectiveness():
    """
    Analyze learning effectiveness across different methods and sources
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        analysis = await meta_learner.analyze_learning_effectiveness()
        return {
            'success': True,
            'analysis': analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing effectiveness: {str(e)}")


@router.post("/track")
async def track_learning_session(request: TrackSessionRequest):
    """
    Manually track a learning session

    Useful for integrating external learning activities
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        await meta_learner.track_learning_session(
            source=request.source,
            topic=request.topic,
            duration_minutes=request.duration_minutes,
            knowledge_gained=request.knowledge_gained,
            quality=min(1.0, max(0.0, request.quality))  # Clamp to 0-1
        )

        return {
            'success': True,
            'message': f"Tracked learning session: {request.topic}",
            'total_sessions': len(meta_learner.learning_sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking session: {str(e)}")


@router.post("/optimize")
async def optimize_strategy():
    """
    Trigger learning strategy optimization

    Analyzes past performance and adjusts learning approach
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        report = await meta_learner.optimize_learning_strategy()
        return {
            'success': True,
            'optimization_report': report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing: {str(e)}")


@router.get("/reflection/status")
async def get_reflection_status():
    """
    Get self-reflection system status
    """
    if not self_reflection:
        raise HTTPException(status_code=503, detail="Reflection system not initialized")

    try:
        summary = self_reflection.get_reflection_summary()
        return {
            'success': True,
            'reflection_summary': summary,
            'daily_due': self_reflection.should_perform_daily_reflection(),
            'weekly_due': self_reflection.should_perform_weekly_reflection()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reflection status: {str(e)}")


@router.post("/reflection/daily")
async def trigger_daily_reflection():
    """
    Trigger a daily self-reflection

    Generates insights about learning progress, achievements, and challenges
    """
    if not self_reflection:
        raise HTTPException(status_code=503, detail="Reflection system not initialized")

    try:
        reflection = await self_reflection.daily_reflection()
        return {
            'success': True,
            'reflection': reflection
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing reflection: {str(e)}")


@router.post("/reflection/weekly")
async def trigger_weekly_reflection():
    """
    Trigger a weekly self-reflection

    Deeper analysis of learning patterns, strategy effectiveness
    """
    if not self_reflection:
        raise HTTPException(status_code=503, detail="Reflection system not initialized")

    try:
        reflection = await self_reflection.weekly_reflection()
        return {
            'success': True,
            'reflection': reflection
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing reflection: {str(e)}")


@router.get("/sessions")
async def get_learning_sessions(limit: int = 50):
    """
    Get recent learning sessions

    Args:
        limit: Maximum number of sessions to return
    """
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Learning system not initialized")

    try:
        sessions = meta_learner.learning_sessions[-limit:]

        # Group by source
        by_source = {}
        for session in sessions:
            source = session.get('source', 'unknown')
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(session)

        return {
            'success': True,
            'sessions': sessions,
            'count': len(sessions),
            'by_source': {k: len(v) for k, v in by_source.items()}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting sessions: {str(e)}")
