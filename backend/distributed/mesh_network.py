"""
Mesh Network - P2P communication layer for Darwin instances

Provides:
- Direct peer-to-peer connections
- Message routing between instances
- Gossip protocol for discovery
- Failover and redundancy
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Set
from pathlib import Path
import uuid

from utils.logger import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """Types of mesh messages"""
    PING = "ping"
    PONG = "pong"
    DISCOVERY = "discovery"
    ANNOUNCEMENT = "announcement"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    RELAY = "relay"


class ConnectionState(Enum):
    """State of a peer connection"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


@dataclass
class MeshMessage:
    """A message in the mesh network"""
    id: str
    message_type: MessageType
    source_id: str
    target_id: Optional[str]  # None for broadcasts
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 5  # Time-to-live for relayed messages
    hop_count: int = 0
    path: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'message_type': self.message_type.value,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'ttl': self.ttl,
            'hop_count': self.hop_count,
            'path': self.path
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MeshMessage':
        return cls(
            id=data['id'],
            message_type=MessageType(data['message_type']),
            source_id=data['source_id'],
            target_id=data.get('target_id'),
            payload=data.get('payload', {}),
            timestamp=datetime.fromisoformat(data['timestamp']),
            ttl=data.get('ttl', 5),
            hop_count=data.get('hop_count', 0),
            path=data.get('path', [])
        )


@dataclass
class PeerConnection:
    """A connection to a peer instance"""
    peer_id: str
    peer_name: str
    address: str
    state: ConnectionState = ConnectionState.DISCONNECTED
    connected_at: Optional[datetime] = None
    last_activity: datetime = field(default_factory=datetime.utcnow)
    latency_ms: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'peer_id': self.peer_id,
            'peer_name': self.peer_name,
            'address': self.address,
            'state': self.state.value,
            'connected_at': self.connected_at.isoformat() if self.connected_at else None,
            'last_activity': self.last_activity.isoformat(),
            'latency_ms': self.latency_ms,
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'errors': self.errors
        }


class MeshNetwork:
    """
    Peer-to-peer mesh network for Darwin instances.

    Features:
    - Direct connections to known peers
    - Message routing through mesh
    - Gossip-based peer discovery
    - Automatic failover
    """

    def __init__(
        self,
        instance_id: str,
        instance_name: str,
        host: str = "0.0.0.0",
        port: int = 8001,
        data_path: str = "./data/distributed/mesh"
    ):
        """
        Initialize the mesh network.

        Args:
            instance_id: This instance's ID
            instance_name: This instance's name
            host: Host to listen on
            port: Port for mesh communication
            data_path: Path for persistent storage
        """
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.host = host
        self.port = port
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Peer connections
        self._peers: Dict[str, PeerConnection] = {}

        # Message handlers
        self._handlers: Dict[MessageType, List[Callable[[MeshMessage], Awaitable[None]]]] = {
            mt: [] for mt in MessageType
        }

        # Seen messages (to prevent loops)
        self._seen_messages: Set[str] = set()
        self._max_seen = 10000

        # Network state
        self._running = False
        self._server = None
        self._maintenance_task: Optional[asyncio.Task] = None

        # Statistics
        self._stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'messages_relayed': 0,
            'broadcasts_sent': 0,
            'connection_attempts': 0,
            'connection_failures': 0
        }

        logger.info(f"MeshNetwork initialized: {instance_name} ({instance_id})")

    async def start(self):
        """Start the mesh network"""
        if self._running:
            return

        self._running = True

        # Start maintenance task
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())

        logger.info(f"MeshNetwork started on {self.host}:{self.port}")

    async def stop(self):
        """Stop the mesh network"""
        self._running = False

        if self._maintenance_task:
            self._maintenance_task.cancel()
            try:
                await self._maintenance_task
            except asyncio.CancelledError:
                pass

        # Disconnect all peers
        for peer_id in list(self._peers.keys()):
            await self.disconnect_peer(peer_id)

        logger.info("MeshNetwork stopped")

    async def connect_peer(self, peer_id: str, peer_name: str, address: str) -> bool:
        """
        Connect to a peer.

        Args:
            peer_id: Peer's instance ID
            peer_name: Peer's name
            address: Peer's address (host:port)

        Returns:
            True if connected successfully
        """
        if peer_id in self._peers and self._peers[peer_id].state == ConnectionState.CONNECTED:
            return True

        self._stats['connection_attempts'] += 1

        connection = PeerConnection(
            peer_id=peer_id,
            peer_name=peer_name,
            address=address,
            state=ConnectionState.CONNECTING
        )
        self._peers[peer_id] = connection

        try:
            # Test connection with ping
            ping_start = datetime.utcnow()
            response = await self._send_ping(address)

            if response:
                latency = (datetime.utcnow() - ping_start).total_seconds() * 1000
                connection.state = ConnectionState.CONNECTED
                connection.connected_at = datetime.utcnow()
                connection.latency_ms = latency

                logger.info(f"Connected to peer: {peer_name} ({address}) - {latency:.1f}ms")

                # Announce ourselves
                await self._announce_to_peer(peer_id)

                return True
            else:
                connection.state = ConnectionState.FAILED
                self._stats['connection_failures'] += 1
                return False

        except Exception as e:
            logger.error(f"Failed to connect to {peer_name}: {e}")
            connection.state = ConnectionState.FAILED
            connection.errors += 1
            self._stats['connection_failures'] += 1
            return False

    async def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer"""
        if peer_id in self._peers:
            peer = self._peers[peer_id]
            peer.state = ConnectionState.DISCONNECTED
            logger.info(f"Disconnected from peer: {peer.peer_name}")

    async def _send_ping(self, address: str) -> bool:
        """Send a ping to test connectivity"""
        try:
            import aiohttp

            url = f"http://{address}/api/v1/distributed/mesh/ping"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.post(url, json={'source_id': self.instance_id}) as response:
                    return response.status == 200

        except Exception as e:
            logger.debug(f"Ping failed to {address}: {e}")
            return False

    async def _announce_to_peer(self, peer_id: str):
        """Announce our presence and known peers to a peer"""
        peer = self._peers.get(peer_id)
        if not peer or peer.state != ConnectionState.CONNECTED:
            return

        # Share our known peers
        known_peers = [
            {
                'id': p.peer_id,
                'name': p.peer_name,
                'address': p.address
            }
            for p in self._peers.values()
            if p.state == ConnectionState.CONNECTED and p.peer_id != peer_id
        ]

        message = MeshMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.ANNOUNCEMENT,
            source_id=self.instance_id,
            target_id=peer_id,
            payload={
                'instance_name': self.instance_name,
                'known_peers': known_peers
            }
        )

        await self.send_message(message)

    async def send_message(self, message: MeshMessage) -> bool:
        """
        Send a message to a peer or broadcast.

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        if message.id in self._seen_messages:
            return False

        self._seen_messages.add(message.id)
        self._trim_seen_messages()

        # Add ourselves to path
        message.path.append(self.instance_id)
        message.hop_count += 1

        if message.target_id:
            # Direct message
            return await self._send_direct(message)
        else:
            # Broadcast
            return await self._broadcast(message)

    async def _send_direct(self, message: MeshMessage) -> bool:
        """Send a direct message to a specific peer"""
        target_id = message.target_id

        # Check if we have a direct connection
        if target_id in self._peers:
            peer = self._peers[target_id]
            if peer.state == ConnectionState.CONNECTED:
                success = await self._transmit(peer.address, message)
                if success:
                    peer.messages_sent += 1
                    self._stats['messages_sent'] += 1
                return success

        # Try to relay through other peers
        if message.ttl > 0 and message.hop_count < message.ttl:
            for peer_id, peer in self._peers.items():
                if peer.state == ConnectionState.CONNECTED and peer_id not in message.path:
                    relay_message = MeshMessage(
                        id=message.id,
                        message_type=MessageType.RELAY,
                        source_id=self.instance_id,
                        target_id=peer_id,
                        payload={
                            'original_message': message.to_dict()
                        },
                        ttl=message.ttl - 1,
                        hop_count=message.hop_count,
                        path=message.path.copy()
                    )
                    success = await self._transmit(peer.address, relay_message)
                    if success:
                        self._stats['messages_relayed'] += 1
                        return True

        return False

    async def _broadcast(self, message: MeshMessage) -> bool:
        """Broadcast a message to all connected peers"""
        success = False

        for peer_id, peer in self._peers.items():
            if peer.state == ConnectionState.CONNECTED and peer_id not in message.path:
                if await self._transmit(peer.address, message):
                    peer.messages_sent += 1
                    success = True

        if success:
            self._stats['broadcasts_sent'] += 1
            self._stats['messages_sent'] += 1

        return success

    async def _transmit(self, address: str, message: MeshMessage) -> bool:
        """Transmit a message to an address"""
        try:
            import aiohttp

            url = f"http://{address}/api/v1/distributed/mesh/receive"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(url, json=message.to_dict()) as response:
                    return response.status == 200

        except Exception as e:
            logger.debug(f"Transmit failed to {address}: {e}")
            return False

    async def receive_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a received message.

        Args:
            message_data: Raw message data

        Returns:
            Response dict
        """
        try:
            message = MeshMessage.from_dict(message_data)

            # Check if already seen
            if message.id in self._seen_messages:
                return {'status': 'duplicate', 'message_id': message.id}

            self._seen_messages.add(message.id)
            self._trim_seen_messages()
            self._stats['messages_received'] += 1

            # Update peer activity
            if message.source_id in self._peers:
                self._peers[message.source_id].last_activity = datetime.utcnow()
                self._peers[message.source_id].messages_received += 1

            # Handle relay messages
            if message.message_type == MessageType.RELAY:
                return await self._handle_relay(message)

            # Check if message is for us
            if message.target_id and message.target_id != self.instance_id:
                # Forward to target
                if message.ttl > 0:
                    await self.send_message(message)
                return {'status': 'forwarded', 'message_id': message.id}

            # Dispatch to handlers
            for handler in self._handlers.get(message.message_type, []):
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Handler error for {message.message_type}: {e}")

            return {'status': 'received', 'message_id': message.id}

        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return {'status': 'error', 'error': str(e)}

    async def _handle_relay(self, message: MeshMessage) -> Dict[str, Any]:
        """Handle a relay message"""
        original_data = message.payload.get('original_message')
        if not original_data:
            return {'status': 'error', 'error': 'No original message'}

        original = MeshMessage.from_dict(original_data)

        # Check if the original is for us
        if original.target_id == self.instance_id:
            return await self.receive_message(original_data)

        # Forward if TTL allows
        if original.ttl > 0:
            self._stats['messages_relayed'] += 1
            await self.send_message(original)

        return {'status': 'relayed', 'message_id': original.id}

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable[[MeshMessage], Awaitable[None]]
    ):
        """Register a message handler"""
        self._handlers[message_type].append(handler)

    def _trim_seen_messages(self):
        """Trim seen messages set to prevent memory growth"""
        if len(self._seen_messages) > self._max_seen:
            # Remove oldest half
            to_remove = len(self._seen_messages) - (self._max_seen // 2)
            for _ in range(to_remove):
                self._seen_messages.pop()

    async def _maintenance_loop(self):
        """Periodic maintenance tasks"""
        while self._running:
            try:
                # Ping connected peers to check health
                for peer_id, peer in list(self._peers.items()):
                    if peer.state == ConnectionState.CONNECTED:
                        # Check last activity
                        inactive_seconds = (datetime.utcnow() - peer.last_activity).total_seconds()
                        if inactive_seconds > 30:
                            # Send ping
                            success = await self._send_ping(peer.address)
                            if not success:
                                peer.state = ConnectionState.DISCONNECTED
                                logger.warning(f"Lost connection to peer: {peer.peer_name}")

                await asyncio.sleep(15)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance error: {e}")
                await asyncio.sleep(5)

    def get_connected_peers(self) -> List[PeerConnection]:
        """Get list of connected peers"""
        return [p for p in self._peers.values() if p.state == ConnectionState.CONNECTED]

    def get_peer(self, peer_id: str) -> Optional[PeerConnection]:
        """Get a specific peer"""
        return self._peers.get(peer_id)

    def get_status(self) -> Dict[str, Any]:
        """Get mesh network status"""
        return {
            'instance_id': self.instance_id,
            'instance_name': self.instance_name,
            'running': self._running,
            'host': self.host,
            'port': self.port,
            'total_peers': len(self._peers),
            'connected_peers': len(self.get_connected_peers()),
            'peers': [p.to_dict() for p in self._peers.values()],
            'statistics': self._stats,
            'seen_messages': len(self._seen_messages)
        }

    async def broadcast_consciousness_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Broadcast a consciousness event to all peers"""
        message = MeshMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.BROADCAST,
            source_id=self.instance_id,
            target_id=None,
            payload={
                'event_type': event_type,
                'data': data,
                'source_name': self.instance_name
            }
        )

        await self.send_message(message)

    async def request_sync(self, peer_id: str, memory_types: List[str] = None):
        """Request a sync from a specific peer"""
        message = MeshMessage(
            id=str(uuid.uuid4()),
            message_type=MessageType.SYNC_REQUEST,
            source_id=self.instance_id,
            target_id=peer_id,
            payload={
                'memory_types': memory_types or ['all']
            }
        )

        await self.send_message(message)
