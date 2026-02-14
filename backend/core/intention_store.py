"""
Intention Store — Bridges chat conversations to autonomous consciousness actions.

When Darwin expresses an intention in chat ("I want to understand how I work")
or Paulo requests something ("explore your memory system"), this store captures
those intentions and feeds them into the consciousness cycle's decision-making.

Without this bridge, chat and consciousness are disconnected — Darwin says things
but never follows through autonomously.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.logger import get_logger as _get_logger

logger = _get_logger(__name__)

# How long intentions stay active before expiring
INTENTION_TTL_HOURS = 48

# Max pending intentions per category (prevent goal flooding)
MAX_PER_CATEGORY = 3

# Max total pending intentions
MAX_TOTAL_PENDING = 12

# Valid categories (map to ActionCategory in proactive_engine)
VALID_CATEGORIES = {
    "exploration", "learning", "optimization", "maintenance",
    "creativity", "communication", "self_understanding"
}

# Keywords that indicate semantically similar intentions
_SIMILARITY_GROUPS = [
    {"memory", "memória", "remember"},
    {"file", "filesystem", "ficheiro", "aceder", "access"},
    {"identity", "self-understanding", "self-awareness", "self-knowledge", "who i am"},
    {"backup", "integrity", "verify"},
    {"improve", "optimize", "enhancement"},
    {"explore", "discover", "investigate"},
    {"learn", "understand", "study"},
    {"error", "mistake", "limit", "bug"},
]


class IntentionStore:
    """Persistent store for intentions extracted from chat conversations."""

    def __init__(self, db_path: str = "./data/darwin.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create the intentions table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent TEXT NOT NULL,
                    category TEXT DEFAULT 'exploration',
                    source TEXT DEFAULT 'chat',
                    confidence REAL DEFAULT 0.7,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    acted_on_at TEXT DEFAULT '',
                    expires_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_intentions_status
                ON intentions(status)
            """)
            conn.commit()
        finally:
            conn.close()

    async def extract_from_conversation(
        self, messages: List[Dict], router
    ):
        """
        Extract intentions from recent chat messages using LLM.

        Follows the same fire-and-forget pattern as PauloModel.update_from_conversation().
        """
        if not router or len(messages) < 2:
            return

        conv_text = "\n".join(
            f"{'Paulo' if m['role'] == 'user' else 'Darwin'}: {m['content'][:300]}"
            for m in messages[-10:]
        )

        try:
            result = await router.generate(
                task_description="extract intentions from conversation",
                prompt=f"""From this conversation, extract any intentions or goals.
An intention is something Darwin wants to do, Paulo asked Darwin to do, or Darwin committed to doing.

Examples of intentions:
- "I want to understand how my memory works" → {{"intent": "understand own memory system", "category": "self_understanding", "confidence": 0.8}}
- "Can you explore quantum computing?" → {{"intent": "explore quantum computing", "category": "exploration", "confidence": 0.9}}
- "I should optimize my code generation" → {{"intent": "optimize code generation pipeline", "category": "optimization", "confidence": 0.7}}

Categories: exploration, learning, optimization, maintenance, creativity, communication, self_understanding

Return ONLY a JSON array. If no intentions found, return [].
Only include clear intentions, not casual chat.

Conversation:
{conv_text}

JSON array:""",
                system_prompt="Extract action intentions. Return valid JSON array only.",
                context={"activity_type": "intention_extraction"},
                max_tokens=500,
                temperature=0.3
            )

            response = result.get("result", "").strip()

            # Clean markdown wrapper if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(
                    lines[1:-1] if lines[-1].startswith("```") else lines[1:]
                )

            intentions = json.loads(response)
            added = 0
            for item in intentions:
                if isinstance(item, dict) and "intent" in item:
                    category = item.get("category", "exploration")
                    if category not in VALID_CATEGORIES:
                        category = "exploration"
                    confidence = min(max(float(item.get("confidence", 0.7)), 0.0), 1.0)

                    if self._is_duplicate(item["intent"]):
                        self._reinforce(item["intent"])
                    else:
                        self._add_intention(
                            intent=item["intent"],
                            category=category,
                            source="chat",
                            confidence=confidence
                        )
                        added += 1

            if added > 0:
                logger.info(f"Extracted {added} intention(s) from conversation")

        except json.JSONDecodeError:
            logger.debug("Intention extraction returned non-JSON (no intentions found)")
        except Exception as e:
            logger.debug(f"Intention extraction failed (non-critical): {e}")

    def _add_intention(
        self, intent: str, category: str, source: str, confidence: float
    ):
        """Insert a new intention into the database."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=INTENTION_TTL_HOURS)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT INTO intentions (intent, category, source, confidence, status, created_at, expires_at)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
                (intent, category, source, confidence,
                 now.isoformat(), expires.isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def _is_duplicate(self, intent: str) -> bool:
        """Check if a similar pending intention already exists (semantic dedup)."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Get all pending intents
            rows = conn.execute(
                "SELECT intent FROM intentions WHERE status = 'pending'"
            ).fetchall()
            intent_lower = intent.lower()

            for (existing,) in rows:
                existing_lower = existing.lower()
                # Exact or substring match
                if intent_lower == existing_lower:
                    return True
                if intent_lower in existing_lower or existing_lower in intent_lower:
                    return True
                # Semantic similarity: share 3+ significant words
                intent_words = set(w for w in intent_lower.split() if len(w) > 3)
                existing_words = set(w for w in existing_lower.split() if len(w) > 3)
                overlap = intent_words & existing_words
                if len(overlap) >= 3:
                    return True
                # Same similarity group
                for group in _SIMILARITY_GROUPS:
                    if any(k in intent_lower for k in group) and any(k in existing_lower for k in group):
                        # Both mention the same concept area AND same category-style words
                        if len(overlap) >= 2:
                            return True

            return False
        finally:
            conn.close()

    def _reinforce(self, intent: str):
        """Boost confidence of an existing matching intention."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """UPDATE intentions SET confidence = MIN(confidence + 0.1, 1.0)
                   WHERE status = 'pending'
                   AND LOWER(intent) = LOWER(?)""",
                (intent,)
            )
            conn.commit()
        finally:
            conn.close()

    def get_pending(self, limit: int = 3) -> List[Dict]:
        """Get top pending intentions, filtering expired ones."""
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT id, intent, category, confidence, created_at
                   FROM intentions
                   WHERE status = 'pending' AND expires_at > ?
                   ORDER BY confidence DESC, created_at DESC
                   LIMIT ?""",
                (now, limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_active_context(self) -> str:
        """Format pending intentions for LLM context injection."""
        pending = self.get_pending(limit=5)
        if not pending:
            return ""

        lines = ["INTENÇÕES PENDENTES (de conversas anteriores):"]
        for i, p in enumerate(pending, 1):
            lines.append(f"- {p['intent']} [{p['category']}]")

        lines.append("Tenta alinhar as tuas atividades com estas intenções quando possível.")
        return "\n".join(lines)

    def mark_acted_on(self, intent_id: int):
        """Mark an intention as being worked on."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """UPDATE intentions SET status = 'in_progress', acted_on_at = ?
                   WHERE id = ?""",
                (datetime.utcnow().isoformat(), intent_id)
            )
            conn.commit()
        finally:
            conn.close()

    def mark_completed(self, intent_id: int):
        """Mark an intention as completed."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE intentions SET status = 'completed' WHERE id = ?",
                (intent_id,)
            )
            conn.commit()
        finally:
            conn.close()

    def expire_old(self):
        """Bulk-expire intentions past their TTL."""
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """UPDATE intentions SET status = 'expired'
                   WHERE status = 'pending' AND expires_at <= ?""",
                (now,)
            )
            expired = cursor.rowcount
            conn.commit()
            if expired > 0:
                logger.info(f"Expired {expired} stale intention(s)")
        finally:
            conn.close()

    def cleanup_duplicates(self):
        """Remove semantically duplicate pending intentions, keeping highest-confidence."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT id, intent, category, confidence FROM intentions WHERE status = 'pending' ORDER BY confidence DESC"
            ).fetchall()

            seen_themes = {}  # category → best intent
            to_remove = []

            for r in rows:
                intent_lower = r['intent'].lower()
                cat = r['category']

                # Check if we already have a similar one in this category
                is_dup = False
                key = f"{cat}"
                if key in seen_themes:
                    for existing_intent in seen_themes[key]:
                        existing_lower = existing_intent.lower()
                        # Word overlap check
                        words_new = set(w for w in intent_lower.split() if len(w) > 3)
                        words_existing = set(w for w in existing_lower.split() if len(w) > 3)
                        if len(words_new & words_existing) >= 2:
                            is_dup = True
                            break
                        if intent_lower in existing_lower or existing_lower in intent_lower:
                            is_dup = True
                            break

                if is_dup:
                    to_remove.append(r['id'])
                else:
                    seen_themes.setdefault(key, []).append(r['intent'])

            # Also enforce per-category limit
            cat_counts = {}
            all_rows = conn.execute(
                "SELECT id, category FROM intentions WHERE status = 'pending' AND id NOT IN ({}) ORDER BY confidence DESC".format(
                    ','.join(str(i) for i in to_remove) if to_remove else '0'
                )
            ).fetchall()
            for r in all_rows:
                cat_counts[r['category']] = cat_counts.get(r['category'], 0) + 1
                if cat_counts[r['category']] > MAX_PER_CATEGORY:
                    to_remove.append(r['id'])

            if to_remove:
                placeholders = ','.join('?' * len(to_remove))
                conn.execute(
                    f"UPDATE intentions SET status = 'consolidated' WHERE id IN ({placeholders})",
                    to_remove
                )
                conn.commit()
                logger.info(f"Cleaned up {len(to_remove)} duplicate/excess intentions")

            return len(to_remove)
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get intention statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            stats = {}
            for status in ('pending', 'in_progress', 'completed', 'expired'):
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM intentions WHERE status = ?",
                    (status,)
                )
                stats[status] = cursor.fetchone()[0]
            return stats
        finally:
            conn.close()
