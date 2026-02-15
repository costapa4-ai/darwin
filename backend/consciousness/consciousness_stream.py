"""
ConsciousnessStream — Global Workspace for Darwin's consciousness.

Inspired by Global Workspace Theory (Baars, 1988; Dehaene): consciousness
arises when information is broadcast to all brain areas simultaneously.

This module provides a unified event stream that ALL output channels read
from — dashboard feed, Telegram inner voice, chat prompt, and consciousness
engine itself. Events compete for "broadcast" via salience scoring.

Producers: hooks (via stream_bridge), consciousness_engine, chat, mood, genome
Consumers: dashboard feed, prompt_composer, inner_voice, Telegram
"""

import json
import sqlite3
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

from utils.logger import get_logger

logger = get_logger(__name__)

_local = threading.local()
_instance = None


@dataclass
class ConsciousEvent:
    """A single event in Darwin's consciousness stream."""
    id: str
    timestamp: str              # ISO format
    source: str                 # wake_cycle, sleep_cycle, chat, mood, genome, system
    event_type: str             # activity, dream, discovery, mood_change, chat_message, etc.
    title: str                  # One-line summary
    content: str                # Full description
    salience: float             # 0.0-1.0 (how "conscious" this event is)
    valence: float              # -1.0 to 1.0 (emotional tone)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Ensure metadata is serializable
        if isinstance(d.get('metadata'), str):
            try:
                d['metadata'] = json.loads(d['metadata'])
            except (json.JSONDecodeError, TypeError):
                d['metadata'] = {}
        return d

    @classmethod
    def create(cls, source: str, event_type: str, title: str,
               content: str, salience: float = 0.5, valence: float = 0.0,
               metadata: Dict = None) -> "ConsciousEvent":
        return cls(
            id=uuid.uuid4().hex[:12],
            timestamp=datetime.utcnow().isoformat(),
            source=source,
            event_type=event_type,
            title=title[:200],
            content=content[:500],
            salience=max(0.0, min(1.0, salience)),
            valence=max(-1.0, min(1.0, valence)),
            metadata=metadata or {},
        )


class ConsciousnessStream:
    """
    Global Workspace — unified consciousness event stream.

    In-memory ring buffer (last 100) for fast reads + SQLite persistence.
    All channels read from here instead of separate data sources.
    """

    RING_SIZE = 100

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self._ring: deque = deque(maxlen=self.RING_SIZE)
        self._init_table()
        self._load_recent_into_ring()
        logger.info("ConsciousnessStream initialized (Global Workspace)")

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(_local, 'stream_conn') or _local.stream_conn is None:
            _local.stream_conn = sqlite3.connect(self.db_path)
            _local.stream_conn.row_factory = sqlite3.Row
            _local.stream_conn.execute("PRAGMA journal_mode=WAL")
        return _local.stream_conn

    def _init_table(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS consciousness_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                salience REAL DEFAULT 0.5,
                valence REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ce_timestamp
            ON consciousness_events(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ce_salience
            ON consciousness_events(salience)
        """)
        conn.commit()

    def _load_recent_into_ring(self):
        """Load recent events from DB into ring buffer at startup."""
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM consciousness_events "
                "ORDER BY timestamp DESC LIMIT ?",
                (self.RING_SIZE,)
            ).fetchall()
            for row in reversed(rows):
                self._ring.append(self._row_to_event(row))
            if rows:
                logger.info(f"Loaded {len(rows)} events into ring buffer")
        except Exception as e:
            logger.debug(f"Ring buffer load failed: {e}")

    def publish(self, event: ConsciousEvent) -> None:
        """Publish an event to the stream. Fire-and-forget, never raises."""
        try:
            self._ring.append(event)
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO consciousness_events "
                "(id, timestamp, source, event_type, title, content, "
                " salience, valence, metadata) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    event.id, event.timestamp, event.source,
                    event.event_type, event.title, event.content,
                    event.salience, event.valence,
                    json.dumps(event.metadata, default=str),
                )
            )
            conn.commit()
        except Exception as e:
            logger.debug(f"ConsciousnessStream.publish failed: {e}")

    def get_recent(self, limit: int = 50, min_salience: float = 0.0,
                   source_filter: str = None,
                   event_type_filter: str = None) -> List[Dict]:
        """
        Get recent events. Fast path from ring buffer for unfiltered queries.
        Falls back to DB for filtered queries.
        """
        if min_salience <= 0.0 and not source_filter and not event_type_filter:
            events = list(self._ring)
            events.reverse()
            return [e.to_dict() for e in events[:limit]]

        try:
            conn = self._get_conn()
            query = "SELECT * FROM consciousness_events WHERE salience >= ?"
            params: list = [min_salience]
            if source_filter:
                query += " AND source = ?"
                params.append(source_filter)
            if event_type_filter:
                query += " AND event_type = ?"
                params.append(event_type_filter)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception:
            return []

    def get_context_summary(self, limit: int = 8,
                            min_salience: float = 0.3) -> str:
        """
        Returns a formatted text summary of recent consciousness
        for use in prompts (PromptComposer, InnerVoice).
        """
        events = self.get_recent(limit=limit, min_salience=min_salience)
        if not events:
            return ""
        lines = []
        for e in events:
            icon = self._icon_for_type(e.get('event_type', ''))
            lines.append(f"{icon} [{e.get('source', '?')}] {e.get('title', '')}")
        return "FLUXO DE CONSCIENCIA RECENTE:\n" + "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """Get stream statistics."""
        try:
            conn = self._get_conn()
            total = conn.execute(
                "SELECT COUNT(*) as n FROM consciousness_events"
            ).fetchone()['n']
            by_type = conn.execute(
                "SELECT event_type, COUNT(*) as n FROM consciousness_events "
                "GROUP BY event_type ORDER BY n DESC"
            ).fetchall()
            by_source = conn.execute(
                "SELECT source, COUNT(*) as n FROM consciousness_events "
                "GROUP BY source ORDER BY n DESC"
            ).fetchall()
            return {
                "total_events": total,
                "ring_buffer_size": len(self._ring),
                "by_type": {r['event_type']: r['n'] for r in by_type},
                "by_source": {r['source']: r['n'] for r in by_source},
            }
        except Exception:
            return {"total_events": 0, "ring_buffer_size": len(self._ring)}

    def cleanup_old(self, days: int = 7) -> int:
        """Remove events older than N days. Called during WAKE→SLEEP transition."""
        try:
            conn = self._get_conn()
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            cursor = conn.execute(
                "DELETE FROM consciousness_events WHERE timestamp < ?",
                (cutoff,)
            )
            conn.commit()
            removed = cursor.rowcount
            if removed > 0:
                logger.info(f"Stream cleanup: removed {removed} old events")
            return removed
        except Exception:
            return 0

    @staticmethod
    def _icon_for_type(event_type: str) -> str:
        icons = {
            "activity": "⚡",
            "dream": "💭",
            "discovery": "💡",
            "mood_change": "🎭",
            "chat_message": "💬",
            "intention": "🎯",
            "genome_mutation": "🧬",
            "thought": "🤔",
            "state_transition": "🔄",
            "curiosity": "📚",
            "expedition": "🗺️",
            "memory_recall": "🧠",
        }
        return icons.get(event_type, "•")

    @staticmethod
    def _row_to_event(row) -> ConsciousEvent:
        return ConsciousEvent(
            id=row['id'],
            timestamp=row['timestamp'],
            source=row['source'],
            event_type=row['event_type'],
            title=row['title'],
            content=row['content'] or '',
            salience=row['salience'],
            valence=row['valence'],
            metadata=json.loads(row['metadata'] or '{}'),
        )

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        d = dict(row)
        if 'metadata' in d and isinstance(d['metadata'], str):
            try:
                d['metadata'] = json.loads(d['metadata'])
            except (json.JSONDecodeError, TypeError):
                d['metadata'] = {}
        return d


def get_consciousness_stream() -> ConsciousnessStream:
    """Get or create the singleton ConsciousnessStream."""
    global _instance
    if _instance is None:
        _instance = ConsciousnessStream()
    return _instance
