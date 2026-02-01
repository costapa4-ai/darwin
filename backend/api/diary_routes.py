"""
Diary API Routes - Access Darwin's consciousness journal

Provides endpoints to read diary entries, add thoughts,
and get insights from Darwin's daily reflections.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/v1/consciousness/diary", tags=["diary"])

# Global reference (set by initialization)
diary_engine = None


class ThoughtEntry(BaseModel):
    thought: str
    depth: Optional[str] = "surface"  # surface, medium, deep


class LearningEntry(BaseModel):
    learning: str
    source: Optional[str] = None


class DiscoveryEntry(BaseModel):
    discovery: str
    significance: Optional[str] = "medium"  # low, medium, high


class ChallengeEntry(BaseModel):
    challenge: str
    resolved: Optional[bool] = False


def initialize_diary(engine):
    """Initialize diary routes with engine instance"""
    global diary_engine
    diary_engine = engine


@router.get("/today")
async def get_todays_diary():
    """Get today's diary data (not yet written to file)"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    return {
        'date': datetime.utcnow().strftime("%Y-%m-%d"),
        'learnings': diary_engine.todays_learnings,
        'thoughts': diary_engine.todays_thoughts,
        'discoveries': diary_engine.todays_discoveries,
        'challenges': diary_engine.todays_challenges,
        'mood_snapshots': len(diary_engine.todays_mood_arc),
        'status': 'in_progress'
    }


@router.get("/entry/{date}")
async def get_diary_entry(date: str):
    """
    Get diary entry for a specific date.

    Args:
        date: Date in YYYY-MM-DD format
    """
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    content = diary_engine.get_diary_entry(date)
    if not content:
        raise HTTPException(status_code=404, detail=f"No diary entry for {date}")

    return {
        'date': date,
        'content': content,
        'format': 'markdown'
    }


@router.get("/recent")
async def get_recent_entries(days: int = 7):
    """Get recent diary entries"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    entries = diary_engine.get_recent_entries(days)
    return {
        'entries': entries,
        'count': len(entries),
        'days_requested': days
    }


@router.get("/insights")
async def get_diary_insights():
    """Get summarized insights from recent diary entries"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    summary = diary_engine.get_insights_summary()
    return summary


@router.post("/thought")
async def add_thought(entry: ThoughtEntry):
    """Add a thought to today's diary"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    diary_engine.add_thought(entry.thought, entry.depth)
    return {
        'success': True,
        'message': 'Thought recorded',
        'thought': entry.thought,
        'depth': entry.depth,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/learning")
async def add_learning(entry: LearningEntry):
    """Add a learning to today's diary"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    diary_engine.add_learning(entry.learning, entry.source)
    return {
        'success': True,
        'message': 'Learning recorded',
        'learning': entry.learning,
        'source': entry.source,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/discovery")
async def add_discovery(entry: DiscoveryEntry):
    """Add a discovery to today's diary"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    diary_engine.add_discovery(entry.discovery, entry.significance)
    return {
        'success': True,
        'message': 'Discovery recorded',
        'discovery': entry.discovery,
        'significance': entry.significance,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/challenge")
async def add_challenge(entry: ChallengeEntry):
    """Add a challenge to today's diary"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    diary_engine.add_challenge(entry.challenge, entry.resolved)
    return {
        'success': True,
        'message': 'Challenge recorded',
        'challenge': entry.challenge,
        'resolved': entry.resolved,
        'timestamp': datetime.utcnow().isoformat()
    }


@router.post("/write")
async def write_diary_entry(trigger: str = "manual"):
    """
    Manually trigger writing the diary entry.

    This is normally done automatically at wake->sleep transition.
    """
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    try:
        filepath = await diary_engine.write_daily_entry(trigger=trigger)
        return {
            'success': True,
            'message': 'Diary entry written',
            'file': filepath,
            'trigger': trigger
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write diary: {str(e)}")


@router.post("/consolidate-insights")
async def consolidate_insights():
    """Consolidate recent insights into long-term storage"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    try:
        filepath = await diary_engine.write_insight_to_longterm()
        if filepath:
            return {
                'success': True,
                'message': 'Insights consolidated',
                'file': filepath
            }
        else:
            return {
                'success': False,
                'message': 'No entries to consolidate'
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to consolidate: {str(e)}")


@router.post("/mood-snapshot")
async def take_mood_snapshot():
    """Take a snapshot of current mood for the diary"""
    if not diary_engine:
        raise HTTPException(status_code=503, detail="Diary engine not available")

    diary_engine.record_mood_snapshot()
    return {
        'success': True,
        'message': 'Mood snapshot recorded',
        'total_snapshots': len(diary_engine.todays_mood_arc),
        'timestamp': datetime.utcnow().isoformat()
    }
