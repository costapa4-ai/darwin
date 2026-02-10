"""
State Manager - Manages Darwin's consciousness state transitions.

Handles transitions between WAKE and SLEEP states, including:
- Triggering hooks before/after transitions
- Broadcasting status updates
- Managing cycle counters
- Celebrating milestones

v4.2: Integrated with formal StateMachine for validated transitions and logging.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from consciousness.models import ConsciousnessState, Activity, Dream
from consciousness.state_machine import (
    StateMachine,
    ConsciousnessState as FormalState,
    StateTransition,
    InvalidTransitionError,
    to_legacy_state,
    from_legacy_state
)

if TYPE_CHECKING:
    from consciousness.consciousness_engine import ConsciousnessEngine

from utils.logger import setup_logger

logger = setup_logger(__name__)


class StateManager:
    """
    Manages state transitions for the consciousness engine.

    This class encapsulates all state transition logic, making it easier
    to test and maintain separately from the main engine.

    v4.2: Now uses a formal StateMachine for validated transitions and logging.
    """

    def __init__(self, engine: "ConsciousnessEngine", use_formal_state_machine: bool = True):
        """
        Initialize state manager with reference to parent engine.

        Args:
            engine: The ConsciousnessEngine instance this manager belongs to
            use_formal_state_machine: Whether to use the formal state machine (default: True)
        """
        self.engine = engine
        self._use_formal_sm = use_formal_state_machine

        # Initialize formal state machine if enabled
        if self._use_formal_sm:
            self._state_machine = StateMachine(
                initial_state=FormalState.INITIALIZING,
                validate_transitions=True,
                log_transitions=True
            )
            self._setup_state_machine_callbacks()
        else:
            self._state_machine = None

    def _setup_state_machine_callbacks(self) -> None:
        """Set up callbacks for state machine events."""
        if not self._state_machine:
            return

        # Log all transitions
        def log_transition(transition: StateTransition):
            logger.info(
                f"[StateMachine] {transition.from_state.value} -> {transition.to_state.value} "
                f"(trigger: {transition.trigger})"
            )

        self._state_machine.on_post_transition(log_transition)

        # State-specific callbacks
        def on_enter_sleep(transition: StateTransition):
            print(f"[StateMachine] Entered SLEEP state")

        def on_enter_wake(transition: StateTransition):
            print(f"[StateMachine] Entered WAKE state")

        def on_exit_wake(transition: StateTransition):
            print(f"[StateMachine] Exiting WAKE state after {self._state_machine.state_duration_seconds:.1f}s")

        def on_exit_sleep(transition: StateTransition):
            print(f"[StateMachine] Exiting SLEEP state after {self._state_machine.state_duration_seconds:.1f}s")

        self._state_machine.on_enter(FormalState.SLEEP, on_enter_sleep)
        self._state_machine.on_enter(FormalState.WAKE, on_enter_wake)
        self._state_machine.on_exit(FormalState.WAKE, on_exit_wake)
        self._state_machine.on_exit(FormalState.SLEEP, on_exit_sleep)

    async def initialize(self, start_in_wake: bool = True) -> None:
        """
        Initialize the state machine after engine startup.

        Call this after restoring state to sync the formal state machine.
        """
        if not self._state_machine:
            return

        # Sync state machine with engine state
        current_state = self.engine.state
        formal_state = from_legacy_state(current_state.value)

        try:
            await self._state_machine.transition(
                formal_state,
                reason=f"Initializing to {formal_state.display_name}",
                trigger="startup"
            )
        except InvalidTransitionError as e:
            logger.warning(f"State machine initialization warning: {e}")
            # Force the transition for initial sync
            await self._state_machine.transition(
                formal_state,
                reason=f"Force sync to {formal_state.display_name}",
                trigger="startup",
                force=True
            )

    def should_transition(self) -> bool:
        """
        Check if the engine should transition to a different state.

        Returns:
            True if a transition should occur
        """
        # Skip transitions if in debug mode
        if self.engine.debug_mode in ['sleep', 'wake']:
            return False

        elapsed = (datetime.utcnow() - self.engine.cycle_start_time).total_seconds() / 60

        if self.engine.state == ConsciousnessState.WAKE:
            return elapsed >= self.engine.wake_duration
        elif self.engine.state == ConsciousnessState.SLEEP:
            return elapsed >= self.engine.sleep_duration

        return False

    async def check_and_transition(self) -> Optional[ConsciousnessState]:
        """
        Check if transition needed and perform it.

        Returns:
            New state if transitioned, None otherwise
        """
        if not self.should_transition():
            return None

        if self.engine.state == ConsciousnessState.WAKE:
            await self.transition_to_sleep()
            return ConsciousnessState.SLEEP
        elif self.engine.state == ConsciousnessState.SLEEP:
            await self.transition_to_wake()
            return ConsciousnessState.WAKE

        return None

    async def transition_to_sleep(self) -> None:
        """Execute transition from WAKE to SLEEP state."""
        logger.info("Transitioning to SLEEP state")

        # Validate transition with formal state machine
        if self._state_machine:
            try:
                # Begin transitioning phase
                await self._state_machine.transition(
                    FormalState.TRANSITIONING,
                    reason="Beginning sleep cycle",
                    trigger="timer",
                    context={
                        "activities_count": len(self.engine.wake_activities),
                        "wake_cycles_completed": self.engine.wake_cycles_completed
                    }
                )
            except InvalidTransitionError as e:
                logger.error(f"Invalid transition to SLEEP: {e}")
                print(f"Invalid transition: {e}")
                return

        print(f"\n😴 Darwin is getting tired... transitioning to SLEEP")
        print(f"📊 Wake cycle summary: {len(self.engine.wake_activities)} activities completed")

        # Trigger before_sleep hooks
        await self._trigger_hooks('BEFORE_SLEEP', {
            'activities_count': len(self.engine.wake_activities),
            'wake_cycles_completed': self.engine.wake_cycles_completed
        })

        # Write diary entry before sleeping
        await self._write_diary_entry("wake_to_sleep")

        # Announce transition via communicator
        await self._announce_sleep_transition()

        # Update engine state
        self.engine.state = ConsciousnessState.SLEEP
        self.engine.cycle_start_time = datetime.utcnow()
        self.engine.wake_cycles_completed += 1

        # Complete transition in formal state machine
        if self._state_machine:
            await self._state_machine.transition(
                FormalState.SLEEP,
                reason="Sleep cycle started",
                trigger="timer"
            )

        # Broadcast to channels
        await self._broadcast_status(
            f"Darwin is entering SLEEP mode. Completed {len(self.engine.wake_activities)} activities during wake cycle.",
            "sleep"
        )

        # Celebrate milestones
        await self._check_milestone(
            self.engine.wake_cycles_completed,
            "wake cycles"
        )

        # Print activity summary
        self._print_wake_summary()

        # Run memory consolidation during sleep transition
        await self._consolidate_memories()

        # Trim wake activities (keep last 50)
        self._trim_activities()

        # Trigger after_sleep hooks
        await self._trigger_hooks('AFTER_SLEEP', {
            'wake_cycles_completed': self.engine.wake_cycles_completed
        })

        logger.info(f"Transitioned to SLEEP. Wake cycles completed: {self.engine.wake_cycles_completed}")

    async def transition_to_wake(self) -> None:
        """Execute transition from SLEEP to WAKE state."""
        logger.info("Transitioning to WAKE state")

        # Validate transition with formal state machine
        if self._state_machine:
            try:
                # Begin transitioning phase
                await self._state_machine.transition(
                    FormalState.TRANSITIONING,
                    reason="Beginning wake cycle",
                    trigger="timer",
                    context={
                        "dreams_count": len(self.engine.sleep_dreams),
                        "sleep_cycles_completed": self.engine.sleep_cycles_completed
                    }
                )
            except InvalidTransitionError as e:
                logger.error(f"Invalid transition to WAKE: {e}")
                print(f"Invalid transition: {e}")
                return

        print(f"\n🌅 Darwin is waking up... transitioning to WAKE")
        print(f"📊 Sleep cycle summary: {len(self.engine.sleep_dreams)} dreams explored")

        # Trigger before_wake hooks
        await self._trigger_hooks('BEFORE_WAKE', {
            'dreams_count': len(self.engine.sleep_dreams),
            'sleep_cycles_completed': self.engine.sleep_cycles_completed
        })

        # Announce transition via communicator
        await self._announce_wake_transition()

        # Update engine state
        self.engine.state = ConsciousnessState.WAKE
        self.engine.cycle_start_time = datetime.utcnow()
        self.engine.sleep_cycles_completed += 1

        # Complete transition in formal state machine
        if self._state_machine:
            await self._state_machine.transition(
                FormalState.WAKE,
                reason="Wake cycle started",
                trigger="timer"
            )

        # Broadcast wake and dreams to channels
        await self._broadcast_dreams()

        # Celebrate milestones
        await self._check_milestone(
            self.engine.sleep_cycles_completed,
            "sleep cycles"
        )

        # Print dream summary
        self._print_dream_summary()

        # Trim dreams (keep last 50)
        self._trim_dreams()

        # Trigger after_wake hooks
        await self._trigger_hooks('AFTER_WAKE', {
            'sleep_cycles_completed': self.engine.sleep_cycles_completed,
            'dreams_count': len(self.engine.sleep_dreams)
        })

        logger.info(f"Transitioned to WAKE. Sleep cycles completed: {self.engine.sleep_cycles_completed}")

    async def force_transition(self, target_state: ConsciousnessState, reason: str = "") -> bool:
        """
        Force a transition to a specific state (for debugging/testing).

        Args:
            target_state: Target state to transition to
            reason: Reason for the forced transition

        Returns:
            True if transition succeeded
        """
        logger.warning(f"Forcing transition to {target_state.value}: {reason}")

        if self._state_machine:
            formal_target = from_legacy_state(target_state.value)
            await self._state_machine.transition(
                formal_target,
                reason=reason or "Forced transition",
                trigger="manual",
                force=True
            )

        self.engine.state = target_state
        self.engine.cycle_start_time = datetime.utcnow()

        print(f"Forced transition to {target_state.value}: {reason}")
        return True

    async def shutdown(self) -> None:
        """Initiate graceful shutdown."""
        if self._state_machine:
            try:
                await self._state_machine.shutdown(reason="Engine shutdown requested")
                await self._state_machine.stop()
            except Exception as e:
                logger.warning(f"Shutdown transition error: {e}")

    async def _trigger_hooks(self, event_name: str, context: Dict[str, Any]) -> None:
        """Trigger lifecycle hooks."""
        try:
            from consciousness.hooks import trigger_hook, HookEvent
            event = getattr(HookEvent, event_name, None)
            if event:
                await trigger_hook(event, context, source='consciousness_engine')
        except Exception as e:
            logger.warning(f"Hook trigger failed for {event_name}: {e}")

    async def _write_diary_entry(self, trigger: str) -> None:
        """Write diary entry if diary engine is available."""
        if not self.engine.diary_engine:
            return

        try:
            diary_path = await self.engine.diary_engine.write_daily_entry(trigger=trigger)
            print(f"📔 Diary entry written: {diary_path}")
        except Exception as e:
            logger.warning(f"Failed to write diary: {e}")

    async def _announce_sleep_transition(self) -> None:
        """Announce sleep transition via communicator."""
        if not self.engine.communicator:
            return

        try:
            await self.engine.communicator.share_reflection(
                thought=f"Completed {len(self.engine.wake_activities)} activities during wake cycle. Time to rest and learn deeply.",
                depth="medium"
            )

            from personality.mood_system import MoodInfluencer
            self.engine.communicator.process_mood_event(MoodInfluencer.SLEEP_CYCLE_START)
        except Exception as e:
            logger.warning(f"Failed to announce sleep transition: {e}")

    async def _announce_wake_transition(self) -> None:
        """Announce wake transition via communicator."""
        if not self.engine.communicator:
            return

        try:
            discoveries_count = self._count_discoveries()
            await self.engine.communicator.share_reflection(
                thought=f"Waking up refreshed! Explored {len(self.engine.sleep_dreams)} topics and made {discoveries_count} discoveries during sleep.",
                depth="medium"
            )

            from personality.mood_system import MoodInfluencer
            self.engine.communicator.process_mood_event(
                MoodInfluencer.WAKE_CYCLE_START,
                context={'discoveries': discoveries_count}
            )
        except Exception as e:
            logger.warning(f"Failed to announce wake transition: {e}")

    async def _broadcast_status(self, message: str, status: str) -> None:
        """Broadcast status to channel gateway."""
        if not hasattr(self.engine, 'channel_gateway') or not self.engine.channel_gateway:
            return

        try:
            await self.engine.channel_gateway.broadcast_status(message, status)
        except Exception as e:
            logger.warning(f"Channel broadcast failed: {e}")

    async def _broadcast_dreams(self) -> None:
        """Broadcast dream summary to channels."""
        if not hasattr(self.engine, 'channel_gateway') or not self.engine.channel_gateway:
            return

        try:
            discoveries_count = self._count_discoveries()
            dream_summary = f"Explored {len(self.engine.sleep_dreams)} topics and made {discoveries_count} discoveries."

            highlights = []
            for dream in self.engine.sleep_dreams[-3:]:
                if hasattr(dream, 'insights') and dream.insights:
                    highlights.extend(dream.insights[:1])

            await self.engine.channel_gateway.broadcast_dream(dream_summary, highlights)
        except Exception as e:
            logger.warning(f"Dream broadcast failed: {e}")

    async def _check_milestone(self, count: int, milestone_type: str) -> None:
        """Check and celebrate milestones."""
        if not self.engine.communicator:
            return

        if count % 10 == 0:
            try:
                await self.engine.communicator.celebrate_achievement(
                    achievement=f"Completed {count} {milestone_type}!",
                    milestone=f"{count} {milestone_type}"
                )
            except Exception as e:
                logger.warning(f"Failed to celebrate milestone: {e}")

    def _count_discoveries(self) -> int:
        """Count total discoveries from dreams."""
        return sum(
            len(d.insights) for d in self.engine.sleep_dreams
            if hasattr(d, 'insights') and d.insights
        )

    def _print_wake_summary(self) -> None:
        """Print summary of wake activities."""
        if not self.engine.wake_activities:
            return

        print("✨ During this wake period, I:")
        for activity in self.engine.wake_activities[-5:]:
            print(f"   • {activity.description}")

    def _print_dream_summary(self) -> None:
        """Print summary of sleep dreams."""
        if not self.engine.sleep_dreams:
            return

        print("💡 During sleep, I discovered:")
        for dream in self.engine.sleep_dreams[-3:]:
            insights_count = len(dream.insights) if hasattr(dream, 'insights') and dream.insights else 0
            description = dream.description if hasattr(dream, 'description') else 'Unknown'
            print(f"   • {description} ({insights_count} insights)")

    async def _consolidate_memories(self) -> None:
        """Run hierarchical memory consolidation during sleep transition."""
        if not hasattr(self.engine, 'hierarchical_memory') or not self.engine.hierarchical_memory:
            return
        try:
            stats = await self.engine.hierarchical_memory.consolidate_memories()
            logger.info(
                f"Memory consolidation: {stats.get('episodes_reviewed', 0)} reviewed, "
                f"{stats.get('knowledge_created', 0)} knowledge items created, "
                f"{stats.get('episodes_pruned', 0)} pruned"
            )
        except Exception as e:
            logger.warning(f"Memory consolidation failed: {e}")

    def _trim_activities(self) -> None:
        """Trim wake activities to keep last 50."""
        max_activities = getattr(self.engine, '_max_wake_activities', 50)
        if len(self.engine.wake_activities) > max_activities:
            self.engine.wake_activities = self.engine.wake_activities[-max_activities:]

    def _trim_dreams(self) -> None:
        """Trim dreams to keep last 50."""
        max_dreams = getattr(self.engine, '_max_sleep_dreams', 50)
        if len(self.engine.sleep_dreams) > max_dreams:
            self.engine.sleep_dreams = self.engine.sleep_dreams[-max_dreams:]

    def get_cycle_info(self) -> Dict[str, Any]:
        """Get current cycle information."""
        elapsed = (datetime.utcnow() - self.engine.cycle_start_time).total_seconds() / 60

        if self.engine.state == ConsciousnessState.WAKE:
            duration = self.engine.wake_duration
        else:
            duration = self.engine.sleep_duration

        info = {
            "state": self.engine.state.value,
            "elapsed_minutes": round(elapsed, 1),
            "duration_minutes": duration,
            "remaining_minutes": max(0, round(duration - elapsed, 1)),
            "progress_percent": min(100, round(elapsed / duration * 100, 1)),
            "wake_cycles_completed": self.engine.wake_cycles_completed,
            "sleep_cycles_completed": self.engine.sleep_cycles_completed
        }

        # Add state machine info if available
        if self._state_machine:
            info["state_machine"] = self._state_machine.get_state_info()

        return info

    def get_transition_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transition history from formal state machine."""
        if self._state_machine:
            return self._state_machine.get_transition_history(limit)
        return []

    def get_failed_transitions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get failed transition history from formal state machine."""
        if self._state_machine:
            return self._state_machine.get_failed_transitions(limit)
        return []

    def can_transition_to(self, target_state: ConsciousnessState) -> bool:
        """Check if a transition to target_state is valid."""
        if self._state_machine:
            formal_target = from_legacy_state(target_state.value)
            return self._state_machine.can_transition_to(formal_target)
        # Without state machine, allow all transitions
        return True

    def get_valid_transitions(self) -> List[str]:
        """Get all valid states we can transition to."""
        if self._state_machine:
            return [s.value for s in self._state_machine.get_valid_transitions()]
        return ["wake", "sleep"]
