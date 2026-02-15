"""
InterestWatchdog — Passive organic topic discovery from Darwin's activities.

Monitors activities, findings, and chat for interesting topics and
registers them in the InterestGraph. Pure regex extraction — no AI calls.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Set

from utils.logger import get_logger

logger = get_logger(__name__)


# Operational/technical terms that should never become interests
_NOISE_WORDS = frozenset({
    # Infrastructure
    "git", "docker", "backup", "cpu", "ram", "memory", "disk", "server",
    "port", "timeout", "config", "configuration", "database", "sqlite",
    # File/code ops
    "file", "files", "path", "directory", "folder", "log", "logs", "error",
    "errors", "exception", "traceback", "stack", "debug", "warning",
    # Web/API
    "json", "html", "css", "api", "http", "https", "url", "endpoint",
    "request", "response", "websocket", "cors",
    # Dev tools
    "npm", "pip", "bash", "sudo", "chmod", "mkdir", "curl", "wget",
    "python", "javascript", "typescript", "node", "uvicorn", "fastapi",
    # Darwin internals
    "darwin", "genome", "proactive", "consciousness", "watchdog", "router",
    "ollama", "haiku", "sonnet", "claude", "qwen", "model", "token",
    "prompt", "inference", "embedding",
    # Generic ops
    "todo", "fix", "bug", "test", "tests", "update", "install", "build",
    "deploy", "run", "start", "stop", "restart", "check", "verify",
    # Report/task noise
    "report", "summary", "action", "plan", "locate", "generate", "execute",
    "corrective", "integrity", "entries", "display", "extract", "step",
})

# Signal words that precede interesting topics (PT + EN)
_SIGNAL_PATTERN = re.compile(
    r'(?:sobre|about|interest(?:ed)?\s+in|curious\s+about|learn(?:ing)?\s+about'
    r'|explor(?:e|ing|ar)|descobri[r]?|aprend[ei]r?|estudar|investigar'
    r'|quero\s+saber|fascina)'
    r'\s+(.{3,60}?)(?:\.|,|!|\?|$)',
    re.IGNORECASE
)

# Capitalized multi-word phrases (2-4 words, each starting with uppercase)
_CAPITALIZED_PHRASE = re.compile(
    r'\b([A-ZÀ-Ú][a-zà-ú]+'
    r'(?:\s+(?:de|do|da|dos|das|e|the|of|and|in|for))?\s+'
    r'[A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){0,2})\b'
)

# Common verbs/words that shouldn't end a topic phrase
_STOP_TAIL_WORDS = frozenset({
    "quero", "estou", "tenho", "posso", "gostava", "preciso", "acho",
    "seria", "como", "onde", "quando", "qual", "porque", "também",
    "fala", "diz", "olá", "vou", "sou", "sei", "mas", "ainda",
    "want", "have", "also", "think", "know", "need", "should", "could",
    "the", "this", "that", "then", "here", "there", "but", "and",
})

# Quoted phrases
_QUOTED_PHRASE = re.compile(r'[""«](.{3,50}?)[""»]')


class InterestWatchdog:
    """Passive observer that discovers interesting topics from Darwin's activities."""

    def __init__(self, interest_graph, hierarchical_memory=None):
        self.interest_graph = interest_graph
        self.memory = hierarchical_memory
        self.new_this_cycle = 0
        self.MAX_NEW_PER_CYCLE = 3
        self._seen_topics: Set[str] = set()
        self._history: List[Dict] = []  # observation log (kept last 100)
        self._MAX_HISTORY = 100

        logger.info("InterestWatchdog initialized — organic topic discovery active")

    def _log_observation(self, source: str, input_text: str, extracted: List[str],
                         registered: Optional[str], reject_reasons: List[str]):
        """Record an observation event for the history log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "input_preview": input_text[:120],
            "extracted_topics": extracted,
            "registered": registered,
            "rejected": reject_reasons,
            "cycle_count": self.new_this_cycle,
        }
        self._history.append(entry)
        if len(self._history) > self._MAX_HISTORY:
            self._history = self._history[-self._MAX_HISTORY:]

    def observe_activity(self, goal: str, narrative: str):
        """Extract topics from a completed wake cycle activity."""
        if self.new_this_cycle >= self.MAX_NEW_PER_CYCLE:
            self._log_observation("activity", goal[:120], [], None, ["rate_limit"])
            return

        text = f"{goal} {narrative}"
        topics = self._extract_topics(text)
        registered = None
        rejects = []
        for topic in topics:
            if registered:
                rejects.append(f"{topic}: skipped (already registered one)")
            elif self._register(topic, f"activity: {goal[:50]}"):
                registered = topic
            else:
                rejects.append(f"{topic}: filtered")
        self._log_observation("activity", goal[:120], topics, registered, rejects)

    def observe_finding(self, title: str, description: str, source: str):
        """Extract topics from a new finding."""
        if self.new_this_cycle >= self.MAX_NEW_PER_CYCLE:
            self._log_observation("finding", title[:120], [], None, ["rate_limit"])
            return

        text = f"{title} {description}"
        topics = self._extract_topics(text)
        registered = None
        rejects = []
        for topic in topics:
            if registered:
                rejects.append(f"{topic}: skipped (already registered one)")
            elif self._register(topic, f"finding: {title[:50]}"):
                registered = topic
            else:
                rejects.append(f"{topic}: filtered")
        self._log_observation("finding", title[:120], topics, registered, rejects)

    def observe_chat(self, messages: List[Dict]):
        """Extract topics from chat messages — prioritize Paulo's messages."""
        # Only look at Paulo's messages (user interests matter most)
        user_text = " ".join(
            msg.get("content", "")
            for msg in messages
            if msg.get("role") in ("user", "human")
        )
        if not user_text.strip():
            return

        if self.new_this_cycle >= self.MAX_NEW_PER_CYCLE:
            self._log_observation("chat", user_text[:120], [], None, ["rate_limit"])
            return

        topics = self._extract_topics(user_text)
        registered = None
        rejects = []
        for topic in topics:
            if registered:
                rejects.append(f"{topic}: skipped (already registered one)")
            elif self._register(topic, "chat"):
                registered = topic
            else:
                rejects.append(f"{topic}: filtered")
        self._log_observation("chat", user_text[:120], topics, registered, rejects)

    def _extract_topics(self, text: str) -> List[str]:
        """Extract candidate topics from text using regex patterns."""
        if not text or len(text) < 10:
            return []

        candidates = []

        # 1. After signal words (highest quality)
        for match in _SIGNAL_PATTERN.finditer(text):
            phrase = match.group(1).strip().rstrip(".,!?;:")
            if phrase:
                candidates.append(phrase)

        # 2. Quoted phrases
        for match in _QUOTED_PHRASE.finditer(text):
            phrase = match.group(1).strip()
            if phrase:
                candidates.append(phrase)

        # 3. Capitalized multi-word phrases
        for match in _CAPITALIZED_PHRASE.finditer(text):
            phrase = match.group(1).strip()
            # Skip if it's at the start of a sentence (common false positive)
            pos = match.start()
            if pos > 0 and text[pos - 1] not in ".!?\n":
                # Trim trailing stop words (e.g. "Medieval Quero" → "Medieval")
                words = phrase.split()
                while len(words) > 1 and words[-1].lower() in _STOP_TAIL_WORDS:
                    words.pop()
                if len(words) >= 2:
                    candidates.append(" ".join(words))

        # Deduplicate and filter
        seen = set()
        filtered = []
        for topic in candidates:
            normalized = topic.lower().strip()
            if normalized in seen:
                continue
            seen.add(normalized)

            words = normalized.split()
            # Must be 2-6 words
            if len(words) < 2 or len(words) > 6:
                continue
            # No noise words dominating
            noise_count = sum(1 for w in words if w in _NOISE_WORDS)
            if noise_count > len(words) // 2:
                continue
            # Not too short overall
            if len(normalized) < 5:
                continue

            filtered.append(topic)

        return filtered[:5]  # max 5 candidates per observation

    def _check_worth(self, topic: str) -> Optional[str]:
        """Check if topic is worth adding. Returns reject reason or None if OK."""
        key = self.interest_graph._key(topic)

        if key in self._seen_topics:
            return "seen_this_cycle"
        self._seen_topics.add(key)

        if key in self.interest_graph.active_interests:
            return "already_active"
        if key in self.interest_graph.dormant_interests:
            return "already_dormant"

        if self.memory:
            try:
                words = set(topic.lower().split())
                knowledge = self.memory.search_semantic_knowledge(
                    tags=words, min_confidence=0.7, limit=1
                )
                if knowledge:
                    return "in_semantic_memory"
            except Exception:
                pass

        return None  # worth registering

    def _register(self, topic: str, sparked_by: str) -> bool:
        """Register a topic as a new interest. Returns True if registered."""
        if self.new_this_cycle >= self.MAX_NEW_PER_CYCLE:
            return False

        reject = self._check_worth(topic)
        if reject:
            return False

        self.interest_graph.discover_interest(
            topic=topic,
            sparked_by=f"watchdog/{sparked_by}",
            enthusiasm=0.5
        )
        self.new_this_cycle += 1
        logger.info(f"InterestWatchdog: new interest '{topic}' (sparked by: {sparked_by})")
        return True

    def reset_cycle(self):
        """Reset per-cycle counters. Called at wake→sleep transition."""
        if self.new_this_cycle > 0:
            logger.info(f"InterestWatchdog: cycle reset ({self.new_this_cycle} topics discovered)")
        self.new_this_cycle = 0
        self._seen_topics.clear()

    def get_stats(self) -> Dict:
        """Stats for Observatory."""
        return {
            "new_this_cycle": self.new_this_cycle,
            "max_per_cycle": self.MAX_NEW_PER_CYCLE,
            "seen_topics_count": len(self._seen_topics),
            "total_observations": len(self._history),
            "total_registered": sum(1 for h in self._history if h.get("registered")),
        }

    def get_history(self, limit: int = 30) -> List[Dict]:
        """Get recent observation history for the dashboard."""
        return list(reversed(self._history[-limit:]))
