"""WebSocket manager for real-time updates"""
import asyncio
from typing import Set, Dict, Any
from fastapi import WebSocket
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {
            "findings": set(),  # Subscribers to findings updates
            "consciousness": set(),  # Subscribers to consciousness updates
        }

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)

        # Remove from task subscriptions
        for subscribers in self.task_subscribers.values():
            subscribers.discard(websocket)

        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        dead_connections = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)

    async def send_to_task_subscribers(self, task_id: str, message: dict):
        """Send message to clients subscribed to a specific task"""
        if task_id not in self.task_subscribers:
            return

        dead_connections = set()

        for connection in self.task_subscribers[task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to task subscriber: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.task_subscribers[task_id].discard(conn)

    def subscribe_to_task(self, websocket: WebSocket, task_id: str):
        """Subscribe a client to task updates"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()

        self.task_subscribers[task_id].add(websocket)
        logger.info(f"Client subscribed to task {task_id}")

    def subscribe_to_channel(self, websocket: WebSocket, channel: str):
        """Subscribe a client to a channel (findings, consciousness, etc.)"""
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(websocket)
        logger.info(f"Client subscribed to channel: {channel}")

    def unsubscribe_from_channel(self, websocket: WebSocket, channel: str):
        """Unsubscribe a client from a channel"""
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(websocket)

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel"""
        if channel not in self.channel_subscribers:
            return

        dead_connections = set()

        for connection in self.channel_subscribers[channel]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to channel {channel}: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.channel_subscribers[channel].discard(conn)

    async def notify_new_finding(self, finding: Dict[str, Any]):
        """Notify all subscribers of a new finding"""
        await self.broadcast_to_channel("findings", {
            "type": "new_finding",
            "finding": finding
        })
        # Also broadcast to all connections for general awareness
        await self.broadcast({
            "type": "finding_added",
            "finding_id": finding.get("id"),
            "title": finding.get("title"),
            "finding_type": finding.get("type"),
            "priority": finding.get("priority")
        })

    async def notify_finding_update(self, finding_id: str, action: str):
        """Notify subscribers of finding updates (read, dismissed)"""
        await self.broadcast_to_channel("findings", {
            "type": "finding_update",
            "finding_id": finding_id,
            "action": action
        })


manager = ConnectionManager()


async def notify_new_finding(finding: Dict[str, Any]):
    """Helper function to notify about new findings"""
    await manager.notify_new_finding(finding)
