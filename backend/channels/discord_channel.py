"""
Discord Channel - Darwin's Discord Bot Integration

Meme-aware, reaction-based personality with rich embeds.
Uses Discord's embed system for beautiful message formatting.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

from .base_channel import (
    BaseChannel, ChannelMessage, IncomingMessage,
    ChannelType, MessageType, MessagePriority
)
from utils.logger import get_logger

logger = get_logger(__name__)


class DiscordChannel(BaseChannel):
    """
    Discord bot channel implementation.

    Uses Discord HTTP API for webhooks and bot messages.
    Personality: Meme-aware, uses rich embeds, reaction-friendly.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Discord channel.

        Args:
            config: Configuration including:
                - bot_token: Discord bot token
                - webhook_urls: List of webhook URLs for broadcasts
                - channel_ids: List of channel IDs (for bot mode)
                - enabled: Whether channel is enabled
        """
        super().__init__(ChannelType.DISCORD, config)

        self.bot_token = config.get('bot_token', '')
        self.webhook_urls = config.get('webhook_urls', [])
        self.channel_ids = config.get('channel_ids', [])
        self.api_base = "https://discord.com/api/v10"

        # Discord colors for embeds
        self.colors = {
            'dream': 0x9B59B6,      # Purple
            'discovery': 0x3498DB,   # Blue
            'thought': 0xF1C40F,     # Yellow
            'alert': 0xE74C3C,       # Red
            'success': 0x2ECC71,     # Green
            'poetry': 0xE91E63,      # Pink
            'status': 0x95A5A6,      # Gray
        }

        # Personality flavor for Discord: meme-aware
        self.personality_flavor = 'hacker'

        # Gateway connection for receiving messages
        self._gateway_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info("DiscordChannel initialized")

    async def connect(self) -> bool:
        """Connect to Discord"""
        # For simplicity, we'll use webhook mode primarily
        # Full bot mode with gateway would require more complex implementation

        if not self.bot_token and not self.webhook_urls:
            logger.warning("Discord not configured (no token or webhooks)")
            return False

        try:
            self._session = aiohttp.ClientSession()

            # Verify bot token if provided
            if self.bot_token:
                headers = {'Authorization': f'Bot {self.bot_token}'}
                async with self._session.get(
                    f"{self.api_base}/users/@me",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Discord connected as {data.get('username')}#{data.get('discriminator')}")
                        self.connected = True
                        return True

            # Fallback to webhook-only mode
            if self.webhook_urls:
                logger.info("Discord connected in webhook-only mode")
                self.connected = True
                return True

            return False

        except Exception as e:
            logger.error(f"Discord connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Discord"""
        if self._gateway_task:
            self._gateway_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._session:
            await self._session.close()

        self.connected = False
        logger.info("Discord disconnected")
        return True

    async def send_message(self, message: ChannelMessage, target_id: str) -> bool:
        """Send a message to a specific channel"""
        if not self.connected or not self._session:
            return False

        # Check if target is a webhook URL
        if target_id.startswith('https://discord.com/api/webhooks/'):
            return await self._send_webhook(message, target_id)

        # Otherwise use bot API to send to channel
        if not self.bot_token:
            logger.warning("Bot token required for channel messages")
            return False

        try:
            embed = self._create_embed(message)
            headers = {'Authorization': f'Bot {self.bot_token}'}

            payload = {
                'embeds': [embed] if embed else None,
                'content': message.content if not embed else None
            }

            async with self._session.post(
                f"{self.api_base}/channels/{target_id}/messages",
                headers=headers,
                json=payload
            ) as response:
                return response.status in [200, 201]

        except Exception as e:
            logger.error(f"Discord send error: {e}")
            return False

    async def _send_webhook(self, message: ChannelMessage, webhook_url: str) -> bool:
        """Send message via webhook"""
        try:
            embed = self._create_embed(message)

            payload = {
                'username': 'Darwin',
                'avatar_url': 'https://raw.githubusercontent.com/github/explore/main/topics/artificial-intelligence/artificial-intelligence.png',
                'embeds': [embed] if embed else None,
                'content': message.content if not embed else None
            }

            async with self._session.post(webhook_url, json=payload) as response:
                return response.status in [200, 204]

        except Exception as e:
            logger.error(f"Discord webhook error: {e}")
            return False

    async def broadcast(self, message: ChannelMessage) -> int:
        """Broadcast to all configured channels/webhooks"""
        if not self.connected:
            return 0

        success_count = 0

        # Send to webhooks
        for webhook_url in self.webhook_urls:
            if await self._send_webhook(message, webhook_url):
                success_count += 1
                await asyncio.sleep(0.5)  # Rate limit protection

        # Send to channels (if bot mode)
        if self.bot_token:
            for channel_id in self.channel_ids:
                if await self.send_message(message, channel_id):
                    success_count += 1
                    await asyncio.sleep(0.5)

        return success_count

    def format_message(self, message: ChannelMessage) -> str:
        """
        Format message for Discord.

        Discord uses embeds primarily, so this returns plain text
        for simple messages only.
        """
        parts = []

        # Discord doesn't need heavy formatting - embeds handle it
        if message.title:
            parts.append(f"**{message.title}**\n")

        parts.append(message.content)

        if message.code_block:
            lang = message.code_language or ''
            parts.append(f"\n```{lang}\n{message.code_block}\n```")

        return "".join(parts)

    def _create_embed(self, message: ChannelMessage) -> Optional[Dict[str, Any]]:
        """Create a Discord embed from a channel message"""

        # Determine embed color based on message type
        color = self.colors.get(message.message_type.value, 0x7289DA)

        if message.priority == MessagePriority.URGENT:
            color = self.colors['alert']

        embed = {
            'color': color,
            'timestamp': message.timestamp.isoformat(),
            'footer': {
                'text': 'Darwin AI',
                'icon_url': 'https://raw.githubusercontent.com/github/explore/main/topics/artificial-intelligence/artificial-intelligence.png'
            }
        }

        # Set title based on message type
        type_titles = {
            MessageType.DREAM: '💭 Dream Report',
            MessageType.DISCOVERY: '🔍 Discovery',
            MessageType.THOUGHT: '💡 Shower Thought',
            MessageType.STATUS: '📊 Status Update',
            MessageType.ALERT: '🚨 Alert',
            MessageType.POETRY: '🎭 Code Poetry',
            MessageType.LEARNING: '📚 Learning Milestone',
        }

        embed['title'] = message.title or type_titles.get(message.message_type, 'Darwin Says')

        # Description (main content)
        description = message.content
        if len(description) > 4096:
            description = description[:4093] + '...'
        embed['description'] = description

        # Add fields for metadata
        fields = []

        if message.message_type == MessageType.DISCOVERY:
            discovery_type = message.metadata.get('discovery_type', 'general')
            severity = message.metadata.get('severity', 'normal')
            fields.append({
                'name': 'Type',
                'value': discovery_type.title(),
                'inline': True
            })
            fields.append({
                'name': 'Severity',
                'value': severity.title(),
                'inline': True
            })

        if message.message_type == MessageType.STATUS:
            state = message.metadata.get('state', 'unknown')
            state_emoji = '☀️' if state == 'wake' else '🌙' if state == 'sleep' else '🔄'
            fields.append({
                'name': 'State',
                'value': f'{state_emoji} {state.title()}',
                'inline': True
            })

        if fields:
            embed['fields'] = fields

        # Add code block as a field
        if message.code_block:
            code_preview = message.code_block[:1000]
            if len(message.code_block) > 1000:
                code_preview += '...'
            embed['fields'] = embed.get('fields', []) + [{
                'name': f'Code ({message.code_language or "text"})',
                'value': f'```{message.code_language or ""}\n{code_preview}\n```',
                'inline': False
            }]

        # Image if present
        if message.image_url:
            embed['image'] = {'url': message.image_url}

        return embed

    # Discord-specific emoji (using Discord emoji syntax)
    def get_emoji(self, emoji_type: str) -> str:
        """Get Discord emoji (supports custom server emojis if needed)"""
        # Using standard Unicode emojis - could be extended for custom server emojis
        discord_emojis = {
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
            'contemplative': '🧘',
            'pepe': ':pepe:',  # Custom emoji placeholder
            'stonks': ':stonks:',  # Custom emoji placeholder
        }
        return discord_emojis.get(emoji_type, super().get_emoji(emoji_type))
