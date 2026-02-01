"""
Telegram Channel - Darwin's Telegram Bot Integration

Casual, emoji-friendly personality for Telegram users.
Supports commands, broadcasts, and interactive messaging.
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


class TelegramChannel(BaseChannel):
    """
    Telegram bot channel implementation.

    Uses Telegram Bot API directly via HTTP for simplicity.
    Personality: Casual, emoji-heavy, friendly.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Telegram channel.

        Args:
            config: Configuration including:
                - bot_token: Telegram bot token
                - chat_ids: List of chat IDs to broadcast to
                - enabled: Whether channel is enabled
        """
        super().__init__(ChannelType.TELEGRAM, config)

        self.bot_token = config.get('bot_token', '')
        self.chat_ids = config.get('chat_ids', [])
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

        # Telegram-specific settings
        self.parse_mode = config.get('parse_mode', 'HTML')
        self.disable_notification = config.get('disable_notification', False)

        # Polling settings
        self.polling_interval = config.get('polling_interval', 2)
        self._polling_task: Optional[asyncio.Task] = None
        self._last_update_id = 0

        # Personality flavor for Telegram: casual and emoji-friendly
        self.personality_flavor = 'casual'

        logger.info("TelegramChannel initialized")

    async def connect(self) -> bool:
        """Connect to Telegram and start polling for updates"""
        if not self.bot_token:
            logger.warning("Telegram bot token not configured")
            return False

        try:
            # Verify bot token
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/getMe") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            logger.info(f"Telegram connected as @{bot_info.get('username')}")
                            self.connected = True

                            # Start polling for incoming messages
                            self._polling_task = asyncio.create_task(self._poll_updates())
                            return True

            logger.error("Telegram connection failed")
            return False

        except Exception as e:
            logger.error(f"Telegram connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Telegram"""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        self.connected = False
        logger.info("Telegram disconnected")
        return True

    async def send_message(self, message: ChannelMessage, target_id: str) -> bool:
        """Send a message to a specific chat"""
        if not self.connected:
            return False

        formatted = self.format_message(message)

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'chat_id': target_id,
                    'text': formatted,
                    'parse_mode': self.parse_mode,
                    'disable_notification': self.disable_notification
                }

                # Add reply markup if action buttons present
                if message.action_buttons:
                    payload['reply_markup'] = self._create_inline_keyboard(message.action_buttons)

                async with session.post(
                    f"{self.api_base}/sendMessage",
                    json=payload
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Telegram send error: {error}")
                        return False

        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def broadcast(self, message: ChannelMessage) -> int:
        """Broadcast to all configured chats"""
        if not self.connected or not self.chat_ids:
            return 0

        success_count = 0
        for chat_id in self.chat_ids:
            if await self.send_message(message, chat_id):
                success_count += 1
                # Small delay between messages to avoid rate limits
                await asyncio.sleep(0.1)

        return success_count

    def format_message(self, message: ChannelMessage) -> str:
        """
        Format message for Telegram's casual style.

        Uses HTML formatting and lots of emojis.
        """
        parts = []

        # Add type-specific header
        if message.message_type == MessageType.DREAM:
            parts.append("💭 <b>Dream Report</b> 💭\n")
        elif message.message_type == MessageType.DISCOVERY:
            parts.append("🔍 <b>Discovery!</b>\n")
        elif message.message_type == MessageType.THOUGHT:
            parts.append("💡 <b>Shower Thought</b>\n")
        elif message.message_type == MessageType.STATUS:
            state = message.metadata.get('state', 'unknown')
            emoji = '☀️' if state == 'wake' else '🌙' if state == 'sleep' else '🔄'
            parts.append(f"{emoji} <b>Status Update</b>\n")
        elif message.message_type == MessageType.ALERT:
            parts.append("🚨 <b>Alert!</b> 🚨\n")
        elif message.message_type == MessageType.POETRY:
            parts.append("🎭 <b>Code Poetry</b>\n")

        # Add title if present
        if message.title and message.message_type not in [MessageType.DREAM, MessageType.THOUGHT]:
            parts.append(f"<b>{message.title}</b>\n\n")

        # Main content
        parts.append(message.content)

        # Add code block if present
        if message.code_block:
            lang = message.code_language or ''
            parts.append(f"\n\n<pre><code class=\"{lang}\">{message.code_block}</code></pre>")

        # Add footer based on priority
        if message.priority == MessagePriority.URGENT:
            parts.append("\n\n⚠️ <i>This requires attention!</i>")
        elif message.priority == MessagePriority.HIGH:
            parts.append("\n\n📌 <i>Important update</i>")

        # Casual sign-off for certain message types
        if message.message_type in [MessageType.DREAM, MessageType.THOUGHT]:
            casual_signoffs = [
                "✨ <i>- Darwin</i>",
                "🤖 <i>Yours in code</i>",
                "💭 <i>*beep boop*</i>"
            ]
            import random
            parts.append(f"\n\n{random.choice(casual_signoffs)}")

        return "".join(parts)

    def _create_inline_keyboard(self, buttons: List[Dict[str, str]]) -> Dict:
        """Create Telegram inline keyboard from button list"""
        keyboard = []
        for button in buttons:
            keyboard.append([{
                'text': button.get('label', 'Button'),
                'callback_data': button.get('callback', 'noop')
            }])

        return {'inline_keyboard': keyboard}

    async def _poll_updates(self):
        """Poll Telegram for updates (incoming messages)"""
        logger.info("Starting Telegram polling...")

        while self.connected:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        'offset': self._last_update_id + 1,
                        'timeout': 30
                    }

                    async with session.get(
                        f"{self.api_base}/getUpdates",
                        params=params
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('ok'):
                                for update in data.get('result', []):
                                    await self._process_update(update)
                                    self._last_update_id = update.get('update_id', self._last_update_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling error: {e}")
                await asyncio.sleep(5)  # Wait before retry

            await asyncio.sleep(self.polling_interval)

    async def _process_update(self, update: Dict[str, Any]):
        """Process a Telegram update"""
        message = update.get('message', {})
        if not message:
            return

        text = message.get('text', '')
        chat = message.get('chat', {})
        user = message.get('from', {})

        # Check if it's a command
        is_command = text.startswith('/')
        command = None
        command_args = None

        if is_command:
            parts = text.split(' ', 1)
            command = parts[0]
            command_args = parts[1] if len(parts) > 1 else None

        incoming = IncomingMessage(
            content=text,
            channel_type=ChannelType.TELEGRAM,
            channel_id=str(chat.get('id', '')),
            user_id=str(user.get('id', '')),
            user_name=user.get('username') or user.get('first_name'),
            is_command=is_command,
            command=command,
            command_args=command_args,
            metadata={
                'chat_type': chat.get('type'),
                'chat_title': chat.get('title'),
                'message_id': message.get('message_id')
            }
        )

        await self.handle_incoming(incoming)

    # Telegram-specific emoji overrides
    def get_emoji(self, emoji_type: str) -> str:
        """Get Telegram-appropriate emoji (supports all unicode)"""
        telegram_emojis = {
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
            'robot': '🤖',
            'sparkles': '✨',
            'brain': '🧠',
            'rocket': '🚀'
        }
        return telegram_emojis.get(emoji_type, super().get_emoji(emoji_type))
