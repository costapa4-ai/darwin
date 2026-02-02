"""
Formal State Machine - Explicit state definitions, validated transitions, and logging.

This module implements a formal state machine pattern for Darwin's consciousness,
ensuring that only valid state transitions occur and all transitions are logged.
"""

from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Callable, Any, TYPE_CHECKING
from dataclasses import dataclass, field
import asyncio

if TYPE_CHECKING:
    from consciousness.consciousness_engine import ConsciousnessEngine

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConsciousnessState(Enum):
    """
    Darwin's consciousness states with explicit definitions.

    State Diagram:

        INITIALIZING
             │
             ├──────────────────┐
             ▼                  ▼
           WAKE              SLEEP
             │                  │
             ▼                  ▼
        TRANSITIONING ◄───► TRANSITIONING
             │                  │
             ▼                  ▼
           SLEEP              WAKE
             │                  │
             └────────┬─────────┘
                      ▼
              SHUTTING_DOWN
    """
    INITIALIZING = "initializing"      # System starting up
    WAKE = "wake"                      # Active development mode
    SLEEP = "sleep"                    # Deep research/learning mode
    TRANSITIONING = "transitioning"    # Mid-transition state
    SHUTTING_DOWN = "shutting_down"    # System shutting down
    STOPPED = "stopped"                # Terminal state

    @property
    def is_active(self) -> bool:
        """Check if this is an active operational state."""
        return self in (ConsciousnessState.WAKE, ConsciousnessState.SLEEP)

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (ConsciousnessState.STOPPED, ConsciousnessState.SHUTTING_DOWN)

    @property
    def display_name(self) -> str:
        """Human-readable state name."""
        return {
            ConsciousnessState.INITIALIZING: "Initializing",
            ConsciousnessState.WAKE: "Awake",
            ConsciousnessState.SLEEP: "Sleeping",
            ConsciousnessState.TRANSITIONING: "Transitioning",
            ConsciousnessState.SHUTTING_DOWN: "Shutting Down",
            ConsciousnessState.STOPPED: "Stopped"
        }.get(self, self.value.title())


@dataclass
class StateTransition:
    """
    Represents a state transition event.

    Captures the full context of a transition for logging and debugging.
    """
    from_state: ConsciousnessState
    to_state: ConsciousnessState
    timestamp: datetime = field(default_factory=datetime.utcnow)
    reason: str = ""
    trigger: str = ""  # What triggered the transition (timer, manual, restore)
    context: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    duration_ms: Optional[float] = None  # How long the transition took

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "trigger": self.trigger,
            "context": self.context,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateTransition":
        """Create from dictionary."""
        return cls(
            from_state=ConsciousnessState(data["from_state"]),
            to_state=ConsciousnessState(data["to_state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            reason=data.get("reason", ""),
            trigger=data.get("trigger", ""),
            context=data.get("context", {}),
            success=data.get("success", True),
            error=data.get("error"),
            duration_ms=data.get("duration_ms")
        )


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, from_state: ConsciousnessState, to_state: ConsciousnessState, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        message = f"Invalid transition from {from_state.value} to {to_state.value}"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class TransitionValidator:
    """
    Validates state transitions against defined rules.

    Implements a whitelist approach - only explicitly allowed transitions are valid.
    """

    # Define valid transitions as (from_state, to_state) pairs
    VALID_TRANSITIONS: Set[tuple] = {
        # Initialization transitions
        (ConsciousnessState.INITIALIZING, ConsciousnessState.WAKE),
        (ConsciousnessState.INITIALIZING, ConsciousnessState.SLEEP),
        (ConsciousnessState.INITIALIZING, ConsciousnessState.TRANSITIONING),

        # Wake cycle transitions
        (ConsciousnessState.WAKE, ConsciousnessState.TRANSITIONING),
        (ConsciousnessState.TRANSITIONING, ConsciousnessState.SLEEP),

        # Sleep cycle transitions
        (ConsciousnessState.SLEEP, ConsciousnessState.TRANSITIONING),
        (ConsciousnessState.TRANSITIONING, ConsciousnessState.WAKE),

        # Shutdown transitions (can shutdown from any active state)
        (ConsciousnessState.WAKE, ConsciousnessState.SHUTTING_DOWN),
        (ConsciousnessState.SLEEP, ConsciousnessState.SHUTTING_DOWN),
        (ConsciousnessState.TRANSITIONING, ConsciousnessState.SHUTTING_DOWN),
        (ConsciousnessState.INITIALIZING, ConsciousnessState.SHUTTING_DOWN),
        (ConsciousnessState.SHUTTING_DOWN, ConsciousnessState.STOPPED),

        # Direct transitions (for debug mode or forced transitions)
        (ConsciousnessState.WAKE, ConsciousnessState.SLEEP),
        (ConsciousnessState.SLEEP, ConsciousnessState.WAKE),
    }

    @classmethod
    def is_valid(cls, from_state: ConsciousnessState, to_state: ConsciousnessState) -> bool:
        """Check if a transition is valid."""
        # Self-transitions are always valid (no-op)
        if from_state == to_state:
            return True
        return (from_state, to_state) in cls.VALID_TRANSITIONS

    @classmethod
    def get_valid_next_states(cls, current_state: ConsciousnessState) -> List[ConsciousnessState]:
        """Get all valid states that can be transitioned to from current state."""
        valid_next = []
        for from_s, to_s in cls.VALID_TRANSITIONS:
            if from_s == current_state:
                valid_next.append(to_s)
        return valid_next

    @classmethod
    def validate(cls, from_state: ConsciousnessState, to_state: ConsciousnessState) -> None:
        """
        Validate a transition, raising InvalidTransitionError if invalid.
        """
        if not cls.is_valid(from_state, to_state):
            valid_next = cls.get_valid_next_states(from_state)
            valid_str = ", ".join(s.value for s in valid_next) if valid_next else "none"
            raise InvalidTransitionError(
                from_state,
                to_state,
                f"Valid transitions from {from_state.value}: {valid_str}"
            )


class TransitionLog:
    """
    Maintains a log of all state transitions.

    Provides history, statistics, and debugging capabilities.
    """

    def __init__(self, max_entries: int = 1000):
        """
        Initialize transition log.

        Args:
            max_entries: Maximum number of entries to keep in memory
        """
        self._entries: List[StateTransition] = []
        self._max_entries = max_entries
        self._failed_transitions: List[StateTransition] = []

    def record(self, transition: StateTransition) -> None:
        """Record a transition."""
        self._entries.append(transition)

        # Track failed transitions separately
        if not transition.success:
            self._failed_transitions.append(transition)

        # Trim if needed
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        if len(self._failed_transitions) > 100:
            self._failed_transitions = self._failed_transitions[-100:]

        # Log the transition
        if transition.success:
            logger.info(
                f"State transition: {transition.from_state.value} -> {transition.to_state.value} "
                f"(trigger: {transition.trigger}, reason: {transition.reason})"
            )
        else:
            logger.error(
                f"Failed transition: {transition.from_state.value} -> {transition.to_state.value} "
                f"(error: {transition.error})"
            )

    def get_history(self, limit: int = 50) -> List[StateTransition]:
        """Get recent transition history."""
        return self._entries[-limit:]

    def get_failed(self, limit: int = 20) -> List[StateTransition]:
        """Get recent failed transitions."""
        return self._failed_transitions[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get transition statistics."""
        total = len(self._entries)
        failed = len([t for t in self._entries if not t.success])

        # Count transitions by type
        transition_counts: Dict[str, int] = {}
        for t in self._entries:
            key = f"{t.from_state.value}->{t.to_state.value}"
            transition_counts[key] = transition_counts.get(key, 0) + 1

        # Calculate average duration
        durations = [t.duration_ms for t in self._entries if t.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_transitions": total,
            "failed_transitions": failed,
            "success_rate": ((total - failed) / total * 100) if total > 0 else 100,
            "transition_counts": transition_counts,
            "avg_duration_ms": round(avg_duration, 2),
            "oldest_entry": self._entries[0].timestamp.isoformat() if self._entries else None,
            "newest_entry": self._entries[-1].timestamp.isoformat() if self._entries else None
        }

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert log to list of dictionaries."""
        return [t.to_dict() for t in self._entries]

    def clear(self) -> int:
        """Clear the log. Returns number of entries cleared."""
        count = len(self._entries)
        self._entries.clear()
        self._failed_transitions.clear()
        return count


# Type alias for transition callbacks
TransitionCallback = Callable[[StateTransition], Any]


class StateMachine:
    """
    Formal state machine for Darwin's consciousness.

    Features:
    - Explicit state definitions
    - Validated transitions
    - Transition logging
    - Pre/post transition hooks
    - Statistics and debugging
    """

    def __init__(
        self,
        initial_state: ConsciousnessState = ConsciousnessState.INITIALIZING,
        validate_transitions: bool = True,
        log_transitions: bool = True
    ):
        """
        Initialize the state machine.

        Args:
            initial_state: Starting state
            validate_transitions: Whether to validate transitions
            log_transitions: Whether to log transitions
        """
        self._state = initial_state
        self._validate = validate_transitions
        self._log_transitions = log_transitions
        self._log = TransitionLog()
        self._state_entered_at = datetime.utcnow()

        # Callbacks
        self._pre_transition_callbacks: List[TransitionCallback] = []
        self._post_transition_callbacks: List[TransitionCallback] = []
        self._state_enter_callbacks: Dict[ConsciousnessState, List[TransitionCallback]] = {}
        self._state_exit_callbacks: Dict[ConsciousnessState, List[TransitionCallback]] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

    @property
    def state(self) -> ConsciousnessState:
        """Get current state."""
        return self._state

    @property
    def state_duration_seconds(self) -> float:
        """Get how long we've been in the current state."""
        return (datetime.utcnow() - self._state_entered_at).total_seconds()

    @property
    def is_active(self) -> bool:
        """Check if in an active operational state."""
        return self._state.is_active

    @property
    def is_terminal(self) -> bool:
        """Check if in a terminal state."""
        return self._state.is_terminal

    def can_transition_to(self, target_state: ConsciousnessState) -> bool:
        """Check if a transition to target_state is valid."""
        return TransitionValidator.is_valid(self._state, target_state)

    def get_valid_transitions(self) -> List[ConsciousnessState]:
        """Get all valid states we can transition to."""
        return TransitionValidator.get_valid_next_states(self._state)

    async def transition(
        self,
        to_state: ConsciousnessState,
        reason: str = "",
        trigger: str = "manual",
        context: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> StateTransition:
        """
        Transition to a new state.

        Args:
            to_state: Target state
            reason: Human-readable reason for transition
            trigger: What triggered the transition (timer, manual, restore, etc.)
            context: Additional context for the transition
            force: If True, skip validation (use with caution)

        Returns:
            StateTransition record

        Raises:
            InvalidTransitionError: If transition is invalid and not forced
        """
        async with self._lock:
            start_time = datetime.utcnow()
            from_state = self._state

            transition = StateTransition(
                from_state=from_state,
                to_state=to_state,
                timestamp=start_time,
                reason=reason,
                trigger=trigger,
                context=context or {}
            )

            # Skip if no actual change
            if from_state == to_state:
                transition.reason = "No-op: already in target state"
                if self._log_transitions:
                    self._log.record(transition)
                return transition

            try:
                # Validate transition
                if self._validate and not force:
                    TransitionValidator.validate(from_state, to_state)

                # Execute pre-transition callbacks
                await self._execute_callbacks(self._pre_transition_callbacks, transition)

                # Execute state exit callbacks
                if from_state in self._state_exit_callbacks:
                    await self._execute_callbacks(
                        self._state_exit_callbacks[from_state],
                        transition
                    )

                # Perform the transition
                self._state = to_state
                self._state_entered_at = datetime.utcnow()

                # Execute state enter callbacks
                if to_state in self._state_enter_callbacks:
                    await self._execute_callbacks(
                        self._state_enter_callbacks[to_state],
                        transition
                    )

                # Execute post-transition callbacks
                await self._execute_callbacks(self._post_transition_callbacks, transition)

                # Calculate duration
                transition.duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                transition.success = True

                # Print transition info
                print(f"{'='*50}")
                print(f"State Transition: {from_state.display_name} -> {to_state.display_name}")
                print(f"  Trigger: {trigger}")
                print(f"  Reason: {reason or 'Not specified'}")
                print(f"  Duration: {transition.duration_ms:.1f}ms")
                print(f"{'='*50}")

            except InvalidTransitionError as e:
                transition.success = False
                transition.error = str(e)
                logger.error(f"Invalid transition attempted: {e}")
                print(f"Invalid transition: {e}")
                raise

            except Exception as e:
                transition.success = False
                transition.error = str(e)
                logger.error(f"Transition failed: {e}")
                raise

            finally:
                if self._log_transitions:
                    self._log.record(transition)

            return transition

    async def _execute_callbacks(
        self,
        callbacks: List[TransitionCallback],
        transition: StateTransition
    ) -> None:
        """Execute a list of callbacks."""
        for callback in callbacks:
            try:
                result = callback(transition)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    # Callback registration methods

    def on_pre_transition(self, callback: TransitionCallback) -> None:
        """Register a callback to run before any transition."""
        self._pre_transition_callbacks.append(callback)

    def on_post_transition(self, callback: TransitionCallback) -> None:
        """Register a callback to run after any transition."""
        self._post_transition_callbacks.append(callback)

    def on_enter(self, state: ConsciousnessState, callback: TransitionCallback) -> None:
        """Register a callback to run when entering a specific state."""
        if state not in self._state_enter_callbacks:
            self._state_enter_callbacks[state] = []
        self._state_enter_callbacks[state].append(callback)

    def on_exit(self, state: ConsciousnessState, callback: TransitionCallback) -> None:
        """Register a callback to run when exiting a specific state."""
        if state not in self._state_exit_callbacks:
            self._state_exit_callbacks[state] = []
        self._state_exit_callbacks[state].append(callback)

    # Convenience methods for common transitions

    async def start(self, wake: bool = True) -> StateTransition:
        """Start the state machine (transition from INITIALIZING)."""
        target = ConsciousnessState.WAKE if wake else ConsciousnessState.SLEEP
        return await self.transition(
            target,
            reason=f"Starting in {target.display_name} mode",
            trigger="startup"
        )

    async def begin_sleep_transition(self, reason: str = "") -> StateTransition:
        """Begin transition from WAKE to SLEEP."""
        return await self.transition(
            ConsciousnessState.TRANSITIONING,
            reason=reason or "Beginning sleep transition",
            trigger="timer"
        )

    async def complete_sleep_transition(self) -> StateTransition:
        """Complete transition to SLEEP."""
        return await self.transition(
            ConsciousnessState.SLEEP,
            reason="Completed sleep transition",
            trigger="timer"
        )

    async def begin_wake_transition(self, reason: str = "") -> StateTransition:
        """Begin transition from SLEEP to WAKE."""
        return await self.transition(
            ConsciousnessState.TRANSITIONING,
            reason=reason or "Beginning wake transition",
            trigger="timer"
        )

    async def complete_wake_transition(self) -> StateTransition:
        """Complete transition to WAKE."""
        return await self.transition(
            ConsciousnessState.WAKE,
            reason="Completed wake transition",
            trigger="timer"
        )

    async def shutdown(self, reason: str = "") -> StateTransition:
        """Begin shutdown."""
        return await self.transition(
            ConsciousnessState.SHUTTING_DOWN,
            reason=reason or "Shutdown requested",
            trigger="shutdown"
        )

    async def stop(self) -> StateTransition:
        """Complete shutdown."""
        return await self.transition(
            ConsciousnessState.STOPPED,
            reason="Shutdown complete",
            trigger="shutdown"
        )

    # State information

    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information."""
        return {
            "current_state": self._state.value,
            "display_name": self._state.display_name,
            "is_active": self._state.is_active,
            "is_terminal": self._state.is_terminal,
            "state_duration_seconds": round(self.state_duration_seconds, 1),
            "state_entered_at": self._state_entered_at.isoformat(),
            "valid_transitions": [s.value for s in self.get_valid_transitions()],
            "transition_stats": self._log.get_stats()
        }

    def get_transition_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transition history."""
        return [t.to_dict() for t in self._log.get_history(limit)]

    def get_failed_transitions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get failed transition history."""
        return [t.to_dict() for t in self._log.get_failed(limit)]


# Backwards compatibility aliases
# These map the new formal states to the legacy ConsciousnessState values
def to_legacy_state(state: ConsciousnessState) -> str:
    """Convert formal state to legacy state string."""
    if state in (ConsciousnessState.WAKE, ConsciousnessState.INITIALIZING):
        return "wake"
    elif state == ConsciousnessState.SLEEP:
        return "sleep"
    elif state == ConsciousnessState.TRANSITIONING:
        return "transition"
    else:
        return state.value


def from_legacy_state(legacy: str) -> ConsciousnessState:
    """Convert legacy state string to formal state."""
    mapping = {
        "wake": ConsciousnessState.WAKE,
        "sleep": ConsciousnessState.SLEEP,
        "transition": ConsciousnessState.TRANSITIONING,
        "transitioning": ConsciousnessState.TRANSITIONING,
        "initializing": ConsciousnessState.INITIALIZING,
        "shutting_down": ConsciousnessState.SHUTTING_DOWN,
        "stopped": ConsciousnessState.STOPPED
    }
    return mapping.get(legacy.lower(), ConsciousnessState.WAKE)
