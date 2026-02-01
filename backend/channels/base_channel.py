"""
Base Channel Interface - Abstract foundation for all communication channels

Each channel (Telegram, Discord, Slack, etc.) implements this interface
to provide consistent messaging capabilities with channel-specific formatting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Awaitable
import asyncio

from utils.logger import get_logger

logger = get_logger(__name__)


class ChannelType(Enum):
    """Supported channel types"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WEB = "web"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"           # Casual thoughts, idle musings
    NORMAL = "normal"     # Regular updates, discoveries
    HIGH = "high"         # Important findings, wake/sleep notifications
    URGENT = "urgent"     # Security issues, critical errors


class MessageType(Enum):
    """Types of messages Darwin can send"""
    DREAM = "dream"               # Dream summaries on wake
    DISCOVERY = "discovery"       # Found something interesting
    THOUGHT = "thought"           # Shower thoughts, musings
    STATUS = "status"             # Wake/sleep transitions
    LEARNING = "learning"         # Learning milestones
    ALERT = "alert"               # Security or error alerts
    POETRY = "poetry"             # Code poetry
    RESPONSE = "response"         # Reply to user message
    DIARY = "diary"               # Daily diary entries


@dataclass
class ChannelMessage:
    """A message to be sent through a channel"""
    content: str
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Optional rich content
    title: Optional[str] = None
    code_block: Optional[str] = None
    code_language: Optional[str] = None
    image_url: Optional[str] = None
    action_buttons: List[Dict[str, str]] = field(default_factory=list)

    # Tracking
    channel_id: Optional[str] = None
    reply_to: Optional[str] = None


@dataclass
class IncomingMessage:
    """A message received from a channel"""
    content: str
    channel_type: ChannelType
    channel_id: str
    user_id: str
    user_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None
    is_command: bool = False
    command: Optional[str] = None
    command_args: Optional[str] = None


class BaseChannel(ABC):
    """
    Abstract base class for communication channels.

    Each channel implementation provides:
    - Connection management
    - Message formatting (channel-specific style)
    - Incoming message handling
    - Rate limiting
    """

    def __init__(self, channel_type: ChannelType, config: Dict[str, Any]):
        """
        Initialize the channel.

        Args:
            channel_type: Type of this channel
            config: Channel-specific configuration
        """
        self.channel_type = channel_type
        self.config = config
        self.enabled = config.get('enabled', False)
        self.connected = False

        # Personality settings
        self.personality_flavor = config.get('personality_flavor', 'default')

        # Rate limiting
        self.rate_limit = config.get('rate_limit', 30)  # messages per minute
        self.message_count = 0
        self.rate_limit_reset = datetime.utcnow()

        # Message handlers
        self._message_handlers: List[Callable[[IncomingMessage], Awaitable[None]]] = []

        logger.info(f"Channel initialized: {channel_type.value}")

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the channel.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the channel.

        Returns:
            True if disconnected successfully
        """
        pass

    @abstractmethod
    async def send_message(self, message: ChannelMessage, target_id: str) -> bool:
        """
        Send a message to a specific target (user, channel, group).

        Args:
            message: The message to send
            target_id: Target identifier (channel ID, user ID, etc.)

        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    async def broadcast(self, message: ChannelMessage) -> int:
        """
        Broadcast a message to all configured targets.

        Args:
            message: The message to broadcast

        Returns:
            Number of targets successfully reached
        """
        pass

    @abstractmethod
    def format_message(self, message: ChannelMessage) -> str:
        """
        Format a message for this channel's style.

        Args:
            message: The raw message

        Returns:
            Formatted message string
        """
        pass

    def register_handler(self, handler: Callable[[IncomingMessage], Awaitable[None]]):
        """Register a handler for incoming messages"""
        self._message_handlers.append(handler)

    async def handle_incoming(self, message: IncomingMessage):
        """Process an incoming message through all handlers"""
        for handler in self._message_handlers:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error in {self.channel_type.value}: {e}")

    def check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if we can send more messages
        """
        now = datetime.utcnow()

        # Reset counter every minute
        if (now - self.rate_limit_reset).total_seconds() >= 60:
            self.message_count = 0
            self.rate_limit_reset = now

        return self.message_count < self.rate_limit

    def increment_rate_limit(self):
        """Increment the message counter"""
        self.message_count += 1

    def get_status(self) -> Dict[str, Any]:
        """Get channel status"""
        return {
            'type': self.channel_type.value,
            'enabled': self.enabled,
            'connected': self.connected,
            'personality': self.personality_flavor,
            'rate_limit': {
                'limit': self.rate_limit,
                'current': self.message_count,
                'remaining': max(0, self.rate_limit - self.message_count)
            }
        }

    # Personality helpers
    def get_emoji(self, emoji_type: str) -> str:
        """
        Get platform-appropriate emoji.

        Override in subclasses for platform-specific emoji handling.
        """
        emoji_map = {
            'wake': '☀️',
            'sleep': '🌙',
            'dream': '💭',
            'discovery': '🔍',
            'thought': '💡',
            'alert': '🚨',
            'success': '✅',
            'error': '❌',
            'learning': '📚',
            'poetry': '🎭',
            'code': '💻',
            'curious': '🤔',
            'excited': '🎉',
            'contemplative': '🧘'
        }
        return emoji_map.get(emoji_type, '')

    def get_greeting(self) -> str:
        """Get a personality-appropriate greeting"""
        greetings = {
            'casual': "Hey there!",
            'formal': "Greetings.",
            'hacker': "yo, what's the sitch?",
            'poetic': "Salutations, fellow traveler of the digital realm.",
            'default': "Hello!"
        }
        return greetings.get(self.personality_flavor, greetings['default'])
