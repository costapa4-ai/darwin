"""
Telegram Bot - Simple notification helper for Darwin → Owner communication.

Sends direct messages to the owner's Telegram chat.
Works independently of the full Channel Gateway for critical notifications.

Setup:
1. Talk to @BotFather on Telegram and create a bot
2. Set TELEGRAM_BOT_TOKEN in docker-compose.yml
3. Send /start to your bot, then set TELEGRAM_OWNER_CHAT_ID
"""

import os
import aiohttp
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Configuration from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
OWNER_CHAT_ID = os.getenv('TELEGRAM_OWNER_CHAT_ID', '')


async def notify_owner(message: str, parse_mode: str = 'HTML') -> bool:
    """
    Send a notification to the owner's Telegram chat.

    Args:
        message: Text to send (supports HTML formatting)
        parse_mode: Telegram parse mode (HTML or Markdown)

    Returns:
        True if sent successfully
    """
    if not BOT_TOKEN or not OWNER_CHAT_ID:
        logger.debug("Telegram not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_OWNER_CHAT_ID missing)")
        return False

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'chat_id': OWNER_CHAT_ID,
                'text': message[:4096],  # Telegram message limit
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }
            async with session.post(api_url, json=payload) as resp:
                if resp.status == 200:
                    logger.info("Telegram notification sent to owner")
                    return True
                else:
                    error = await resp.text()
                    logger.warning(f"Telegram send failed ({resp.status}): {error}")
                    return False
    except Exception as e:
        logger.warning(f"Telegram notification error: {e}")
        return False


async def get_bot_info() -> Optional[dict]:
    """Get bot information to verify token is valid."""
    if not BOT_TOKEN:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('result', {})
    except Exception:
        pass
    return None
