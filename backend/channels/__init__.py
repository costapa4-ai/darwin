"""
Darwin Multi-Channel Gateway

Enables Darwin to communicate across multiple platforms:
- Telegram
- Discord
- Slack
- Web UI (existing)

Each channel has its own personality flavor while maintaining
Darwin's core consciousness.
"""

from .base_channel import BaseChannel, ChannelMessage, ChannelType
from .gateway import ChannelGateway

__all__ = ['BaseChannel', 'ChannelMessage', 'ChannelType', 'ChannelGateway']
