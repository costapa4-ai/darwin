"""
Channel Gateway Initialization

Sets up the multi-channel communication gateway and registers channels.
Configuration is loaded from environment variables and config files.
"""

import os
from typing import Dict, Any, Optional

from utils.logger import setup_logger

logger = setup_logger(__name__)


async def init_channel_gateway(settings) -> Optional[Any]:
    """
    Initialize the Channel Gateway and register channels.

    Channels are configured via environment variables:
    - TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS
    - DISCORD_BOT_TOKEN, DISCORD_WEBHOOK_URLS
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_IDS

    Args:
        settings: Application settings

    Returns:
        ChannelGateway instance or None
    """
    # Check if channels are enabled
    enable_channels = getattr(settings, 'enable_channels', False) or os.getenv('ENABLE_CHANNELS', 'false').lower() == 'true'

    if not enable_channels:
        logger.info("Channel gateway disabled (set ENABLE_CHANNELS=true to enable)")
        return None

    try:
        from channels.gateway import ChannelGateway
        from channels.telegram_channel import TelegramChannel
        from channels.discord_channel import DiscordChannel

        gateway = ChannelGateway(config_path="./data/channels/config.json")

        # Initialize Telegram if configured
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_chats = os.getenv('TELEGRAM_CHAT_IDS', '')

        if telegram_token:
            chat_ids = [c.strip() for c in telegram_chats.split(',') if c.strip()]
            telegram_config = {
                'bot_token': telegram_token,
                'chat_ids': chat_ids,
                'enabled': True,
                'personality_flavor': 'casual'
            }
            telegram = TelegramChannel(telegram_config)
            gateway.register_channel(telegram)
            logger.info(f"Telegram channel registered ({len(chat_ids)} chat targets)")
        else:
            logger.info("Telegram not configured (TELEGRAM_BOT_TOKEN not set)")

        # Initialize Discord if configured
        discord_token = os.getenv('DISCORD_BOT_TOKEN', '')
        discord_webhooks = os.getenv('DISCORD_WEBHOOK_URLS', '')
        discord_channels = os.getenv('DISCORD_CHANNEL_IDS', '')

        if discord_token or discord_webhooks:
            webhook_urls = [w.strip() for w in discord_webhooks.split(',') if w.strip()]
            channel_ids = [c.strip() for c in discord_channels.split(',') if c.strip()]

            discord_config = {
                'bot_token': discord_token,
                'webhook_urls': webhook_urls,
                'channel_ids': channel_ids,
                'enabled': True,
                'personality_flavor': 'hacker'
            }
            discord = DiscordChannel(discord_config)
            gateway.register_channel(discord)
            logger.info(f"Discord channel registered ({len(webhook_urls)} webhooks, {len(channel_ids)} channels)")
        else:
            logger.info("Discord not configured (DISCORD_BOT_TOKEN/DISCORD_WEBHOOK_URLS not set)")

        # Start the gateway
        await gateway.start()
        logger.info("Channel gateway started")

        return gateway

    except Exception as e:
        logger.error(f"Failed to initialize channel gateway: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def get_channel_env_template() -> str:
    """
    Get a template for channel environment variables.

    Returns:
        Template string for .env file
    """
    return """
# Channel Gateway Configuration
# Set ENABLE_CHANNELS=true to enable multi-channel communication

ENABLE_CHANNELS=false

# Telegram Configuration
# Get your bot token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=
# Comma-separated list of chat IDs to broadcast to
TELEGRAM_CHAT_IDS=

# Discord Configuration
# Create a bot at https://discord.com/developers/applications
DISCORD_BOT_TOKEN=
# Comma-separated webhook URLs for broadcasting
DISCORD_WEBHOOK_URLS=
# Comma-separated channel IDs (for bot mode)
DISCORD_CHANNEL_IDS=

# Slack Configuration (future)
SLACK_BOT_TOKEN=
SLACK_CHANNEL_IDS=
"""
