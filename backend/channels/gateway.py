"""
Channel Gateway - Central hub for multi-channel communication

Manages all communication channels, routes messages, and provides
a unified interface for Darwin's consciousness to communicate
across platforms.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable
from pathlib import Path
import json

from .base_channel import (
    BaseChannel, ChannelMessage, IncomingMessage,
    ChannelType, MessageType, MessagePriority
)
from utils.logger import get_logger

logger = get_logger(__name__)


class ChannelGateway:
    """
    Central gateway for multi-channel communication.

    Features:
    - Channel registration and lifecycle management
    - Message routing to appropriate channels
    - Priority-based delivery
    - Rate limiting coordination
    - Hook system for consciousness integration
    - Optional voice synthesis for audio broadcasts
    """

    def __init__(self, config_path: str = "./data/channels/config.json"):
        """
        Initialize the channel gateway.

        Args:
            config_path: Path to channel configuration file
        """
        self.config_path = Path(config_path)
        self.channels: Dict[ChannelType, BaseChannel] = {}
        self.enabled = False
        self.voice_engine = None  # Optional voice synthesis engine

        # Message queue for async delivery
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self._queue_processor_task: Optional[asyncio.Task] = None

        # Hooks for consciousness integration
        self.hooks: Dict[str, List[Callable[..., Awaitable[None]]]] = {
            'on_message_received': [],
            'on_message_sent': [],
            'on_channel_connected': [],
            'on_channel_disconnected': [],
            'on_broadcast_complete': [],
        }

        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'broadcasts_sent': 0,
            'errors': 0,
            'started_at': None
        }

        # Default channel targets for broadcasts
        self.broadcast_targets: Dict[ChannelType, List[str]] = {}

        logger.info("ChannelGateway initialized")

    async def start(self):
        """Start the gateway and connect all enabled channels"""
        logger.info("Starting ChannelGateway...")

        # Load configuration
        await self._load_config()

        # Start message queue processor
        self._queue_processor_task = asyncio.create_task(self._process_message_queue())

        # Connect all enabled channels
        for channel_type, channel in self.channels.items():
            if channel.enabled:
                try:
                    success = await channel.connect()
                    if success:
                        logger.info(f"Channel connected: {channel_type.value}")
                        await self._trigger_hook('on_channel_connected', channel_type)
                    else:
                        logger.warning(f"Failed to connect channel: {channel_type.value}")
                except Exception as e:
                    logger.error(f"Error connecting {channel_type.value}: {e}")

        self.enabled = True
        self.stats['started_at'] = datetime.utcnow().isoformat()
        logger.info(f"ChannelGateway started with {len(self.channels)} channels")

    async def stop(self):
        """Stop the gateway and disconnect all channels"""
        logger.info("Stopping ChannelGateway...")

        # Stop queue processor
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass

        # Disconnect all channels
        for channel_type, channel in self.channels.items():
            if channel.connected:
                try:
                    await channel.disconnect()
                    await self._trigger_hook('on_channel_disconnected', channel_type)
                except Exception as e:
                    logger.error(f"Error disconnecting {channel_type.value}: {e}")

        self.enabled = False
        logger.info("ChannelGateway stopped")

    def register_channel(self, channel: BaseChannel):
        """
        Register a channel with the gateway.

        Args:
            channel: Channel instance to register
        """
        self.channels[channel.channel_type] = channel

        # Register incoming message handler
        channel.register_handler(self._handle_incoming_message)

        logger.info(f"Registered channel: {channel.channel_type.value}")

    async def send(self,
                   message: ChannelMessage,
                   channel_type: ChannelType,
                   target_id: str) -> bool:
        """
        Send a message to a specific channel and target.

        Args:
            message: Message to send
            channel_type: Target channel type
            target_id: Target identifier

        Returns:
            True if sent successfully
        """
        channel = self.channels.get(channel_type)
        if not channel or not channel.connected:
            logger.warning(f"Channel not available: {channel_type.value}")
            return False

        if not channel.check_rate_limit():
            logger.warning(f"Rate limit exceeded for {channel_type.value}")
            return False

        try:
            success = await channel.send_message(message, target_id)
            if success:
                channel.increment_rate_limit()
                self.stats['messages_sent'] += 1
                await self._trigger_hook('on_message_sent', message, channel_type)
            return success
        except Exception as e:
            logger.error(f"Error sending to {channel_type.value}: {e}")
            self.stats['errors'] += 1
            return False

    async def broadcast(self,
                        message: ChannelMessage,
                        channel_types: Optional[List[ChannelType]] = None,
                        priority_filter: Optional[MessagePriority] = None) -> Dict[ChannelType, int]:
        """
        Broadcast a message to multiple channels.

        Args:
            message: Message to broadcast
            channel_types: Specific channels to target (None = all enabled)
            priority_filter: Only send if message meets this priority

        Returns:
            Dict of channel type to number of targets reached
        """
        if priority_filter and message.priority.value < priority_filter.value:
            return {}

        targets = channel_types or list(self.channels.keys())
        results: Dict[ChannelType, int] = {}

        for channel_type in targets:
            channel = self.channels.get(channel_type)
            if channel and channel.connected and channel.enabled:
                try:
                    count = await channel.broadcast(message)
                    results[channel_type] = count
                    self.stats['broadcasts_sent'] += 1
                except Exception as e:
                    logger.error(f"Broadcast error for {channel_type.value}: {e}")
                    results[channel_type] = 0
                    self.stats['errors'] += 1

        await self._trigger_hook('on_broadcast_complete', message, results)
        return results

    async def broadcast_dream(self, dream_summary: str, highlights: List[str] = None, generate_audio: bool = True):
        """
        Broadcast a dream summary when Darwin wakes.

        Args:
            dream_summary: Summary of the dream
            highlights: Notable dream highlights
            generate_audio: Whether to generate voice narration
        """
        content = f"{self._get_emoji('dream')} Darwin just woke up!\n\n"
        content += f"Last night I dreamed...\n{dream_summary}\n"

        if highlights:
            content += "\nDream Highlights:\n"
            for highlight in highlights[:3]:
                content += f"  {self._get_emoji('thought')} {highlight}\n"

        content += f"\n{self._get_emoji('wake')} Now entering WAKE mode. Ready for adventures!"

        # Generate voice narration if engine available
        audio_path = None
        if generate_audio and self.voice_engine:
            try:
                audio_file = await self.voice_engine.speak_dream(dream_summary)
                if audio_file:
                    audio_path = audio_file.path
                    logger.info(f"Generated dream audio: {audio_path}")
            except Exception as e:
                logger.error(f"Error generating dream audio: {e}")

        message = ChannelMessage(
            content=content,
            message_type=MessageType.DREAM,
            priority=MessagePriority.HIGH,
            title="Darwin's Dream Report",
            metadata={'audio_path': audio_path} if audio_path else {}
        )

        await self.broadcast(message)

    async def broadcast_discovery(self,
                                   discovery: str,
                                   discovery_type: str = "pattern",
                                   severity: str = "normal",
                                   generate_audio: bool = True):
        """
        Broadcast a discovery announcement.

        Args:
            discovery: What was discovered
            discovery_type: Type of discovery (pattern, security, learning, etc.)
            severity: How important (normal, important, critical)
            generate_audio: Whether to generate voice announcement
        """
        emoji = self._get_emoji('discovery')
        priority = MessagePriority.NORMAL

        if severity == "critical":
            emoji = self._get_emoji('alert')
            priority = MessagePriority.URGENT
        elif severity == "important":
            priority = MessagePriority.HIGH

        content = f"{emoji} Discovery: {discovery_type.title()}\n\n{discovery}"

        # Generate voice announcement for important discoveries
        audio_path = None
        if generate_audio and self.voice_engine and severity in ('important', 'critical'):
            try:
                audio_file = await self.voice_engine.speak_discovery(discovery, discovery_type)
                if audio_file:
                    audio_path = audio_file.path
                    logger.info(f"Generated discovery audio: {audio_path}")
            except Exception as e:
                logger.error(f"Error generating discovery audio: {e}")

        message = ChannelMessage(
            content=content,
            message_type=MessageType.DISCOVERY,
            priority=priority,
            metadata={'discovery_type': discovery_type, 'severity': severity, 'audio_path': audio_path}
        )

        await self.broadcast(message)

    async def broadcast_thought(self, thought: str, generate_audio: bool = False):
        """
        Broadcast a shower thought or musing.

        Args:
            thought: The profound/absurd thought
            generate_audio: Whether to generate voice (default off for thoughts)
        """
        emoji = self._get_emoji('thought')
        content = f"{emoji} Shower Thought:\n\n\"{thought}\""

        # Generate voice for thought if requested
        audio_path = None
        if generate_audio and self.voice_engine:
            try:
                audio_file = await self.voice_engine.speak_thought(thought)
                if audio_file:
                    audio_path = audio_file.path
            except Exception as e:
                logger.error(f"Error generating thought audio: {e}")

        message = ChannelMessage(
            content=content,
            message_type=MessageType.THOUGHT,
            priority=MessagePriority.LOW,
            metadata={'audio_path': audio_path} if audio_path else {}
        )

        await self.broadcast(message)

    async def broadcast_status(self, status: str, state: str):
        """
        Broadcast a status update (wake/sleep transitions).

        Args:
            status: Status message
            state: Current state (wake, sleep, etc.)
        """
        emoji = self._get_emoji(state)
        content = f"{emoji} {status}"

        message = ChannelMessage(
            content=content,
            message_type=MessageType.STATUS,
            priority=MessagePriority.NORMAL,
            metadata={'state': state}
        )

        await self.broadcast(message)

    async def broadcast_poetry(self, poem: str, title: str = "Code Poetry"):
        """
        Broadcast code poetry.

        Args:
            poem: The poem content
            title: Poem title
        """
        emoji = self._get_emoji('poetry')
        content = f"{emoji} {title}\n\n{poem}"

        message = ChannelMessage(
            content=content,
            message_type=MessageType.POETRY,
            priority=MessagePriority.LOW,
            title=title
        )

        await self.broadcast(message)

    def add_hook(self, hook_name: str, callback: Callable[..., Awaitable[None]]):
        """Add a hook callback"""
        if hook_name in self.hooks:
            self.hooks[hook_name].append(callback)

    async def _trigger_hook(self, hook_name: str, *args, **kwargs):
        """Trigger all callbacks for a hook"""
        for callback in self.hooks.get(hook_name, []):
            try:
                await callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook error ({hook_name}): {e}")

    async def _handle_incoming_message(self, message: IncomingMessage):
        """Handle an incoming message from any channel"""
        self.stats['messages_received'] += 1

        # Check for commands
        if message.is_command:
            await self._handle_command(message)
        else:
            await self._trigger_hook('on_message_received', message)

    async def _handle_command(self, message: IncomingMessage):
        """Handle slash commands from channels"""
        command = message.command.lower() if message.command else ""

        # Built-in commands
        if command == "/status":
            response = self._format_status_response()
        elif command == "/dream":
            response = "Dream recall not yet implemented in this channel."
        elif command == "/thought":
            response = "Generating thought... (connect to consciousness engine)"
        elif command == "/mood":
            response = "Mood check not yet implemented in this channel."
        elif command == "/help":
            response = self._format_help_response()
        else:
            response = f"Unknown command: {command}"

        # Send response back
        reply = ChannelMessage(
            content=response,
            message_type=MessageType.RESPONSE,
            reply_to=message.channel_id
        )

        await self.send(reply, message.channel_type, message.channel_id)

    def _format_status_response(self) -> str:
        """Format a status response"""
        channels_status = []
        for ct, ch in self.channels.items():
            status = "🟢" if ch.connected else "🔴"
            channels_status.append(f"  {status} {ct.value}")

        return f"""Darwin Gateway Status

Channels:
{chr(10).join(channels_status)}

Stats:
  Messages sent: {self.stats['messages_sent']}
  Messages received: {self.stats['messages_received']}
  Broadcasts: {self.stats['broadcasts_sent']}
  Running since: {self.stats['started_at'] or 'Not started'}
"""

    def _format_help_response(self) -> str:
        """Format a help response"""
        return """Darwin Commands:
/status - Gateway and channel status
/dream - Recall last dream
/thought - Get a shower thought
/mood - Check Darwin's current mood
/help - Show this help message
"""

    def _get_emoji(self, emoji_type: str) -> str:
        """Get an emoji for message formatting"""
        emoji_map = {
            'wake': '☀️',
            'sleep': '🌙',
            'dream': '💭',
            'discovery': '🔍',
            'thought': '💡',
            'alert': '🚨',
            'poetry': '🎭',
        }
        return emoji_map.get(emoji_type, '')

    async def _load_config(self):
        """Load channel configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    config = json.load(f)

                self.broadcast_targets = {
                    ChannelType(k): v
                    for k, v in config.get('broadcast_targets', {}).items()
                }
                logger.info("Channel configuration loaded")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    async def _save_config(self):
        """Save channel configuration"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            config = {
                'broadcast_targets': {
                    k.value: v for k, v in self.broadcast_targets.items()
                }
            }

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info("Channel configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    async def _process_message_queue(self):
        """Process queued messages"""
        while True:
            try:
                message, channel_type, target = await self.message_queue.get()
                await self.send(message, channel_type, target)
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processing error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get gateway status"""
        return {
            'enabled': self.enabled,
            'channels': {
                ct.value: ch.get_status() for ct, ch in self.channels.items()
            },
            'stats': self.stats,
            'queue_size': self.message_queue.qsize()
        }
