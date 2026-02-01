"""
Channel Gateway API Routes
Endpoints for managing Darwin's multi-channel communication
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/channels", tags=["channels"])

# Global gateway reference (set by initialization)
gateway = None


class BroadcastRequest(BaseModel):
    """Request to broadcast a message"""
    content: str
    message_type: str = "thought"  # dream, discovery, thought, status, alert, poetry
    title: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent
    channels: Optional[List[str]] = None  # specific channels, or all if None


class SendMessageRequest(BaseModel):
    """Request to send a message to a specific target"""
    content: str
    channel: str  # telegram, discord, slack, web
    target_id: str  # chat_id, channel_id, etc.
    message_type: str = "response"


class ChannelConfigRequest(BaseModel):
    """Request to configure a channel"""
    channel: str
    enabled: bool
    config: dict = {}


def initialize_channels(channel_gateway):
    """Initialize channel routes with gateway instance"""
    global gateway
    gateway = channel_gateway
    print("Channel Routes initialized")


@router.get("/status")
async def get_gateway_status():
    """
    Get channel gateway status

    Returns:
    - Gateway enabled state
    - Status of each channel
    - Message statistics
    """
    if not gateway:
        return {
            'success': True,
            'enabled': False,
            'message': 'Channel gateway not initialized',
            'channels': {}
        }

    try:
        status = gateway.get_status()
        return {
            'success': True,
            **status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/list")
async def list_channels():
    """
    List all available channels and their configuration
    """
    if not gateway:
        return {
            'success': True,
            'channels': [],
            'message': 'Gateway not initialized'
        }

    try:
        channels = []
        for channel_type, channel in gateway.channels.items():
            channels.append({
                'type': channel_type.value,
                'enabled': channel.enabled,
                'connected': channel.connected,
                'personality': channel.personality_flavor
            })

        return {
            'success': True,
            'channels': channels,
            'count': len(channels)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing channels: {str(e)}")


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest):
    """
    Broadcast a message to all enabled channels (or specific ones)

    Supports different message types:
    - dream: Dream summaries (when Darwin wakes)
    - discovery: Findings and insights
    - thought: Shower thoughts, musings
    - status: Wake/sleep transitions
    - alert: Important notifications
    - poetry: Code poetry
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        from channels.base_channel import ChannelMessage, MessageType, MessagePriority, ChannelType

        # Map string to enum
        type_map = {
            'dream': MessageType.DREAM,
            'discovery': MessageType.DISCOVERY,
            'thought': MessageType.THOUGHT,
            'status': MessageType.STATUS,
            'alert': MessageType.ALERT,
            'poetry': MessageType.POETRY,
            'learning': MessageType.LEARNING,
        }

        priority_map = {
            'low': MessagePriority.LOW,
            'normal': MessagePriority.NORMAL,
            'high': MessagePriority.HIGH,
            'urgent': MessagePriority.URGENT,
        }

        message = ChannelMessage(
            content=request.content,
            message_type=type_map.get(request.message_type, MessageType.THOUGHT),
            priority=priority_map.get(request.priority, MessagePriority.NORMAL),
            title=request.title
        )

        # Determine target channels
        target_channels = None
        if request.channels:
            target_channels = [
                ChannelType(c) for c in request.channels
                if c in [ct.value for ct in ChannelType]
            ]

        results = await gateway.broadcast(message, target_channels)

        return {
            'success': True,
            'broadcast_results': {
                ct.value: count for ct, count in results.items()
            },
            'total_sent': sum(results.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Broadcast error: {str(e)}")


@router.post("/send")
async def send_message(request: SendMessageRequest):
    """
    Send a message to a specific channel and target
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        from channels.base_channel import ChannelMessage, MessageType, ChannelType

        type_map = {
            'response': MessageType.RESPONSE,
            'dream': MessageType.DREAM,
            'discovery': MessageType.DISCOVERY,
            'thought': MessageType.THOUGHT,
        }

        message = ChannelMessage(
            content=request.content,
            message_type=type_map.get(request.message_type, MessageType.RESPONSE)
        )

        channel_type = ChannelType(request.channel)
        success = await gateway.send(message, channel_type, request.target_id)

        return {
            'success': success,
            'channel': request.channel,
            'target': request.target_id
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid channel: {request.channel}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send error: {str(e)}")


@router.post("/broadcast/dream")
async def broadcast_dream(dream_summary: str, highlights: Optional[List[str]] = None):
    """
    Broadcast a dream summary (typically called when Darwin wakes)
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        await gateway.broadcast_dream(dream_summary, highlights or [])
        return {
            'success': True,
            'message': 'Dream broadcast sent'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dream broadcast error: {str(e)}")


@router.post("/broadcast/discovery")
async def broadcast_discovery(
    discovery: str,
    discovery_type: str = "pattern",
    severity: str = "normal"
):
    """
    Broadcast a discovery announcement
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        await gateway.broadcast_discovery(discovery, discovery_type, severity)
        return {
            'success': True,
            'message': 'Discovery broadcast sent'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery broadcast error: {str(e)}")


@router.post("/broadcast/thought")
async def broadcast_thought(thought: str):
    """
    Broadcast a shower thought
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        await gateway.broadcast_thought(thought)
        return {
            'success': True,
            'message': 'Thought broadcast sent'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thought broadcast error: {str(e)}")


@router.post("/broadcast/status")
async def broadcast_status(status: str, state: str):
    """
    Broadcast a status update (wake/sleep transitions)
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        await gateway.broadcast_status(status, state)
        return {
            'success': True,
            'message': 'Status broadcast sent'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status broadcast error: {str(e)}")


@router.get("/stats")
async def get_channel_stats():
    """
    Get detailed channel statistics
    """
    if not gateway:
        return {
            'success': True,
            'stats': {
                'messages_sent': 0,
                'messages_received': 0,
                'broadcasts_sent': 0,
                'errors': 0
            }
        }

    return {
        'success': True,
        'stats': gateway.stats
    }


@router.post("/test")
async def test_channels():
    """
    Send a test message to all enabled channels

    Useful for verifying channel configuration
    """
    if not gateway or not gateway.enabled:
        raise HTTPException(status_code=503, detail="Channel gateway not available")

    try:
        from channels.base_channel import ChannelMessage, MessageType, MessagePriority

        test_message = ChannelMessage(
            content="This is a test message from Darwin's Channel Gateway. If you see this, the channel is working correctly!",
            message_type=MessageType.STATUS,
            priority=MessagePriority.LOW,
            title="Channel Test"
        )

        results = await gateway.broadcast(test_message)

        return {
            'success': True,
            'test_results': {
                ct.value: count for ct, count in results.items()
            },
            'message': 'Test messages sent to enabled channels'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test error: {str(e)}")
