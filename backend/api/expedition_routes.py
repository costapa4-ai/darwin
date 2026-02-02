"""
Curiosity Expedition Routes - Darwin's Web Adventures API

Endpoints for managing and viewing Darwin's curiosity-driven expeditions.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/consciousness/expeditions", tags=["expeditions"])

# Global reference (set by initialization)
expedition_engine = None


class TopicRequest(BaseModel):
    topic: str
    question: str
    priority: Optional[int] = 5


def initialize_expeditions(engine):
    """Initialize expedition routes with engine instance"""
    global expedition_engine
    expedition_engine = engine


@router.get("/status")
async def get_expedition_status():
    """Get current expedition system status"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    status = expedition_engine.get_queue_status()
    return {
        'success': True,
        **status
    }


@router.get("/queue")
async def get_queue():
    """Get the current curiosity queue"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    return {
        'success': True,
        'queue': expedition_engine.topic_queue,
        'count': len(expedition_engine.topic_queue)
    }


@router.post("/queue/add")
async def add_to_queue(request: TopicRequest):
    """Add a topic to the curiosity queue"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    success = expedition_engine.add_to_queue(
        topic=request.topic,
        question=request.question,
        priority=request.priority,
        source="api"
    )

    return {
        'success': success,
        'message': f"Added '{request.topic}' to queue with priority {request.priority}",
        'queue_size': len(expedition_engine.topic_queue)
    }


@router.post("/start")
async def start_expedition(topic: Optional[str] = None, question: Optional[str] = None):
    """
    Start a new expedition.

    If topic/question provided, uses those. Otherwise picks from queue.
    """
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    if not expedition_engine.can_start_expedition():
        return {
            'success': False,
            'message': 'Cannot start expedition (cooldown or already in progress)',
            'current_expedition': expedition_engine.current_expedition.topic if expedition_engine.current_expedition else None
        }

    topic_entry = None
    if topic and question:
        topic_entry = {'topic': topic, 'question': question}

    expedition = await expedition_engine.start_expedition(topic_entry)

    if expedition:
        return {
            'success': True,
            'message': f"Expedition started: {expedition.topic}",
            'expedition_id': expedition.id,
            'topic': expedition.topic,
            'question': expedition.question
        }
    else:
        return {
            'success': False,
            'message': 'Failed to start expedition (no topics available)'
        }


@router.post("/conduct")
async def conduct_expedition():
    """
    Conduct the current expedition (do the actual research).

    Must call /start first to begin an expedition.
    """
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    if not expedition_engine.current_expedition:
        return {
            'success': False,
            'message': 'No expedition in progress. Call /start first.'
        }

    expedition = await expedition_engine.conduct_expedition()

    if expedition:
        return {
            'success': True,
            'expedition': {
                'id': expedition.id,
                'topic': expedition.topic,
                'success': expedition.success,
                'discoveries_count': len(expedition.discoveries),
                'insights_count': len(expedition.insights),
                'duration_minutes': expedition.duration_minutes,
                'summary': expedition.summary,
                'related_topics': expedition.related_topics
            }
        }
    else:
        return {
            'success': False,
            'message': 'Expedition conduct failed'
        }


@router.get("/recent")
async def get_recent_expeditions(limit: int = 10):
    """Get recent expedition summaries"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    expeditions = expedition_engine.get_recent_expeditions(limit)
    return {
        'success': True,
        'expeditions': expeditions,
        'count': len(expeditions)
    }


@router.get("/feedback/statistics")
async def get_feedback_statistics():
    """Get statistics about the feedback loop system"""
    from consciousness.feedback_loops import get_feedback_manager

    feedback_manager = get_feedback_manager()
    if not feedback_manager:
        return {
            'success': False,
            'message': 'Feedback loop manager not initialized',
            'statistics': None
        }

    return {
        'success': True,
        'statistics': feedback_manager.get_statistics()
    }


@router.get("/{expedition_id}")
async def get_expedition(expedition_id: str):
    """Get full expedition details by ID"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    expedition = expedition_engine.get_expedition_by_id(expedition_id)

    if not expedition:
        raise HTTPException(status_code=404, detail=f"Expedition {expedition_id} not found")

    return {
        'success': True,
        'expedition': expedition
    }


@router.get("/{expedition_id}/markdown")
async def get_expedition_markdown(expedition_id: str):
    """Get expedition as markdown document"""
    if not expedition_engine:
        raise HTTPException(status_code=503, detail="Expedition engine not available")

    md_file = expedition_engine.expeditions_dir / f"{expedition_id}.md"

    if not md_file.exists():
        raise HTTPException(status_code=404, detail=f"Expedition {expedition_id} not found")

    content = md_file.read_text()

    return {
        'success': True,
        'expedition_id': expedition_id,
        'format': 'markdown',
        'content': content
    }
