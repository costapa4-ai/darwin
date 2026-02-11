"""
Persistent Conversation Store — Darwin's long-term conversation memory.

SQLite-backed storage for all chat messages (web + telegram).
Survives restarts. Enables Darwin to remember past conversations,
learn about Paulo, and reference previous discussions naturally.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)

# Thread-local storage for SQLite connections (SQLite is not thread-safe)
_local = threading.local()


class ConversationStore:
    """Persistent conversation memory with search and summarization."""

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self._init_tables()
        count = self._get_message_count()
        logger.info(f"ConversationStore initialized ({count} messages in history)")

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection."""
        if not hasattr(_local, 'conn') or _local.conn is None:
            _local.conn = sqlite3.connect(self.db_path)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA journal_mode=WAL")
        return _local.conn

    def _init_tables(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                channel TEXT DEFAULT 'web',
                mood TEXT DEFAULT '',
                consciousness_state TEXT DEFAULT '',
                personality_mode TEXT DEFAULT 'normal',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT DEFAULT '[]',
                facts_learned TEXT DEFAULT '[]',
                emotional_highlights TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS relationship_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                confidence REAL DEFAULT 0.8,
                source TEXT DEFAULT '',
                learned_date TEXT NOT NULL,
                category TEXT DEFAULT 'general'
            );

            CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON chat_messages(timestamp);
            CREATE INDEX IF NOT EXISTS idx_chat_channel ON chat_messages(channel);
            CREATE INDEX IF NOT EXISTS idx_chat_role ON chat_messages(role);
            CREATE INDEX IF NOT EXISTS idx_summaries_date ON conversation_summaries(date);
            CREATE INDEX IF NOT EXISTS idx_facts_category ON relationship_facts(category);
        """)
        conn.commit()

    def _get_message_count(self) -> int:
        """Get total message count."""
        conn = self._get_conn()
        row = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()
        return row[0] if row else 0

    def save_message(
        self,
        role: str,
        content: str,
        channel: str = "web",
        mood: str = "",
        consciousness_state: str = "",
        personality_mode: str = "normal",
        metadata: Optional[Dict] = None
    ) -> int:
        """Save a chat message and return its ID."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO chat_messages
               (role, content, timestamp, channel, mood, consciousness_state, personality_mode, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                role,
                content,
                datetime.utcnow().isoformat(),
                channel,
                mood,
                consciousness_state,
                personality_mode,
                json.dumps(metadata or {})
            )
        )
        conn.commit()
        return cursor.lastrowid

    def get_recent(self, limit: int = 20, channel: Optional[str] = None) -> List[Dict]:
        """Get recent messages, optionally filtered by channel."""
        conn = self._get_conn()
        if channel:
            rows = conn.execute(
                "SELECT * FROM chat_messages WHERE channel = ? ORDER BY id DESC LIMIT ?",
                (channel, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_messages ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def get_context_window(self, limit: int = 10) -> str:
        """Build a formatted conversation context string for LLM injection."""
        messages = self.get_recent(limit)
        if not messages:
            return "(Primeira conversa — ainda não falámos antes)"

        lines = []
        for msg in messages:
            role = "Paulo" if msg['role'] == 'user' else "Darwin"
            # Truncate long messages for context
            content = msg['content'][:200]
            if len(msg['content']) > 200:
                content += "..."
            ts = msg['timestamp'][:16].replace('T', ' ')
            lines.append(f"[{ts}] {role}: {content}")

        return "\n".join(lines)

    def search_past(self, query: str, limit: int = 5) -> List[Dict]:
        """Search past conversations by keyword."""
        conn = self._get_conn()
        # Simple LIKE search — good enough for most cases
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_today_messages(self) -> List[Dict]:
        """Get all messages from today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE timestamp LIKE ? ORDER BY id",
            (f"{today}%",)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_today_summary(self) -> Optional[str]:
        """Get today's conversation summary if it exists."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = self._get_conn()
        row = conn.execute(
            "SELECT summary FROM conversation_summaries WHERE date = ?",
            (today,)
        ).fetchone()
        return row['summary'] if row else None

    def save_daily_summary(
        self,
        date: str,
        summary: str,
        key_topics: List[str] = None,
        facts_learned: List[str] = None,
        emotional_highlights: List[str] = None
    ):
        """Save or update a daily conversation summary."""
        conn = self._get_conn()
        # Check if exists
        existing = conn.execute(
            "SELECT id FROM conversation_summaries WHERE date = ?",
            (date,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE conversation_summaries
                   SET summary = ?, key_topics = ?, facts_learned = ?, emotional_highlights = ?
                   WHERE date = ?""",
                (
                    summary,
                    json.dumps(key_topics or []),
                    json.dumps(facts_learned or []),
                    json.dumps(emotional_highlights or []),
                    date
                )
            )
        else:
            conn.execute(
                """INSERT INTO conversation_summaries
                   (date, summary, key_topics, facts_learned, emotional_highlights, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    summary,
                    json.dumps(key_topics or []),
                    json.dumps(facts_learned or []),
                    json.dumps(emotional_highlights or []),
                    datetime.utcnow().isoformat()
                )
            )
        conn.commit()

    def get_recent_summaries(self, days: int = 7) -> List[Dict]:
        """Get conversation summaries from the last N days."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM conversation_summaries WHERE date >= ? ORDER BY date DESC",
            (cutoff,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ==================== Relationship Facts ====================

    def get_relationship_facts(self, category: Optional[str] = None) -> List[Dict]:
        """Get stored facts about Paulo."""
        conn = self._get_conn()
        if category:
            rows = conn.execute(
                "SELECT * FROM relationship_facts WHERE category = ? ORDER BY confidence DESC",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM relationship_facts ORDER BY confidence DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_relationship_context(self) -> str:
        """Get formatted relationship facts for LLM injection."""
        facts = self.get_relationship_facts()
        if not facts:
            return "(Ainda estou a conhecer o Paulo — é o meu criador)"

        lines = []
        for f in facts[:15]:  # Top 15 facts by confidence
            lines.append(f"- {f['fact']}")
        return "\n".join(lines)

    def store_relationship_fact(
        self,
        fact: str,
        source: str = "conversation",
        confidence: float = 0.8,
        category: str = "general"
    ) -> int:
        """Store a new fact about Paulo. Deduplicates by content similarity."""
        conn = self._get_conn()

        # Simple dedup: check if very similar fact exists
        existing = conn.execute(
            "SELECT id, confidence FROM relationship_facts WHERE fact = ?",
            (fact,)
        ).fetchone()

        if existing:
            # Reinforce confidence
            new_confidence = min(1.0, existing['confidence'] + 0.05)
            conn.execute(
                "UPDATE relationship_facts SET confidence = ? WHERE id = ?",
                (new_confidence, existing['id'])
            )
            conn.commit()
            return existing['id']

        cursor = conn.execute(
            """INSERT INTO relationship_facts (fact, confidence, source, learned_date, category)
               VALUES (?, ?, ?, ?, ?)""",
            (fact, confidence, source, datetime.utcnow().isoformat(), category)
        )
        conn.commit()
        logger.info(f"New relationship fact stored: {fact[:60]}...")
        return cursor.lastrowid

    # ==================== Maintenance ====================

    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        user_msgs = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE role = 'user'").fetchone()[0]
        darwin_msgs = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE role = 'darwin'").fetchone()[0]
        summaries = conn.execute("SELECT COUNT(*) FROM conversation_summaries").fetchone()[0]
        facts = conn.execute("SELECT COUNT(*) FROM relationship_facts").fetchone()[0]

        # Messages per channel
        channels = conn.execute(
            "SELECT channel, COUNT(*) as count FROM chat_messages GROUP BY channel"
        ).fetchall()

        return {
            "total_messages": total,
            "user_messages": user_msgs,
            "darwin_messages": darwin_msgs,
            "daily_summaries": summaries,
            "relationship_facts": facts,
            "messages_by_channel": {r['channel']: r['count'] for r in channels}
        }

    def cleanup_old_messages(self, keep_days: int = 30):
        """Archive messages older than keep_days (keep summaries forever)."""
        cutoff = (datetime.utcnow() - timedelta(days=keep_days)).isoformat()
        conn = self._get_conn()
        deleted = conn.execute(
            "DELETE FROM chat_messages WHERE timestamp < ?",
            (cutoff,)
        ).rowcount
        conn.commit()
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} messages older than {keep_days} days")
        return deleted
