"""
Consciousness Models - Data structures for Darwin's consciousness system.

This module contains the core data models used throughout the consciousness engine.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


class ConsciousnessState(Enum):
    """Darwin's consciousness states"""
    WAKE = "wake"
    SLEEP = "sleep"
    TRANSITION = "transition"


@dataclass
class Activity:
    """An activity Darwin performs while awake"""
    type: str  # 'code_optimization', 'tool_creation', 'idea_implementation', 'curiosity_share'
    description: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict] = None
    insights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type,
            "description": self.description,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "insights": self.insights
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Activity":
        """Create from dictionary."""
        return cls(
            type=data["type"],
            description=data["description"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result"),
            insights=data.get("insights", [])
        )


@dataclass
class CuriosityMoment:
    """A curiosity moment Darwin shares while awake"""
    topic: str
    fact: str
    source: str
    significance: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "topic": self.topic,
            "fact": self.fact,
            "source": self.source,
            "significance": self.significance,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CuriosityMoment":
        """Create from dictionary."""
        return cls(
            topic=data["topic"],
            fact=data["fact"],
            source=data["source"],
            significance=data.get("significance", ""),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class Dream:
    """A research dream Darwin has during sleep"""
    topic: str
    description: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    insights: List[str] = field(default_factory=list)
    exploration_details: Optional[Dict[str, Any]] = None  # URLs, repos, files explored

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "topic": self.topic,
            "description": self.description,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "insights": self.insights,
            "exploration_details": self.exploration_details
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dream":
        """Create from dictionary."""
        return cls(
            topic=data["topic"],
            description=data["description"],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            success=data.get("success", False),
            insights=data.get("insights", []),
            exploration_details=data.get("exploration_details")
        )


# Activity type constants
class ActivityType:
    """Constants for activity types."""
    CODE_OPTIMIZATION = "code_optimization"
    TOOL_CREATION = "tool_creation"
    IDEA_IMPLEMENTATION = "idea_implementation"
    CURIOSITY_SHARE = "curiosity_share"
    POETRY = "poetry"
    SELF_IMPROVEMENT = "self_improvement"
    APPLY_CHANGES = "apply_changes"


# Default cycle durations
DEFAULT_WAKE_DURATION_MINUTES = 120  # 2 hours
DEFAULT_SLEEP_DURATION_MINUTES = 30  # 30 minutes
