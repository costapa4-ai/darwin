"""
Context Awareness API Routes
Endpoints for context information and user activity tracking
"""
from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/api/v1/context", tags=["context"])

# Global communicator instance (set from main.py)
communicator = None


def initialize_context(comm):
    """Initialize context routes with communicator"""
    global communicator
    communicator = comm
    print("✅ Context Routes initialized")


@router.get("/status")
async def get_context_status():
    """
    📊 Get current context status

    Returns:
    - User presence (active/idle/away)
    - Time of day
    - System load
    - Verbosity level
    - Recommended cooldown
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Context system not initialized")

    try:
        context_info = communicator.get_context_info()

        return {
            'success': True,
            'context': context_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting context: {str(e)}")


@router.post("/user-activity")
async def notify_user_activity():
    """
    👤 Notify that user is active

    Call this when user:
    - Sends a message
    - Clicks something
    - Interacts with Darwin

    This helps Darwin adapt its communication style
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Context system not initialized")

    try:
        communicator.notify_user_activity()

        # Get updated context
        context_info = communicator.get_context_info()

        return {
            'success': True,
            'message': 'User activity registered',
            'new_context': context_info['current_context']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error notifying activity: {str(e)}")


@router.get("/greeting")
async def get_context_greeting():
    """
    👋 Get context-appropriate greeting

    Returns greeting based on:
    - Time of day
    - User presence
    - Recent activity
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Context system not initialized")

    try:
        greeting = communicator.context.get_greeting()

        return {
            'success': True,
            'greeting': greeting,
            'time_of_day': communicator.context.get_time_of_day().value,
            'user_presence': communicator.context.get_user_presence().value
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting greeting: {str(e)}")


@router.get("/suggestion")
async def get_activity_suggestion():
    """
    💡 Get suggested activity based on context

    Returns what Darwin should focus on based on:
    - User presence
    - System load
    - Time of day
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Context system not initialized")

    try:
        suggestion = communicator.context.get_activity_suggestion()

        return {
            'success': True,
            'suggestion': suggestion,
            'context': communicator.context.get_context()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting suggestion: {str(e)}")


@router.get("/verbosity")
async def get_verbosity_info():
    """
    🔊 Get current verbosity settings

    Returns:
    - Current verbosity level
    - Recommended cooldown
    - Whether Darwin should be verbose
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Context system not initialized")

    try:
        return {
            'success': True,
            'verbosity_level': communicator.context.get_verbosity_level(),
            'recommended_cooldown': communicator.context.get_message_cooldown(),
            'should_be_verbose': communicator.context.should_be_verbose(),
            'manual_verbosity': communicator.verbosity_level,
            'manual_cooldown': communicator.message_cooldown
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting verbosity: {str(e)}")
