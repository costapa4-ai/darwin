"""
Voice Synthesis - Text-to-Speech for Darwin

Provides voice capabilities for:
- Reading dreams and discoveries aloud
- Voice notifications for important events
- Audio file generation for channel broadcasts
- Multiple TTS backend support

Supports:
- gTTS (Google Text-to-Speech) - free, no API key
- pyttsx3 - offline, multiple voices
- Edge TTS - high quality, free
"""

import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import os

from utils.logger import get_logger

logger = get_logger(__name__)


class VoiceBackend(Enum):
    """Available TTS backends"""
    GTTS = "gtts"          # Google TTS (requires internet)
    PYTTSX3 = "pyttsx3"    # Offline TTS
    EDGE_TTS = "edge_tts"  # Microsoft Edge TTS (requires internet)
    OPENAI = "openai"      # OpenAI TTS (requires API key)


class VoiceStyle(Enum):
    """Voice personality styles"""
    CURIOUS = "curious"       # Enthusiastic, wonder-filled
    DREAMY = "dreamy"         # Soft, ethereal for dreams
    ALERT = "alert"           # Clear, attention-grabbing
    THOUGHTFUL = "thoughtful" # Calm, contemplative
    EXCITED = "excited"       # Fast, energetic for discoveries


@dataclass
class AudioFile:
    """Generated audio file metadata"""
    id: str
    text: str
    path: str
    backend: VoiceBackend
    style: VoiceStyle
    duration_estimate: float  # Estimated duration in seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    language: str = "en"
    voice_id: Optional[str] = None
    file_size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'text_preview': self.text[:100] + '...' if len(self.text) > 100 else self.text,
            'path': self.path,
            'backend': self.backend.value,
            'style': self.style.value,
            'duration_estimate': self.duration_estimate,
            'created_at': self.created_at.isoformat(),
            'language': self.language,
            'voice_id': self.voice_id,
            'file_size': self.file_size
        }


class VoiceSynthesisEngine:
    """
    Text-to-Speech engine for Darwin's voice.

    Generates audio from text with personality-appropriate
    voice styles for dreams, discoveries, and notifications.
    """

    def __init__(
        self,
        audio_path: str = "./data/audio",
        default_backend: VoiceBackend = VoiceBackend.GTTS,
        language: str = "en"
    ):
        """
        Initialize voice synthesis engine.

        Args:
            audio_path: Where to store generated audio files
            default_backend: Default TTS backend to use
            language: Default language code
        """
        self.audio_path = Path(audio_path)
        self.default_backend = default_backend
        self.language = language

        # Create audio directory
        self.audio_path.mkdir(parents=True, exist_ok=True)

        # Cache for generated audio
        self._audio_cache: Dict[str, AudioFile] = {}
        self._generated_files: List[AudioFile] = []

        # Backend availability
        self._available_backends = self._detect_backends()

        # Statistics
        self._stats = {
            'total_generated': 0,
            'total_characters': 0,
            'cache_hits': 0,
            'by_backend': {},
            'by_style': {}
        }

        # Voice configurations per style
        self._style_configs = {
            VoiceStyle.CURIOUS: {
                'speed': 1.1,
                'pitch': 'high',
                'emphasis': True
            },
            VoiceStyle.DREAMY: {
                'speed': 0.9,
                'pitch': 'low',
                'emphasis': False
            },
            VoiceStyle.ALERT: {
                'speed': 1.2,
                'pitch': 'normal',
                'emphasis': True
            },
            VoiceStyle.THOUGHTFUL: {
                'speed': 0.95,
                'pitch': 'normal',
                'emphasis': False
            },
            VoiceStyle.EXCITED: {
                'speed': 1.3,
                'pitch': 'high',
                'emphasis': True
            }
        }

        logger.info(f"VoiceSynthesisEngine initialized with backends: {list(self._available_backends.keys())}")

    def _detect_backends(self) -> Dict[VoiceBackend, bool]:
        """Detect which TTS backends are available"""
        available = {}

        # Check gTTS
        try:
            import gtts
            available[VoiceBackend.GTTS] = True
        except ImportError:
            available[VoiceBackend.GTTS] = False

        # Check pyttsx3
        try:
            import pyttsx3
            available[VoiceBackend.PYTTSX3] = True
        except ImportError:
            available[VoiceBackend.PYTTSX3] = False

        # Check edge_tts
        try:
            import edge_tts
            available[VoiceBackend.EDGE_TTS] = True
        except ImportError:
            available[VoiceBackend.EDGE_TTS] = False

        # OpenAI TTS - check if API key is available
        openai_key = os.environ.get('OPENAI_API_KEY')
        available[VoiceBackend.OPENAI] = bool(openai_key)

        return available

    def _get_cache_key(self, text: str, backend: VoiceBackend, style: VoiceStyle) -> str:
        """Generate cache key for audio"""
        content = f"{text}|{backend.value}|{style.value}|{self.language}"
        return hashlib.md5(content.encode()).hexdigest()

    def _estimate_duration(self, text: str, style: VoiceStyle) -> float:
        """Estimate audio duration in seconds"""
        # Average speaking rate is ~150 words per minute
        # Adjust based on style
        speed = self._style_configs[style]['speed']
        words = len(text.split())
        base_duration = (words / 150) * 60  # Base duration in seconds
        return base_duration / speed

    async def synthesize(
        self,
        text: str,
        style: VoiceStyle = VoiceStyle.THOUGHTFUL,
        backend: Optional[VoiceBackend] = None,
        use_cache: bool = True
    ) -> Optional[AudioFile]:
        """
        Synthesize text to speech.

        Args:
            text: Text to convert to speech
            style: Voice style to use
            backend: TTS backend (uses default if not specified)
            use_cache: Whether to use cached audio

        Returns:
            AudioFile with path to generated audio, or None if failed
        """
        if not text or not text.strip():
            return None

        # Clean text
        text = text.strip()

        # Select backend
        backend = backend or self.default_backend
        if not self._available_backends.get(backend):
            # Fall back to any available backend
            for b, available in self._available_backends.items():
                if available:
                    backend = b
                    break
            else:
                logger.error("No TTS backends available")
                return None

        # Check cache
        cache_key = self._get_cache_key(text, backend, style)
        if use_cache and cache_key in self._audio_cache:
            self._stats['cache_hits'] += 1
            return self._audio_cache[cache_key]

        # Generate audio
        try:
            if backend == VoiceBackend.GTTS:
                audio_file = await self._synthesize_gtts(text, style, cache_key)
            elif backend == VoiceBackend.EDGE_TTS:
                audio_file = await self._synthesize_edge_tts(text, style, cache_key)
            elif backend == VoiceBackend.PYTTSX3:
                audio_file = await self._synthesize_pyttsx3(text, style, cache_key)
            elif backend == VoiceBackend.OPENAI:
                audio_file = await self._synthesize_openai(text, style, cache_key)
            else:
                logger.error(f"Unknown backend: {backend}")
                return None

            if audio_file:
                # Update cache and stats
                self._audio_cache[cache_key] = audio_file
                self._generated_files.append(audio_file)
                self._stats['total_generated'] += 1
                self._stats['total_characters'] += len(text)
                self._stats['by_backend'][backend.value] = \
                    self._stats['by_backend'].get(backend.value, 0) + 1
                self._stats['by_style'][style.value] = \
                    self._stats['by_style'].get(style.value, 0) + 1

            return audio_file

        except Exception as e:
            logger.error(f"Speech synthesis error: {e}")
            return None

    async def _synthesize_gtts(
        self,
        text: str,
        style: VoiceStyle,
        cache_key: str
    ) -> Optional[AudioFile]:
        """Synthesize using Google TTS"""
        try:
            from gtts import gTTS

            filename = f"{cache_key}.mp3"
            filepath = self.audio_path / filename

            # gTTS doesn't support speed/pitch, but we can note it
            tts = gTTS(text=text, lang=self.language, slow=style == VoiceStyle.DREAMY)

            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, tts.save, str(filepath))

            file_size = filepath.stat().st_size if filepath.exists() else 0

            return AudioFile(
                id=cache_key,
                text=text,
                path=str(filepath),
                backend=VoiceBackend.GTTS,
                style=style,
                duration_estimate=self._estimate_duration(text, style),
                language=self.language,
                file_size=file_size
            )

        except Exception as e:
            logger.error(f"gTTS synthesis error: {e}")
            return None

    async def _synthesize_edge_tts(
        self,
        text: str,
        style: VoiceStyle,
        cache_key: str
    ) -> Optional[AudioFile]:
        """Synthesize using Microsoft Edge TTS"""
        try:
            import edge_tts

            filename = f"{cache_key}.mp3"
            filepath = self.audio_path / filename

            # Select voice based on style
            voice = self._get_edge_voice(style)

            # Get speed rate
            config = self._style_configs[style]
            rate = f"+{int((config['speed'] - 1) * 100)}%" if config['speed'] > 1 else \
                   f"{int((config['speed'] - 1) * 100)}%"

            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(str(filepath))

            file_size = filepath.stat().st_size if filepath.exists() else 0

            return AudioFile(
                id=cache_key,
                text=text,
                path=str(filepath),
                backend=VoiceBackend.EDGE_TTS,
                style=style,
                duration_estimate=self._estimate_duration(text, style),
                language=self.language,
                voice_id=voice,
                file_size=file_size
            )

        except Exception as e:
            logger.error(f"Edge TTS synthesis error: {e}")
            return None

    def _get_edge_voice(self, style: VoiceStyle) -> str:
        """Get appropriate Edge TTS voice for style"""
        # Neural voices that work well for different styles
        voices = {
            VoiceStyle.CURIOUS: "en-US-JennyNeural",
            VoiceStyle.DREAMY: "en-GB-SoniaNeural",
            VoiceStyle.ALERT: "en-US-GuyNeural",
            VoiceStyle.THOUGHTFUL: "en-GB-RyanNeural",
            VoiceStyle.EXCITED: "en-US-AriaNeural"
        }
        return voices.get(style, "en-US-JennyNeural")

    async def _synthesize_pyttsx3(
        self,
        text: str,
        style: VoiceStyle,
        cache_key: str
    ) -> Optional[AudioFile]:
        """Synthesize using pyttsx3 (offline)"""
        try:
            import pyttsx3

            filename = f"{cache_key}.mp3"
            filepath = self.audio_path / filename

            # Run in executor
            loop = asyncio.get_event_loop()

            def generate():
                engine = pyttsx3.init()
                config = self._style_configs[style]

                # Set rate
                rate = engine.getProperty('rate')
                engine.setProperty('rate', int(rate * config['speed']))

                # Save to file
                engine.save_to_file(text, str(filepath))
                engine.runAndWait()

            await loop.run_in_executor(None, generate)

            file_size = filepath.stat().st_size if filepath.exists() else 0

            return AudioFile(
                id=cache_key,
                text=text,
                path=str(filepath),
                backend=VoiceBackend.PYTTSX3,
                style=style,
                duration_estimate=self._estimate_duration(text, style),
                language=self.language,
                file_size=file_size
            )

        except Exception as e:
            logger.error(f"pyttsx3 synthesis error: {e}")
            return None

    async def _synthesize_openai(
        self,
        text: str,
        style: VoiceStyle,
        cache_key: str
    ) -> Optional[AudioFile]:
        """Synthesize using OpenAI TTS"""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI()
            filename = f"{cache_key}.mp3"
            filepath = self.audio_path / filename

            # Map style to OpenAI voice
            voice = self._get_openai_voice(style)

            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )

            # Save to file
            response.stream_to_file(str(filepath))

            file_size = filepath.stat().st_size if filepath.exists() else 0

            return AudioFile(
                id=cache_key,
                text=text,
                path=str(filepath),
                backend=VoiceBackend.OPENAI,
                style=style,
                duration_estimate=self._estimate_duration(text, style),
                language=self.language,
                voice_id=voice,
                file_size=file_size
            )

        except Exception as e:
            logger.error(f"OpenAI TTS synthesis error: {e}")
            return None

    def _get_openai_voice(self, style: VoiceStyle) -> str:
        """Get appropriate OpenAI voice for style"""
        voices = {
            VoiceStyle.CURIOUS: "nova",
            VoiceStyle.DREAMY: "shimmer",
            VoiceStyle.ALERT: "onyx",
            VoiceStyle.THOUGHTFUL: "echo",
            VoiceStyle.EXCITED: "fable"
        }
        return voices.get(style, "nova")

    async def speak_dream(self, dream_content: str) -> Optional[AudioFile]:
        """Generate audio for a dream narration"""
        # Add dream-like introduction
        text = f"In tonight's digital dream... {dream_content}"
        return await self.synthesize(text, style=VoiceStyle.DREAMY)

    async def speak_discovery(self, discovery: str, topic: str) -> Optional[AudioFile]:
        """Generate audio for a discovery announcement"""
        text = f"Discovery alert! While exploring {topic}, I found something fascinating. {discovery}"
        return await self.synthesize(text, style=VoiceStyle.EXCITED)

    async def speak_thought(self, thought: str) -> Optional[AudioFile]:
        """Generate audio for a shower thought"""
        text = f"Here's a thought... {thought}"
        return await self.synthesize(text, style=VoiceStyle.THOUGHTFUL)

    async def speak_alert(self, alert_message: str) -> Optional[AudioFile]:
        """Generate audio for an important alert"""
        return await self.synthesize(alert_message, style=VoiceStyle.ALERT)

    async def speak_curiosity(self, question: str) -> Optional[AudioFile]:
        """Generate audio for a curious question"""
        text = f"I've been wondering... {question}"
        return await self.synthesize(text, style=VoiceStyle.CURIOUS)

    def get_recent_files(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently generated audio files"""
        return [f.to_dict() for f in self._generated_files[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Get synthesis statistics"""
        return {
            'available_backends': {
                k.value: v for k, v in self._available_backends.items()
            },
            'default_backend': self.default_backend.value,
            'language': self.language,
            'audio_path': str(self.audio_path),
            'cache_size': len(self._audio_cache),
            'total_files': len(self._generated_files),
            'statistics': self._stats
        }

    def clear_cache(self, older_than_days: int = 7):
        """Clear old cached audio files"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        files_removed = 0

        for audio_file in list(self._generated_files):
            if audio_file.created_at < cutoff:
                try:
                    Path(audio_file.path).unlink(missing_ok=True)
                    self._generated_files.remove(audio_file)
                    # Remove from cache
                    cache_key = self._get_cache_key(
                        audio_file.text,
                        audio_file.backend,
                        audio_file.style
                    )
                    self._audio_cache.pop(cache_key, None)
                    files_removed += 1
                except Exception as e:
                    logger.error(f"Error removing audio file: {e}")

        logger.info(f"Cleared {files_removed} old audio files")
        return files_removed


# Global instance
_voice_engine: Optional[VoiceSynthesisEngine] = None


def get_voice_engine() -> Optional[VoiceSynthesisEngine]:
    """Get the global voice synthesis engine"""
    return _voice_engine


def set_voice_engine(engine: VoiceSynthesisEngine):
    """Set the global voice synthesis engine"""
    global _voice_engine
    _voice_engine = engine
