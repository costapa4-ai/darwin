"""WebSocket manager for real-time updates"""
import asyncio
from datetime import datetime
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Heartbeat configuration
HEARTBEAT_INTERVAL_SECONDS = 30  # Send ping every 30 seconds
HEARTBEAT_TIMEOUT_SECONDS = 90   # Consider connection stale after 90 seconds


class ConnectionManager:
    """Manages WebSocket connections with heartbeat support"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        self.channel_subscribers: Dict[str, Set[WebSocket]] = {
            "findings": set(),  # Subscribers to findings updates
            "consciousness": set(),  # Subscribers to consciousness updates
        }
        # Heartbeat tracking
        self.last_pong: Dict[WebSocket, datetime] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.last_pong[websocket] = datetime.now()
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        self.last_pong.pop(websocket, None)

        # Remove from task subscriptions
        for subscribers in self.task_subscribers.values():
            subscribers.discard(websocket)

        # Remove from channel subscriptions
        for subscribers in self.channel_subscribers.values():
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

    def handle_pong(self, websocket: WebSocket):
        """Record pong response from client"""
        self.last_pong[websocket] = datetime.now()

    async def start_heartbeat(self):
        """Start the heartbeat background task"""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket heartbeat started")

    async def stop_heartbeat(self):
        """Stop the heartbeat background task"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            logger.info("WebSocket heartbeat stopped")

    async def _heartbeat_loop(self):
        """Background loop that sends pings and removes stale connections"""
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

                now = datetime.now()
                stale_connections = set()

                # Check for stale connections and send pings
                for websocket in list(self.active_connections):
                    last_activity = self.last_pong.get(websocket)

                    if last_activity:
                        seconds_since_pong = (now - last_activity).total_seconds()
                        if seconds_since_pong > HEARTBEAT_TIMEOUT_SECONDS:
                            stale_connections.add(websocket)
                            logger.warning(f"WebSocket stale (no pong for {seconds_since_pong:.0f}s)")
                            continue

                    # Send ping to active connections
                    try:
                        await websocket.send_json({"type": "ping"})
                    except Exception as e:
                        logger.debug(f"Failed to send ping: {e}")
                        stale_connections.add(websocket)

                # Clean up stale connections
                for websocket in stale_connections:
                    self.disconnect(websocket)
                    try:
                        await websocket.close()
                    except Exception:
                        pass

                if stale_connections:
                    logger.info(f"Removed {len(stale_connections)} stale WebSocket connection(s)")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


manager = ConnectionManager()


async def notify_new_finding(finding: Dict[str, Any]):
    """Helper function to notify about new findings"""
    await manager.notify_new_finding(finding)
