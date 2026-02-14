"""
Persistence Manager - Handles state persistence for the consciousness engine.

Manages saving and restoring consciousness state to/from disk, including:
- Activities, dreams, and curiosity moments
- Cycle statistics
- Deduplication data migration
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING


class SafeJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles non-serializable objects by converting to string."""
    def default(self, obj):
        try:
            # Try default serialization first
            return super().default(obj)
        except TypeError:
            # Convert non-serializable objects to their string representation
            return str(obj)

from consciousness.models import (
    ConsciousnessState, Activity, Dream, CuriosityMoment,
    DEFAULT_WAKE_DURATION_MINUTES, DEFAULT_SLEEP_DURATION_MINUTES
)

if TYPE_CHECKING:
    from consciousness.consciousness_engine import ConsciousnessEngine
    from core.deduplication import DeduplicationStore

from utils.logger import setup_logger

logger = setup_logger(__name__)

# State file version
STATE_VERSION = "4.0"


class PersistenceManager:
    """
    Manages persistence of consciousness state.

    This class handles all file I/O for saving and restoring the
    consciousness engine state.
    """

    def __init__(
        self,
        engine: "ConsciousnessEngine",
        state_file: Path,
        dedup_store: "DeduplicationStore"
    ):
        """
        Initialize persistence manager.

        Args:
            engine: The ConsciousnessEngine instance
            state_file: Path to the state file
            dedup_store: Deduplication store for insight tracking
        """
        self.engine = engine
        self.state_file = state_file
        self.dedup_store = dedup_store

    async def save_state(self) -> bool:
        """
        Save complete consciousness state to disk.

        Returns:
            True if save was successful
        """
        try:
            # Ensure data directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = self._build_state_dict()

            # Write to file with atomic operation
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False, cls=SafeJSONEncoder)

            # Atomic rename
            temp_file.replace(self.state_file)

            logger.info(
                f"State saved: {len(self.engine.wake_activities)} activities, "
                f"{len(self.engine.sleep_dreams)} dreams, "
                f"{len(self.engine.curiosity_moments)} curiosities"
            )
            print(
                f"💾 State saved: {len(self.engine.wake_activities)} activities, "
                f"{len(self.engine.sleep_dreams)} dreams, "
                f"{len(self.engine.curiosity_moments)} curiosities"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            print(f"❌ Failed to save state: {e}")
            return False

    def _build_state_dict(self) -> Dict[str, Any]:
        """Build the state dictionary for serialization."""
        return {
            # Current state
            'state': self.engine.state.value,
            'cycle_start_time': self.engine.cycle_start_time.isoformat(),

            # Statistics
            'wake_cycles_completed': self.engine.wake_cycles_completed,
            'sleep_cycles_completed': self.engine.sleep_cycles_completed,
            'total_activities_completed': self.engine.total_activities_completed,
            'total_discoveries_made': self.engine.total_discoveries_made,

            # Activities (last N to prevent file bloat)
            'wake_activities': [
                self._activity_to_dict(a)
                for a in self.engine.wake_activities[-50:]
            ],

            # Dreams (last N)
            'sleep_dreams': [
                self._dream_to_dict(d)
                for d in self.engine.sleep_dreams[-30:]
            ],

            # Curiosities (last N)
            'curiosity_moments': [
                self._curiosity_to_dict(c)
                for c in self.engine.curiosity_moments[-20:]
            ],

            # Deduplication tracking
            'submitted_insights': [],  # Database-backed, kept for compatibility
            'shared_curiosity_topics': list(self.engine.shared_curiosity_topics),
            'dedup_stats': self.dedup_store.get_stats(),

            # Current project (multi-step goal tracking)
            'current_project': getattr(self.engine, 'current_project', None),

            # Metadata
            'saved_at': datetime.utcnow().isoformat(),
            'version': STATE_VERSION
        }

    def _activity_to_dict(self, activity: Activity) -> Dict[str, Any]:
        """Convert Activity to dictionary."""
        return {
            'type': activity.type,
            'description': activity.description,
            'started_at': activity.started_at.isoformat(),
            'completed_at': activity.completed_at.isoformat() if activity.completed_at else None,
            'result': activity.result,
            'insights': activity.insights
        }

    def _dream_to_dict(self, dream: Dream) -> Dict[str, Any]:
        """Convert Dream to dictionary."""
        return {
            'topic': dream.topic,
            'description': dream.description,
            'started_at': dream.started_at.isoformat(),
            'completed_at': dream.completed_at.isoformat() if dream.completed_at else None,
            'success': dream.success,
            'insights': dream.insights,
            'exploration_details': dream.exploration_details
        }

    def _curiosity_to_dict(self, curiosity: CuriosityMoment) -> Dict[str, Any]:
        """Convert CuriosityMoment to dictionary."""
        return {
            'topic': curiosity.topic,
            'fact': curiosity.fact,
            'source': curiosity.source,
            'significance': curiosity.significance,
            'timestamp': curiosity.timestamp.isoformat()
        }

    async def restore_state(self) -> bool:
        """
        Restore consciousness state from disk.

        Returns:
            True if restore was successful
        """
        try:
            if not self.state_file.exists():
                print("ℹ️  No previous state found, starting fresh")
                return False

            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            self._restore_from_dict(state)

            # Migrate legacy deduplication data
            self._migrate_legacy_dedup(state)

            # Adjust cycle if needed
            self._adjust_cycle_timing()

            # Log restoration summary
            self._log_restoration_summary(state)

            return True

        except Exception as e:
            logger.error(f"Failed to restore state: {e}")
            print(f"⚠️  Failed to restore state: {e}")
            print("   Starting fresh...")
            self._reset_to_defaults()
            return False

    def _restore_from_dict(self, state: Dict[str, Any]) -> None:
        """Restore engine state from dictionary."""
        # Restore state
        self.engine.state = ConsciousnessState(state['state'])
        self.engine.cycle_start_time = datetime.fromisoformat(state['cycle_start_time'])

        # Restore statistics
        self.engine.wake_cycles_completed = state.get('wake_cycles_completed', 0)
        self.engine.sleep_cycles_completed = state.get('sleep_cycles_completed', 0)
        self.engine.total_activities_completed = state.get('total_activities_completed', 0)
        self.engine.total_discoveries_made = state.get('total_discoveries_made', 0)

        # Restore activities
        self.engine.wake_activities = [
            self._dict_to_activity(a)
            for a in state.get('wake_activities', [])
        ]

        # Restore dreams
        self.engine.sleep_dreams = [
            self._dict_to_dream(d)
            for d in state.get('sleep_dreams', [])
        ]

        # Restore curiosities
        self.engine.curiosity_moments = [
            self._dict_to_curiosity(c)
            for c in state.get('curiosity_moments', [])
        ]

        # Restore shared topics
        self.engine.shared_curiosity_topics = set(state.get('shared_curiosity_topics', []))

        # Restore current project
        self.engine.current_project = state.get('current_project', None)

    def _dict_to_activity(self, data: Dict[str, Any]) -> Activity:
        """Convert dictionary to Activity."""
        return Activity(
            type=data['type'],
            description=data['description'],
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            result=data.get('result'),
            insights=data.get('insights', [])
        )

    def _dict_to_dream(self, data: Dict[str, Any]) -> Dream:
        """Convert dictionary to Dream."""
        return Dream(
            topic=data['topic'],
            description=data['description'],
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            success=data.get('success', False),
            insights=data.get('insights', []),
            exploration_details=data.get('exploration_details')
        )

    def _dict_to_curiosity(self, data: Dict[str, Any]) -> CuriosityMoment:
        """Convert dictionary to CuriosityMoment."""
        return CuriosityMoment(
            topic=data['topic'],
            fact=data['fact'],
            source=data['source'],
            significance=data.get('significance', ''),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )

    def _migrate_legacy_dedup(self, state: Dict[str, Any]) -> None:
        """Migrate legacy submitted_insights from JSON to database."""
        legacy_insights = state.get('submitted_insights', [])
        if legacy_insights:
            migrated = self.dedup_store.migrate_from_set(
                set(legacy_insights),
                source="json_migration"
            )
            print(f"📦 Migrated {migrated} insights from JSON to database")

        # Log current dedup stats
        dedup_stats = self.dedup_store.get_stats()
        print(
            f"📚 Deduplication database: {dedup_stats['total_entries']} insights, "
            f"{len(self.engine.shared_curiosity_topics)} curiosity topics"
        )

    def _adjust_cycle_timing(self) -> None:
        """Adjust cycle timing if needed after restore."""
        elapsed = (datetime.utcnow() - self.engine.cycle_start_time).total_seconds() / 60
        wake_duration = self.engine.wake_duration
        sleep_duration = self.engine.sleep_duration

        if self.engine.state == ConsciousnessState.WAKE and elapsed > wake_duration:
            # Should have transitioned to sleep already
            excess = elapsed - wake_duration
            if excess < sleep_duration:
                # In middle of sleep cycle
                self.engine.state = ConsciousnessState.SLEEP
                self.engine.cycle_start_time = datetime.utcnow() - timedelta(minutes=excess)
                print(f"⏩ Adjusted to SLEEP mode (excess: {excess:.1f} min)")
            else:
                # Multiple cycles passed, start fresh WAKE
                self.engine.state = ConsciousnessState.WAKE
                self.engine.cycle_start_time = datetime.utcnow()
                print(f"⏩ Multiple cycles passed, starting fresh WAKE")

        elif self.engine.state == ConsciousnessState.SLEEP and elapsed > sleep_duration:
            # Should have transitioned to wake already
            self.engine.state = ConsciousnessState.WAKE
            self.engine.cycle_start_time = datetime.utcnow()
            print(f"⏩ Adjusted to WAKE mode (cycle complete)")

    def _log_restoration_summary(self, state: Dict[str, Any]) -> None:
        """Log restoration summary."""
        elapsed = (datetime.utcnow() - self.engine.cycle_start_time).total_seconds() / 60
        print(f"✅ State restored from {state['saved_at']}")
        print(f"   State: {self.engine.state.value.upper()} (elapsed: {elapsed:.1f} min)")
        print(
            f"   Activities: {len(self.engine.wake_activities)} | "
            f"Dreams: {len(self.engine.sleep_dreams)} | "
            f"Curiosities: {len(self.engine.curiosity_moments)}"
        )

    def _reset_to_defaults(self) -> None:
        """Reset engine to default state."""
        self.engine.wake_activities = []
        self.engine.sleep_dreams = []
        self.engine.curiosity_moments = []
        self.engine.shared_curiosity_topics = set()


async def auto_save_state(engine: "ConsciousnessEngine", interval_seconds: int = 60) -> None:
    """
    Background task for automatic state saving.

    Args:
        engine: ConsciousnessEngine instance
        interval_seconds: Interval between saves
    """
    import asyncio
    while engine.is_running:
        await asyncio.sleep(interval_seconds)
        if hasattr(engine, '_persistence_manager'):
            await engine._persistence_manager.save_state()
