"""
Consciousness Hooks - Event-driven extensibility system

Allows plugins and extensions to hook into Darwin's consciousness
lifecycle events. Inspired by OpenClaw's hook architecture.

Events:
- before_wake, after_wake: Wake transition hooks
- before_sleep, after_sleep: Sleep transition hooks
- on_discovery: When something interesting is found
- on_mood_change: When mood state changes
- on_learning: When a learning session completes
- on_thought: When a shower thought is generated
- on_dream: When a dream is recorded
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional, Awaitable, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback

from utils.logger import get_logger

logger = get_logger(__name__)


class HookEvent(Enum):
    """Available hook events"""
    # Lifecycle events
    BEFORE_WAKE = "before_wake"
    AFTER_WAKE = "after_wake"
    BEFORE_SLEEP = "before_sleep"
    AFTER_SLEEP = "after_sleep"

    # Discovery events
    ON_DISCOVERY = "on_discovery"
    ON_LEARNING = "on_learning"
    ON_EXPEDITION_START = "on_expedition_start"
    ON_EXPEDITION_COMPLETE = "on_expedition_complete"

    # Personality events
    ON_MOOD_CHANGE = "on_mood_change"
    ON_THOUGHT = "on_thought"
    ON_DREAM = "on_dream"

    # System events
    ON_ERROR = "on_error"
    ON_BUDGET_ALERT = "on_budget_alert"
    ON_FINDING = "on_finding"


@dataclass
class HookContext:
    """Context passed to hook callbacks"""
    event: HookEvent
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"

    def get(self, key: str, default: Any = None) -> Any:
        """Get data from context"""
        return self.data.get(key, default)


@dataclass
class RegisteredHook:
    """A registered hook callback"""
    name: str
    callback: Callable[[HookContext], Awaitable[None]]
    priority: int = 50  # 0-100, higher = runs first
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class HooksManager:
    """
    Central manager for consciousness hooks.

    Provides registration, execution, and management of hooks
    for consciousness events.
    """

    def __init__(self):
        """Initialize the hooks manager"""
        self._hooks: Dict[HookEvent, List[RegisteredHook]] = {
            event: [] for event in HookEvent
        }
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        self._enabled = True

        logger.info("HooksManager initialized")

    def register(
        self,
        event: Union[HookEvent, str],
        callback: Callable[[HookContext], Awaitable[None]],
        name: Optional[str] = None,
        priority: int = 50
    ) -> str:
        """
        Register a hook callback.

        Args:
            event: The event to hook into
            callback: Async function to call when event fires
            name: Optional name for the hook (auto-generated if not provided)
            priority: Execution priority (0-100, higher runs first)

        Returns:
            The hook name (for later reference)
        """
        if isinstance(event, str):
            event = HookEvent(event)

        hook_name = name or f"{event.value}_{len(self._hooks[event])}"

        hook = RegisteredHook(
            name=hook_name,
            callback=callback,
            priority=priority
        )

        self._hooks[event].append(hook)
        # Sort by priority (descending)
        self._hooks[event].sort(key=lambda h: h.priority, reverse=True)

        logger.info(f"Registered hook '{hook_name}' for event '{event.value}'")
        return hook_name

    def unregister(self, event: Union[HookEvent, str], name: str) -> bool:
        """
        Unregister a hook.

        Args:
            event: The event the hook is registered to
            name: The hook name

        Returns:
            True if unregistered, False if not found
        """
        if isinstance(event, str):
            event = HookEvent(event)

        for i, hook in enumerate(self._hooks[event]):
            if hook.name == name:
                del self._hooks[event][i]
                logger.info(f"Unregistered hook '{name}' from event '{event.value}'")
                return True

        return False

    def enable_hook(self, event: Union[HookEvent, str], name: str) -> bool:
        """Enable a specific hook"""
        hook = self._get_hook(event, name)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable_hook(self, event: Union[HookEvent, str], name: str) -> bool:
        """Disable a specific hook"""
        hook = self._get_hook(event, name)
        if hook:
            hook.enabled = False
            return True
        return False

    async def trigger(
        self,
        event: Union[HookEvent, str],
        data: Optional[Dict[str, Any]] = None,
        source: str = "system"
    ) -> Dict[str, Any]:
        """
        Trigger an event and run all registered hooks.

        Args:
            event: The event to trigger
            data: Data to pass to hooks
            source: Source identifier for the event

        Returns:
            Execution results
        """
        if not self._enabled:
            return {'skipped': True, 'reason': 'hooks_disabled'}

        if isinstance(event, str):
            event = HookEvent(event)

        context = HookContext(
            event=event,
            data=data or {},
            source=source
        )

        hooks = [h for h in self._hooks[event] if h.enabled]

        if not hooks:
            return {'executed': 0, 'event': event.value}

        results = {
            'event': event.value,
            'executed': 0,
            'success': 0,
            'errors': [],
            'timestamp': datetime.utcnow().isoformat()
        }

        for hook in hooks:
            try:
                start_time = datetime.utcnow()
                await hook.callback(context)

                # Track stats
                duration = (datetime.utcnow() - start_time).total_seconds()
                self._track_execution(hook.name, duration, True)

                results['executed'] += 1
                results['success'] += 1

            except Exception as e:
                logger.error(f"Hook '{hook.name}' error: {e}")
                logger.debug(traceback.format_exc())

                self._track_execution(hook.name, 0, False, str(e))
                results['errors'].append({
                    'hook': hook.name,
                    'error': str(e)
                })

        return results

    async def trigger_parallel(
        self,
        event: Union[HookEvent, str],
        data: Optional[Dict[str, Any]] = None,
        source: str = "system"
    ) -> Dict[str, Any]:
        """
        Trigger hooks in parallel (ignores priority order).

        Use this for independent hooks that don't need sequential execution.
        """
        if not self._enabled:
            return {'skipped': True, 'reason': 'hooks_disabled'}

        if isinstance(event, str):
            event = HookEvent(event)

        context = HookContext(
            event=event,
            data=data or {},
            source=source
        )

        hooks = [h for h in self._hooks[event] if h.enabled]

        if not hooks:
            return {'executed': 0, 'event': event.value}

        async def run_hook(hook: RegisteredHook):
            try:
                await hook.callback(context)
                return (hook.name, True, None)
            except Exception as e:
                return (hook.name, False, str(e))

        results_list = await asyncio.gather(
            *[run_hook(h) for h in hooks],
            return_exceptions=True
        )

        results = {
            'event': event.value,
            'executed': len(results_list),
            'success': sum(1 for r in results_list if isinstance(r, tuple) and r[1]),
            'errors': [
                {'hook': r[0], 'error': r[2]}
                for r in results_list if isinstance(r, tuple) and not r[1]
            ],
            'timestamp': datetime.utcnow().isoformat()
        }

        return results

    def _get_hook(self, event: Union[HookEvent, str], name: str) -> Optional[RegisteredHook]:
        """Get a hook by name"""
        if isinstance(event, str):
            event = HookEvent(event)

        for hook in self._hooks[event]:
            if hook.name == name:
                return hook
        return None

    def _track_execution(self, name: str, duration: float, success: bool, error: str = None):
        """Track hook execution statistics"""
        if name not in self._execution_stats:
            self._execution_stats[name] = {
                'total_calls': 0,
                'successful': 0,
                'failed': 0,
                'total_duration': 0.0,
                'last_error': None
            }

        stats = self._execution_stats[name]
        stats['total_calls'] += 1
        stats['total_duration'] += duration

        if success:
            stats['successful'] += 1
        else:
            stats['failed'] += 1
            stats['last_error'] = error

    def get_registered_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered hooks"""
        return {
            event.value: [
                {
                    'name': hook.name,
                    'priority': hook.priority,
                    'enabled': hook.enabled,
                    'metadata': hook.metadata
                }
                for hook in hooks
            ]
            for event, hooks in self._hooks.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get hook execution statistics"""
        return {
            'enabled': self._enabled,
            'total_hooks': sum(len(hooks) for hooks in self._hooks.values()),
            'hooks_by_event': {
                event.value: len(hooks)
                for event, hooks in self._hooks.items()
            },
            'execution_stats': self._execution_stats
        }

    def enable_all(self):
        """Enable hook system"""
        self._enabled = True
        logger.info("Hooks system enabled")

    def disable_all(self):
        """Disable hook system"""
        self._enabled = False
        logger.info("Hooks system disabled")


# Global hooks manager instance
_hooks_manager: Optional[HooksManager] = None


def get_hooks_manager() -> HooksManager:
    """Get or create the global hooks manager"""
    global _hooks_manager
    if _hooks_manager is None:
        _hooks_manager = HooksManager()
    return _hooks_manager


# Convenience functions for common hook operations
async def trigger_hook(event: Union[HookEvent, str], data: Dict[str, Any] = None, source: str = "system"):
    """Trigger a hook event"""
    return await get_hooks_manager().trigger(event, data, source)


def register_hook(
    event: Union[HookEvent, str],
    callback: Callable[[HookContext], Awaitable[None]],
    name: str = None,
    priority: int = 50
) -> str:
    """Register a hook callback"""
    return get_hooks_manager().register(event, callback, name, priority)


# Decorator for registering hooks
def hook(event: Union[HookEvent, str], name: str = None, priority: int = 50):
    """Decorator for registering hook callbacks"""
    def decorator(func: Callable[[HookContext], Awaitable[None]]):
        register_hook(event, func, name or func.__name__, priority)
        return func
    return decorator
