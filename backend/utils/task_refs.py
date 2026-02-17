"""
Safe asyncio task creation with reference storage.

Prevents garbage collection of fire-and-forget tasks.
"""

import asyncio
from typing import Set

# Module-level set keeps strong references to running tasks
_background_tasks: Set[asyncio.Task] = set()


def create_safe_task(coro, *, name: str = None) -> asyncio.Task:
    """
    Create an asyncio task with automatic reference management.

    The task reference is stored in a module-level set to prevent
    garbage collection before completion. The reference is automatically
    removed when the task finishes.

    Args:
        coro: Coroutine to schedule
        name: Optional name for the task (for debugging)

    Returns:
        The created asyncio.Task
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
