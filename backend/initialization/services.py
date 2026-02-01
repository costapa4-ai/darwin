"""
Service Registry - Provides access to initialized services.

This module allows other parts of the application to access services
that were initialized during startup without circular imports.
"""

from typing import Any, Optional


def get_service(name: str) -> Optional[Any]:
    """Get a registered service by name."""
    try:
        from app.lifespan import get_service as lifespan_get_service
        return lifespan_get_service(name)
    except ImportError:
        return None


def get_consciousness_engine():
    """Get the consciousness engine instance."""
    return get_service('consciousness_engine')


def get_proactive_engine():
    """Get the proactive engine instance."""
    return get_service('proactive_engine')


def get_mood_system():
    """Get the mood system instance."""
    return get_service('mood_system')


def get_diary_engine():
    """Get the diary engine instance."""
    return get_service('diary_engine')
