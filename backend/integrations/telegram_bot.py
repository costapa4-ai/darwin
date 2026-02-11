"""
Telegram Bot - Bidirectional communication between Darwin and Owner.

Sends notifications AND receives messages from the owner's Telegram chat.
Incoming messages are routed to Darwin's consciousness chat (Claude-powered).
Works independently of the full Channel Gateway.

Setup:
1. Talk to @BotFather on Telegram and create a bot
2. Set TELEGRAM_BOT_TOKEN in docker-compose.yml
3. Send /start to your bot, then set TELEGRAM_OWNER_CHAT_ID
"""

import asyncio
import os
import aiohttp
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Configuration from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
OWNER_CHAT_ID = os.getenv('TELEGRAM_OWNER_CHAT_ID', '')

# Polling state
_last_update_id = 0
_polling_task: Optional[asyncio.Task] = None


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


async def send_reply(chat_id: str, text: str, parse_mode: str = 'HTML') -> bool:
    """Send a reply message to a specific Telegram chat."""
    if not BOT_TOKEN:
        return False

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'chat_id': chat_id,
                'text': text[:4096],
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }
            async with session.post(api_url, json=payload) as resp:
                if resp.status == 200:
                    return True
                else:
                    error = await resp.text()
                    logger.warning(f"Telegram reply failed ({resp.status}): {error}")
                    return False
    except Exception as e:
        logger.warning(f"Telegram reply error: {e}")
        return False


# ==================== INCOMING MESSAGE POLLING ====================


async def start_polling():
    """Start background polling for incoming Telegram messages."""
    global _polling_task
    if not BOT_TOKEN or not OWNER_CHAT_ID:
        logger.info("Telegram polling not started (missing BOT_TOKEN or OWNER_CHAT_ID)")
        return
    _polling_task = asyncio.create_task(_poll_loop())
    logger.info("Telegram chat polling started - Darwin can now reply to messages")


async def stop_polling():
    """Stop the polling task."""
    global _polling_task
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
        _polling_task = None
        logger.info("Telegram chat polling stopped")


async def _poll_loop():
    """Long-poll Telegram for incoming messages from the owner."""
    global _last_update_id
    api_base = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # Flush old updates on startup so we don't reply to stale messages
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{api_base}/getUpdates",
                params={'offset': -1, 'timeout': 0}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get('result', [])
                    if results:
                        _last_update_id = results[-1]['update_id']
                        logger.info(f"Telegram: flushed {len(results)} old update(s)")
    except Exception as e:
        logger.warning(f"Telegram flush error: {e}")

    # Main polling loop
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'offset': _last_update_id + 1,
                    'timeout': 30,
                    'allowed_updates': '["message"]',
                }
                async with session.get(
                    f"{api_base}/getUpdates",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=45)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('ok'):
                            for update in data.get('result', []):
                                _last_update_id = update['update_id']
                                await _handle_update(update)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Telegram poll error: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(1)


async def _handle_update(update: dict):
    """Process a Telegram update — route to consciousness chat."""
    message = update.get('message', {})
    if not message or not message.get('text'):
        return

    chat_id = str(message.get('chat', {}).get('id', ''))
    text = message['text'].strip()
    user_name = message.get('from', {}).get('first_name', 'User')

    # Security: only respond to owner
    if chat_id != OWNER_CHAT_ID:
        logger.debug(f"Telegram: ignoring message from non-owner chat {chat_id}")
        return

    logger.info(f"Telegram message from {user_name}: {text[:80]}")

    # Handle /start command
    if text == '/start':
        await send_reply(chat_id, "Olá! Sou o Darwin 🧬\nPodes falar comigo aqui — respondo com o mesmo cérebro do chat web!")
        return

    # Handle /status command
    if text == '/status':
        try:
            from app.lifespan import get_service
            engine = get_service('consciousness_engine')
            if engine:
                from datetime import datetime
                elapsed = (datetime.utcnow() - engine.cycle_start_time).total_seconds() / 60
                state = engine.state.value.upper()
                acts = engine.total_activities_completed
                disc = engine.total_discoveries_made
                await send_reply(
                    chat_id,
                    f"🧬 <b>Darwin Status</b>\n\n"
                    f"Estado: {state} ({elapsed:.0f}min no ciclo)\n"
                    f"Atividades: {acts}\n"
                    f"Descobertas: {disc}"
                )
                return
        except Exception:
            pass
        await send_reply(chat_id, "Estou a correr mas não consigo obter o estado detalhado agora.")
        return

    # Route to consciousness chat for intelligent response
    try:
        from api.consciousness_routes import send_chat_message, ChatMessage
        result = await send_chat_message(ChatMessage(message=text, channel='telegram'))
        reply_text = result.get('content', str(result)) if isinstance(result, dict) else str(result)
    except Exception as e:
        logger.error(f"Telegram chat error: {e}")
        reply_text = f"Desculpa, tive um erro a processar a tua mensagem. Tenta outra vez! 🔧"

    await send_reply(chat_id, reply_text)
