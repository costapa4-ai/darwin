"""
Hooks API Routes
Endpoints for managing Darwin's consciousness hook system
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel

from consciousness.hooks import get_hooks_manager, HookEvent

router = APIRouter(prefix="/api/v1/hooks", tags=["hooks"])


class TriggerHookRequest(BaseModel):
    """Request to manually trigger a hook"""
    event: str
    data: Optional[dict] = None
    source: str = "api"


@router.get("/status")
async def get_hooks_status():
    """
    Get hook system status

    Returns:
    - Whether hooks are enabled
    - Total registered hooks
    - Hooks count by event
    - Execution statistics
    """
    try:
        manager = get_hooks_manager()
        stats = manager.get_stats()

        return {
            'success': True,
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/list")
async def list_hooks():
    """
    List all registered hooks by event
    """
    try:
        manager = get_hooks_manager()
        hooks = manager.get_registered_hooks()

        return {
            'success': True,
            'hooks': hooks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing hooks: {str(e)}")


@router.get("/events")
async def list_events():
    """
    List all available hook events
    """
    events = [
        {
            'name': event.value,
            'description': _get_event_description(event)
        }
        for event in HookEvent
    ]

    return {
        'success': True,
        'events': events,
        'count': len(events)
    }


@router.post("/trigger")
async def trigger_hook(request: TriggerHookRequest):
    """
    Manually trigger a hook event

    Useful for testing hooks and debugging
    """
    try:
        # Validate event name
        try:
            event = HookEvent(request.event)
        except ValueError:
            valid_events = [e.value for e in HookEvent]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event. Valid events: {valid_events}"
            )

        manager = get_hooks_manager()
        results = await manager.trigger(event, request.data, request.source)

        return {
            'success': True,
            'results': results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering hook: {str(e)}")


@router.post("/enable/{event}/{name}")
async def enable_hook(event: str, name: str):
    """Enable a specific hook"""
    try:
        hook_event = HookEvent(event)
        manager = get_hooks_manager()

        if manager.enable_hook(hook_event, name):
            return {
                'success': True,
                'message': f"Hook '{name}' enabled for event '{event}'"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Hook '{name}' not found")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event: {event}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/disable/{event}/{name}")
async def disable_hook(event: str, name: str):
    """Disable a specific hook"""
    try:
        hook_event = HookEvent(event)
        manager = get_hooks_manager()

        if manager.disable_hook(hook_event, name):
            return {
                'success': True,
                'message': f"Hook '{name}' disabled for event '{event}'"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Hook '{name}' not found")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event: {event}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/enable-all")
async def enable_all_hooks():
    """Enable the entire hook system"""
    try:
        manager = get_hooks_manager()
        manager.enable_all()
        return {
            'success': True,
            'message': 'Hook system enabled'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/disable-all")
async def disable_all_hooks():
    """Disable the entire hook system"""
    try:
        manager = get_hooks_manager()
        manager.disable_all()
        return {
            'success': True,
            'message': 'Hook system disabled'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/stats/{hook_name}")
async def get_hook_stats(hook_name: str):
    """Get execution statistics for a specific hook"""
    try:
        manager = get_hooks_manager()
        stats = manager.get_stats()

        hook_stats = stats['execution_stats'].get(hook_name)

        if hook_stats:
            return {
                'success': True,
                'hook': hook_name,
                'stats': hook_stats
            }
        else:
            return {
                'success': True,
                'hook': hook_name,
                'stats': None,
                'message': 'No execution data yet'
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def _get_event_description(event: HookEvent) -> str:
    """Get description for a hook event"""
    descriptions = {
        HookEvent.BEFORE_WAKE: "Triggered before Darwin transitions to wake state",
        HookEvent.AFTER_WAKE: "Triggered after Darwin completes wake transition",
        HookEvent.BEFORE_SLEEP: "Triggered before Darwin transitions to sleep state",
        HookEvent.AFTER_SLEEP: "Triggered after Darwin completes sleep transition",
        HookEvent.ON_DISCOVERY: "Triggered when Darwin discovers something interesting",
        HookEvent.ON_LEARNING: "Triggered when a learning session completes",
        HookEvent.ON_EXPEDITION_START: "Triggered when a curiosity expedition begins",
        HookEvent.ON_EXPEDITION_COMPLETE: "Triggered when a curiosity expedition ends",
        HookEvent.ON_MOOD_CHANGE: "Triggered when Darwin's mood changes",
        HookEvent.ON_THOUGHT: "Triggered when a shower thought is generated",
        HookEvent.ON_DREAM: "Triggered when a dream is recorded",
        HookEvent.ON_ERROR: "Triggered when an error occurs",
        HookEvent.ON_BUDGET_ALERT: "Triggered when budget threshold is reached",
        HookEvent.ON_FINDING: "Triggered when a new finding is added",
    }
    return descriptions.get(event, "No description available")
