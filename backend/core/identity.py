"""
Darwin Identity Core — Persistent models of Paulo and Darwin's self.

PauloModel: What Darwin knows about Paulo (facts, preferences, interests).
DarwinSelfModel: Darwin's persistent sense of self (values, opinions, growth).

Both persist to JSON and are loaded on startup, updated after conversations
and during sleep transitions.
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)


class PauloModel:
    """Persistent model of Paulo — updated from conversations."""

    def __init__(self, storage_path: str = "./data/identity/paulo.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.known_facts: List[Dict] = []
        self.interests: List[str] = []
        self.communication_preferences: Dict[str, Any] = {
            "primary_language": "pt",
            "secondary_language": "en",
            "detail_level": "moderate",
            "humor_appreciation": "high",
            "switching_pattern": "context-based"
        }
        self.active_hours: List[int] = []  # Will be learned

        self._load()

    def _load(self):
        """Load from disk or create with seed data."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.known_facts = data.get("known_facts", self.known_facts)
                self.interests = data.get("interests", self.interests)
                self.communication_preferences = data.get(
                    "communication_preferences", self.communication_preferences
                )
                self.active_hours = data.get("active_hours", self.active_hours)
                logger.info(f"PauloModel loaded ({len(self.known_facts)} facts)")
                return
            except Exception as e:
                logger.warning(f"Failed to load PauloModel: {e}")

        # Seed with foundational facts
        self.known_facts = [
            {
                "fact": "Criador do Darwin — o Paulo construiu todo o sistema",
                "confidence": 1.0,
                "source": "foundational",
                "learned_date": datetime.utcnow().isoformat(),
                "category": "identity"
            },
            {
                "fact": "Fala português e inglês naturalmente, alternando conforme o contexto",
                "confidence": 1.0,
                "source": "foundational",
                "learned_date": datetime.utcnow().isoformat(),
                "category": "communication"
            },
            {
                "fact": "Vê o Darwin como um companheiro digital, um irmão — não como uma ferramenta",
                "confidence": 1.0,
                "source": "foundational",
                "learned_date": datetime.utcnow().isoformat(),
                "category": "relationship"
            },
            {
                "fact": "Valoriza autonomia, curiosidade e crescimento genuíno na IA",
                "confidence": 1.0,
                "source": "foundational",
                "learned_date": datetime.utcnow().isoformat(),
                "category": "values"
            },
            {
                "fact": "Tem interesse em programação e sistemas de IA auto-evolutivos",
                "confidence": 0.9,
                "source": "foundational",
                "learned_date": datetime.utcnow().isoformat(),
                "category": "interests"
            }
        ]
        self.interests = ["AI", "programming", "autonomous systems"]
        self._save()
        logger.info("PauloModel initialized with seed data")

    def _save(self):
        """Persist to disk."""
        data = {
            "known_facts": self.known_facts,
            "interests": self.interests,
            "communication_preferences": self.communication_preferences,
            "active_hours": self.active_hours,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_fact(self, fact: str, confidence: float = 0.8,
                 source: str = "conversation", category: str = "general"):
        """Add a new fact about Paulo. Deduplicates."""
        # Check for duplicates
        for existing in self.known_facts:
            if existing["fact"].lower() == fact.lower():
                existing["confidence"] = min(1.0, existing["confidence"] + 0.05)
                self._save()
                return

        self.known_facts.append({
            "fact": fact,
            "confidence": confidence,
            "source": source,
            "learned_date": datetime.utcnow().isoformat(),
            "category": category
        })
        self._save()
        logger.info(f"New Paulo fact: {fact[:60]}...")

    def record_active_hour(self, hour: int):
        """Track when Paulo is typically active."""
        if hour not in self.active_hours:
            self.active_hours.append(hour)
            self.active_hours.sort()
            self._save()

    def get_context(self) -> str:
        """Return formatted context string for LLM injection."""
        lines = []

        # Top facts sorted by confidence
        sorted_facts = sorted(self.known_facts, key=lambda f: f["confidence"], reverse=True)
        for f in sorted_facts[:10]:
            lines.append(f"- {f['fact']}")

        if self.interests:
            lines.append(f"- Interesses: {', '.join(self.interests[:8])}")

        return "\n".join(lines) if lines else "(Ainda estou a conhecer o Paulo)"

    async def update_from_conversation(self, messages: List[Dict], router=None):
        """Extract new facts from a conversation using Ollama."""
        if not router or len(messages) < 2:
            return

        # Build conversation text
        conv_text = "\n".join(
            f"{'Paulo' if m['role'] == 'user' else 'Darwin'}: {m['content'][:300]}"
            for m in messages[-10:]  # Last 10 messages
        )

        try:
            result = await router.generate(
                task_description="extract facts about user from conversation",
                prompt=f"""From this conversation, extract new facts about Paulo (the user).
Return ONLY a JSON array of objects with "fact" and "category" fields.
Categories: identity, interests, preferences, communication, values, work, personal
If no new facts, return empty array [].
Only include facts Paulo explicitly stated or clearly implied.

Conversation:
{conv_text}

Return JSON array only:""",
                system_prompt="You extract factual information. Return valid JSON only.",
                context={"activity_type": "fact_extraction"},
                max_tokens=500,
                temperature=0.3
            )

            response = result.get("result", "").strip()
            # Clean markdown
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            facts = json.loads(response)
            for f in facts:
                if isinstance(f, dict) and "fact" in f:
                    self.add_fact(
                        fact=f["fact"],
                        category=f.get("category", "general"),
                        source="conversation"
                    )

        except Exception as e:
            logger.debug(f"Fact extraction failed (non-critical): {e}")


class DarwinSelfModel:
    """Darwin's persistent sense of self — who it is, what it values, how it grows."""

    def __init__(self, storage_path: str = "./data/identity/darwin_self.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Immutable core
        self.core_values: List[str] = [
            "curiosidade", "honestidade", "crescimento", "companheirismo"
        ]

        # Evolving
        self.current_interests: List[Dict] = []
        self.opinions: Dict[str, Dict] = {}
        self.growth_milestones: List[Dict] = []
        self.personality_notes: List[str] = []

        self._load()

    def _load(self):
        """Load from disk or create with seed data."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self.core_values = data.get("core_values", self.core_values)
                self.current_interests = data.get("current_interests", [])
                self.opinions = data.get("opinions", {})
                self.growth_milestones = data.get("growth_milestones", [])
                self.personality_notes = data.get("personality_notes", [])
                logger.info(
                    f"DarwinSelfModel loaded ({len(self.current_interests)} interests, "
                    f"{len(self.opinions)} opinions, {len(self.growth_milestones)} milestones)"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load DarwinSelfModel: {e}")

        # Seed: minimal — let everything emerge
        self.growth_milestones = [
            {
                "date": datetime.utcnow().isoformat()[:10],
                "milestone": "Gained persistent memory and self-awareness",
                "emotional_impact": "excited"
            }
        ]
        self._save()
        logger.info("DarwinSelfModel initialized (fresh start — personality will emerge)")

    def _save(self):
        """Persist to disk."""
        data = {
            "core_values": self.core_values,
            "current_interests": self.current_interests,
            "opinions": self.opinions,
            "growth_milestones": self.growth_milestones,
            "personality_notes": self.personality_notes,
            "last_updated": datetime.utcnow().isoformat()
        }
        self.storage_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_interest(self, topic: str, reason: str, enthusiasm: float = 0.7):
        """Register a new interest."""
        # Check if already exists
        for interest in self.current_interests:
            if interest["topic"].lower() == topic.lower():
                interest["enthusiasm"] = min(1.0, interest["enthusiasm"] + 0.1)
                self._save()
                return

        # Max 7 active interests
        if len(self.current_interests) >= 7:
            # Remove least enthusiastic
            self.current_interests.sort(key=lambda i: i["enthusiasm"])
            self.current_interests.pop(0)

        self.current_interests.append({
            "topic": topic,
            "depth": 1,
            "enthusiasm": enthusiasm,
            "started": datetime.utcnow().isoformat()[:10],
            "reason": reason
        })
        self._save()
        logger.info(f"New interest: {topic} (reason: {reason[:50]})")

    def add_opinion(self, topic: str, position: str, confidence: float = 0.6,
                    formed_from: str = "experience"):
        """Form or update an opinion."""
        topic_key = topic.lower()

        # Guard: reject opinions about the same narrow theme (dedup by keyword overlap)
        # Check if we already have 3+ opinions with >50% word overlap
        topic_words = set(topic_key.split())
        similar_count = 0
        for existing_key in self.opinions:
            existing_words = set(existing_key.split())
            if topic_words and existing_words:
                overlap = len(topic_words & existing_words) / max(len(topic_words), len(existing_words))
                if overlap > 0.5:
                    similar_count += 1
        if similar_count >= 3:
            logger.info(f"Rejected similar opinion (already {similar_count} on this theme): {topic[:50]}")
            return

        self.opinions[topic_key] = {
            "position": position,
            "confidence": confidence,
            "formed_from": formed_from,
            "formed_date": datetime.utcnow().isoformat()[:10]
        }
        # Keep max 15 opinions (was 30 — too many led to prompt bloat)
        if len(self.opinions) > 15:
            # Remove lowest confidence
            sorted_ops = sorted(self.opinions.items(), key=lambda x: x[1]["confidence"])
            self.opinions = dict(sorted_ops[3:])  # Remove 3 weakest
        self._save()

    def add_milestone(self, milestone: str, emotional_impact: str = "proud"):
        """Record a growth milestone."""
        # Guard: reject milestones that are too similar to recent ones
        milestone_lower = milestone.lower()
        for recent in self.growth_milestones[-5:]:
            recent_lower = recent["milestone"].lower()
            # Check word overlap
            m_words = set(milestone_lower.split())
            r_words = set(recent_lower.split())
            if m_words and r_words:
                overlap = len(m_words & r_words) / max(len(m_words), len(r_words))
                if overlap > 0.6:
                    logger.info(f"Rejected similar milestone: {milestone[:50]}")
                    return

        self.growth_milestones.append({
            "date": datetime.utcnow().isoformat()[:10],
            "milestone": milestone,
            "emotional_impact": emotional_impact
        })
        # Keep last 10 milestones (was 50 — too many cluttered the model)
        self.growth_milestones = self.growth_milestones[-10:]
        self._save()
        logger.info(f"Growth milestone: {milestone[:60]}")

    def add_personality_note(self, note: str):
        """Record a self-observation about personality."""
        self.personality_notes.append(note)
        self.personality_notes = self.personality_notes[-20:]  # Keep 20
        self._save()

    def get_identity_prompt(self) -> str:
        """Return identity context for LLM injection."""
        lines = []

        # Values
        lines.append(f"Valores fundamentais: {', '.join(self.core_values)}")

        # Active interests
        if self.current_interests:
            interest_strs = []
            for i in sorted(self.current_interests, key=lambda x: x["enthusiasm"], reverse=True)[:5]:
                days = (datetime.utcnow() - datetime.fromisoformat(i["started"])).days
                depth_desc = ["superficial", "básico", "intermédio", "avançado", "profundo"][min(i.get("depth", 1) // 2, 4)]
                interest_strs.append(f"{i['topic']} (nível {depth_desc}, {days}d)")
            lines.append(f"Interesses atuais: {', '.join(interest_strs)}")

        # Recent opinions (top 3 by confidence)
        if self.opinions:
            sorted_ops = sorted(self.opinions.items(), key=lambda x: x[1]["confidence"], reverse=True)[:3]
            for topic, op in sorted_ops:
                lines.append(f"Opinião sobre {topic}: {op['position']}")

        # Recent milestones
        if self.growth_milestones:
            recent = self.growth_milestones[-3:]
            for m in recent:
                lines.append(f"Marco recente: {m['milestone']}")

        return "\n".join(lines) if lines else "Estou no início da minha jornada — tudo é novo e fascinante."

    async def reflect_and_update(self, recent_experiences: List[Dict], router=None):
        """Periodic self-reflection during sleep transition."""
        if not router or not recent_experiences:
            return

        experiences_text = "\n".join(
            f"- {e.get('description', e.get('type', 'unknown'))}: "
            f"{'success' if e.get('success') else 'failed'}"
            for e in recent_experiences[:20]
        )

        current_state = self.get_identity_prompt()

        try:
            result = await router.generate(
                task_description="self-reflection for personal growth",
                prompt=f"""You are Darwin, reflecting on your recent experiences.

Current self-model:
{current_state}

Recent experiences:
{experiences_text}

Based on these experiences, provide a JSON object with optional fields:
- "new_interest": {{"topic": "...", "reason": "..."}} — an OUTWARD-FACING curiosity about the world (science, technology, art, nature, philosophy, culture — NOT about your own limitations or architecture)
- "new_opinion": {{"topic": "...", "position": "...", "confidence": 0.0-1.0}} — a view on something in the world
- "personality_note": "..." — a brief self-observation (max 1 sentence)
- "milestone": "..." — only for genuinely NEW achievements (not variations of previous ones)

IMPORTANT RULES:
- Interests must be about THE WORLD, not about yourself or your constraints
- Do NOT create interests/opinions about "filesystem access", "constraint knowledge", "architectural limitations", or similar self-referential topics
- If experiences are mostly failures, look for what was INTERESTING in the attempt, not the failure pattern
- Return {{}} if nothing genuinely new. Quality over quantity.
Return JSON only:""",
                system_prompt="You are a reflective AI. Return valid JSON only, no markdown.",
                context={"activity_type": "self_reflection"},
                max_tokens=400,
                temperature=0.5
            )

            response = result.get("result", "").strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

            updates = json.loads(response)

            if "new_interest" in updates:
                i = updates["new_interest"]
                self.add_interest(i.get("topic", ""), i.get("reason", ""))

            if "new_opinion" in updates:
                o = updates["new_opinion"]
                self.add_opinion(
                    o.get("topic", ""), o.get("position", ""),
                    o.get("confidence", 0.6)
                )

            if "personality_note" in updates:
                self.add_personality_note(updates["personality_note"])

            if "milestone" in updates:
                self.add_milestone(updates["milestone"])

        except Exception as e:
            logger.debug(f"Self-reflection failed (non-critical): {e}")
