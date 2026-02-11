"""
Hierarchical Memory System - Inspired by Human Brain Architecture
=================================================================

Three-layer memory system:
1. Working Memory: Short-term, actively processing (seconds-minutes)
2. Episodic Memory: Specific experiences with temporal context (hours-days)
3. Semantic Memory: Consolidated general knowledge (permanent)

During SLEEP cycles, episodic memories are consolidated into semantic knowledge.
"""

import asyncio
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import deque
import json
from pathlib import Path
import numpy as np
from enum import Enum

from utils.logger import get_logger
from core.semantic_memory import SemanticMemory

logger = get_logger(__name__)


class MemoryType(Enum):
    """Types of memory in the hierarchical system"""
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class EpisodeCategory(Enum):
    """Categories of episodic experiences"""
    TOOL_EXECUTION = "tool_execution"
    CODE_GENERATION = "code_generation"
    LEARNING = "learning"
    REFLECTION = "reflection"
    WEB_DISCOVERY = "web_discovery"
    PROBLEM_SOLVING = "problem_solving"
    INTERACTION = "interaction"


@dataclass
class WorkingMemoryItem:
    """Item in working memory - currently active information"""
    key: str
    content: Any
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 1.0  # 0-1 scale

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class Episode:
    """An episodic memory - specific experience with context"""
    id: str
    category: EpisodeCategory
    description: str
    content: Dict[str, Any]
    timestamp: datetime
    success: bool = True
    emotional_valence: float = 0.0  # -1 (negative) to +1 (positive)
    importance: float = 1.0  # 0-1 scale
    consolidation_count: int = 0  # How many times reviewed for consolidation
    tags: Set[str] = field(default_factory=set)

    def age_hours(self) -> float:
        """Get age of episode in hours"""
        return (datetime.now() - self.timestamp).total_seconds() / 3600

    def decay_factor(self) -> float:
        """Calculate memory decay (Ebbinghaus forgetting curve)"""
        hours = self.age_hours()
        # Memory strength decays exponentially: S(t) = e^(-t/τ)
        # τ (tau) = time constant (24 hours for episodic memory)
        tau = 24.0
        return np.exp(-hours / tau) * self.importance

    def should_consolidate(self) -> bool:
        """Determine if episode should be consolidated to semantic memory"""
        # Consolidate if:
        # 1. High importance and accessed multiple times
        # 2. Successful experience with emotional significance
        # 3. Old enough to have stabilized (> 1 hour)
        return (
            (self.importance > 0.7 and self.consolidation_count >= 2) or
            (self.success and abs(self.emotional_valence) > 0.5 and self.age_hours() > 1) or
            (self.consolidation_count >= 3)
        )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['category'] = self.category.value
        data['timestamp'] = self.timestamp.isoformat()
        data['tags'] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Episode':
        data['category'] = EpisodeCategory(data['category'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['tags'] = set(data.get('tags', []))
        return cls(**data)


@dataclass
class SemanticKnowledge:
    """Consolidated semantic knowledge - general understanding"""
    id: str
    concept: str  # Core concept/pattern
    description: str
    confidence: float  # 0-1, based on supporting episodes
    source_episodes: List[str] = field(default_factory=list)  # Episode IDs
    created_at: datetime = field(default_factory=datetime.now)
    last_reinforced: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    tags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_reinforced'] = self.last_reinforced.isoformat()
        data['tags'] = list(self.tags)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SemanticKnowledge':
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_reinforced'] = datetime.fromisoformat(data['last_reinforced'])
        data['tags'] = set(data.get('tags', []))
        return cls(**data)


class HierarchicalMemory:
    """
    Three-layer hierarchical memory system inspired by human brain

    Working Memory: Limited capacity (50-100 items), fast access, volatile
    Episodic Memory: Experiences with temporal context, medium-term, decay
    Semantic Memory: General knowledge, long-term, persistent
    """

    def __init__(self, storage_path: str = "./data/memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Working Memory - Limited capacity FIFO queue
        self.working_memory: deque = deque(maxlen=100)
        self.working_memory_index: Dict[str, WorkingMemoryItem] = {}

        # Episodic Memory - Experiences with decay
        self.episodic_memory: Dict[str, Episode] = {}
        self.episodic_index_by_category: Dict[EpisodeCategory, List[str]] = {
            cat: [] for cat in EpisodeCategory
        }

        # Semantic Memory - Consolidated knowledge
        self.semantic_memory: Dict[str, SemanticKnowledge] = {}
        self.semantic_index_by_tag: Dict[str, List[str]] = {}

        # Integration with existing SemanticMemory (vector DB)
        self.vector_memory = SemanticMemory()

        # Consolidation statistics
        self.consolidation_stats = {
            'total_consolidations': 0,
            'last_consolidation': None,
            'episodes_consolidated': 0,
            'knowledge_created': 0
        }

        # Load persisted state
        self._load_state()

        logger.info(f"🧠 HierarchicalMemory initialized:")
        logger.info(f"   Working: {len(self.working_memory)} items")
        logger.info(f"   Episodic: {len(self.episodic_memory)} episodes")
        logger.info(f"   Semantic: {len(self.semantic_memory)} knowledge items")

    # ==================== WORKING MEMORY ====================

    def add_to_working_memory(self, key: str, content: Any, importance: float = 1.0) -> None:
        """
        Add item to working memory (short-term, active processing)

        Args:
            key: Unique identifier
            content: Content to store
            importance: Importance weight (0-1)
        """
        # If already exists, update
        if key in self.working_memory_index:
            item = self.working_memory_index[key]
            item.content = content
            item.access_count += 1
            item.importance = max(item.importance, importance)
            logger.debug(f"📝 Updated working memory: {key}")
        else:
            item = WorkingMemoryItem(
                key=key,
                content=content,
                importance=importance
            )
            self.working_memory.append(item)
            self.working_memory_index[key] = item
            logger.debug(f"📝 Added to working memory: {key}")

    def get_from_working_memory(self, key: str) -> Optional[Any]:
        """Retrieve item from working memory"""
        item = self.working_memory_index.get(key)
        if item:
            item.access_count += 1
            return item.content
        return None

    def get_working_memory_context(self, max_items: int = 10) -> List[Dict[str, Any]]:
        """Get recent working memory items for context"""
        # Sort by importance * recency
        items = sorted(
            self.working_memory,
            key=lambda x: x.importance * (1.0 / max(1, x.access_count)),
            reverse=True
        )[:max_items]

        return [item.to_dict() for item in items]

    def clear_working_memory(self) -> None:
        """Clear working memory (typically at state transitions)"""
        logger.info(f"🗑️  Clearing working memory ({len(self.working_memory)} items)")
        self.working_memory.clear()
        self.working_memory_index.clear()

    # ==================== EPISODIC MEMORY ====================

    def add_episode(
        self,
        episode_id: str,
        category: EpisodeCategory,
        description: str,
        content: Dict[str, Any],
        success: bool = True,
        emotional_valence: float = 0.0,
        importance: float = 1.0,
        tags: Optional[Set[str]] = None
    ) -> Episode:
        """
        Add episodic memory (specific experience with temporal context)

        Args:
            episode_id: Unique episode identifier
            category: Episode category
            description: Human-readable description
            content: Structured content/data
            success: Whether experience was successful
            emotional_valence: -1 (negative) to +1 (positive)
            importance: Importance weight (0-1)
            tags: Optional tags for indexing

        Returns:
            Created Episode
        """
        episode = Episode(
            id=episode_id,
            category=category,
            description=description,
            content=content,
            timestamp=datetime.now(),
            success=success,
            emotional_valence=emotional_valence,
            importance=importance,
            tags=tags or set()
        )

        self.episodic_memory[episode_id] = episode
        self.episodic_index_by_category[category].append(episode_id)

        logger.info(f"💭 Stored episode: {category.value} - {description[:50]}...")

        return episode

    def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Retrieve specific episode"""
        return self.episodic_memory.get(episode_id)

    def get_recent_episodes(
        self,
        category: Optional[EpisodeCategory] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[Episode]:
        """
        Get recent episodic memories

        Args:
            category: Filter by category (None = all)
            limit: Maximum number of episodes
            min_importance: Minimum importance threshold

        Returns:
            List of recent episodes
        """
        if category:
            episode_ids = self.episodic_index_by_category[category]
            episodes = [self.episodic_memory[eid] for eid in episode_ids if eid in self.episodic_memory]
        else:
            episodes = list(self.episodic_memory.values())

        # Filter by importance
        episodes = [e for e in episodes if e.importance >= min_importance]

        # Sort by timestamp (most recent first)
        episodes.sort(key=lambda e: e.timestamp, reverse=True)

        return episodes[:limit]

    def prune_episodic_memory(self, max_age_hours: float = 168) -> int:
        """
        Prune old episodic memories (decay over time)

        Args:
            max_age_hours: Maximum age to keep (default 7 days = 168 hours)

        Returns:
            Number of episodes pruned
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        pruned_ids = []
        for episode_id, episode in list(self.episodic_memory.items()):
            # Keep if:
            # 1. Recent (within max_age)
            # 2. High importance and not forgotten (decay factor)
            # 3. Already consolidated
            if (
                episode.timestamp < cutoff and
                episode.decay_factor() < 0.1 and
                episode.consolidation_count == 0
            ):
                pruned_ids.append(episode_id)
                del self.episodic_memory[episode_id]

                # Remove from category index
                if episode_id in self.episodic_index_by_category[episode.category]:
                    self.episodic_index_by_category[episode.category].remove(episode_id)

        if pruned_ids:
            logger.info(f"🗑️  Pruned {len(pruned_ids)} old episodes")

        return len(pruned_ids)

    # ==================== SEMANTIC MEMORY ====================

    def add_semantic_knowledge(
        self,
        knowledge_id: str,
        concept: str,
        description: str,
        confidence: float,
        source_episodes: List[str],
        tags: Optional[Set[str]] = None
    ) -> SemanticKnowledge:
        """
        Add semantic knowledge (consolidated understanding)

        Args:
            knowledge_id: Unique identifier
            concept: Core concept/pattern name
            description: Detailed description
            confidence: Confidence level (0-1)
            source_episodes: Episode IDs that support this knowledge
            tags: Optional tags for indexing

        Returns:
            Created SemanticKnowledge
        """
        knowledge = SemanticKnowledge(
            id=knowledge_id,
            concept=concept,
            description=description,
            confidence=confidence,
            source_episodes=source_episodes,
            tags=tags or set()
        )

        self.semantic_memory[knowledge_id] = knowledge

        # Update tag index
        for tag in knowledge.tags:
            if tag not in self.semantic_index_by_tag:
                self.semantic_index_by_tag[tag] = []
            self.semantic_index_by_tag[tag].append(knowledge_id)

        # Store in vector DB for semantic search
        asyncio.create_task(self._store_in_vector_db(knowledge))

        logger.info(f"🧠 Added semantic knowledge: {concept}")

        return knowledge

    def _find_existing_knowledge_by_concept(self, concept: str) -> Optional[str]:
        """Find existing semantic knowledge ID by concept name."""
        for kid, knowledge in self.semantic_memory.items():
            if knowledge.concept == concept:
                return kid
        return None

    def _reinforce_semantic_knowledge(
        self,
        knowledge_id: str,
        description: str,
        confidence: float,
        source_episodes: List[str],
    ) -> SemanticKnowledge:
        """Reinforce existing semantic knowledge with new evidence."""
        knowledge = self.semantic_memory[knowledge_id]
        knowledge.description = description
        knowledge.confidence = min(1.0, (knowledge.confidence + confidence) / 2 + 0.05)
        knowledge.last_reinforced = datetime.now()
        knowledge.usage_count += 1
        # Add new source episodes without duplicating
        existing = set(knowledge.source_episodes)
        for ep_id in source_episodes:
            if ep_id not in existing:
                knowledge.source_episodes.append(ep_id)
        logger.info(f"🧠 Reinforced semantic knowledge: {knowledge.concept} (confidence={knowledge.confidence:.2f})")
        return knowledge

    async def _store_in_vector_db(self, knowledge: SemanticKnowledge) -> None:
        """Store semantic knowledge in vector database"""
        try:
            await self.vector_memory.store_execution(
                task_id=f"semantic_{knowledge.id}",
                task_description=knowledge.concept,
                code=knowledge.description,
                result={"success": True},
                metadata={
                    "type": "semantic_knowledge",
                    "confidence": knowledge.confidence,
                    "tags": list(knowledge.tags)
                }
            )
        except Exception as e:
            logger.error(f"Failed to store in vector DB: {e}")

    def get_semantic_knowledge(self, knowledge_id: str) -> Optional[SemanticKnowledge]:
        """Retrieve specific semantic knowledge"""
        knowledge = self.semantic_memory.get(knowledge_id)
        if knowledge:
            knowledge.usage_count += 1
            knowledge.last_reinforced = datetime.now()
        return knowledge

    def search_semantic_knowledge(
        self,
        tags: Optional[Set[str]] = None,
        min_confidence: float = 0.0,
        limit: int = 10
    ) -> List[SemanticKnowledge]:
        """
        Search semantic knowledge

        Args:
            tags: Filter by tags (None = all)
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching knowledge items
        """
        if tags:
            # Get knowledge IDs matching any tag
            knowledge_ids = set()
            for tag in tags:
                knowledge_ids.update(self.semantic_index_by_tag.get(tag, []))
            knowledge_items = [
                self.semantic_memory[kid] for kid in knowledge_ids
                if kid in self.semantic_memory
            ]
        else:
            knowledge_items = list(self.semantic_memory.values())

        # Filter by confidence
        knowledge_items = [k for k in knowledge_items if k.confidence >= min_confidence]

        # Sort by confidence * usage
        knowledge_items.sort(
            key=lambda k: k.confidence * (1 + np.log1p(k.usage_count)),
            reverse=True
        )

        return knowledge_items[:limit]

    # ==================== CONSOLIDATION ====================

    async def consolidate_memories(self, min_episodes: int = 3) -> Dict[str, Any]:
        """
        Consolidate episodic memories into semantic knowledge (SLEEP mode)

        This simulates memory consolidation during sleep:
        1. Identify episodes ready for consolidation
        2. Find patterns across related episodes
        3. Extract general knowledge
        4. Create semantic memory entries
        5. Mark episodes as consolidated

        Args:
            min_episodes: Minimum episodes needed to form semantic knowledge

        Returns:
            Consolidation statistics
        """
        logger.info("🌙 Starting memory consolidation (SLEEP mode)...")

        stats = {
            'episodes_reviewed': 0,
            'episodes_consolidated': 0,
            'knowledge_created': 0,
            'patterns_found': []
        }

        # Get episodes ready for consolidation
        consolidation_candidates = []
        for episode in self.episodic_memory.values():
            if episode.should_consolidate():
                consolidation_candidates.append(episode)
                episode.consolidation_count += 1

        stats['episodes_reviewed'] = len(consolidation_candidates)

        if not consolidation_candidates:
            logger.info("   No episodes ready for consolidation")
            return stats

        logger.info(f"   Found {len(consolidation_candidates)} episodes for consolidation")

        # Group by category and tags
        category_groups: Dict[EpisodeCategory, List[Episode]] = {}
        for episode in consolidation_candidates:
            if episode.category not in category_groups:
                category_groups[episode.category] = []
            category_groups[episode.category].append(episode)

        # Consolidate each category
        for category, episodes in category_groups.items():
            if len(episodes) < min_episodes:
                continue

            # Find patterns within category
            patterns = await self._find_patterns_in_episodes(episodes)

            for pattern in patterns:
                # Check if this pattern already exists as semantic knowledge
                existing_id = self._find_existing_knowledge_by_concept(pattern['concept'])

                if existing_id:
                    # Reinforce existing knowledge instead of duplicating
                    self._reinforce_semantic_knowledge(
                        knowledge_id=existing_id,
                        description=pattern['description'],
                        confidence=pattern['confidence'],
                        source_episodes=[e.id for e in pattern['episodes']],
                    )
                    stats['patterns_found'].append(f"{pattern['concept']} (reinforced)")
                else:
                    # Create new semantic knowledge
                    knowledge_id = f"semantic_{category.value}_{len(self.semantic_memory)}"
                    self.add_semantic_knowledge(
                        knowledge_id=knowledge_id,
                        concept=pattern['concept'],
                        description=pattern['description'],
                        confidence=pattern['confidence'],
                        source_episodes=[e.id for e in pattern['episodes']],
                        tags=pattern['tags']
                    )
                    stats['knowledge_created'] += 1
                    stats['patterns_found'].append(pattern['concept'])

                # Mark episodes as consolidated
                for episode in pattern['episodes']:
                    episode.consolidation_count += 1
                    stats['episodes_consolidated'] += 1

        # Update global stats
        self.consolidation_stats['total_consolidations'] += 1
        self.consolidation_stats['last_consolidation'] = datetime.now().isoformat()
        self.consolidation_stats['episodes_consolidated'] += stats['episodes_consolidated']
        self.consolidation_stats['knowledge_created'] += stats['knowledge_created']

        # Prune old episodes
        pruned = self.prune_episodic_memory()
        stats['episodes_pruned'] = pruned

        # Save state
        self._save_state()

        logger.info(f"✅ Consolidation complete:")
        logger.info(f"   Episodes reviewed: {stats['episodes_reviewed']}")
        logger.info(f"   Episodes consolidated: {stats['episodes_consolidated']}")
        logger.info(f"   Knowledge created: {stats['knowledge_created']}")
        logger.info(f"   Patterns: {', '.join(stats['patterns_found'][:5])}")

        return stats

    async def _find_patterns_in_episodes(self, episodes: List[Episode]) -> List[Dict[str, Any]]:
        """
        Find patterns across episodes to create semantic knowledge

        Args:
            episodes: List of related episodes

        Returns:
            List of identified patterns
        """
        patterns = []

        # Group by common tags
        tag_groups: Dict[str, List[Episode]] = {}
        for episode in episodes:
            for tag in episode.tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(episode)

        # Create patterns from tag groups
        for tag, tag_episodes in tag_groups.items():
            if len(tag_episodes) < 2:
                continue

            # Calculate average success rate
            success_rate = sum(1 for e in tag_episodes if e.success) / len(tag_episodes)

            # Extract common elements
            all_content_keys = set()
            for episode in tag_episodes:
                all_content_keys.update(episode.content.keys())

            # Build pattern description
            if success_rate > 0.7:
                sentiment = "successful"
                confidence = success_rate
            elif success_rate < 0.3:
                sentiment = "problematic"
                confidence = 1.0 - success_rate
            else:
                sentiment = "variable"
                confidence = 0.5

            concept = f"{tag.replace('_', ' ').title()} Pattern"

            description = f"Based on {len(tag_episodes)} episodes, {sentiment} pattern observed. "
            description += f"Common elements: {', '.join(list(all_content_keys)[:5])}"

            patterns.append({
                'concept': concept,
                'description': description,
                'confidence': confidence,
                'episodes': tag_episodes,
                'tags': {tag, tag_episodes[0].category.value}
            })

        return patterns

    # ==================== CONTEXT RETRIEVAL ====================

    def get_memory_context(
        self,
        query: str,
        include_working: bool = True,
        include_episodic: bool = True,
        include_semantic: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive memory context for a query

        Args:
            query: Query string
            include_working: Include working memory
            include_episodic: Include recent episodes
            include_semantic: Include semantic knowledge

        Returns:
            Dict with memory context from all layers
        """
        context = {}

        if include_working:
            context['working_memory'] = self.get_working_memory_context(max_items=5)

        if include_episodic:
            # Get recent episodes across categories
            recent_episodes = self.get_recent_episodes(limit=10, min_importance=0.5)
            context['recent_episodes'] = [e.to_dict() for e in recent_episodes]

        if include_semantic:
            # Search semantic knowledge
            # Extract potential tags from query
            query_words = set(query.lower().split())
            matching_knowledge = self.search_semantic_knowledge(
                tags=query_words,
                min_confidence=0.6,
                limit=5
            )
            context['semantic_knowledge'] = [k.to_dict() for k in matching_knowledge]

        return context

    # ==================== PERSISTENCE ====================

    def _save_state(self) -> None:
        """Save memory state to disk"""
        try:
            # Save episodic memory
            episodic_file = self.storage_path / "episodic_memory.json"
            episodic_data = {
                'episodes': {eid: e.to_dict() for eid, e in self.episodic_memory.items()},
                'stats': self.consolidation_stats
            }
            with open(episodic_file, 'w') as f:
                json.dump(episodic_data, f, indent=2)

            # Save semantic memory
            semantic_file = self.storage_path / "semantic_knowledge.json"
            semantic_data = {
                'knowledge': {kid: k.to_dict() for kid, k in self.semantic_memory.items()}
            }
            with open(semantic_file, 'w') as f:
                json.dump(semantic_data, f, indent=2)

            logger.debug("💾 Memory state saved")

        except Exception as e:
            logger.error(f"Failed to save memory state: {e}")

    def _load_state(self) -> None:
        """Load memory state from disk"""
        try:
            # Load episodic memory
            episodic_file = self.storage_path / "episodic_memory.json"
            if episodic_file.exists():
                with open(episodic_file, 'r') as f:
                    data = json.load(f)

                for eid, edata in data.get('episodes', {}).items():
                    episode = Episode.from_dict(edata)
                    self.episodic_memory[eid] = episode
                    self.episodic_index_by_category[episode.category].append(eid)

                self.consolidation_stats = data.get('stats', self.consolidation_stats)

            # Load semantic memory
            semantic_file = self.storage_path / "semantic_knowledge.json"
            if semantic_file.exists():
                with open(semantic_file, 'r') as f:
                    data = json.load(f)

                for kid, kdata in data.get('knowledge', {}).items():
                    knowledge = SemanticKnowledge.from_dict(kdata)
                    self.semantic_memory[kid] = knowledge

                    # Rebuild tag index
                    for tag in knowledge.tags:
                        if tag not in self.semantic_index_by_tag:
                            self.semantic_index_by_tag[tag] = []
                        self.semantic_index_by_tag[tag].append(kid)

            logger.debug("📥 Memory state loaded")

        except Exception as e:
            logger.error(f"Failed to load memory state: {e}")

    # ==================== STATISTICS ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        return {
            'working_memory': {
                'size': len(self.working_memory),
                'capacity': self.working_memory.maxlen
            },
            'episodic_memory': {
                'total_episodes': len(self.episodic_memory),
                'by_category': {
                    cat.value: len(episodes)
                    for cat, episodes in self.episodic_index_by_category.items()
                },
                'avg_age_hours': np.mean([e.age_hours() for e in self.episodic_memory.values()])
                    if self.episodic_memory else 0
            },
            'semantic_memory': {
                'total_knowledge': len(self.semantic_memory),
                'avg_confidence': np.mean([k.confidence for k in self.semantic_memory.values()])
                    if self.semantic_memory else 0,
                'total_usage': sum(k.usage_count for k in self.semantic_memory.values())
            },
            'consolidation_stats': self.consolidation_stats
        }
