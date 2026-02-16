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

    _DEFAULT_MAX_ACTIVE = 7

    @staticmethod
    def _genome_get(key: str, default=None):
        """Read a value from the genome, with fallback."""
        try:
            from consciousness.genome_manager import get_genome
            val = get_genome().get(key)
            return val if val is not None else default
        except Exception:
            return default

    @property
    def MAX_ACTIVE(self):
        """Max active interests — genome-driven."""
        return self._genome_get(
            'creativity.exploration.max_active_interests',
            self._DEFAULT_MAX_ACTIVE
        )

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

    def get_stats(self) -> dict:
        """Get interest statistics for Observatory dashboard."""
        active = {}
        total_time = 0.0
        total_disc = 0
        for key, interest in self.active_interests.items():
            active[key] = {
                "topic": interest.topic,
                "depth": interest.depth,
                "enthusiasm": round(interest.enthusiasm, 2),
                "sessions": len(interest.sessions),
                "discoveries": len(interest.discoveries),
                "total_time_minutes": round(interest.total_time_minutes, 1),
                "days_since_explored": round(interest.days_since_explored, 1),
                "age_days": interest.age_days,
            }
            total_time += interest.total_time_minutes
            total_disc += len(interest.discoveries)
        return {
            "active_count": len(self.active_interests),
            "dormant_count": len(self.dormant_interests),
            "total_exploration_minutes": round(total_time, 1),
            "total_discoveries": total_disc,
            "active_interests": active,
            "recent_events": self.interest_history[-5:],
        }

    def _key(self, topic: str) -> str:
        """Normalize topic to key."""
        return topic.lower().strip().replace(" ", "_")

    # Prefixes that indicate a meta/recursive topic
    _META_PREFIXES = [
        "best practices for", "common mistakes in", "future trends in",
        "how to", "introduction to", "improve",
        "real-world applications of", "history and evolution of",
        "open problems in", "surprising connections between",
        "key people and breakthroughs in", "debates and controversies around",
        "how ", " might change in the next decade",
        " in different cultures and contexts",
        " and other fields",
    ]

    # Characters that indicate a garbage topic (code, paths, noise)
    _GARBAGE_CHARS = set('#!{}[]\\<>/=;`$@%^&*\n\t')

    def _is_garbage_topic(self, topic: str) -> bool:
        """Detect topics that are code, file paths, or noise — not real interests."""
        if not topic or len(topic.strip()) < 3:
            return True
        # Contains code/path characters
        if any(c in topic for c in self._GARBAGE_CHARS):
            return True
        # Starts with punctuation or technical markers
        stripped = topic.strip()
        if stripped[0] in '([{#!/-_0123456789':
            return True
        # All uppercase (error codes, constants)
        if stripped.upper() == stripped and len(stripped) > 5:
            return True
        # Contains "Finding:" — operational alert, not a real interest
        if 'finding:' in topic.lower():
            return True
        return False

    def _extract_core_topic(self, topic: str) -> str:
        """Strip known meta-prefixes to get the core subject.

        e.g. "Open problems in Debates around X" → "X"
        """
        lower = topic.lower().strip()
        changed = True
        while changed:
            changed = False
            for prefix in self._META_PREFIXES:
                if lower.startswith(prefix):
                    topic = topic[len(prefix):]
                    lower = topic.lower().strip()
                    changed = True
                elif lower.endswith(prefix):
                    topic = topic[:-len(prefix)]
                    lower = topic.lower().strip()
                    changed = True
        return topic.strip()

    def _word_set(self, text: str) -> set:
        """Extract meaningful words (>3 chars) from text."""
        return {w for w in text.lower().split() if len(w) > 3
                and w not in {'the', 'and', 'for', 'from', 'with', 'that', 'this',
                              'about', 'into', 'como', 'para', 'como', 'entre'}}

    def _are_similar(self, topic_a: str, topic_b: str) -> bool:
        """Check if two topics are semantically similar (would lead to same info)."""
        core_a = self._extract_core_topic(topic_a).lower().strip()
        core_b = self._extract_core_topic(topic_b).lower().strip()

        # Same core after prefix stripping
        if core_a == core_b:
            return True

        # One core is substring of the other
        if core_a and core_b:
            if core_a in core_b or core_b in core_a:
                return True

        # Word overlap > 60%
        words_a = self._word_set(topic_a)
        words_b = self._word_set(topic_b)
        if words_a and words_b:
            overlap = len(words_a & words_b)
            smaller = min(len(words_a), len(words_b))
            if smaller > 0 and overlap / smaller >= 0.6:
                return True

        return False

    def _is_recursive_topic(self, topic: str) -> bool:
        """Detect topics that are recursive prefix chains or garbage."""
        if self._is_garbage_topic(topic):
            return True
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
        # Guard: reject recursive prefix chains and garbage
        if self._is_recursive_topic(topic):
            logger.warning(f"Rejected bad topic: {topic[:80]}...")
            return Interest({"topic": topic, "enthusiasm": 0})

        key = self._key(topic)

        # Already active (exact match)?
        if key in self.active_interests:
            existing = self.active_interests[key]
            existing.enthusiasm = min(1.0, existing.enthusiasm + 0.1)
            self._save()
            return existing

        # Already active (similar to existing)?
        for existing_key, existing in self.active_interests.items():
            if self._are_similar(topic, existing.topic):
                existing.enthusiasm = min(1.0, existing.enthusiasm + 0.05)
                self._save()
                logger.debug(f"Topic '{topic[:40]}' merged into existing '{existing.topic[:40]}'")
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

    def deduplicate(self) -> int:
        """Find and merge similar/duplicate active interests.

        1. Remove garbage topics (code, paths, operational alerts)
        2. Group interests that would lead to the same information
        3. Keep the one with highest depth + sessions, retire the rest

        Returns number of interests removed.
        """
        if len(self.active_interests) <= 1:
            return 0

        total_removed = 0

        # Phase 1: Remove garbage interests that slipped through
        garbage_keys = [
            k for k, interest in list(self.active_interests.items())
            if self._is_garbage_topic(interest.topic)
        ]
        for k in garbage_keys:
            garbage = self.active_interests.pop(k)
            self._log_event(k, "removed_garbage", garbage.topic[:50])
            total_removed += 1
            logger.info(f"Interest removed (garbage): '{garbage.topic[:60]}'")

        # Phase 2: Group similar interests and merge
        if len(self.active_interests) > 1:
            keys = list(self.active_interests.keys())
            topics = {k: self.active_interests[k].topic for k in keys}
            grouped = set()
            groups = []

            for i, k1 in enumerate(keys):
                if k1 in grouped:
                    continue
                group = [k1]
                for k2 in keys[i + 1:]:
                    if k2 in grouped:
                        continue
                    if self._are_similar(topics[k1], topics[k2]):
                        group.append(k2)
                        grouped.add(k2)
                if len(group) > 1:
                    groups.append(group)

            for group in groups:
                # Pick the best interest to keep (highest depth + sessions)
                def score(k):
                    i = self.active_interests[k]
                    return (i.depth, len(i.sessions), i.enthusiasm)

                group.sort(key=score, reverse=True)
                keeper_key = group[0]
                keeper = self.active_interests[keeper_key]

                for dup_key in group[1:]:
                    dup = self.active_interests[dup_key]

                    # Merge data into keeper
                    for disc in dup.discoveries:
                        if disc not in keeper.discoveries:
                            keeper.discoveries.append(disc)
                    for sess in dup.sessions:
                        keeper.sessions.append(sess)
                    keeper.total_time_minutes += dup.total_time_minutes
                    keeper.enthusiasm = max(keeper.enthusiasm, dup.enthusiasm)

                    # Remove duplicate
                    del self.active_interests[dup_key]
                    self._log_event(dup_key, "merged_into", keeper_key)
                    total_removed += 1

                logger.info(
                    f"Interest dedup: kept '{keeper.topic}', merged {len(group) - 1} duplicates"
                )

        if total_removed > 0:
            self._save()
            logger.info(f"Interest dedup complete: {total_removed} removed, {len(self.active_interests)} remaining")

        return total_removed

    def evolve_interests(self):
        """Natural interest evolution — called during sleep transition.

        - Enthusiasm decays for unexplored interests
        - Deep + low enthusiasm → dormant
        - Related topics may spawn new interests
        - Deduplicates similar interests
        """
        # Deduplicate first — before decay calculations
        self.deduplicate()

        to_retire = []

        interest_decay_days = self._genome_get(
            'creativity.exploration.interest_decay_days', 30
        )
        decay_rate = 1.0 / max(1, interest_decay_days)

        for key, interest in self.active_interests.items():
            # Natural enthusiasm decay (genome-driven rate per day)
            decay = interest.days_since_explored * decay_rate
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
