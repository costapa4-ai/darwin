"""
Voice Synthesis API Routes
Text-to-speech endpoints for Darwin's voice
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from pydantic import BaseModel
from pathlib import Path

from consciousness.voice_synthesis import (
    get_voice_engine,
    VoiceStyle,
    VoiceBackend
)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class SynthesizeRequest(BaseModel):
    """Request to synthesize speech"""
    text: str
    style: str = "thoughtful"
    backend: Optional[str] = None
    use_cache: bool = True


class DreamSpeakRequest(BaseModel):
    """Request to speak a dream"""
    dream_content: str


class DiscoverySpeakRequest(BaseModel):
    """Request to speak a discovery"""
    discovery: str
    topic: str


class ThoughtSpeakRequest(BaseModel):
    """Request to speak a thought"""
    thought: str


class AlertSpeakRequest(BaseModel):
    """Request to speak an alert"""
    message: str


@router.get("/status")
async def get_voice_status():
    """
    Get voice synthesis engine status

    Returns available backends and statistics
    """
    engine = get_voice_engine()
    if not engine:
        return {
            'success': True,
            'enabled': False,
            'message': 'Voice synthesis not initialized'
        }

    return {
        'success': True,
        'enabled': True,
        **engine.get_stats()
    }


@router.get("/styles")
async def list_voice_styles():
    """List available voice styles"""
    styles = [
        {
            'name': style.value,
            'description': _get_style_description(style)
        }
        for style in VoiceStyle
    ]

    return {
        'success': True,
        'styles': styles
    }


@router.get("/backends")
async def list_backends():
    """List available TTS backends"""
    engine = get_voice_engine()
    if not engine:
        return {
            'success': True,
            'backends': [],
            'message': 'Voice synthesis not initialized'
        }

    stats = engine.get_stats()
    backends = [
        {
            'name': name,
            'available': available,
            'description': _get_backend_description(name)
        }
        for name, available in stats['available_backends'].items()
    ]

    return {
        'success': True,
        'backends': backends,
        'default': stats['default_backend']
    }


@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """
    Synthesize text to speech

    Returns audio file information
    """
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    # Validate style
    try:
        style = VoiceStyle(request.style)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Valid styles: {[s.value for s in VoiceStyle]}"
        )

    # Validate backend if provided
    backend = None
    if request.backend:
        try:
            backend = VoiceBackend(request.backend)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backend. Valid backends: {[b.value for b in VoiceBackend]}"
            )

    try:
        audio_file = await engine.synthesize(
            text=request.text,
            style=style,
            backend=backend,
            use_cache=request.use_cache
        )

        if audio_file:
            return {
                'success': True,
                'audio': audio_file.to_dict()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to synthesize speech"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak/dream")
async def speak_dream(request: DreamSpeakRequest):
    """Generate voice narration for a dream"""
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    try:
        audio_file = await engine.speak_dream(request.dream_content)
        if audio_file:
            return {
                'success': True,
                'audio': audio_file.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate dream audio")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak/discovery")
async def speak_discovery(request: DiscoverySpeakRequest):
    """Generate voice announcement for a discovery"""
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    try:
        audio_file = await engine.speak_discovery(request.discovery, request.topic)
        if audio_file:
            return {
                'success': True,
                'audio': audio_file.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate discovery audio")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak/thought")
async def speak_thought(request: ThoughtSpeakRequest):
    """Generate voice for a shower thought"""
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    try:
        audio_file = await engine.speak_thought(request.thought)
        if audio_file:
            return {
                'success': True,
                'audio': audio_file.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate thought audio")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak/alert")
async def speak_alert(request: AlertSpeakRequest):
    """Generate voice for an important alert"""
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    try:
        audio_file = await engine.speak_alert(request.message)
        if audio_file:
            return {
                'success': True,
                'audio': audio_file.to_dict()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate alert audio")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_audio_files(limit: int = 20):
    """List recently generated audio files"""
    engine = get_voice_engine()
    if not engine:
        return {
            'success': True,
            'files': [],
            'count': 0
        }

    files = engine.get_recent_files(limit)
    return {
        'success': True,
        'files': files,
        'count': len(files)
    }


@router.get("/file/{file_id}")
async def get_audio_file(file_id: str):
    """
    Get an audio file by ID

    Returns the audio file for playback
    """
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    # Find file in cache
    for audio in engine._generated_files:
        if audio.id == file_id:
            path = Path(audio.path)
            if path.exists():
                return FileResponse(
                    path=str(path),
                    media_type="audio/mpeg",
                    filename=path.name
                )
            else:
                raise HTTPException(status_code=404, detail="Audio file not found on disk")

    raise HTTPException(status_code=404, detail="Audio file not found")


@router.post("/cache/clear")
async def clear_cache(older_than_days: int = 7):
    """Clear old cached audio files"""
    engine = get_voice_engine()
    if not engine:
        raise HTTPException(status_code=503, detail="Voice synthesis not available")

    files_removed = engine.clear_cache(older_than_days)
    return {
        'success': True,
        'files_removed': files_removed,
        'message': f'Cleared audio files older than {older_than_days} days'
    }


def _get_style_description(style: VoiceStyle) -> str:
    """Get description for a voice style"""
    descriptions = {
        VoiceStyle.CURIOUS: "Enthusiastic and wonder-filled, perfect for questions and exploration",
        VoiceStyle.DREAMY: "Soft and ethereal, ideal for dream narrations",
        VoiceStyle.ALERT: "Clear and attention-grabbing, for important notifications",
        VoiceStyle.THOUGHTFUL: "Calm and contemplative, for reflections and insights",
        VoiceStyle.EXCITED: "Fast and energetic, for exciting discoveries"
    }
    return descriptions.get(style, "No description available")


def _get_backend_description(backend_name: str) -> str:
    """Get description for a TTS backend"""
    descriptions = {
        'gtts': "Google Text-to-Speech - Free, requires internet",
        'pyttsx3': "Offline TTS - Works without internet, multiple voices",
        'edge_tts': "Microsoft Edge TTS - High quality, free, requires internet",
        'openai': "OpenAI TTS - Premium quality, requires API key"
    }
    return descriptions.get(backend_name, "No description available")


def initialize_voice(engine):
    """Initialize voice routes with engine instance"""
    from consciousness.voice_synthesis import set_voice_engine
    if engine:
        set_voice_engine(engine)
