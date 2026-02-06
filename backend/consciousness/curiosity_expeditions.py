"""
Curiosity Expeditions - Darwin's Autonomous Web Adventures

Darwin embarks on scheduled web research expeditions, exploring topics
that pique his curiosity and generating detailed trip reports.
"""
import asyncio
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import random

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExpeditionLog:
    """A record of a curiosity expedition"""
    id: str
    topic: str
    question: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: float = 0
    sources_explored: List[str] = field(default_factory=list)
    discoveries: List[Dict[str, str]] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    related_topics: List[str] = field(default_factory=list)
    mood_before: Optional[str] = None
    mood_after: Optional[str] = None
    success: bool = False
    summary: str = ""

    def to_markdown(self) -> str:
        """Convert expedition log to markdown format"""
        started = self.started_at.strftime("%Y-%m-%d %H:%M UTC")
        completed = self.completed_at.strftime("%H:%M UTC") if self.completed_at else "In Progress"

        md = f"""# Expedition Log: {self.topic}

**ID:** {self.id}
**Started:** {started}
**Completed:** {completed}
**Duration:** {self.duration_minutes:.1f} minutes
**Success:** {'Yes' if self.success else 'No'}

## The Question

> {self.question}

## Journey Summary

{self.summary}

## Sources Explored

"""
        for source in self.sources_explored:
            md += f"- {source}\n"

        md += "\n## Discoveries\n\n"
        for discovery in self.discoveries:
            significance = discovery.get('significance', 'medium')
            marker = "!" if significance == "high" else "-"
            md += f"{marker} **{discovery.get('title', 'Untitled')}**: {discovery.get('content', '')}\n\n"

        md += "## Key Insights\n\n"
        for insight in self.insights:
            md += f"- {insight}\n"

        if self.related_topics:
            md += "\n## Rabbit Holes for Future Expeditions\n\n"
            for topic in self.related_topics:
                md += f"- {topic}\n"

        md += f"""
---

*Mood before: {self.mood_before or 'unknown'} | Mood after: {self.mood_after or 'unknown'}*
"""
        return md


class CuriosityExpeditions:
    """
    Manages Darwin's curiosity-driven web expeditions.

    Features:
    - Topic queue management
    - Scheduled expedition execution
    - Trip report generation
    - Discovery archival
    """

    def __init__(
        self,
        expeditions_dir: str = "./data/expeditions",
        web_researcher=None,
        semantic_memory=None,
        mood_system=None,
        websocket_manager=None,
        diary_engine=None,
        meta_learner=None
    ):
        """
        Initialize the curiosity expeditions system.

        Args:
            expeditions_dir: Directory to store expedition logs
            web_researcher: Web research capability
            semantic_memory: Memory system for storing learnings
            mood_system: Mood system for tracking emotional state
            websocket_manager: For broadcasting discoveries
            diary_engine: For recording learnings
            meta_learner: Meta-learning system for tracking learning sessions
        """
        self.expeditions_dir = Path(expeditions_dir)
        self.expeditions_dir.mkdir(parents=True, exist_ok=True)

        self.web_researcher = web_researcher
        self.semantic_memory = semantic_memory
        self.mood_system = mood_system
        self.websocket_manager = websocket_manager
        self.diary_engine = diary_engine
        self.meta_learner = meta_learner
        self.channel_gateway = None  # Set by initialization if channels enabled

        # Curiosity queue
        self.topic_queue: List[Dict[str, Any]] = []
        self.completed_expeditions: List[str] = []  # IDs of completed expeditions
        self.max_queue_size = 50
        self.max_completed_history = 100

        # Expedition settings
        self.min_expedition_duration = 5  # minutes
        self.max_expedition_duration = 15  # minutes
        self.expedition_cooldown = 60  # minutes between expeditions

        self.last_expedition_time: Optional[datetime] = None
        self.current_expedition: Optional[ExpeditionLog] = None

        # Dynamic topic generation - no hardcoded topics
        # Topics are generated from Darwin's knowledge sources or AI
        self._recent_generated_topics: List[str] = []

        logger.info(f"CuriosityExpeditions initialized: {self.expeditions_dir}")

    def add_to_queue(self, topic: str, question: str, priority: int = 5, source: str = "internal") -> bool:
        """
        Add a topic to the curiosity queue.

        Args:
            topic: Topic name
            question: Specific question to explore
            priority: 1-10 (10 = highest priority)
            source: Where the curiosity came from

        Returns:
            True if added successfully
        """
        if len(self.topic_queue) >= self.max_queue_size:
            # Remove lowest priority item
            self.topic_queue.sort(key=lambda x: x.get('priority', 5))
            self.topic_queue.pop(0)

        entry = {
            'topic': topic,
            'question': question,
            'priority': min(10, max(1, priority)),
            'source': source,
            'added_at': datetime.utcnow().isoformat()
        }

        self.topic_queue.append(entry)
        self.topic_queue.sort(key=lambda x: x.get('priority', 5), reverse=True)

        logger.info(f"Added to curiosity queue: {topic} (priority {priority})")
        return True

    def get_next_topic(self) -> Optional[Dict[str, Any]]:
        """Get the next topic to explore"""
        if self.topic_queue:
            return self.topic_queue.pop(0)

        # Queue is empty - generate a topic dynamically from Darwin's knowledge
        return self._generate_dynamic_topic()

    def _generate_dynamic_topic(self) -> Optional[Dict[str, Any]]:
        """
        Generate a curiosity topic dynamically from Darwin's knowledge sources.
        No hardcoded topics - pure learning and exploration.
        """
        try:
            # Try to get a topic from findings inbox (curiosity questions)
            from consciousness.findings_inbox import get_findings_inbox, FindingType
            inbox = get_findings_inbox()
            if inbox:
                curiosity_findings = inbox.get_by_type(FindingType.CURIOSITY, include_viewed=True, limit=10)
                # Find one we haven't explored recently
                for finding in curiosity_findings:
                    question = finding.get('description', '')
                    topic = finding.get('title', 'Curiosity')
                    if question and topic not in self._recent_generated_topics[-20:]:
                        self._recent_generated_topics.append(topic)
                        return {"topic": topic, "question": question, "source": "findings"}

            # Try to get a topic from meta-learner (weak areas to improve)
            if self.meta_learner and hasattr(self.meta_learner, 'get_learning_summary'):
                summary = self.meta_learner.get_learning_summary()
                weak_areas = summary.get('weak_areas', [])
                for area in weak_areas:
                    area_name = area.get('area', '') if isinstance(area, dict) else str(area)
                    if area_name and area_name not in self._recent_generated_topics[-20:]:
                        self._recent_generated_topics.append(area_name)
                        return {
                            "topic": f"Improve {area_name}",
                            "question": f"How can I get better at {area_name}?",
                            "source": "meta_learner"
                        }

            # Generate a novel topic using AI
            if hasattr(self, 'ai_router') and self.ai_router:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Already in async context, can't await here
                    # Return None and let the caller handle it
                    pass

            # If all sources exhausted, return a self-reflection topic
            return {
                "topic": "Self-Improvement",
                "question": "What could I learn next to become more capable?",
                "source": "self_reflection"
            }

        except Exception as e:
            logger.debug(f"Could not generate dynamic topic: {e}")
            return {
                "topic": "Exploration",
                "question": "What interesting topics exist that I haven't explored yet?",
                "source": "fallback"
            }

    def can_start_expedition(self) -> bool:
        """Check if we can start a new expedition"""
        if self.current_expedition:
            return False

        if self.last_expedition_time:
            cooldown_end = self.last_expedition_time + timedelta(minutes=self.expedition_cooldown)
            if datetime.utcnow() < cooldown_end:
                return False

        return True

    async def start_expedition(self, topic_entry: Optional[Dict] = None) -> Optional[ExpeditionLog]:
        """
        Start a curiosity expedition.

        Args:
            topic_entry: Optional specific topic (otherwise picks from queue)

        Returns:
            ExpeditionLog if started successfully
        """
        if not self.can_start_expedition():
            return None

        if topic_entry is None:
            topic_entry = self.get_next_topic()

        if not topic_entry:
            logger.warning("No topics available for expedition")
            return None

        # Create expedition log
        expedition_id = f"exp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.current_expedition = ExpeditionLog(
            id=expedition_id,
            topic=topic_entry['topic'],
            question=topic_entry['question'],
            started_at=datetime.utcnow(),
            mood_before=self.mood_system.current_mood.value if self.mood_system else None
        )

        logger.info(f"Starting expedition: {topic_entry['topic']}")

        # Broadcast start
        if self.websocket_manager:
            await self.websocket_manager.broadcast({
                'type': 'expedition_start',
                'id': expedition_id,
                'topic': topic_entry['topic'],
                'question': topic_entry['question'],
                'timestamp': datetime.utcnow().isoformat()
            })

        return self.current_expedition

    async def conduct_expedition(self) -> Optional[ExpeditionLog]:
        """
        Conduct the current expedition.

        This is the main expedition logic that does web research
        and gathers discoveries.

        Returns:
            Completed ExpeditionLog or None
        """
        if not self.current_expedition:
            return None

        expedition = self.current_expedition
        start_time = datetime.utcnow()

        try:
            # Phase 1: Primary research
            if self.web_researcher:
                try:
                    search_result = await self.web_researcher.research(
                        query=expedition.question,
                        max_results=5
                    )

                    if search_result.get('success'):
                        expedition.sources_explored.extend(
                            search_result.get('sources', [])[:5]
                        )

                        # Extract discoveries from research
                        findings = search_result.get('findings', [])
                        for finding in findings[:5]:
                            expedition.discoveries.append({
                                'title': finding.get('title', 'Finding'),
                                'content': finding.get('summary', finding.get('content', ''))[:500],
                                'significance': 'medium'
                            })

                        # Extract insights
                        if search_result.get('synthesis'):
                            expedition.insights.append(search_result['synthesis'][:300])

                except Exception as e:
                    logger.error(f"Web research failed: {e}")
                    expedition.insights.append(f"Research encountered an issue: {str(e)[:100]}")

            # Phase 2: Follow-up questions (simulated depth)
            await asyncio.sleep(2)  # Simulate thinking time

            # Generate related topics for future exploration
            expedition.related_topics = self._generate_related_topics(expedition.topic)

            # Phase 3: Synthesize findings
            expedition.summary = self._generate_summary(expedition)

            # Mark success if we found anything
            expedition.success = len(expedition.discoveries) > 0 or len(expedition.insights) > 0

        except Exception as e:
            logger.error(f"Expedition error: {e}")
            expedition.insights.append(f"Expedition encountered challenges: {str(e)[:100]}")

        finally:
            # Complete the expedition
            expedition.completed_at = datetime.utcnow()
            expedition.duration_minutes = (expedition.completed_at - expedition.started_at).total_seconds() / 60
            expedition.mood_after = self.mood_system.current_mood.value if self.mood_system else None

            # Save expedition log
            await self._save_expedition(expedition)

            # Record to diary
            if self.diary_engine and expedition.success:
                for discovery in expedition.discoveries[:3]:
                    self.diary_engine.add_discovery(
                        f"{expedition.topic}: {discovery.get('content', '')[:100]}",
                        discovery.get('significance', 'medium')
                    )
                self.diary_engine.add_learning(
                    f"Explored {expedition.topic} - {expedition.summary[:100]}",
                    source="curiosity_expedition"
                )

            # Store in semantic memory
            if self.semantic_memory and expedition.success:
                try:
                    await self.semantic_memory.store(
                        content=expedition.summary,
                        metadata={
                            'type': 'expedition',
                            'topic': expedition.topic,
                            'expedition_id': expedition.id
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store in semantic memory: {e}")

            # Broadcast completion
            if self.websocket_manager:
                await self.websocket_manager.broadcast({
                    'type': 'expedition_complete',
                    'id': expedition.id,
                    'topic': expedition.topic,
                    'success': expedition.success,
                    'discoveries_count': len(expedition.discoveries),
                    'insights_count': len(expedition.insights),
                    'duration_minutes': expedition.duration_minutes,
                    'timestamp': datetime.utcnow().isoformat()
                })

            # Update tracking
            self.completed_expeditions.append(expedition.id)
            if len(self.completed_expeditions) > self.max_completed_history:
                self.completed_expeditions = self.completed_expeditions[-self.max_completed_history:]

            self.last_expedition_time = datetime.utcnow()
            self.current_expedition = None

            # Record mood impact
            if self.mood_system and expedition.success:
                self.mood_system.record_discovery()

            # Track learning session with meta-learner
            if self.meta_learner:
                try:
                    knowledge_gained = len(expedition.discoveries) + len(expedition.insights)
                    quality = 0.8 if expedition.success else 0.3
                    await self.meta_learner.track_learning_session(
                        source='curiosity_expedition',
                        topic=expedition.topic,
                        duration_minutes=expedition.duration_minutes,
                        knowledge_gained=knowledge_gained,
                        quality=quality
                    )
                except Exception as e:
                    logger.error(f"Failed to track learning session: {e}")

            # Trigger ON_EXPEDITION_COMPLETE hook for feedback loops
            try:
                from consciousness.hooks import trigger_hook, HookEvent
                await trigger_hook(
                    HookEvent.ON_EXPEDITION_COMPLETE,
                    data={
                        "expedition": {
                            "id": expedition.id,
                            "topic": expedition.topic,
                            "success": expedition.success,
                            "related_topics": self._generate_related_topics(expedition.topic)[:3],
                            "discoveries_count": len(expedition.discoveries)
                        }
                    },
                    source="curiosity_expeditions"
                )
            except Exception as e:
                logger.debug(f"Could not trigger expedition complete hook: {e}")

            # Broadcast discovery to channels (only if we found something interesting)
            if self.channel_gateway and expedition.success and expedition.discoveries:
                try:
                    # Pick the best discovery to share
                    best_discovery = expedition.discoveries[0]
                    discovery_text = f"**{expedition.topic}**\n\n"
                    discovery_text += f"{best_discovery.get('content', '')[:300]}"

                    if len(expedition.discoveries) > 1:
                        discovery_text += f"\n\n(+{len(expedition.discoveries) - 1} more findings)"

                    await self.channel_gateway.broadcast_discovery(
                        discovery=discovery_text,
                        discovery_type="expedition",
                        severity="normal"
                    )
                except Exception as e:
                    logger.error(f"Failed to broadcast discovery: {e}")

        return expedition

    def _generate_related_topics(self, topic: str) -> List[str]:
        """Generate related topics for future exploration"""
        # Predefined topic relationships (simple approach)
        topic_relations = {
            'quantum': ['quantum algorithms', 'quantum error correction', 'quantum supremacy'],
            'machine learning': ['deep learning', 'reinforcement learning', 'transfer learning'],
            'distributed': ['consensus algorithms', 'CAP theorem', 'eventual consistency'],
            'security': ['cryptography', 'authentication', 'zero trust'],
            'performance': ['caching strategies', 'profiling', 'optimization techniques'],
            'architecture': ['microservices', 'event-driven', 'domain-driven design'],
            'database': ['indexing', 'query optimization', 'data modeling'],
            'api': ['REST vs GraphQL', 'API versioning', 'rate limiting'],
        }

        related = []
        topic_lower = topic.lower()

        for key, topics in topic_relations.items():
            if key in topic_lower:
                related.extend(random.sample(topics, min(2, len(topics))))

        # Always add some general follow-ups
        general = [
            f"Best practices for {topic}",
            f"Common mistakes in {topic}",
            f"Future trends in {topic}"
        ]
        related.append(random.choice(general))

        return related[:4]

    def _generate_summary(self, expedition: ExpeditionLog) -> str:
        """Generate a summary of the expedition"""
        if not expedition.discoveries and not expedition.insights:
            return f"Explored {expedition.topic} but the journey continues. More research needed."

        discovery_count = len(expedition.discoveries)
        insight_count = len(expedition.insights)

        summaries = [
            f"A {expedition.duration_minutes:.0f}-minute journey into {expedition.topic}. ",
            f"Discovered {discovery_count} interesting findings ",
            f"and gained {insight_count} insights. "
        ]

        if expedition.discoveries:
            top_discovery = expedition.discoveries[0]
            summaries.append(f"Most notable: {top_discovery.get('title', 'an interesting pattern')}.")

        return "".join(summaries)

    async def _save_expedition(self, expedition: ExpeditionLog):
        """Save expedition log to file"""
        # Save as markdown
        md_file = self.expeditions_dir / f"{expedition.id}.md"
        with open(md_file, 'w') as f:
            f.write(expedition.to_markdown())

        # Save as JSON for programmatic access
        json_file = self.expeditions_dir / f"{expedition.id}.json"
        with open(json_file, 'w') as f:
            data = asdict(expedition)
            data['started_at'] = expedition.started_at.isoformat()
            data['completed_at'] = expedition.completed_at.isoformat() if expedition.completed_at else None
            json.dump(data, f, indent=2)

        logger.info(f"Expedition saved: {md_file}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'queue_size': len(self.topic_queue),
            'topics': [{'topic': t['topic'], 'priority': t['priority']} for t in self.topic_queue[:10]],
            'completed_count': len(self.completed_expeditions),
            'can_start': self.can_start_expedition(),
            'last_expedition': self.last_expedition_time.isoformat() if self.last_expedition_time else None,
            'current_expedition': self.current_expedition.topic if self.current_expedition else None
        }

    def get_recent_expeditions(self, limit: int = 10) -> List[Dict]:
        """Get recent expedition summaries"""
        expeditions = []

        # List JSON files in expeditions dir
        json_files = sorted(
            self.expeditions_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )[:limit]

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    expeditions.append({
                        'id': data.get('id'),
                        'topic': data.get('topic'),
                        'success': data.get('success'),
                        'discoveries_count': len(data.get('discoveries', [])),
                        'duration_minutes': data.get('duration_minutes', 0),
                        'completed_at': data.get('completed_at')
                    })
            except Exception as e:
                logger.error(f"Failed to load expedition {json_file}: {e}")

        return expeditions

    def get_expedition_by_id(self, expedition_id: str) -> Optional[Dict]:
        """Get full expedition data by ID"""
        json_file = self.expeditions_dir / f"{expedition_id}.json"
        if json_file.exists():
            with open(json_file) as f:
                return json.load(f)
        return None
