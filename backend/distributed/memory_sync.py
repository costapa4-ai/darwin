"""
Memory Synchronization Protocol - Share memories between Darwin instances

Handles synchronization of:
- Semantic memories (learned knowledge)
- Episodic memories (experiences)
- Dreams and discoveries
- Learning progress

Supports conflict resolution and selective sync.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class SyncMode(Enum):
    """Memory synchronization modes"""
    PUSH = "push"           # Send local changes to remote
    PULL = "pull"           # Fetch remote changes
    BIDIRECTIONAL = "bidirectional"  # Full two-way sync
    SELECTIVE = "selective" # Only sync specific categories


class ConflictResolution(Enum):
    """How to resolve sync conflicts"""
    LOCAL_WINS = "local_wins"       # Keep local version
    REMOTE_WINS = "remote_wins"     # Keep remote version
    NEWER_WINS = "newer_wins"       # Keep most recent
    MERGE = "merge"                 # Attempt to merge
    MANUAL = "manual"               # Queue for manual resolution


class MemoryType(Enum):
    """Types of memories that can be synced"""
    SEMANTIC = "semantic"       # Learned knowledge
    EPISODIC = "episodic"       # Experiences
    DREAMS = "dreams"           # Dream records
    DISCOVERIES = "discoveries" # Curiosity findings
    LEARNINGS = "learnings"     # Meta-learning progress
    DIARY = "diary"             # Consciousness diary entries


@dataclass
class MemoryRecord:
    """A single memory record for synchronization"""
    id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    source_instance: str
    version: int = 1
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """Compute content checksum for change detection"""
        content_str = json.dumps(self.content, sort_keys=True)
        return hashlib.md5(content_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'memory_type': self.memory_type.value,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source_instance': self.source_instance,
            'version': self.version,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryRecord':
        return cls(
            id=data['id'],
            memory_type=MemoryType(data['memory_type']),
            content=data['content'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            source_instance=data['source_instance'],
            version=data.get('version', 1),
            checksum=data.get('checksum', '')
        )


@dataclass
class SyncConflict:
    """Represents a synchronization conflict"""
    memory_id: str
    memory_type: MemoryType
    local_version: MemoryRecord
    remote_version: MemoryRecord
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'memory_id': self.memory_id,
            'memory_type': self.memory_type.value,
            'local_version': self.local_version.to_dict(),
            'remote_version': self.remote_version.to_dict(),
            'detected_at': self.detected_at.isoformat(),
            'resolved': self.resolved,
            'resolution': self.resolution
        }


@dataclass
class SyncResult:
    """Result of a synchronization operation"""
    success: bool
    mode: SyncMode
    records_sent: int = 0
    records_received: int = 0
    conflicts: List[SyncConflict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'mode': self.mode.value,
            'records_sent': self.records_sent,
            'records_received': self.records_received,
            'conflicts_count': len(self.conflicts),
            'errors': self.errors,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration_seconds': self.duration_seconds
        }


class MemorySyncProtocol:
    """
    Protocol for synchronizing memories between Darwin instances.

    Features:
    - Incremental sync based on change detection
    - Conflict detection and resolution
    - Selective sync by memory type
    - Versioning for consistency
    """

    def __init__(
        self,
        instance_id: str,
        data_path: str = "./data/distributed/sync"
    ):
        """
        Initialize the sync protocol.

        Args:
            instance_id: ID of this instance
            data_path: Path for sync state storage
        """
        self.instance_id = instance_id
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Local memory index (id -> checksum)
        self._local_index: Dict[str, str] = {}

        # Pending conflicts
        self._conflicts: List[SyncConflict] = []

        # Sync history
        self._sync_history: List[SyncResult] = []

        # Sync state per peer
        self._peer_sync_state: Dict[str, Dict[str, Any]] = {}

        # Default conflict resolution
        self.default_resolution = ConflictResolution.NEWER_WINS

        # Memory type handlers
        self._memory_handlers: Dict[MemoryType, Dict[str, callable]] = {}

        logger.info(f"MemorySyncProtocol initialized for instance {instance_id}")

    def register_memory_handler(
        self,
        memory_type: MemoryType,
        get_all: callable,
        get_by_id: callable,
        save: callable,
        delete: callable = None
    ):
        """
        Register handlers for a memory type.

        Args:
            memory_type: Type of memory
            get_all: Function to get all memories of this type
            get_by_id: Function to get a specific memory
            save: Function to save a memory
            delete: Optional function to delete a memory
        """
        self._memory_handlers[memory_type] = {
            'get_all': get_all,
            'get_by_id': get_by_id,
            'save': save,
            'delete': delete
        }
        logger.info(f"Registered handler for {memory_type.value}")

    async def sync_with_peer(
        self,
        peer_address: str,
        mode: SyncMode = SyncMode.BIDIRECTIONAL,
        memory_types: List[MemoryType] = None,
        conflict_resolution: ConflictResolution = None
    ) -> SyncResult:
        """
        Synchronize memories with a peer instance.

        Args:
            peer_address: Address of peer (host:port)
            mode: Synchronization mode
            memory_types: Types to sync (None = all)
            conflict_resolution: How to resolve conflicts

        Returns:
            SyncResult with details of the operation
        """
        result = SyncResult(success=False, mode=mode)
        conflict_resolution = conflict_resolution or self.default_resolution
        memory_types = memory_types or list(MemoryType)

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Get peer's memory index
                peer_index = await self._get_peer_index(session, peer_address, memory_types)

                if mode in (SyncMode.PULL, SyncMode.BIDIRECTIONAL):
                    # Pull changes from peer
                    received = await self._pull_from_peer(
                        session, peer_address, peer_index, memory_types, conflict_resolution
                    )
                    result.records_received = received

                if mode in (SyncMode.PUSH, SyncMode.BIDIRECTIONAL):
                    # Push changes to peer
                    sent = await self._push_to_peer(
                        session, peer_address, peer_index, memory_types
                    )
                    result.records_sent = sent

                result.success = True
                result.conflicts = [c for c in self._conflicts if not c.resolved]

        except Exception as e:
            logger.error(f"Sync error with {peer_address}: {e}")
            result.errors.append(str(e))

        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

        # Update sync state
        self._peer_sync_state[peer_address] = {
            'last_sync': result.completed_at.isoformat(),
            'success': result.success,
            'records_synced': result.records_sent + result.records_received
        }

        self._sync_history.append(result)
        self._save_state()

        return result

    async def _get_peer_index(
        self,
        session,
        peer_address: str,
        memory_types: List[MemoryType]
    ) -> Dict[str, Dict[str, str]]:
        """Get memory index from peer"""
        url = f"http://{peer_address}/api/v1/distributed/sync/index"
        params = {'types': ','.join(t.value for t in memory_types)}

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('index', {})
            else:
                raise Exception(f"Failed to get peer index: {response.status}")

    async def _pull_from_peer(
        self,
        session,
        peer_address: str,
        peer_index: Dict[str, Dict[str, str]],
        memory_types: List[MemoryType],
        conflict_resolution: ConflictResolution
    ) -> int:
        """Pull changed memories from peer"""
        records_received = 0

        for memory_type in memory_types:
            type_key = memory_type.value
            peer_memories = peer_index.get(type_key, {})

            # Find memories we need
            needed_ids = []
            for mem_id, checksum in peer_memories.items():
                local_checksum = self._local_index.get(f"{type_key}:{mem_id}")
                if local_checksum != checksum:
                    needed_ids.append(mem_id)

            if not needed_ids:
                continue

            # Fetch needed memories
            url = f"http://{peer_address}/api/v1/distributed/sync/memories"
            payload = {'type': type_key, 'ids': needed_ids}

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    for record_data in data.get('memories', []):
                        record = MemoryRecord.from_dict(record_data)

                        # Check for conflict
                        local_checksum = self._local_index.get(f"{type_key}:{record.id}")
                        if local_checksum and local_checksum != record.checksum:
                            # We have a conflict
                            conflict = await self._handle_conflict(
                                memory_type, record, conflict_resolution
                            )
                            if conflict:
                                self._conflicts.append(conflict)
                                continue

                        # Save the memory
                        await self._save_memory(memory_type, record)
                        records_received += 1

        return records_received

    async def _push_to_peer(
        self,
        session,
        peer_address: str,
        peer_index: Dict[str, Dict[str, str]],
        memory_types: List[MemoryType]
    ) -> int:
        """Push local memories to peer"""
        records_sent = 0

        for memory_type in memory_types:
            if memory_type not in self._memory_handlers:
                continue

            type_key = memory_type.value
            peer_memories = peer_index.get(type_key, {})
            handler = self._memory_handlers[memory_type]

            # Get local memories
            local_memories = await handler['get_all']()

            # Find memories peer doesn't have or are outdated
            to_push = []
            for memory in local_memories:
                record = self._to_memory_record(memory, memory_type)
                peer_checksum = peer_memories.get(record.id)
                if peer_checksum != record.checksum:
                    to_push.append(record)

            if not to_push:
                continue

            # Push to peer
            url = f"http://{peer_address}/api/v1/distributed/sync/receive"
            payload = {
                'source_instance': self.instance_id,
                'memories': [r.to_dict() for r in to_push]
            }

            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    records_sent += data.get('accepted', 0)

        return records_sent

    async def _handle_conflict(
        self,
        memory_type: MemoryType,
        remote_record: MemoryRecord,
        resolution: ConflictResolution
    ) -> Optional[SyncConflict]:
        """Handle a sync conflict"""
        # Get local version
        handler = self._memory_handlers.get(memory_type)
        if not handler:
            return None

        local_memory = await handler['get_by_id'](remote_record.id)
        if not local_memory:
            return None

        local_record = self._to_memory_record(local_memory, memory_type)

        if resolution == ConflictResolution.REMOTE_WINS:
            await self._save_memory(memory_type, remote_record)
            return None

        elif resolution == ConflictResolution.LOCAL_WINS:
            return None  # Keep local, don't save remote

        elif resolution == ConflictResolution.NEWER_WINS:
            if remote_record.updated_at > local_record.updated_at:
                await self._save_memory(memory_type, remote_record)
                return None
            return None  # Local is newer

        elif resolution == ConflictResolution.MERGE:
            merged = await self._merge_records(local_record, remote_record)
            if merged:
                await self._save_memory(memory_type, merged)
                return None

        # Manual resolution needed
        return SyncConflict(
            memory_id=remote_record.id,
            memory_type=memory_type,
            local_version=local_record,
            remote_version=remote_record
        )

    async def _merge_records(
        self,
        local: MemoryRecord,
        remote: MemoryRecord
    ) -> Optional[MemoryRecord]:
        """Attempt to merge two conflicting records"""
        # Simple merge: combine content, keeping newer metadata
        try:
            merged_content = {**local.content}

            # Add remote content that doesn't exist locally
            for key, value in remote.content.items():
                if key not in merged_content:
                    merged_content[key] = value
                elif isinstance(value, list) and isinstance(merged_content[key], list):
                    # Merge lists
                    merged_content[key] = list(set(merged_content[key] + value))

            newer = remote if remote.updated_at > local.updated_at else local

            return MemoryRecord(
                id=local.id,
                memory_type=local.memory_type,
                content=merged_content,
                created_at=min(local.created_at, remote.created_at),
                updated_at=datetime.utcnow(),
                source_instance=self.instance_id,
                version=max(local.version, remote.version) + 1
            )

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return None

    async def _save_memory(self, memory_type: MemoryType, record: MemoryRecord):
        """Save a memory record"""
        handler = self._memory_handlers.get(memory_type)
        if handler:
            await handler['save'](record.content, record.id)
            self._local_index[f"{memory_type.value}:{record.id}"] = record.checksum

    def _to_memory_record(self, memory: Any, memory_type: MemoryType) -> MemoryRecord:
        """Convert a memory object to MemoryRecord"""
        # Handle different memory formats
        if isinstance(memory, dict):
            return MemoryRecord(
                id=memory.get('id', str(hash(json.dumps(memory, sort_keys=True)))),
                memory_type=memory_type,
                content=memory,
                created_at=datetime.fromisoformat(memory.get('created_at', datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(memory.get('updated_at', datetime.utcnow().isoformat())),
                source_instance=memory.get('source_instance', self.instance_id)
            )
        elif hasattr(memory, 'to_dict'):
            data = memory.to_dict()
            return self._to_memory_record(data, memory_type)
        else:
            raise ValueError(f"Cannot convert {type(memory)} to MemoryRecord")

    def get_local_index(self, memory_types: List[MemoryType] = None) -> Dict[str, Dict[str, str]]:
        """Get index of local memories for sync"""
        index = {}
        memory_types = memory_types or list(MemoryType)

        for memory_type in memory_types:
            type_key = memory_type.value
            index[type_key] = {}

            for key, checksum in self._local_index.items():
                if key.startswith(f"{type_key}:"):
                    mem_id = key[len(f"{type_key}:"):]
                    index[type_key][mem_id] = checksum

        return index

    async def receive_memories(
        self,
        source_instance: str,
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Receive memories pushed from another instance"""
        accepted = 0
        rejected = 0

        for memory_data in memories:
            try:
                record = MemoryRecord.from_dict(memory_data)
                memory_type = record.memory_type

                # Check if we have a handler
                if memory_type not in self._memory_handlers:
                    rejected += 1
                    continue

                # Check for conflict
                local_checksum = self._local_index.get(f"{memory_type.value}:{record.id}")
                if local_checksum and local_checksum != record.checksum:
                    # Conflict - use default resolution
                    conflict = await self._handle_conflict(
                        memory_type, record, self.default_resolution
                    )
                    if conflict:
                        self._conflicts.append(conflict)
                        rejected += 1
                        continue

                await self._save_memory(memory_type, record)
                accepted += 1

            except Exception as e:
                logger.error(f"Failed to receive memory: {e}")
                rejected += 1

        return {
            'accepted': accepted,
            'rejected': rejected,
            'conflicts': len([c for c in self._conflicts if not c.resolved])
        }

    def resolve_conflict(
        self,
        conflict_id: str,
        keep_version: str  # 'local' or 'remote'
    ) -> bool:
        """Manually resolve a conflict"""
        for conflict in self._conflicts:
            if conflict.memory_id == conflict_id and not conflict.resolved:
                if keep_version == 'remote':
                    asyncio.create_task(
                        self._save_memory(conflict.memory_type, conflict.remote_version)
                    )
                conflict.resolved = True
                conflict.resolution = keep_version
                return True
        return False

    def get_conflicts(self) -> List[Dict[str, Any]]:
        """Get unresolved conflicts"""
        return [c.to_dict() for c in self._conflicts if not c.resolved]

    def get_sync_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent sync history"""
        return [r.to_dict() for r in self._sync_history[-limit:]]

    def _save_state(self):
        """Save sync state to disk"""
        try:
            state_file = self.data_path / "sync_state.json"
            state = {
                'local_index': self._local_index,
                'peer_sync_state': self._peer_sync_state,
                'conflicts': [c.to_dict() for c in self._conflicts],
                'updated_at': datetime.utcnow().isoformat()
            }

            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    def _load_state(self):
        """Load sync state from disk"""
        try:
            state_file = self.data_path / "sync_state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)

                self._local_index = state.get('local_index', {})
                self._peer_sync_state = state.get('peer_sync_state', {})

        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get sync protocol status"""
        return {
            'instance_id': self.instance_id,
            'local_memory_count': len(self._local_index),
            'pending_conflicts': len([c for c in self._conflicts if not c.resolved]),
            'registered_handlers': [t.value for t in self._memory_handlers.keys()],
            'peer_sync_state': self._peer_sync_state,
            'recent_syncs': len(self._sync_history)
        }
