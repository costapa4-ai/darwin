"""
Instance Registry - Discovery and registration for Darwin instances

Manages the distributed network of Darwin instances:
- Instance registration and discovery
- Health monitoring via heartbeats
- Capability advertisement
- Network topology tracking
"""

import asyncio
import hashlib
import socket
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
import uuid

from utils.logger import get_logger

logger = get_logger(__name__)


class InstanceStatus(Enum):
    """Status of a Darwin instance"""
    ONLINE = "online"
    OFFLINE = "offline"
    SLEEPING = "sleeping"
    DREAMING = "dreaming"
    SYNCING = "syncing"
    UNKNOWN = "unknown"


class InstanceRole(Enum):
    """Role of an instance in the mesh"""
    PRIMARY = "primary"      # Main instance, authoritative for conflicts
    REPLICA = "replica"      # Read-heavy, syncs from primary
    PEER = "peer"            # Equal peer in mesh
    OBSERVER = "observer"    # Read-only, no write capabilities


@dataclass
class InstanceCapabilities:
    """Capabilities advertised by an instance"""
    can_dream: bool = True
    can_learn: bool = True
    can_execute_code: bool = False
    can_browse_web: bool = True
    has_voice: bool = False
    has_ui_automation: bool = False
    max_memory_mb: int = 1024
    supported_models: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'can_dream': self.can_dream,
            'can_learn': self.can_learn,
            'can_execute_code': self.can_execute_code,
            'can_browse_web': self.can_browse_web,
            'has_voice': self.has_voice,
            'has_ui_automation': self.has_ui_automation,
            'max_memory_mb': self.max_memory_mb,
            'supported_models': self.supported_models
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstanceCapabilities':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DarwinInstance:
    """Represents a Darwin instance in the network"""
    instance_id: str
    name: str
    host: str
    port: int
    role: InstanceRole = InstanceRole.PEER
    status: InstanceStatus = InstanceStatus.UNKNOWN
    capabilities: InstanceCapabilities = field(default_factory=InstanceCapabilities)
    version: str = "3.0.0"
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Consciousness state summary
    memory_count: int = 0
    learning_sessions: int = 0
    dreams_count: int = 0
    current_mood: str = "neutral"

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def is_alive(self) -> bool:
        """Check if instance is considered alive (heartbeat within 60s)"""
        return (datetime.utcnow() - self.last_heartbeat).total_seconds() < 60

    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'instance_id': self.instance_id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'role': self.role.value,
            'status': self.status.value,
            'capabilities': self.capabilities.to_dict(),
            'version': self.version,
            'registered_at': self.registered_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'is_alive': self.is_alive,
            'address': self.address,
            'memory_count': self.memory_count,
            'learning_sessions': self.learning_sessions,
            'dreams_count': self.dreams_count,
            'current_mood': self.current_mood,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DarwinInstance':
        data = data.copy()
        data['role'] = InstanceRole(data.get('role', 'peer'))
        data['status'] = InstanceStatus(data.get('status', 'unknown'))
        data['capabilities'] = InstanceCapabilities.from_dict(data.get('capabilities', {}))
        data['registered_at'] = datetime.fromisoformat(data['registered_at']) if isinstance(data.get('registered_at'), str) else data.get('registered_at', datetime.utcnow())
        data['last_heartbeat'] = datetime.fromisoformat(data['last_heartbeat']) if isinstance(data.get('last_heartbeat'), str) else data.get('last_heartbeat', datetime.utcnow())
        # Remove computed properties
        data.pop('is_alive', None)
        data.pop('address', None)
        data.pop('api_url', None)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class InstanceRegistry:
    """
    Central registry for Darwin instance discovery and management.

    Features:
    - Local instance registration
    - Remote instance discovery
    - Heartbeat monitoring
    - Capability matching
    - Network topology awareness
    """

    def __init__(
        self,
        instance_name: str = None,
        host: str = "0.0.0.0",
        port: int = 8000,
        data_path: str = "./data/distributed"
    ):
        """
        Initialize the instance registry.

        Args:
            instance_name: Name for this instance
            host: Host address for this instance
            port: Port for this instance
            data_path: Path for persistent storage
        """
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Generate or load instance ID
        self.instance_id = self._get_or_create_instance_id()
        self.instance_name = instance_name or f"darwin-{self.instance_id[:8]}"
        self.host = host
        self.port = port

        # Registry of known instances
        self._instances: Dict[str, DarwinInstance] = {}
        self._local_instance: Optional[DarwinInstance] = None

        # Discovery state
        self._discovery_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # Callbacks for events
        self._on_instance_joined: List[callable] = []
        self._on_instance_left: List[callable] = []
        self._on_instance_updated: List[callable] = []

        # Known seed nodes for discovery
        self._seed_nodes: Set[str] = set()

        logger.info(f"InstanceRegistry initialized: {self.instance_name} ({self.instance_id})")

    def _get_or_create_instance_id(self) -> str:
        """Get existing instance ID or create a new one"""
        id_file = self.data_path / "instance_id"

        if id_file.exists():
            return id_file.read_text().strip()

        # Generate new ID based on machine characteristics
        machine_id = f"{socket.gethostname()}-{uuid.getnode()}"
        instance_id = hashlib.sha256(machine_id.encode()).hexdigest()[:16]

        id_file.write_text(instance_id)
        return instance_id

    def create_local_instance(self, capabilities: InstanceCapabilities = None) -> DarwinInstance:
        """Create and register the local instance"""
        self._local_instance = DarwinInstance(
            instance_id=self.instance_id,
            name=self.instance_name,
            host=self._get_local_ip(),
            port=self.port,
            role=InstanceRole.PEER,
            status=InstanceStatus.ONLINE,
            capabilities=capabilities or InstanceCapabilities()
        )

        self._instances[self.instance_id] = self._local_instance
        self._save_registry()

        return self._local_instance

    def _get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Connect to external address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def start(self):
        """Start the registry services"""
        if self._running:
            return

        self._running = True

        # Load persisted registry
        self._load_registry()

        # Create local instance if not exists
        if not self._local_instance:
            self.create_local_instance()

        # Start background tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._discovery_task = asyncio.create_task(self._discovery_loop())

        logger.info("InstanceRegistry started")

    async def stop(self):
        """Stop the registry services"""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass

        # Mark local instance as offline
        if self._local_instance:
            self._local_instance.status = InstanceStatus.OFFLINE
            self._save_registry()

        logger.info("InstanceRegistry stopped")

    def register_instance(self, instance: DarwinInstance) -> bool:
        """
        Register a remote instance.

        Args:
            instance: Instance to register

        Returns:
            True if newly registered, False if updated
        """
        is_new = instance.instance_id not in self._instances

        instance.last_heartbeat = datetime.utcnow()
        self._instances[instance.instance_id] = instance
        self._save_registry()

        if is_new:
            logger.info(f"New instance registered: {instance.name} ({instance.address})")
            for callback in self._on_instance_joined:
                try:
                    callback(instance)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        else:
            for callback in self._on_instance_updated:
                try:
                    callback(instance)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

        return is_new

    def unregister_instance(self, instance_id: str) -> bool:
        """
        Unregister an instance.

        Args:
            instance_id: ID of instance to remove

        Returns:
            True if removed, False if not found
        """
        if instance_id in self._instances:
            instance = self._instances.pop(instance_id)
            self._save_registry()

            logger.info(f"Instance unregistered: {instance.name}")
            for callback in self._on_instance_left:
                try:
                    callback(instance)
                except Exception as e:
                    logger.error(f"Callback error: {e}")

            return True
        return False

    def get_instance(self, instance_id: str) -> Optional[DarwinInstance]:
        """Get an instance by ID"""
        return self._instances.get(instance_id)

    def get_all_instances(self, include_offline: bool = False) -> List[DarwinInstance]:
        """Get all registered instances"""
        instances = list(self._instances.values())
        if not include_offline:
            instances = [i for i in instances if i.is_alive]
        return instances

    def get_instances_by_capability(self, capability: str) -> List[DarwinInstance]:
        """Get instances with a specific capability"""
        instances = []
        for instance in self.get_all_instances():
            caps = instance.capabilities
            if getattr(caps, capability, False):
                instances.append(instance)
        return instances

    def get_instances_by_role(self, role: InstanceRole) -> List[DarwinInstance]:
        """Get instances with a specific role"""
        return [i for i in self.get_all_instances() if i.role == role]

    def add_seed_node(self, address: str):
        """Add a seed node for discovery"""
        self._seed_nodes.add(address)
        logger.info(f"Added seed node: {address}")

    def update_local_status(self, status: InstanceStatus):
        """Update local instance status"""
        if self._local_instance:
            self._local_instance.status = status
            self._local_instance.last_heartbeat = datetime.utcnow()
            self._save_registry()

    def update_local_state(
        self,
        memory_count: int = None,
        learning_sessions: int = None,
        dreams_count: int = None,
        current_mood: str = None
    ):
        """Update local instance consciousness state"""
        if self._local_instance:
            if memory_count is not None:
                self._local_instance.memory_count = memory_count
            if learning_sessions is not None:
                self._local_instance.learning_sessions = learning_sessions
            if dreams_count is not None:
                self._local_instance.dreams_count = dreams_count
            if current_mood is not None:
                self._local_instance.current_mood = current_mood
            self._save_registry()

    async def _heartbeat_loop(self):
        """Send periodic heartbeats and check for dead instances"""
        while self._running:
            try:
                # Update local heartbeat
                if self._local_instance:
                    self._local_instance.last_heartbeat = datetime.utcnow()

                # Check for dead instances
                dead_instances = []
                for instance_id, instance in self._instances.items():
                    if instance_id != self.instance_id and not instance.is_alive:
                        dead_instances.append(instance_id)

                for instance_id in dead_instances:
                    instance = self._instances[instance_id]
                    instance.status = InstanceStatus.OFFLINE
                    logger.warning(f"Instance appears offline: {instance.name}")

                    for callback in self._on_instance_left:
                        try:
                            callback(instance)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                self._save_registry()
                await asyncio.sleep(15)  # Heartbeat every 15 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)

    async def _discovery_loop(self):
        """Periodically discover new instances"""
        while self._running:
            try:
                # Try to discover instances from seed nodes
                for seed in self._seed_nodes:
                    await self._discover_from_seed(seed)

                await asyncio.sleep(30)  # Discovery every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                await asyncio.sleep(10)

    async def _discover_from_seed(self, seed_address: str):
        """Try to discover instances from a seed node"""
        try:
            import aiohttp

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                url = f"http://{seed_address}/api/v1/distributed/instances"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        for instance_data in data.get('instances', []):
                            if instance_data['instance_id'] != self.instance_id:
                                instance = DarwinInstance.from_dict(instance_data)
                                self.register_instance(instance)

        except Exception as e:
            logger.debug(f"Could not reach seed {seed_address}: {e}")

    def _save_registry(self):
        """Persist registry to disk"""
        try:
            registry_file = self.data_path / "registry.json"
            data = {
                'local_instance_id': self.instance_id,
                'instances': {
                    iid: inst.to_dict()
                    for iid, inst in self._instances.items()
                },
                'seed_nodes': list(self._seed_nodes),
                'updated_at': datetime.utcnow().isoformat()
            }

            with open(registry_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    def _load_registry(self):
        """Load registry from disk"""
        try:
            registry_file = self.data_path / "registry.json"
            if registry_file.exists():
                with open(registry_file) as f:
                    data = json.load(f)

                for iid, inst_data in data.get('instances', {}).items():
                    if iid != self.instance_id:  # Don't load stale local instance
                        instance = DarwinInstance.from_dict(inst_data)
                        self._instances[iid] = instance

                self._seed_nodes = set(data.get('seed_nodes', []))

                logger.info(f"Loaded {len(self._instances)} instances from registry")

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")

    def on_instance_joined(self, callback: callable):
        """Register callback for when an instance joins"""
        self._on_instance_joined.append(callback)

    def on_instance_left(self, callback: callable):
        """Register callback for when an instance leaves"""
        self._on_instance_left.append(callback)

    def on_instance_updated(self, callback: callable):
        """Register callback for when an instance is updated"""
        self._on_instance_updated.append(callback)

    def get_status(self) -> Dict[str, Any]:
        """Get registry status"""
        return {
            'instance_id': self.instance_id,
            'instance_name': self.instance_name,
            'running': self._running,
            'local_instance': self._local_instance.to_dict() if self._local_instance else None,
            'total_instances': len(self._instances),
            'online_instances': len([i for i in self._instances.values() if i.is_alive]),
            'seed_nodes': list(self._seed_nodes)
        }


# Global instance
_instance_registry: Optional[InstanceRegistry] = None


def get_instance_registry() -> Optional[InstanceRegistry]:
    """Get the global instance registry"""
    return _instance_registry


def set_instance_registry(registry: InstanceRegistry):
    """Set the global instance registry"""
    global _instance_registry
    _instance_registry = registry
