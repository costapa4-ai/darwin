"""
Findings Inbox - Darwin's Discovery Storage System

Persistent storage for Darwin's proactive discoveries, insights, and observations.
Following the ApprovalQueue pattern from approval_system.py for persistence.

Findings Types:
- DISCOVERY: New projects, files, or patterns found
- INSIGHT: Analysis results and learned patterns
- ANOMALY: System health issues or unusual behavior
- SUGGESTION: Improvement recommendations
- CURIOSITY: Interesting questions or observations
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict, field

from utils.logger import get_logger

logger = get_logger(__name__)


class FindingType(Enum):
    """Types of findings Darwin can generate."""
    DISCOVERY = "discovery"       # New projects, files, patterns
    INSIGHT = "insight"           # Analysis results, learned patterns
    ANOMALY = "anomaly"           # System issues, unusual behavior
    SUGGESTION = "suggestion"     # Improvement recommendations
    CURIOSITY = "curiosity"       # Interesting questions/observations


class FindingPriority(Enum):
    """Priority levels for findings."""
    LOW = 1        # Informational, can wait
    MEDIUM = 2     # Noteworthy, review soon
    HIGH = 3       # Important, review promptly
    URGENT = 4     # Critical, requires attention


@dataclass
class Finding:
    """Represents a discovery or insight from Darwin's proactive exploration."""
    id: str
    type: str  # FindingType value
    title: str
    description: str
    source: str  # Which action/module created this
    priority: str  # FindingPriority value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None  # Auto-cleanup date
    viewed_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Enhanced actionable fields
    impact: Optional[str] = None  # What this means / why it matters
    recommended_actions: List[str] = field(default_factory=list)  # Suggested actions
    resolution_steps: List[str] = field(default_factory=list)  # How to resolve (for issues)
    category: Optional[str] = None  # Sub-category within the type
    related_files: List[str] = field(default_factory=list)  # Relevant file paths
    learn_more: Optional[str] = None  # Additional context or resources

    def is_expired(self) -> bool:
        """Check if finding has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > datetime.fromisoformat(self.expires_at)

    def is_viewed(self) -> bool:
        """Check if finding has been viewed."""
        return self.viewed_at is not None

    def is_dismissed(self) -> bool:
        """Check if finding has been dismissed."""
        return self.dismissed_at is not None

    def is_active(self) -> bool:
        """Check if finding is active (not expired or dismissed)."""
        return not self.is_expired() and not self.is_dismissed()


class FindingsInbox:
    """
    Darwin's Findings Inbox - Persistent storage for discoveries.

    Following the ApprovalQueue pattern from approval_system.py:
    - JSON file-based persistence
    - In-memory list for fast access
    - Auto-save on state changes
    - Auto-cleanup of expired items
    """

    def __init__(self, storage_path: str = "/app/data/findings"):
        """
        Initialize FindingsInbox with storage path.

        Args:
            storage_path: Directory for JSON persistence
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.findings: List[Finding] = []
        self.archived: List[Finding] = []  # Viewed/dismissed findings

        self._load_state()
        logger.info(f"FindingsInbox initialized with {len(self.findings)} active findings")

    def add_finding(
        self,
        type: FindingType,
        title: str,
        description: str,
        source: str,
        priority: FindingPriority = FindingPriority.MEDIUM,
        expires_in_days: int = 7,
        metadata: Optional[Dict[str, Any]] = None,
        impact: Optional[str] = None,
        recommended_actions: Optional[List[str]] = None,
        resolution_steps: Optional[List[str]] = None,
        category: Optional[str] = None,
        related_files: Optional[List[str]] = None,
        learn_more: Optional[str] = None
    ) -> str:
        """
        Add a new finding to the inbox.

        Args:
            type: Type of finding (discovery, insight, etc.)
            title: Short title for the finding
            description: Detailed description
            source: Module/action that created this
            priority: Priority level
            expires_in_days: Days until auto-cleanup (0 = never)
            metadata: Additional data specific to the finding type
            impact: What this means / why it matters
            recommended_actions: List of suggested actions to take
            resolution_steps: Step-by-step guide to resolve issues
            category: Sub-category within the finding type
            related_files: Relevant file paths
            learn_more: Additional context or documentation links

        Returns:
            The ID of the created finding
        """
        finding_id = f"finding_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        expires_at = None
        if expires_in_days > 0:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        finding = Finding(
            id=finding_id,
            type=type.value,
            title=title,
            description=description,
            source=source,
            priority=priority.value,
            expires_at=expires_at,
            metadata=metadata or {},
            impact=impact,
            recommended_actions=recommended_actions or [],
            resolution_steps=resolution_steps or [],
            category=category,
            related_files=related_files or [],
            learn_more=learn_more
        )

        self.findings.append(finding)
        self._save_state()

        logger.info(f"📥 New finding added: {title} ({type.value}) from {source}")

        # Notify via WebSocket (async-safe)
        try:
            import asyncio
            from api.websocket import notify_new_finding
            # Schedule notification without blocking
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(notify_new_finding(asdict(finding)))
        except Exception as e:
            logger.debug(f"Could not send WebSocket notification: {e}")

        return finding_id

    def get_unread(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get unread findings, sorted by priority and date.

        Args:
            limit: Maximum number of findings to return

        Returns:
            List of finding dictionaries
        """
        unread = [f for f in self.findings if f.is_active() and not f.is_viewed()]

        # Sort by priority (descending) then by date (descending)
        unread.sort(
            key=lambda f: (
                -FindingPriority[f.priority.upper()].value if isinstance(f.priority, str) else -f.priority,
                f.created_at
            ),
            reverse=True
        )

        return [asdict(f) for f in unread[:limit]]

    def get_all_active(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all active findings (not dismissed or expired).

        Args:
            limit: Maximum number of findings to return

        Returns:
            List of finding dictionaries
        """
        active = [f for f in self.findings if f.is_active()]

        # Sort by date descending
        active.sort(key=lambda f: f.created_at, reverse=True)

        return [asdict(f) for f in active[:limit]]

    def get_by_type(
        self,
        type: FindingType,
        include_viewed: bool = True,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get findings filtered by type.

        Args:
            type: The finding type to filter by
            include_viewed: Whether to include already viewed findings
            limit: Maximum number to return

        Returns:
            List of finding dictionaries
        """
        filtered = [
            f for f in self.findings
            if f.type == type.value and f.is_active()
            and (include_viewed or not f.is_viewed())
        ]

        filtered.sort(key=lambda f: f.created_at, reverse=True)
        return [asdict(f) for f in filtered[:limit]]

    def get_by_priority(
        self,
        min_priority: FindingPriority = FindingPriority.MEDIUM,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get findings with at least the specified priority.

        Args:
            min_priority: Minimum priority level
            limit: Maximum number to return

        Returns:
            List of finding dictionaries
        """
        filtered = [
            f for f in self.findings
            if f.is_active()
            and (FindingPriority[f.priority.upper()].value if isinstance(f.priority, str) else f.priority) >= min_priority.value
        ]

        # Sort by priority descending, then date descending
        filtered.sort(
            key=lambda f: (
                -(FindingPriority[f.priority.upper()].value if isinstance(f.priority, str) else f.priority),
                f.created_at
            ),
            reverse=True
        )

        return [asdict(f) for f in filtered[:limit]]

    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific finding by ID.

        Args:
            finding_id: The finding ID

        Returns:
            Finding dictionary or None
        """
        for finding in self.findings:
            if finding.id == finding_id:
                return asdict(finding)

        # Check archived
        for finding in self.archived:
            if finding.id == finding_id:
                return asdict(finding)

        return None

    def mark_as_read(self, finding_id: str) -> bool:
        """
        Mark a finding as viewed.

        Args:
            finding_id: The finding ID

        Returns:
            True if successful
        """
        for finding in self.findings:
            if finding.id == finding_id:
                finding.viewed_at = datetime.now().isoformat()
                self._save_state()
                logger.info(f"👁️ Finding marked as read: {finding_id}")
                return True

        return False

    def dismiss(self, finding_id: str) -> bool:
        """
        Dismiss a finding (move to archived).

        Args:
            finding_id: The finding ID

        Returns:
            True if successful
        """
        for finding in self.findings:
            if finding.id == finding_id:
                finding.dismissed_at = datetime.now().isoformat()
                self.findings.remove(finding)
                self.archived.append(finding)
                self._save_state()
                logger.info(f"🗑️ Finding dismissed: {finding_id}")
                return True

        return False

    def auto_cleanup(self, max_age_days: int = 7) -> int:
        """
        Remove expired findings and old archived items.

        Args:
            max_age_days: Maximum age for expired findings

        Returns:
            Number of findings removed
        """
        initial_count = len(self.findings)
        now = datetime.now()
        cutoff = now - timedelta(days=max_age_days)

        # Remove expired findings
        expired = [f for f in self.findings if f.is_expired()]
        for finding in expired:
            self.findings.remove(finding)
            self.archived.append(finding)

        # Trim archived to last 100
        self.archived = self.archived[-100:]

        removed = initial_count - len(self.findings)

        if removed > 0:
            self._save_state()
            logger.info(f"🧹 Cleaned up {removed} expired findings")

        return removed

    def get_statistics(self) -> Dict[str, Any]:
        """Get inbox statistics."""
        active = [f for f in self.findings if f.is_active()]
        unread = [f for f in active if not f.is_viewed()]

        by_type = {}
        by_priority = {}

        for finding in active:
            # Count by type
            by_type[finding.type] = by_type.get(finding.type, 0) + 1

            # Count by priority
            priority_str = finding.priority if isinstance(finding.priority, str) else str(finding.priority)
            by_priority[priority_str] = by_priority.get(priority_str, 0) + 1

        return {
            "total_active": len(active),
            "total_unread": len(unread),
            "total_archived": len(self.archived),
            "by_type": by_type,
            "by_priority": by_priority,
            "oldest_active": active[-1].created_at if active else None,
            "newest_active": active[0].created_at if active else None
        }

    def get_unread_count(self) -> int:
        """Get count of unread findings."""
        return len([f for f in self.findings if f.is_active() and not f.is_viewed()])

    def _save_state(self):
        """Persist inbox state to disk."""
        try:
            state = {
                "findings": [asdict(f) for f in self.findings],
                "archived": [asdict(f) for f in self.archived[-100:]],  # Keep last 100
                "saved_at": datetime.now().isoformat()
            }

            state_file = self.storage_path / "findings_inbox.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"❌ Failed to save findings inbox state: {e}")

    def _load_state(self):
        """Load inbox state from disk."""
        try:
            state_file = self.storage_path / "findings_inbox.json"

            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                self.findings = [
                    Finding(**f) for f in state.get('findings', [])
                ]
                self.archived = [
                    Finding(**f) for f in state.get('archived', [])
                ]

                logger.info(f"📥 Loaded {len(self.findings)} findings, {len(self.archived)} archived")

                # Auto-cleanup on load
                self.auto_cleanup()

        except Exception as e:
            logger.error(f"⚠️ Failed to load findings inbox state: {e}")
            self.findings = []
            self.archived = []


# Global instance
_findings_inbox: Optional[FindingsInbox] = None


def get_findings_inbox() -> FindingsInbox:
    """Get or create the findings inbox instance."""
    global _findings_inbox
    if _findings_inbox is None:
        _findings_inbox = FindingsInbox()
    return _findings_inbox


def set_findings_inbox(inbox: FindingsInbox):
    """Set the global findings inbox instance."""
    global _findings_inbox
    _findings_inbox = inbox
