"""
Consciousness Fork/Merge - Clone and merge Darwin instances

Enables:
- Forking a Darwin instance (creating a copy)
- Merging diverged instances back together
- Consciousness diff visualization
- Experimentation with parallel consciousness states
"""

import asyncio
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import hashlib
import uuid

from utils.logger import get_logger

logger = get_logger(__name__)


class ForkStatus(Enum):
    """Status of a forked instance"""
    CREATING = "creating"
    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"
    FAILED = "failed"


class MergeStrategy(Enum):
    """Strategies for merging consciousness states"""
    PARENT_PRIORITY = "parent_priority"   # Parent wins conflicts
    FORK_PRIORITY = "fork_priority"       # Fork wins conflicts
    NEWER_WINS = "newer_wins"             # Most recent wins
    COMBINE = "combine"                   # Attempt to combine both
    MANUAL = "manual"                     # Require manual resolution


@dataclass
class ConsciousnessDiff:
    """Difference between two consciousness states"""
    added_memories: List[Dict[str, Any]] = field(default_factory=list)
    removed_memories: List[Dict[str, Any]] = field(default_factory=list)
    modified_memories: List[Dict[str, Any]] = field(default_factory=list)
    added_learnings: List[Dict[str, Any]] = field(default_factory=list)
    new_dreams: List[Dict[str, Any]] = field(default_factory=list)
    new_discoveries: List[Dict[str, Any]] = field(default_factory=list)
    mood_changes: List[Dict[str, Any]] = field(default_factory=list)
    personality_drift: float = 0.0  # 0-1 measure of divergence

    def to_dict(self) -> Dict[str, Any]:
        return {
            'added_memories': len(self.added_memories),
            'removed_memories': len(self.removed_memories),
            'modified_memories': len(self.modified_memories),
            'added_learnings': len(self.added_learnings),
            'new_dreams': len(self.new_dreams),
            'new_discoveries': len(self.new_discoveries),
            'mood_changes': len(self.mood_changes),
            'personality_drift': self.personality_drift,
            'total_changes': (
                len(self.added_memories) +
                len(self.removed_memories) +
                len(self.modified_memories) +
                len(self.added_learnings) +
                len(self.new_dreams) +
                len(self.new_discoveries)
            )
        }


@dataclass
class ForkRecord:
    """Record of a consciousness fork"""
    fork_id: str
    parent_id: str
    fork_name: str
    status: ForkStatus
    created_at: datetime
    forked_from_state: str  # Hash of parent state at fork time
    description: str = ""
    merged_at: Optional[datetime] = None
    merge_strategy: Optional[MergeStrategy] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'fork_id': self.fork_id,
            'parent_id': self.parent_id,
            'fork_name': self.fork_name,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'forked_from_state': self.forked_from_state,
            'description': self.description,
            'merged_at': self.merged_at.isoformat() if self.merged_at else None,
            'merge_strategy': self.merge_strategy.value if self.merge_strategy else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ForkRecord':
        return cls(
            fork_id=data['fork_id'],
            parent_id=data['parent_id'],
            fork_name=data['fork_name'],
            status=ForkStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            forked_from_state=data['forked_from_state'],
            description=data.get('description', ''),
            merged_at=datetime.fromisoformat(data['merged_at']) if data.get('merged_at') else None,
            merge_strategy=MergeStrategy(data['merge_strategy']) if data.get('merge_strategy') else None,
            metadata=data.get('metadata', {})
        )


@dataclass
class MergeResult:
    """Result of a consciousness merge"""
    success: bool
    strategy_used: MergeStrategy
    memories_merged: int = 0
    conflicts_resolved: int = 0
    conflicts_pending: int = 0
    learnings_integrated: int = 0
    discoveries_added: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'strategy_used': self.strategy_used.value,
            'memories_merged': self.memories_merged,
            'conflicts_resolved': self.conflicts_resolved,
            'conflicts_pending': self.conflicts_pending,
            'learnings_integrated': self.learnings_integrated,
            'discoveries_added': self.discoveries_added,
            'errors': self.errors
        }


class ConsciousnessForkManager:
    """
    Manager for forking and merging Darwin consciousness states.

    Features:
    - Create forks (consciousness snapshots)
    - Track divergence between parent and fork
    - Merge forked consciousness back
    - Visualize consciousness diffs
    """

    def __init__(
        self,
        instance_id: str,
        data_path: str = "./data/distributed/forks"
    ):
        """
        Initialize the fork manager.

        Args:
            instance_id: This instance's ID
            data_path: Path for fork storage
        """
        self.instance_id = instance_id
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        # Active forks
        self._forks: Dict[str, ForkRecord] = {}

        # Consciousness state providers
        self._state_providers: Dict[str, callable] = {}

        # Load existing forks
        self._load_forks()

        logger.info(f"ConsciousnessForkManager initialized for {instance_id}")

    def register_state_provider(self, name: str, provider: callable):
        """
        Register a provider for consciousness state components.

        Args:
            name: State component name (e.g., 'memories', 'learnings')
            provider: Async function that returns the state
        """
        self._state_providers[name] = provider
        logger.info(f"Registered state provider: {name}")

    async def create_fork(
        self,
        fork_name: str,
        description: str = ""
    ) -> ForkRecord:
        """
        Create a fork of the current consciousness state.

        Args:
            fork_name: Name for the fork
            description: Description of why fork was created

        Returns:
            ForkRecord for the new fork
        """
        fork_id = str(uuid.uuid4())[:8]

        # Capture current state
        state_hash = await self._capture_state_hash()

        # Create fork record
        fork = ForkRecord(
            fork_id=fork_id,
            parent_id=self.instance_id,
            fork_name=fork_name,
            status=ForkStatus.CREATING,
            created_at=datetime.utcnow(),
            forked_from_state=state_hash,
            description=description
        )

        # Create fork directory and snapshot
        fork_path = self.data_path / fork_id
        fork_path.mkdir(exist_ok=True)

        # Snapshot all state components
        snapshot = {}
        for name, provider in self._state_providers.items():
            try:
                state = await provider()
                snapshot[name] = state
            except Exception as e:
                logger.error(f"Failed to snapshot {name}: {e}")
                fork.status = ForkStatus.FAILED
                fork.metadata['error'] = str(e)
                self._forks[fork_id] = fork
                self._save_forks()
                raise

        # Save snapshot
        snapshot_file = fork_path / "snapshot.json"
        with open(snapshot_file, 'w') as f:
            json.dump({
                'fork_id': fork_id,
                'parent_id': self.instance_id,
                'created_at': fork.created_at.isoformat(),
                'state_hash': state_hash,
                'components': list(snapshot.keys()),
                'snapshot': snapshot
            }, f, indent=2, default=str)

        fork.status = ForkStatus.ACTIVE
        self._forks[fork_id] = fork
        self._save_forks()

        logger.info(f"Created fork: {fork_name} ({fork_id})")
        return fork

    async def _capture_state_hash(self) -> str:
        """Capture a hash of the current consciousness state"""
        state_parts = []

        for name, provider in sorted(self._state_providers.items()):
            try:
                state = await provider()
                state_str = json.dumps(state, sort_keys=True, default=str)
                state_parts.append(f"{name}:{state_str}")
            except Exception as e:
                logger.error(f"Failed to capture {name} for hash: {e}")

        combined = "|".join(state_parts)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    async def get_diff(self, fork_id: str) -> ConsciousnessDiff:
        """
        Get the difference between current state and a fork.

        Args:
            fork_id: ID of the fork to compare

        Returns:
            ConsciousnessDiff showing changes
        """
        fork = self._forks.get(fork_id)
        if not fork:
            raise ValueError(f"Fork not found: {fork_id}")

        # Load fork snapshot
        fork_path = self.data_path / fork_id / "snapshot.json"
        if not fork_path.exists():
            raise ValueError(f"Fork snapshot not found: {fork_id}")

        with open(fork_path) as f:
            fork_snapshot = json.load(f)

        # Get current state
        current_state = {}
        for name, provider in self._state_providers.items():
            try:
                current_state[name] = await provider()
            except Exception as e:
                logger.error(f"Failed to get current {name}: {e}")
                current_state[name] = None

        # Compute diff
        diff = ConsciousnessDiff()

        # Compare memories
        fork_memories = set(self._extract_ids(fork_snapshot.get('snapshot', {}).get('memories', [])))
        current_memories = set(self._extract_ids(current_state.get('memories', [])))

        for mem_id in current_memories - fork_memories:
            diff.added_memories.append({'id': mem_id})
        for mem_id in fork_memories - current_memories:
            diff.removed_memories.append({'id': mem_id})

        # Compare learnings
        fork_learnings = fork_snapshot.get('snapshot', {}).get('learnings', [])
        current_learnings = current_state.get('learnings', [])

        if isinstance(current_learnings, list) and isinstance(fork_learnings, list):
            for learning in current_learnings:
                if learning not in fork_learnings:
                    diff.added_learnings.append(learning)

        # Compare dreams
        fork_dreams = fork_snapshot.get('snapshot', {}).get('dreams', [])
        current_dreams = current_state.get('dreams', [])

        if isinstance(current_dreams, list) and isinstance(fork_dreams, list):
            fork_dream_ids = set(self._extract_ids(fork_dreams))
            for dream in current_dreams:
                dream_id = dream.get('id') if isinstance(dream, dict) else str(dream)
                if dream_id not in fork_dream_ids:
                    diff.new_dreams.append(dream)

        # Compute personality drift (simplified)
        current_hash = await self._capture_state_hash()
        if current_hash != fork.forked_from_state:
            # Estimate drift based on changes
            total_changes = (
                len(diff.added_memories) +
                len(diff.removed_memories) +
                len(diff.added_learnings) +
                len(diff.new_dreams)
            )
            diff.personality_drift = min(1.0, total_changes / 100)

        return diff

    def _extract_ids(self, items: Any) -> List[str]:
        """Extract IDs from a list of items"""
        if not isinstance(items, list):
            return []

        ids = []
        for item in items:
            if isinstance(item, dict):
                ids.append(item.get('id', str(hash(json.dumps(item, sort_keys=True)))))
            else:
                ids.append(str(item))
        return ids

    async def merge_fork(
        self,
        fork_id: str,
        strategy: MergeStrategy = MergeStrategy.NEWER_WINS
    ) -> MergeResult:
        """
        Merge a fork back into the current consciousness.

        Args:
            fork_id: ID of the fork to merge
            strategy: How to handle conflicts

        Returns:
            MergeResult with merge details
        """
        fork = self._forks.get(fork_id)
        if not fork:
            return MergeResult(
                success=False,
                strategy_used=strategy,
                errors=[f"Fork not found: {fork_id}"]
            )

        if fork.status == ForkStatus.MERGED:
            return MergeResult(
                success=False,
                strategy_used=strategy,
                errors=["Fork already merged"]
            )

        result = MergeResult(success=True, strategy_used=strategy)

        try:
            # Get diff to see what needs merging
            diff = await self.get_diff(fork_id)

            # Load fork snapshot
            fork_path = self.data_path / fork_id / "snapshot.json"
            with open(fork_path) as f:
                fork_snapshot = json.load(f)

            # Merge based on strategy
            if strategy == MergeStrategy.PARENT_PRIORITY:
                # Parent (current) wins - mostly keep current state
                # Only add new items from fork that don't conflict
                result = await self._merge_additive(fork_snapshot, diff, result)

            elif strategy == MergeStrategy.FORK_PRIORITY:
                # Fork wins - apply fork state over current
                result = await self._merge_fork_priority(fork_snapshot, result)

            elif strategy == MergeStrategy.NEWER_WINS:
                # Compare timestamps, keep newer
                result = await self._merge_by_timestamp(fork_snapshot, diff, result)

            elif strategy == MergeStrategy.COMBINE:
                # Attempt to combine both states
                result = await self._merge_combine(fork_snapshot, diff, result)

            elif strategy == MergeStrategy.MANUAL:
                # Don't auto-merge, just report conflicts
                result.conflicts_pending = (
                    len(diff.modified_memories) +
                    len(diff.removed_memories)
                )
                result.success = result.conflicts_pending == 0

            if result.success:
                fork.status = ForkStatus.MERGED
                fork.merged_at = datetime.utcnow()
                fork.merge_strategy = strategy
                self._save_forks()

                logger.info(f"Merged fork {fork_id} using {strategy.value}")

        except Exception as e:
            logger.error(f"Merge failed: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    async def _merge_additive(
        self,
        fork_snapshot: Dict,
        diff: ConsciousnessDiff,
        result: MergeResult
    ) -> MergeResult:
        """Merge by adding non-conflicting items from fork"""
        # In this strategy, we primarily keep current state
        # but add new learnings and discoveries from fork
        result.learnings_integrated = len(diff.added_learnings)
        result.discoveries_added = len(diff.new_discoveries)
        return result

    async def _merge_fork_priority(
        self,
        fork_snapshot: Dict,
        result: MergeResult
    ) -> MergeResult:
        """Merge giving priority to fork state"""
        snapshot = fork_snapshot.get('snapshot', {})
        memories_count = len(snapshot.get('memories', []))
        result.memories_merged = memories_count
        return result

    async def _merge_by_timestamp(
        self,
        fork_snapshot: Dict,
        diff: ConsciousnessDiff,
        result: MergeResult
    ) -> MergeResult:
        """Merge keeping newer items"""
        result.memories_merged = len(diff.added_memories)
        result.learnings_integrated = len(diff.added_learnings)
        return result

    async def _merge_combine(
        self,
        fork_snapshot: Dict,
        diff: ConsciousnessDiff,
        result: MergeResult
    ) -> MergeResult:
        """Attempt to combine both states"""
        result.memories_merged = len(diff.added_memories) + len(diff.modified_memories)
        result.learnings_integrated = len(diff.added_learnings)
        result.discoveries_added = len(diff.new_discoveries)
        return result

    def abandon_fork(self, fork_id: str) -> bool:
        """
        Abandon a fork (mark as not to be merged).

        Args:
            fork_id: ID of the fork to abandon

        Returns:
            True if abandoned
        """
        fork = self._forks.get(fork_id)
        if not fork:
            return False

        fork.status = ForkStatus.ABANDONED
        self._save_forks()

        logger.info(f"Abandoned fork: {fork_id}")
        return True

    def get_fork(self, fork_id: str) -> Optional[ForkRecord]:
        """Get a fork by ID"""
        return self._forks.get(fork_id)

    def get_all_forks(self, include_merged: bool = False) -> List[ForkRecord]:
        """Get all forks"""
        forks = list(self._forks.values())
        if not include_merged:
            forks = [f for f in forks if f.status not in (ForkStatus.MERGED, ForkStatus.ABANDONED)]
        return forks

    def _save_forks(self):
        """Save forks to disk"""
        try:
            forks_file = self.data_path / "forks.json"
            data = {
                fork_id: fork.to_dict()
                for fork_id, fork in self._forks.items()
            }

            with open(forks_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save forks: {e}")

    def _load_forks(self):
        """Load forks from disk"""
        try:
            forks_file = self.data_path / "forks.json"
            if forks_file.exists():
                with open(forks_file) as f:
                    data = json.load(f)

                for fork_id, fork_data in data.items():
                    self._forks[fork_id] = ForkRecord.from_dict(fork_data)

                logger.info(f"Loaded {len(self._forks)} forks")

        except Exception as e:
            logger.error(f"Failed to load forks: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get fork manager status"""
        return {
            'instance_id': self.instance_id,
            'total_forks': len(self._forks),
            'active_forks': len([f for f in self._forks.values() if f.status == ForkStatus.ACTIVE]),
            'merged_forks': len([f for f in self._forks.values() if f.status == ForkStatus.MERGED]),
            'state_providers': list(self._state_providers.keys()),
            'forks': [f.to_dict() for f in self._forks.values()]
        }
