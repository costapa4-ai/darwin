"""
A-MEM: Agentic Memory System

Implements Zettelkasten-inspired interconnected knowledge networks with
spreading activation for better memory recall.

Based on research:
- A-MEM: Agentic Memory for LLM Agents (arXiv:2502.12110)
- Synapse: Episodic-Semantic Memory via Spreading Activation (arXiv:2601.02744)
- MIRIX: Multi-Agent Memory System (arXiv:2507.07957)

Key features:
1. Notes with contextual descriptions, keywords, and tags
2. Dynamic linking between related memories
3. Spreading activation for relevance propagation
4. Episodic-to-semantic consolidation
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryNote:
    """A single memory note in the knowledge network"""
    id: str
    content: str
    context: str
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source: str = ""  # Where this memory came from
    note_type: str = "episodic"  # episodic, semantic, procedural
    importance: float = 0.5  # 0.0 to 1.0
    activation: float = 0.0  # Current activation level
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    linked_notes: Set[str] = field(default_factory=set)  # IDs of linked notes

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['created_at'] = self.created_at.isoformat()
        result['last_accessed'] = self.last_accessed.isoformat()
        result['linked_notes'] = list(self.linked_notes)
        return result

    @staticmethod
    def generate_id(content: str, context: str) -> str:
        """Generate unique ID from content hash"""
        combined = f"{content}:{context}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]


class KnowledgeGraph:
    """
    Graph structure for memory connections.

    Uses adjacency list representation with edge weights
    for spreading activation.
    """

    def __init__(self):
        self.nodes: Dict[str, MemoryNote] = {}
        self.edges: Dict[str, Dict[str, float]] = defaultdict(dict)  # node_id -> {connected_id: weight}
        self.reverse_edges: Dict[str, Dict[str, float]] = defaultdict(dict)  # For bidirectional traversal

    def add_node(self, note: MemoryNote):
        """Add a memory note to the graph"""
        self.nodes[note.id] = note

    def add_edge(self, from_id: str, to_id: str, weight: float = 1.0):
        """Add a weighted connection between two notes"""
        if from_id in self.nodes and to_id in self.nodes:
            self.edges[from_id][to_id] = weight
            self.reverse_edges[to_id][from_id] = weight

    def get_neighbors(self, node_id: str) -> List[Tuple[str, float]]:
        """Get all connected nodes with their weights"""
        return list(self.edges.get(node_id, {}).items())

    def get_node(self, node_id: str) -> Optional[MemoryNote]:
        """Get a note by ID"""
        return self.nodes.get(node_id)


class AgenticMemory:
    """
    A-MEM: Zettelkasten-inspired memory system with spreading activation.

    Features:
    - Dynamic note creation with automatic keyword/tag extraction
    - Automatic linking to related notes
    - Spreading activation for context-aware retrieval
    - Episodic to semantic consolidation
    """

    def __init__(self, nucleus=None, max_notes: int = 10000):
        """
        Initialize the agentic memory system.

        Args:
            nucleus: LLM interface for keyword/tag extraction
            max_notes: Maximum number of notes to keep (LRU eviction)
        """
        self.nucleus = nucleus
        self.max_notes = max_notes
        self.graph = KnowledgeGraph()

        # Activation parameters
        self.decay_rate = 0.1  # Activation decay per step
        self.spread_factor = 0.7  # How much activation spreads to neighbors
        self.activation_threshold = 0.1  # Min activation to consider

        # Consolidation tracking
        self.consolidation_interval = timedelta(hours=1)
        self.last_consolidation = datetime.utcnow()

        # Statistics
        self.total_stores = 0
        self.total_recalls = 0
        self.total_consolidations = 0

    async def store(
        self,
        content: str,
        context: str,
        source: str = "",
        note_type: str = "episodic",
        importance: float = 0.5
    ) -> MemoryNote:
        """
        Store a new memory with automatic processing.

        Args:
            content: The main content to remember
            context: Contextual information
            source: Where this memory came from
            note_type: episodic, semantic, or procedural
            importance: How important is this memory (0.0-1.0)

        Returns:
            The created MemoryNote
        """
        self.total_stores += 1

        # Generate unique ID
        note_id = MemoryNote.generate_id(content, context)

        # Check for duplicate
        if note_id in self.graph.nodes:
            existing = self.graph.nodes[note_id]
            existing.access_count += 1
            existing.last_accessed = datetime.utcnow()
            existing.importance = max(existing.importance, importance)
            return existing

        # Extract keywords and tags
        keywords = await self._extract_keywords(content)
        tags = await self._infer_tags(content, context)

        # Create note
        note = MemoryNote(
            id=note_id,
            content=content,
            context=context,
            keywords=keywords,
            tags=tags,
            source=source,
            note_type=note_type,
            importance=importance,
            activation=importance  # Start with importance as initial activation
        )

        # Add to graph
        self.graph.add_node(note)

        # Find and link related notes
        await self._link_related_notes(note)

        # Evict old notes if needed
        await self._evict_if_needed()

        logger.info(f"Stored memory: {note_id[:8]}... with {len(note.keywords)} keywords")
        return note

    async def recall(
        self,
        query: str,
        context: Optional[str] = None,
        limit: int = 10,
        min_relevance: float = 0.1
    ) -> List[Tuple[MemoryNote, float]]:
        """
        Recall memories using spreading activation.

        Args:
            query: What to search for
            context: Optional context to narrow search
            limit: Maximum notes to return
            min_relevance: Minimum relevance score

        Returns:
            List of (note, relevance_score) tuples
        """
        self.total_recalls += 1

        # Reset activations
        for note in self.graph.nodes.values():
            note.activation = 0.0

        # Find seed nodes (initial matches)
        seeds = await self._find_seed_nodes(query, context)

        if not seeds:
            return []

        # Set initial activation for seeds
        for note_id, relevance in seeds:
            if note_id in self.graph.nodes:
                self.graph.nodes[note_id].activation = relevance

        # Spread activation through the network
        activated = self._spread_activation(seeds, max_steps=3)

        # Rank by activation level
        ranked = [
            (self.graph.nodes[note_id], activation)
            for note_id, activation in activated.items()
            if activation >= min_relevance
        ]
        ranked.sort(key=lambda x: x[1], reverse=True)

        # Update access timestamps
        for note, _ in ranked[:limit]:
            note.access_count += 1
            note.last_accessed = datetime.utcnow()

        return ranked[:limit]

    async def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content using LLM or heuristics"""
        if self.nucleus:
            try:
                prompt = f"""Extract 5-10 important keywords from this text.
Return only the keywords, one per line.

TEXT: {content[:500]}

KEYWORDS:"""
                response = await self.nucleus.generate(prompt)
                text = response.get('text', response) if isinstance(response, dict) else str(response)
                keywords = [kw.strip() for kw in text.strip().split('\n') if kw.strip()]
                return keywords[:10]
            except Exception as e:
                logger.warning(f"Keyword extraction failed: {e}")

        # Fallback: simple word frequency
        words = content.lower().split()
        # Filter common words and short words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'must', 'to', 'of', 'in', 'for', 'on', 'with',
                     'at', 'by', 'from', 'as', 'into', 'through', 'during', 'before', 'after',
                     'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once',
                     'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either', 'neither',
                     'not', 'only', 'own', 'same', 'than', 'too', 'very', 'just', 'can'}

        word_freq = defaultdict(int)
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in stopwords:
                word_freq[clean_word] += 1

        # Return top 10 by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:10]]

    async def _infer_tags(self, content: str, context: str) -> List[str]:
        """Infer categorical tags for the content"""
        tags = []

        # Pattern-based tag inference
        content_lower = content.lower()
        context_lower = context.lower()
        combined = f"{content_lower} {context_lower}"

        tag_patterns = {
            'code': ['function', 'class', 'def ', 'import', 'return', 'variable'],
            'architecture': ['pattern', 'design', 'structure', 'architecture', 'module'],
            'optimization': ['optimize', 'performance', 'speed', 'efficient', 'cache'],
            'security': ['security', 'vulnerability', 'auth', 'permission', 'safe'],
            'learning': ['learn', 'understand', 'discover', 'insight', 'knowledge'],
            'tool': ['tool', 'utility', 'helper', 'function', 'method'],
            'bug': ['bug', 'error', 'fix', 'issue', 'problem'],
            'idea': ['idea', 'concept', 'proposal', 'suggestion', 'improvement'],
            'research': ['research', 'study', 'paper', 'article', 'analysis'],
            'web': ['http', 'url', 'website', 'api', 'endpoint']
        }

        for tag, patterns in tag_patterns.items():
            if any(p in combined for p in patterns):
                tags.append(tag)

        return tags[:5]  # Limit to 5 tags

    async def _find_seed_nodes(
        self,
        query: str,
        context: Optional[str]
    ) -> List[Tuple[str, float]]:
        """Find initial matching notes for spreading activation"""
        query_keywords = await self._extract_keywords(query)
        query_tags = await self._infer_tags(query, context or "")

        seeds = []

        for note_id, note in self.graph.nodes.items():
            # Calculate relevance based on keyword/tag overlap
            keyword_overlap = len(set(query_keywords) & set(note.keywords))
            tag_overlap = len(set(query_tags) & set(note.tags))

            # Normalize scores
            keyword_score = keyword_overlap / max(len(query_keywords), 1)
            tag_score = tag_overlap / max(len(query_tags), 1)

            # Combined relevance with importance weighting
            relevance = (keyword_score * 0.6 + tag_score * 0.4) * (0.5 + note.importance * 0.5)

            # Recency boost
            age_days = (datetime.utcnow() - note.created_at).days
            recency_factor = 1.0 / (1.0 + age_days * 0.1)
            relevance *= (0.7 + recency_factor * 0.3)

            if relevance > 0.1:
                seeds.append((note_id, relevance))

        # Sort by relevance and return top matches
        seeds.sort(key=lambda x: x[1], reverse=True)
        return seeds[:20]

    def _spread_activation(
        self,
        seeds: List[Tuple[str, float]],
        max_steps: int = 3
    ) -> Dict[str, float]:
        """
        Spread activation through the knowledge graph.

        Uses the spreading activation algorithm from cognitive science
        to find related memories through the link structure.
        """
        activations = {}

        # Initialize with seed activations
        for note_id, activation in seeds:
            activations[note_id] = activation

        # Iteratively spread activation
        for step in range(max_steps):
            new_activations = {}

            for note_id, activation in activations.items():
                if activation < self.activation_threshold:
                    continue

                # Spread to neighbors
                neighbors = self.graph.get_neighbors(note_id)
                for neighbor_id, edge_weight in neighbors:
                    spread = activation * self.spread_factor * edge_weight
                    spread *= (1 - self.decay_rate * step)  # Decay with distance

                    current = new_activations.get(neighbor_id, 0)
                    new_activations[neighbor_id] = max(current, spread)

            # Merge new activations
            for note_id, activation in new_activations.items():
                if note_id not in activations:
                    activations[note_id] = activation
                else:
                    # Combine activations (take max to avoid explosion)
                    activations[note_id] = max(activations[note_id], activation)

        return activations

    async def _link_related_notes(self, new_note: MemoryNote):
        """Find and link related notes to the new note"""
        # Find notes with overlapping keywords/tags
        for note_id, existing in self.graph.nodes.items():
            if note_id == new_note.id:
                continue

            # Calculate similarity
            keyword_overlap = len(set(new_note.keywords) & set(existing.keywords))
            tag_overlap = len(set(new_note.tags) & set(existing.tags))

            similarity = (keyword_overlap * 0.6 + tag_overlap * 0.4)

            # Link if sufficiently similar
            if similarity >= 0.3:
                edge_weight = min(similarity, 1.0)
                self.graph.add_edge(new_note.id, note_id, edge_weight)
                self.graph.add_edge(note_id, new_note.id, edge_weight)

                new_note.linked_notes.add(note_id)
                existing.linked_notes.add(new_note.id)

    async def _evict_if_needed(self):
        """Evict oldest, least important notes if over capacity"""
        if len(self.graph.nodes) <= self.max_notes:
            return

        # Score notes by (importance * recency * access_count)
        scores = []
        for note_id, note in self.graph.nodes.items():
            age_days = (datetime.utcnow() - note.last_accessed).days
            recency_score = 1.0 / (1.0 + age_days)
            access_score = min(note.access_count / 10, 1.0)
            score = note.importance * recency_score * access_score
            scores.append((note_id, score))

        # Sort by score (lowest first)
        scores.sort(key=lambda x: x[1])

        # Remove bottom 10%
        to_remove = int(self.max_notes * 0.1)
        for note_id, _ in scores[:to_remove]:
            # Remove edges
            for linked_id in list(self.graph.nodes[note_id].linked_notes):
                if linked_id in self.graph.nodes:
                    self.graph.nodes[linked_id].linked_notes.discard(note_id)
                if note_id in self.graph.edges:
                    del self.graph.edges[note_id]
                if note_id in self.graph.reverse_edges:
                    del self.graph.reverse_edges[note_id]

            # Remove node
            del self.graph.nodes[note_id]

        logger.info(f"Evicted {to_remove} notes, {len(self.graph.nodes)} remaining")

    async def consolidate(self) -> Dict[str, Any]:
        """
        Consolidate episodic memories into semantic abstractions.

        This is like "sleeping" - converting experiences into knowledge.
        """
        if datetime.utcnow() - self.last_consolidation < self.consolidation_interval:
            return {"skipped": True, "reason": "Too soon since last consolidation"}

        self.total_consolidations += 1
        self.last_consolidation = datetime.utcnow()

        # Find clusters of related episodic memories
        episodic_notes = [
            n for n in self.graph.nodes.values()
            if n.note_type == "episodic" and n.access_count >= 2
        ]

        consolidated = 0

        # Group by shared tags
        tag_groups = defaultdict(list)
        for note in episodic_notes:
            for tag in note.tags:
                tag_groups[tag].append(note)

        # Create semantic notes from large clusters
        for tag, notes in tag_groups.items():
            if len(notes) >= 3:
                # Synthesize a semantic memory from the cluster
                combined_content = " ".join(n.content[:100] for n in notes[:5])
                combined_keywords = list(set(kw for n in notes for kw in n.keywords))[:15]

                semantic_note = MemoryNote(
                    id=MemoryNote.generate_id(f"semantic:{tag}", combined_content),
                    content=f"Pattern about {tag}: {combined_content[:200]}",
                    context=f"Consolidated from {len(notes)} episodic memories",
                    keywords=combined_keywords,
                    tags=[tag, "semantic", "consolidated"],
                    source="consolidation",
                    note_type="semantic",
                    importance=0.7
                )

                if semantic_note.id not in self.graph.nodes:
                    self.graph.add_node(semantic_note)

                    # Link to source notes
                    for source_note in notes:
                        self.graph.add_edge(semantic_note.id, source_note.id, 0.8)
                        semantic_note.linked_notes.add(source_note.id)

                    consolidated += 1

        return {
            "consolidated": consolidated,
            "episodic_processed": len(episodic_notes),
            "total_notes": len(self.graph.nodes)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        type_counts = defaultdict(int)
        for note in self.graph.nodes.values():
            type_counts[note.note_type] += 1

        total_edges = sum(len(edges) for edges in self.graph.edges.values())

        return {
            "total_notes": len(self.graph.nodes),
            "total_edges": total_edges,
            "avg_connections": total_edges / max(len(self.graph.nodes), 1),
            "note_types": dict(type_counts),
            "total_stores": self.total_stores,
            "total_recalls": self.total_recalls,
            "total_consolidations": self.total_consolidations
        }

    def export_graph(self) -> Dict[str, Any]:
        """Export the knowledge graph for visualization"""
        nodes = [note.to_dict() for note in self.graph.nodes.values()]
        edges = [
            {"from": from_id, "to": to_id, "weight": weight}
            for from_id, connections in self.graph.edges.items()
            for to_id, weight in connections.items()
        ]

        return {
            "nodes": nodes,
            "edges": edges,
            "statistics": self.get_statistics()
        }
