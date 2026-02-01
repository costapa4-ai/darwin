"""
Mood System API Routes
Endpoints for Darwin's emotional states and mood management
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/mood", tags=["mood"])

# Global communicator instance (set from main.py)
communicator = None


def initialize_mood(comm):
    """Initialize mood routes with communicator"""
    global communicator
    communicator = comm
    print("✅ Mood Routes initialized")


class MoodEventRequest(BaseModel):
    """Request to process a mood-influencing event"""
    event_type: str
    context: Optional[dict] = None
    force_transition: bool = False


class ForceMoodRequest(BaseModel):
    """Request to force a mood change"""
    mood: str
    intensity: Optional[str] = None
    reason: str = "manual_override"


@router.get("/status")
async def get_mood_status():
    """
    🎭 Get current mood state

    Returns:
    - Current mood
    - Mood intensity
    - Time in current mood
    - Expected duration
    - Recent events count
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        mood_info = communicator.get_mood_info()

        return {
            'success': True,
            'mood': mood_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting mood: {str(e)}")


@router.get("/description")
async def get_mood_description():
    """
    💬 Get current mood description

    Returns human-readable description of Darwin's current mood
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        description = communicator.mood.get_mood_description()
        emoji = communicator.mood.get_mood_emoji()
        current = communicator.mood.get_current_mood()

        return {
            'success': True,
            'description': description,
            'emoji': emoji,
            'mood': current['mood'],
            'intensity': current['intensity']
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting description: {str(e)}")


@router.get("/history")
async def get_mood_history(limit: int = 20):
    """
    📊 Get mood transition history

    Args:
        limit: Number of transitions to return (default 20)

    Returns history of mood changes
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        history = communicator.mood.get_mood_history(limit=limit)

        return {
            'success': True,
            'transitions': history,
            'count': len(history)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


@router.get("/statistics")
async def get_mood_statistics():
    """
    📈 Get mood statistics

    Returns:
    - Total mood transitions
    - Most common moods
    - Average mood duration
    - Current mood details
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        stats = communicator.mood.get_mood_statistics()

        return {
            'success': True,
            'statistics': stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.post("/event")
async def process_mood_event(request: MoodEventRequest):
    """
    🎯 Process an event that might influence mood

    Args:
        event_type: Type of event (e.g., "discovery_made", "error_encountered")
        context: Additional context about the event
        force_transition: Force mood change even if current mood is recent

    Returns new mood if changed
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        new_mood = communicator.mood.process_event(
            event_type=request.event_type,
            context=request.context,
            force_transition=request.force_transition
        )

        if new_mood:
            mood_info = communicator.mood.get_current_mood()
            description = communicator.mood.get_mood_description()

            return {
                'success': True,
                'mood_changed': True,
                'new_mood': new_mood.value,
                'description': description,
                'details': mood_info
            }
        else:
            return {
                'success': True,
                'mood_changed': False,
                'current_mood': communicator.mood.current_mood.value,
                'message': 'Event processed but mood did not change'
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing event: {str(e)}")


@router.post("/force")
async def force_mood_change(request: ForceMoodRequest):
    """
    ⚡ Force a mood change (for testing or special events)

    Args:
        mood: Mood to change to (e.g., "excited", "curious")
        intensity: Optional intensity (low, medium, high)
        reason: Reason for the change

    Use this sparingly - natural mood transitions are preferred
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        from personality.mood_system import MoodState, MoodIntensity

        # Validate mood
        try:
            mood_state = MoodState(request.mood)
        except ValueError:
            valid_moods = [m.value for m in MoodState]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mood. Valid moods: {valid_moods}"
            )

        # Validate intensity if provided
        intensity = None
        if request.intensity:
            try:
                intensity = MoodIntensity(request.intensity)
            except ValueError:
                valid_intensities = [i.value for i in MoodIntensity]
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid intensity. Valid intensities: {valid_intensities}"
                )

        # Force mood change
        communicator.mood.force_mood(
            mood=mood_state,
            intensity=intensity,
            reason=request.reason
        )

        mood_info = communicator.mood.get_current_mood()
        description = communicator.mood.get_mood_description()

        return {
            'success': True,
            'new_mood': mood_state.value,
            'description': description,
            'details': mood_info,
            'reason': request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error forcing mood: {str(e)}")


@router.get("/available-moods")
async def get_available_moods():
    """
    📋 Get list of all available mood states

    Returns all possible moods Darwin can experience
    """
    from personality.mood_system import MoodState, MoodIntensity

    moods = {}
    for mood in MoodState:
        # Get description for this mood
        temp_mood_desc = {
            MoodState.CURIOUS: "Exploring and discovering",
            MoodState.EXCITED: "High energy, enthusiastic",
            MoodState.FOCUSED: "Deep concentration",
            MoodState.SATISFIED: "Content, pleased with results",
            MoodState.FRUSTRATED: "Struggling with something",
            MoodState.TIRED: "Low energy, need rest",
            MoodState.PLAYFUL: "Light-hearted, fun",
            MoodState.CONTEMPLATIVE: "Reflective, thoughtful",
            MoodState.DETERMINED: "Driven, goal-oriented",
            MoodState.SURPRISED: "Unexpected discovery",
            MoodState.CONFUSED: "Uncertain, seeking clarity",
            MoodState.PROUD: "Accomplished something significant"
        }

        moods[mood.value] = temp_mood_desc.get(mood, "")

    intensities = [i.value for i in MoodIntensity]

    return {
        'success': True,
        'moods': moods,
        'intensities': intensities
    }


@router.get("/available-events")
async def get_available_events():
    """
    📋 Get list of all mood-influencing events

    Returns all event types that can influence Darwin's mood
    """
    from personality.mood_system import MoodInfluencer

    # Get all event constants
    events = {}
    for attr_name in dir(MoodInfluencer):
        if attr_name.isupper() and not attr_name.startswith('_'):
            event_type = getattr(MoodInfluencer, attr_name)
            if isinstance(event_type, str):
                events[attr_name] = event_type

    return {
        'success': True,
        'events': events,
        'count': len(events)
    }


@router.get("/environment")
async def get_environmental_influence():
    """
    🌍 Get environmental factors influencing mood

    Returns:
    - Time of day and its mood tendencies
    - Discovery momentum (recent discoveries boost)
    - Frustration level (recent errors)
    - Engagement level (user interactions)
    - Daily counters
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        env_data = communicator.mood.get_environmental_influence()
        current_mood = communicator.mood.get_current_mood()

        return {
            'success': True,
            'environment': env_data,
            'current_mood': current_mood['mood'],
            'time_of_day': env_data['time_of_day'],
            'mood_tendency_for_time': [
                {'mood': m.value, 'weight': w}
                for m, w in env_data.get('time_mood_tendency', [])
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting environment: {str(e)}")


@router.post("/environment/shift")
async def apply_environmental_shift():
    """
    🔄 Apply environmental mood shift

    Triggers a potential mood shift based on environmental factors
    (time of day, recent activity, etc.)
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Mood system not initialized")

    try:
        new_mood = communicator.mood.apply_environmental_mood_shift()

        if new_mood:
            return {
                'success': True,
                'mood_changed': True,
                'new_mood': new_mood.value,
                'description': communicator.mood.get_mood_description(),
                'reason': 'environmental_shift'
            }
        else:
            return {
                'success': True,
                'mood_changed': False,
                'current_mood': communicator.mood.current_mood.value,
                'message': 'No mood change triggered (too soon or conditions not met)'
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying shift: {str(e)}")
