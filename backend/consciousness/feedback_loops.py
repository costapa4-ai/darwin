"""
Feedback Loops Manager - Connecting Darwin's Curiosity Systems

Bridges isolated curiosity systems (Moltbook, Findings, CuriosityEngine, MetaLearner)
into a cohesive learning ecosystem that feeds into the expedition queue.

Architecture:
    Moltbook Posts ──┐
    Findings ────────┼──> FeedbackLoopManager ──> Expedition Queue
    CuriosityEngine ─┘           │
                                 └──> Priority Boost (from meta-learner)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackSource(Enum):
    """Sources that can contribute topics to the expedition queue"""
    MOLTBOOK = "moltbook"
    FINDINGS = "findings"
    META_LEARNER = "meta_learner"
    CURIOSITY_ENGINE = "curiosity_engine"
    CHAT = "chat"
    EXPEDITION = "expedition"


@dataclass
class SourceConfig:
    """Configuration for a feedback source"""
    enabled: bool = True
    base_priority: int = 5
    cooldown_minutes: int = 5
    max_contributions_per_hour: int = 10


@dataclass
class Contribution:
    """Record of a topic contribution"""
    source: FeedbackSource
    topic: str
    question: str
    priority: int
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackLoopManager:
    """
    Connects Darwin's isolated curiosity systems into a cohesive learning ecosystem.

    Features:
    - Rate limiting per source
    - Cooldown between contributions from same source
    - Deduplication of recent topics
    - Priority boosting based on learning effectiveness
    - Hook integration for Findings and Expeditions
    """

    # Default configuration per source
    DEFAULT_CONFIGS = {
        FeedbackSource.MOLTBOOK: SourceConfig(
            enabled=True,
            base_priority=5,
            cooldown_minutes=10,
            max_contributions_per_hour=6
        ),
        FeedbackSource.FINDINGS: SourceConfig(
            enabled=True,
            base_priority=7,
            cooldown_minutes=1,
            max_contributions_per_hour=20
        ),
        FeedbackSource.META_LEARNER: SourceConfig(
            enabled=True,
            base_priority=6,
            cooldown_minutes=5,
            max_contributions_per_hour=10
        ),
        FeedbackSource.CURIOSITY_ENGINE: SourceConfig(
            enabled=True,
            base_priority=6,
            cooldown_minutes=5,
            max_contributions_per_hour=10
        ),
        FeedbackSource.CHAT: SourceConfig(
            enabled=False,  # Opt-in
            base_priority=4,
            cooldown_minutes=5,
            max_contributions_per_hour=5
        ),
        FeedbackSource.EXPEDITION: SourceConfig(
            enabled=True,
            base_priority=4,
            cooldown_minutes=2,
            max_contributions_per_hour=15
        ),
    }

    def __init__(
        self,
        expedition_engine=None,
        findings_inbox=None,
        meta_learner=None,
        hooks_manager=None,
        activity_monitor=None
    ):
        """
        Initialize the FeedbackLoopManager.

        Args:
            expedition_engine: CuriosityExpeditions instance for queueing topics
            findings_inbox: FindingsInbox for receiving high-priority findings
            meta_learner: MetaLearner for effectiveness tracking
            hooks_manager: HooksManager for event integration
            activity_monitor: ActivityMonitor for logging actions
        """
        self.expedition_engine = expedition_engine
        self.findings_inbox = findings_inbox
        self.meta_learner = meta_learner
        self.hooks_manager = hooks_manager
        self.activity_monitor = activity_monitor

        # Per-source configuration
        self.configs: Dict[FeedbackSource, SourceConfig] = {
            source: SourceConfig(
                enabled=cfg.enabled,
                base_priority=cfg.base_priority,
                cooldown_minutes=cfg.cooldown_minutes,
                max_contributions_per_hour=cfg.max_contributions_per_hour
            )
            for source, cfg in self.DEFAULT_CONFIGS.items()
        }

        # Per-source statistics
        self.stats: Dict[FeedbackSource, Dict[str, Any]] = {
            source: {
                "total_contributions": 0,
                "accepted": 0,
                "rejected_rate_limit": 0,
                "rejected_cooldown": 0,
                "rejected_duplicate": 0,
                "last_contribution": None
            }
            for source in FeedbackSource
        }

        # Recent contributions for deduplication (last 50)
        self.recent_contributions: deque = deque(maxlen=50)

        # Topic effectiveness scores from meta-learner (topic -> score)
        # Topics with effectiveness > 0.7 get +2 priority boost
        self.topic_effectiveness: Dict[str, float] = {}

        # Hourly contribution tracking per source
        self._hourly_counts: Dict[FeedbackSource, List[datetime]] = {
            source: [] for source in FeedbackSource
        }

        self._initialized = False
        logger.info("FeedbackLoopManager created")

    async def initialize(self):
        """Initialize hooks and integrations"""
        if self._initialized:
            return

        if self.hooks_manager:
            from consciousness.hooks import HookEvent

            # ON_FINDING -> Queue HIGH/URGENT findings for investigation
            self.hooks_manager.register(
                HookEvent.ON_FINDING,
                self._on_finding_hook,
                name="feedback_on_finding",
                priority=40
            )
            logger.info("Registered ON_FINDING hook for feedback loops")

            # ON_EXPEDITION_COMPLETE -> Queue related topics, update effectiveness
            self.hooks_manager.register(
                HookEvent.ON_EXPEDITION_COMPLETE,
                self._on_expedition_complete_hook,
                name="feedback_on_expedition_complete",
                priority=50
            )
            logger.info("Registered ON_EXPEDITION_COMPLETE hook for feedback loops")

            # ON_LEARNING -> Refresh effectiveness scores from meta-learner
            self.hooks_manager.register(
                HookEvent.ON_LEARNING,
                self._on_learning_hook,
                name="feedback_on_learning",
                priority=30
            )
            logger.info("Registered ON_LEARNING hook for feedback loops")

        self._initialized = True
        logger.info("FeedbackLoopManager initialized with hooks")

    async def contribute_topic(
        self,
        source: FeedbackSource,
        topic: str,
        question: str,
        priority_override: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Contribute a topic to the expedition queue.

        Args:
            source: Which system is contributing
            topic: Topic name for the expedition
            question: Specific question to explore
            priority_override: Override the source's base priority
            metadata: Additional metadata about the contribution

        Returns:
            True if topic was queued, False if rejected
        """
        if not self.expedition_engine:
            logger.warning("Cannot contribute topic: expedition_engine not available")
            return False

        config = self.configs.get(source)
        if not config or not config.enabled:
            logger.debug(f"Source {source.value} is disabled")
            return False

        stats = self.stats[source]
        now = datetime.utcnow()

        # Check rate limit
        if not self._check_rate_limit(source, now):
            stats["rejected_rate_limit"] += 1
            logger.debug(f"Rate limit exceeded for {source.value}")
            return False

        # Check cooldown
        if not self._check_cooldown(source, now):
            stats["rejected_cooldown"] += 1
            logger.debug(f"Cooldown active for {source.value}")
            return False

        # Check for duplicates
        if self._is_duplicate(topic, question):
            stats["rejected_duplicate"] += 1
            logger.debug(f"Duplicate topic rejected: {topic}")
            return False

        # Calculate priority
        base_priority = priority_override if priority_override is not None else config.base_priority
        priority = self._calculate_priority(topic, base_priority)

        # Add to expedition queue
        try:
            self.expedition_engine.add_to_queue(
                topic=topic,
                question=question,
                priority=priority,
                source=source.value
            )

            # Record contribution
            contribution = Contribution(
                source=source,
                topic=topic,
                question=question,
                priority=priority,
                timestamp=now,
                metadata=metadata or {}
            )
            self.recent_contributions.append(contribution)
            self._hourly_counts[source].append(now)

            # Update stats
            stats["total_contributions"] += 1
            stats["accepted"] += 1
            stats["last_contribution"] = now.isoformat()

            # Log activity
            if self.activity_monitor:
                from consciousness.activity_monitor import ActivityCategory, ActivityStatus
                self.activity_monitor.log_activity(
                    category=ActivityCategory.SYSTEM,
                    action="feedback_contribution",
                    description=f"Queued topic from {source.value}: {topic[:50]}",
                    status=ActivityStatus.SUCCESS,
                    details={
                        "source": source.value,
                        "topic": topic,
                        "priority": priority,
                        "question": question[:100]
                    }
                )

            logger.info(f"Topic contributed from {source.value}: {topic} (priority={priority})")
            return True

        except Exception as e:
            logger.error(f"Failed to contribute topic: {e}")
            return False

    async def process_moltbook_post(
        self,
        post: Dict[str, Any],
        analysis: str
    ) -> bool:
        """
        Process a Moltbook post and potentially queue it for expedition.

        Args:
            post: Post data with id, title, content, tags
            analysis: Darwin's analysis/thought about the post

        Returns:
            True if a topic was queued
        """
        if not post or not analysis:
            return False

        title = post.get("title", "")
        content = post.get("content", "")
        tags = post.get("tags", [])

        # Extract topic and question from the post
        # Use the first tag or extract from title
        if tags:
            topic = f"Moltbook: {tags[0]}"
        else:
            # Extract topic from title (first few words)
            words = title.split()[:4]
            topic = f"Moltbook: {' '.join(words)}"

        # Generate a question based on the post
        question = self._generate_question_from_post(title, content, analysis)

        if not question:
            return False

        return await self.contribute_topic(
            source=FeedbackSource.MOLTBOOK,
            topic=topic,
            question=question,
            metadata={
                "post_id": post.get("id"),
                "post_title": title,
                "analysis_preview": analysis[:200] if analysis else ""
            }
        )

    async def process_anomaly_questions(
        self,
        questions: List[str],
        anomaly_data: Dict[str, Any]
    ) -> int:
        """
        Process questions generated by CuriosityEngine from anomalies.

        Args:
            questions: List of questions to explore
            anomaly_data: Context about the anomaly

        Returns:
            Number of topics successfully queued
        """
        queued = 0

        for question in questions[:3]:  # Limit to 3 per anomaly
            topic = f"Anomaly: {anomaly_data.get('type', 'Unknown')}"

            success = await self.contribute_topic(
                source=FeedbackSource.CURIOSITY_ENGINE,
                topic=topic,
                question=question,
                metadata={
                    "anomaly_type": anomaly_data.get("type"),
                    "anomaly_severity": anomaly_data.get("severity")
                }
            )

            if success:
                queued += 1

        return queued

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about feedback loop activity"""
        return {
            "total_queued": sum(s["accepted"] for s in self.stats.values()),
            "by_source": {
                source.value: {
                    **stats,
                    "config": {
                        "enabled": self.configs[source].enabled,
                        "base_priority": self.configs[source].base_priority,
                        "cooldown_minutes": self.configs[source].cooldown_minutes,
                        "max_per_hour": self.configs[source].max_contributions_per_hour
                    }
                }
                for source, stats in self.stats.items()
            },
            "recent_topics": [
                {
                    "source": c.source.value,
                    "topic": c.topic,
                    "priority": c.priority,
                    "timestamp": c.timestamp.isoformat()
                }
                for c in list(self.recent_contributions)[-10:]
            ],
            "topic_effectiveness_cache_size": len(self.topic_effectiveness),
            "initialized": self._initialized
        }

    # --- Hook Callbacks ---

    async def _on_finding_hook(self, context):
        """
        Hook callback for ON_FINDING events.

        Queues HIGH and URGENT findings for investigation.
        """
        data = context.data
        finding = data.get("finding", {})

        priority_str = finding.get("priority", "medium")

        # Only process HIGH and URGENT findings
        if priority_str not in ["high", "urgent", "HIGH", "URGENT", "3", "4"]:
            return

        title = finding.get("title", "Unknown Finding")
        description = finding.get("description", "")
        finding_type = finding.get("type", "finding")

        # Calculate priority: HIGH=7, URGENT=9
        if priority_str in ["urgent", "URGENT", "4"]:
            priority = 9
        else:
            priority = 7

        question = f"Investigate: {title}. What caused this {finding_type}?"
        if description:
            question += f" Context: {description[:100]}"

        await self.contribute_topic(
            source=FeedbackSource.FINDINGS,
            topic=f"Finding: {title[:50]}",
            question=question,
            priority_override=priority,
            metadata={
                "finding_id": finding.get("id"),
                "finding_type": finding_type,
                "original_priority": priority_str
            }
        )

    async def _on_expedition_complete_hook(self, context):
        """
        Hook callback for ON_EXPEDITION_COMPLETE events.

        Updates topic effectiveness and queues related topics.
        """
        data = context.data
        expedition = data.get("expedition", {})

        topic = expedition.get("topic", "")
        success = expedition.get("success", False)
        related_topics = expedition.get("related_topics", [])

        # Update topic effectiveness
        effectiveness = 1.0 if success else 0.3
        self.topic_effectiveness[topic] = effectiveness

        # Also update related topic categories
        topic_lower = topic.lower()
        for keyword in ["quantum", "machine learning", "distributed", "security", "api", "database"]:
            if keyword in topic_lower:
                self.topic_effectiveness[keyword] = (
                    self.topic_effectiveness.get(keyword, 0.5) * 0.7 + effectiveness * 0.3
                )

        # Queue related topics with lower priority
        for related in related_topics[:3]:
            await self.contribute_topic(
                source=FeedbackSource.EXPEDITION,
                topic=related,
                question=f"Following up from {topic}: What should I know about {related}?",
                priority_override=4,  # Lower priority for follow-ups
                metadata={
                    "parent_expedition": expedition.get("id"),
                    "parent_topic": topic
                }
            )

    async def _on_learning_hook(self, context):
        """
        Hook callback for ON_LEARNING events.

        Refreshes topic effectiveness scores from meta-learner.
        """
        if not self.meta_learner:
            return

        try:
            # Get learning analytics from meta-learner
            if hasattr(self.meta_learner, 'get_learning_analytics'):
                analytics = await self.meta_learner.get_learning_analytics()

                # Update effectiveness for topics based on quality scores
                topic_quality = analytics.get("topic_quality", {})
                for topic, quality in topic_quality.items():
                    self.topic_effectiveness[topic] = quality

        except Exception as e:
            logger.debug(f"Could not refresh effectiveness from meta-learner: {e}")

    # --- Private Helper Methods ---

    def _check_rate_limit(self, source: FeedbackSource, now: datetime) -> bool:
        """Check if source has exceeded hourly rate limit"""
        config = self.configs[source]

        # Clean old entries
        one_hour_ago = now - timedelta(hours=1)
        self._hourly_counts[source] = [
            t for t in self._hourly_counts[source]
            if t > one_hour_ago
        ]

        return len(self._hourly_counts[source]) < config.max_contributions_per_hour

    def _check_cooldown(self, source: FeedbackSource, now: datetime) -> bool:
        """Check if source is still in cooldown"""
        config = self.configs[source]
        stats = self.stats[source]

        last = stats.get("last_contribution")
        if not last:
            return True

        try:
            last_time = datetime.fromisoformat(last)
            cooldown_end = last_time + timedelta(minutes=config.cooldown_minutes)
            return now >= cooldown_end
        except (ValueError, TypeError):
            return True

    def _is_duplicate(self, topic: str, question: str) -> bool:
        """Check if this topic/question is a duplicate of recent contributions"""
        topic_lower = topic.lower()
        question_lower = question.lower()

        for contrib in self.recent_contributions:
            # Check for similar topic
            if topic_lower == contrib.topic.lower():
                return True

            # Check for similar question (simple word overlap)
            contrib_words = set(contrib.question.lower().split())
            question_words = set(question_lower.split())
            overlap = len(contrib_words & question_words)
            similarity = overlap / max(len(contrib_words), len(question_words), 1)

            if similarity > 0.7:
                return True

        return False

    def _calculate_priority(self, topic: str, base_priority: int) -> int:
        """Calculate final priority with effectiveness boost"""
        priority = base_priority

        # Check if this topic has high effectiveness
        topic_lower = topic.lower()

        # Direct match
        if topic in self.topic_effectiveness:
            if self.topic_effectiveness[topic] > 0.7:
                priority += 2

        # Keyword match
        for keyword, effectiveness in self.topic_effectiveness.items():
            if keyword.lower() in topic_lower and effectiveness > 0.7:
                priority += 1
                break

        return min(10, priority)  # Cap at 10

    def _generate_question_from_post(
        self,
        title: str,
        content: str,
        analysis: str
    ) -> Optional[str]:
        """Generate an exploratory question from a Moltbook post"""
        if not title:
            return None

        # Simple question generation based on post content
        questions = []

        # Check for question-like titles
        if "?" in title:
            questions.append(title)

        # Generate based on keywords
        keywords = ["how", "why", "what", "when", "where", "should", "can", "will"]
        title_lower = title.lower()

        for keyword in keywords:
            if keyword in title_lower:
                questions.append(f"Explore: {title}")
                break

        # If analysis contains questions, use those
        if analysis and "?" in analysis:
            # Extract the first question from analysis
            for sentence in analysis.split("."):
                if "?" in sentence:
                    questions.append(sentence.strip())
                    break

        # Default: turn title into a question
        if not questions:
            questions.append(f"What can I learn about: {title}?")

        return questions[0] if questions else None

    def configure_source(
        self,
        source: FeedbackSource,
        enabled: Optional[bool] = None,
        base_priority: Optional[int] = None,
        cooldown_minutes: Optional[int] = None,
        max_per_hour: Optional[int] = None
    ):
        """Configure a feedback source at runtime"""
        config = self.configs[source]

        if enabled is not None:
            config.enabled = enabled
        if base_priority is not None:
            config.base_priority = base_priority
        if cooldown_minutes is not None:
            config.cooldown_minutes = cooldown_minutes
        if max_per_hour is not None:
            config.max_contributions_per_hour = max_per_hour

        logger.info(f"Updated config for {source.value}: {config}")


# Global instance
_feedback_manager: Optional[FeedbackLoopManager] = None


def get_feedback_manager() -> Optional[FeedbackLoopManager]:
    """Get the global FeedbackLoopManager instance"""
    return _feedback_manager


def init_feedback_manager(
    expedition_engine=None,
    findings_inbox=None,
    meta_learner=None,
    hooks_manager=None,
    activity_monitor=None
) -> FeedbackLoopManager:
    """Initialize the global FeedbackLoopManager"""
    global _feedback_manager

    _feedback_manager = FeedbackLoopManager(
        expedition_engine=expedition_engine,
        findings_inbox=findings_inbox,
        meta_learner=meta_learner,
        hooks_manager=hooks_manager,
        activity_monitor=activity_monitor
    )

    return _feedback_manager
