"""
ActionResult - Standardized result type for Darwin actions.

Provides a consistent interface for action handlers to return results,
replacing ad-hoc Dict[str, Any] returns with explicit success/failure semantics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class ActionStatus(Enum):
    """Status of an action execution"""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ActionResult:
    """
    Standardized result from action execution.

    Usage:
        # Success
        return ActionResult.ok("Analyzed 5 patterns", data={"patterns": patterns})

        # Failure
        return ActionResult.fail("API connection failed", error_type="connection")

        # Skipped
        return ActionResult.skipped("No new data to process")
    """
    success: bool
    status: ActionStatus = ActionStatus.SUCCESS
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[str] = None

    @classmethod
    def ok(cls, message: str = "", data: Optional[Dict[str, Any]] = None) -> "ActionResult":
        """Create a successful result"""
        return cls(
            success=True,
            status=ActionStatus.SUCCESS,
            message=message,
            data=data or {}
        )

    @classmethod
    def fail(cls, error: str, error_type: str = "error", data: Optional[Dict[str, Any]] = None) -> "ActionResult":
        """Create a failed result"""
        return cls(
            success=False,
            status=ActionStatus.FAILED,
            message=error,
            data=data or {},
            error=error,
            error_type=error_type
        )

    @classmethod
    def skipped(cls, reason: str, data: Optional[Dict[str, Any]] = None) -> "ActionResult":
        """Create a skipped result (not a failure, just nothing to do)"""
        return cls(
            success=True,  # Skipped is not a failure
            status=ActionStatus.SKIPPED,
            message=reason,
            data=data or {}
        )

    @classmethod
    def partial(cls, message: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> "ActionResult":
        """Create a partial success result (some items succeeded, some failed)"""
        return cls(
            success=True,  # Partial is still considered success
            status=ActionStatus.PARTIAL,
            message=message,
            data=data or {},
            error=error
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "data": self.data
        }
        if self.error:
            result["error"] = self.error
        if self.error_type:
            result["error_type"] = self.error_type
        return result

    def __bool__(self) -> bool:
        """Allow using ActionResult in boolean context"""
        return self.success
