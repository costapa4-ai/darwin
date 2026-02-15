"""
Darwin's Interest Graph — Genuine curiosity that spans days and weeks.

Replaces random topic selection with deep, evolving interests.
Interests are sparked by experiences, deepened through expeditions,
and naturally fade or spawn connections over time.
"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)


class Interest:
    """A developing interest with depth tracking."""

    def __init__(self, data: Dict = None):
        data = data or {}
        self.topic: str = data.get("topic", "")
        self.depth: int = data.get("depth", 0)  # 0-10
        self.enthusiasm: float = data.get("enthusiasm", 0.7)  # 0-1
        self.sessions: List[Dict] = data.get("sessions", [])
        self.discoveries: List[str] = data.get("discoveries", [])
        self.related_interests: List[str] = data.get("related_interests", [])
        self.sparked_by: str = data.get("sparked_by", "")
        self.last_explored: str = data.get("last_explored", datetime.utcnow().isoformat())
        self.total_time_minutes: float = data.get("total_time_minutes", 0)
        self.created_at: str = data.get("created_at", datetime.utcnow().isoformat()[:10])

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "depth": self.depth,
            "enthusiasm": self.enthusiasm,
            "sessions": self.sessions[-20:],  # Keep last 20 sessions
            "discoveries": self.discoveries[-30:],
            "related_interests": self.related_interests,
            "sparked_by": self.sparked_by,
            "last_explored": self.last_explored,
            "total_time_minutes": self.total_time_minutes,
            "created_at": self.created_at
        }

    @property
    def days_since_explored(self) -> float:
        """Days since last exploration session."""
        try:
            last = datetime.fromisoformat(self.last_explored)
            return (datetime.utcnow() - last).total_seconds() / 86400
        except Exception:
            return 999

    @property
    def age_days(self) -> int:
        """Days since interest was created."""
        try:
            created = datetime.fromisoformat(self.created_at)
            return (datetime.utcnow() - created).days
        except Exception:
            return 0

    @property
    def exploration_score(self) -> float:
        """Score for topic selection: enthusiasm * recency * depth_gap."""
        recency_factor = 1.0 / (1.0 + self.days_since_explored * 0.3)
        depth_gap = max(0, (10 - self.depth) / 10)  # Higher when less explored
        return self.enthusiasm * recency_factor * (0.3 + 0.7 * depth_gap)


class InterestGraph:
    """Manages Darwin's evolving interests and learning journeys."""

    MAX_ACTIVE = 7

    def __init__(self, storage_path: str = "./data/interests/interests.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.active_interests: Dict[str, Interest] = {}
        self.dormant_interests: Dict[str, Interest] = {}
        self.interest_history: List[Dict] = []  # Log of interest lifecycle events

        self._load()

    def _load(self):
        """Load from disk."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for key, idata in data.get("active_interests", {}).items():
                    self.active_interests[key] = Interest(idata)
                for key, idata in data.get("dormant_interests", {}).items():
                    self.dormant_interests[key] = Interest(idata)
                self.interest_history = data.get("interest_history", [])[-100:]
                logger.info(
                    f"InterestGraph loaded: {len(self.active_interests)} active, "
                    f"{len(self.dormant_interests)} dormant"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load InterestGraph: {e}")

        logger.info("InterestGraph initialized (no prior interests — discovery begins)")
        self._save()

    def _save(self):
        """Persist to disk."""
        data = {
            "active_interests": {k: v.to_dict() for k, v in self.active_interests.items()},
            "dormant_interests": {k: v.to_dict() for k, v in self.dormant_interests.items()},
            "interest_history": self.interest_history[-100:],
            "last_updated": datetime.utcnow().isoformat()
        }
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _key(self, topic: str) -> str:
        """Normalize topic to key."""
        return topic.lower().strip().replace(" ", "_")

    # Prefixes that indicate a meta/recursive topic
    _META_PREFIXES = [
        "best practices for", "common mistakes in", "future trends in",
        "how to", "introduction to", "improve",
    ]

    def _is_recursive_topic(self, topic: str) -> bool:
        """Detect topics that are recursive prefix chains."""
        lower = topic.lower().strip()
        # Check if topic contains the same prefix twice (recursive)
        for prefix in self._META_PREFIXES:
            if lower.count(prefix) >= 2:
                return True
        # Reject topics that are too long (sign of prefix accumulation)
        if len(topic) > 100:
            return True
        return False

    def discover_interest(self, topic: str, sparked_by: str, enthusiasm: float = 0.7) -> Interest:
        """Register a new interest sparked by an experience."""
        # Guard: reject recursive prefix chains
        if self._is_recursive_topic(topic):
            logger.warning(f"Rejected recursive topic: {topic[:80]}...")
            return Interest({"topic": topic, "enthusiasm": 0})

        key = self._key(topic)

        # Already active?
        if key in self.active_interests:
            existing = self.active_interests[key]
            existing.enthusiasm = min(1.0, existing.enthusiasm + 0.1)
            self._save()
            return existing

        # Was dormant? Reactivate
        if key in self.dormant_interests:
            interest = self.dormant_interests.pop(key)
            interest.enthusiasm = enthusiasm
            interest.last_explored = datetime.utcnow().isoformat()
            self.active_interests[key] = interest
            self._log_event(key, "reactivated", sparked_by)
            self._save()
            logger.info(f"Interest reactivated: {topic}")
            return interest

        # New interest — make room if needed
        if len(self.active_interests) >= self.MAX_ACTIVE:
            self._retire_least_enthusiastic()

        interest = Interest({
            "topic": topic,
            "depth": 0,
            "enthusiasm": enthusiasm,
            "sparked_by": sparked_by,
            "created_at": datetime.utcnow().isoformat()[:10]
        })
        self.active_interests[key] = interest
        self._log_event(key, "discovered", sparked_by)
        self._save()
        logger.info(f"New interest discovered: {topic} (sparked by: {sparked_by})")
        return interest

    def deepen_interest(self, topic: str, session_data: Dict):
        """Record a learning session that deepens an interest."""
        key = self._key(topic)
        interest = self.active_interests.get(key)
        if not interest:
            # Auto-discover if not tracked
            interest = self.discover_interest(topic, "expedition")

        # Record session
        interest.sessions.append({
            "date": datetime.utcnow().isoformat()[:10],
            "duration_min": session_data.get("duration_min", 10),
            "summary": session_data.get("summary", "")[:200],
            "sources": session_data.get("sources", [])[:5]
        })

        # Update depth based on accumulated learning
        total_sessions = len(interest.sessions)
        interest.depth = min(10, total_sessions // 2)  # Roughly 20 sessions = depth 10

        # Update time tracking
        interest.total_time_minutes += session_data.get("duration_min", 10)
        interest.last_explored = datetime.utcnow().isoformat()

        # Boost enthusiasm slightly after each session
        interest.enthusiasm = min(1.0, interest.enthusiasm + 0.05)

        # Record discoveries
        for disc in session_data.get("discoveries", []):
            if disc not in interest.discoveries:
                interest.discoveries.append(disc)

        # Record related topics
        for related in session_data.get("related_topics", []):
            if related not in interest.related_interests:
                interest.related_interests.append(related)

        self._save()
        logger.info(f"Interest deepened: {topic} (depth={interest.depth}, sessions={total_sessions})")

    def choose_expedition_topic(self) -> Optional[str]:
        """Choose the best topic for next exploration.

        Weighted by: enthusiasm * recency * depth_gap.
        Returns None if no active interests.
        """
        if not self.active_interests:
            return None

        # Score all active interests
        scored = [
            (key, interest, interest.exploration_score)
            for key, interest in self.active_interests.items()
        ]
        scored.sort(key=lambda x: x[2], reverse=True)

        if scored:
            chosen = scored[0]
            logger.info(
                f"Expedition topic chosen: {chosen[1].topic} "
                f"(score={chosen[2]:.2f}, depth={chosen[1].depth}, "
                f"enthusiasm={chosen[1].enthusiasm:.1f})"
            )
            return chosen[1].topic

        return None

    def evolve_interests(self):
        """Natural interest evolution — called during sleep transition.

        - Enthusiasm decays for unexplored interests
        - Deep + low enthusiasm → dormant
        - Related topics may spawn new interests
        """
        to_retire = []

        for key, interest in self.active_interests.items():
            # Natural enthusiasm decay (0.02/day)
            decay = interest.days_since_explored * 0.02
            interest.enthusiasm = max(0.0, interest.enthusiasm - decay)

            # Retire conditions
            if interest.enthusiasm < 0.1 and interest.depth >= 3:
                # Deep enough and lost interest — natural completion
                to_retire.append(key)
                self._log_event(key, "completed", f"depth={interest.depth}")
            elif interest.enthusiasm < 0.05 and interest.days_since_explored > 14:
                # Faded away — no interest
                to_retire.append(key)
                self._log_event(key, "faded", f"days_inactive={interest.days_since_explored:.0f}")

        # Retire interests
        for key in to_retire:
            interest = self.active_interests.pop(key)
            self.dormant_interests[key] = interest
            logger.info(f"Interest retired: {interest.topic} (depth={interest.depth})")

        # Keep dormant list manageable
        if len(self.dormant_interests) > 30:
            # Remove oldest dormant interests
            sorted_dormant = sorted(
                self.dormant_interests.items(),
                key=lambda x: x[1].last_explored
            )
            self.dormant_interests = dict(sorted_dormant[-30:])

        self._save()

    def get_active_summary(self) -> str:
        """Get a formatted summary of active interests for prompt injection."""
        if not self.active_interests:
            return "(Ainda não desenvolvi interesses específicos)"

        lines = []
        sorted_interests = sorted(
            self.active_interests.values(),
            key=lambda i: i.enthusiasm,
            reverse=True
        )
        for interest in sorted_interests[:5]:
            depth_labels = [
                "novo", "superficial", "básico", "em progresso",
                "intermédio", "bom", "avançado", "profundo",
                "expert", "mestre", "completo"
            ]
            depth_label = depth_labels[min(interest.depth, 10)]
            days = interest.age_days
            sessions = len(interest.sessions)
            lines.append(
                f"- {interest.topic}: nível {depth_label} "
                f"({sessions} sessões, {days}d, entusiasmo {interest.enthusiasm:.0%})"
            )

        return "\n".join(lines)

    def _retire_least_enthusiastic(self):
        """Move the least enthusiastic interest to dormant."""
        if not self.active_interests:
            return

        least = min(self.active_interests.items(), key=lambda x: x[1].enthusiasm)
        key, interest = least
        self.dormant_interests[key] = self.active_interests.pop(key)
        self._log_event(key, "retired_for_space", f"enthusiasm={interest.enthusiasm:.2f}")
        logger.info(f"Interest retired to make room: {interest.topic}")

    def _log_event(self, key: str, event_type: str, detail: str = ""):
        """Log an interest lifecycle event."""
        self.interest_history.append({
            "interest": key,
            "event": event_type,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat()
        })
