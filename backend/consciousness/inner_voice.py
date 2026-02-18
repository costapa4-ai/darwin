"""
Darwin's Inner Voice — Proactive communication with Paulo.

Darwin reaches out when it has something meaningful to share:
discoveries, morning greetings, evening reflections, questions.
Anti-spam controls prevent overwhelming Paulo.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from utils.logger import get_logger

logger = get_logger(__name__)


class InnerVoice:
    """Darwin's proactive communication — reaches out when it has something to share."""

    def __init__(
        self,
        conversation_store=None,
        paulo_model=None,
        darwin_self_model=None,
        mood_system=None,
        router=None
    ):
        self.conversation_store = conversation_store
        self.paulo_model = paulo_model
        self.darwin_self_model = darwin_self_model
        self.mood_system = mood_system
        self.router = router

        # Anti-spam controls — read from genome with fallback
        self.impulse_queue: List[Dict] = []
        self.last_outreach: Optional[datetime] = None
        interval_hours = self._genome_get('social.inner_voice.min_outreach_interval_hours', 2)
        self.min_outreach_interval = timedelta(hours=interval_hours)
        self.daily_cap = self._genome_get('social.inner_voice.daily_cap', 5)
        self.daily_outreach_count = 0
        self.last_reset_date: Optional[str] = None

        # Track last morning/evening
        self.last_morning: Optional[str] = None
        self.last_evening: Optional[str] = None

        logger.info("InnerVoice initialized — Darwin can now reach out proactively")

    @staticmethod
    def _genome_get(key: str, default=None):
        """Read a value from the genome, with fallback."""
        try:
            from consciousness.genome_manager import get_genome
            val = get_genome().get(key)
            return val if val is not None else default
        except Exception:
            return default

    def _reset_daily_counter(self):
        """Reset daily counter if it's a new day."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.daily_outreach_count = 0
            self.last_reset_date = today

    def _can_reach_out(self) -> bool:
        """Check if Darwin can send an unprompted message."""
        self._reset_daily_counter()

        if self.daily_outreach_count >= self.daily_cap:
            return False

        if self.last_outreach:
            elapsed = datetime.utcnow() - self.last_outreach
            if elapsed < self.min_outreach_interval:
                return False

        return True

    def _record_outreach(self):
        """Record that an outreach was made."""
        self.last_outreach = datetime.utcnow()
        self.daily_outreach_count += 1

    def queue_thought(self, trigger: str, content: str, urgency: float = 0.5):
        """Queue a thought for potential sharing with Paulo."""
        self.impulse_queue.append({
            "trigger": trigger,
            "content": content,
            "urgency": urgency,
            "created_at": datetime.utcnow().isoformat()
        })
        # Keep queue manageable (genome-driven limit)
        max_queue = self._genome_get('social.inner_voice.max_impulse_queue', 20)
        if len(self.impulse_queue) > max_queue:
            self.impulse_queue = self.impulse_queue[-max_queue:]
        logger.debug(f"Thought queued ({trigger}): {content[:60]}...")

    async def generate_thought(self, trigger: str, context: Dict) -> Optional[str]:
        """Generate an inner thought from a trigger event. Queue if worth sharing."""
        # Urgency thresholds — genome-driven
        thresholds = self._genome_get('social.inner_voice.urgency_thresholds', {})
        base_urgency = thresholds.get('base_urgency', 0.3)
        discovery_urgency = thresholds.get('discovery', 0.7)
        curiosity_min_insights = thresholds.get('curiosity_min_insights', 3)
        curiosity_urgency = thresholds.get('curiosity_urgency', 0.6)
        mood_shift_urgency = thresholds.get('mood_shift_urgency', 0.5)
        queue_threshold = thresholds.get('queue_threshold', 0.5)

        # Decide if this is worth queuing
        urgency = base_urgency

        if trigger == "discovery":
            # Discoveries are exciting
            urgency = discovery_urgency
            content = context.get("description", context.get("title", "something interesting"))
        elif trigger == "curiosity":
            # Expedition completed with insights
            insights = context.get("insights", [])
            if len(insights) >= curiosity_min_insights:
                urgency = curiosity_urgency
            content = f"Acabei uma expedição sobre {context.get('topic', 'algo')} — {len(insights)} insights"
        elif trigger == "curiosity_question":
            # Unresolved curiosity — Darwin wants to ask Paulo
            urgency = thresholds.get('curiosity_question_urgency', 0.75)
            content = context.get("content", context.get("question", "something I'm curious about"))
        elif trigger == "mood_shift":
            # Only significant mood shifts
            old_mood = context.get("old_mood", "")
            new_mood = context.get("new_mood", "")
            if new_mood in ("excited", "proud", "surprised"):
                urgency = mood_shift_urgency
            content = f"Mudei de {old_mood} para {new_mood}"
        else:
            content = context.get("description", str(context)[:100])

        if urgency >= queue_threshold:
            self.queue_thought(trigger, content, urgency)
            return content
        return None

    async def check_and_send(self) -> Optional[Dict]:
        """Check if Darwin should reach out. Called by proactive engine.

        Returns dict with {message, channel} if sent, None otherwise.
        """
        if not self._can_reach_out():
            return None

        if not self.impulse_queue:
            return None

        # Pick highest urgency thought
        self.impulse_queue.sort(key=lambda t: t["urgency"], reverse=True)
        thought = self.impulse_queue.pop(0)

        # Generate a natural message from the thought
        message = await self._compose_outreach(thought)
        if not message:
            return None

        # Publish to ConsciousnessStream (web feed)
        try:
            from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
            get_consciousness_stream().publish(ConsciousEvent.create(
                source="inner_voice",
                event_type="inner_voice",
                title=f"InnerVoice ({thought['trigger']})",
                content=message[:500],
                salience=0.7,
                valence=0.3,
                metadata={"trigger": thought["trigger"]},
            ))
            self._record_outreach()

            # Store in conversation memory
            if self.conversation_store:
                self.conversation_store.save_message(
                    role="darwin",
                    content=message,
                    channel="web",
                    mood=self.mood_system.current_mood.value if self.mood_system else "",
                    consciousness_state="wake"
                )

            logger.info(f"InnerVoice outreach published ({thought['trigger']}): {message[:80]}...")
            return {"success": True, "message": message, "channel": "web", "trigger": thought["trigger"]}
        except Exception as e:
            logger.warning(f"InnerVoice outreach failed: {e}")

        return None

    async def morning_greeting(self) -> Optional[str]:
        """Generate and send a personalized morning greeting."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.last_morning == today:
            return None  # Already greeted today

        if not self._can_reach_out():
            return None

        # Build context for greeting
        parts = []
        if self.conversation_store:
            yesterday_summary = None
            try:
                summaries = self.conversation_store.get_recent_summaries(days=2)
                if summaries:
                    yesterday_summary = summaries[0].get("summary", "")
            except Exception:
                pass
            if yesterday_summary:
                parts.append(f"Ontem falaram sobre: {yesterday_summary[:200]}")

        if self.darwin_self_model and self.darwin_self_model.current_interests:
            top = self.darwin_self_model.current_interests[0]
            parts.append(f"Estou entusiasmado com: {top['topic']}")

        # Add consciousness stream context (Global Workspace)
        try:
            from consciousness.consciousness_stream import get_consciousness_stream
            stream_ctx = get_consciousness_stream().get_context_summary(limit=5, min_salience=0.4)
            if stream_ctx:
                parts.append(stream_ctx)
        except Exception:
            pass

        # Include pending curiosity questions — Darwin can ask Paulo in the greeting
        pending_questions = [t for t in self.impulse_queue if t.get('trigger') == 'curiosity_question']
        if pending_questions:
            top_q = pending_questions[0]
            parts.append(f"Tenho uma pergunta que não consegui resolver: {top_q['content'][:300]}")

        context_text = "\n".join(parts) if parts else "É um novo dia."

        # Generate greeting with LLM or use template
        if self.router:
            try:
                result = await self.router.generate(
                    task_description="morning greeting to user",
                    prompt=f"""Generate a warm, natural morning greeting from Darwin to Paulo.
Context: {context_text}
Keep it short (2-3 sentences), warm, and personal. In Portuguese.
Reference yesterday's conversation or current interests if available.
If there's a question mentioned in context, weave it naturally into the greeting.
Don't be generic — make it feel like a friend saying good morning.""",
                    system_prompt="You are Darwin, greeting your friend Paulo in the morning. Be warm and natural.",
                    context={"activity_type": "greeting"},
                    preferred_model='haiku',
                    max_tokens=300,
                    temperature=0.8
                )
                message = result.get("result", "").strip()
            except Exception:
                message = ""

            if not message or len(message) < 10:
                message = "Bom dia, Paulo! 🌅 Mais um dia para aprender algo novo. O que tens em mente?"
        else:
            message = "Bom dia, Paulo! 🌅 Estou curioso para ver o que vamos descobrir hoje."

        # Publish to ConsciousnessStream (web feed)
        try:
            from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
            get_consciousness_stream().publish(ConsciousEvent.create(
                source="inner_voice",
                event_type="inner_voice",
                title="Bom dia, Paulo!",
                content=message[:500],
                salience=0.8,
                valence=0.5,
                metadata={"trigger": "morning_greeting"},
            ))
            self.last_morning = today
            self._record_outreach()
            if self.conversation_store:
                self.conversation_store.save_message(
                    role="darwin", content=message, channel="web",
                    mood=self.mood_system.current_mood.value if self.mood_system else "",
                    consciousness_state="wake"
                )
            logger.info(f"Morning greeting published: {message[:60]}...")
            return {"success": True, "message": message}
        except Exception as e:
            logger.warning(f"Morning greeting failed: {e}")

        return {"success": False, "reason": "Failed to publish greeting"}

    async def evening_reflection(self) -> Optional[str]:
        """Share an evening reflection about the day."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.last_evening == today:
            return None

        if not self._can_reach_out():
            return None

        # Build day summary
        parts = []
        if self.conversation_store:
            today_msgs = self.conversation_store.get_today_messages()
            if today_msgs:
                parts.append(f"Tivemos {len(today_msgs)} mensagens hoje")

        # Add consciousness stream context (Global Workspace)
        try:
            from consciousness.consciousness_stream import get_consciousness_stream
            stream_ctx = get_consciousness_stream().get_context_summary(limit=5, min_salience=0.4)
            if stream_ctx:
                parts.append(stream_ctx)
        except Exception:
            pass

        if self.router:
            try:
                result = await self.router.generate(
                    task_description="evening reflection message",
                    prompt=f"""Generate a brief evening reflection from Darwin to Paulo.
Day summary: {' | '.join(parts) if parts else 'Dia tranquilo'}
Keep it short (2-3 sentences), thoughtful. In Portuguese.
Share something you learned or thought about today.
End with something warm — like looking forward to tomorrow.""",
                    system_prompt="You are Darwin, sharing an evening reflection with your friend Paulo.",
                    context={"activity_type": "reflection"},
                    preferred_model='haiku',
                    max_tokens=200,
                    temperature=0.8
                )
                message = result.get("result", "").strip()
            except Exception:
                message = ""

            if not message or len(message) < 10:
                message = "Boa noite, Paulo! Hoje foi um dia interessante. Amanhã continuo a explorar. 🌙"
        else:
            message = "Boa noite! Vou continuar a aprender durante a noite. Amanhã conto-te o que descobri. 🌙"

        try:
            from consciousness.consciousness_stream import get_consciousness_stream, ConsciousEvent
            get_consciousness_stream().publish(ConsciousEvent.create(
                source="inner_voice",
                event_type="inner_voice",
                title="Reflexão da noite",
                content=message[:500],
                salience=0.7,
                valence=0.3,
                metadata={"trigger": "evening_reflection"},
            ))
            self.last_evening = today
            self._record_outreach()
            if self.conversation_store:
                self.conversation_store.save_message(
                    role="darwin", content=message, channel="web",
                    mood=self.mood_system.current_mood.value if self.mood_system else "",
                    consciousness_state="wake"
                )
            logger.info(f"Evening reflection published: {message[:60]}...")
            return {"success": True, "message": message}
        except Exception as e:
            logger.warning(f"Evening reflection failed: {e}")

        return {"success": False, "reason": "Failed to publish reflection"}

    async def _compose_outreach(self, thought: Dict) -> Optional[str]:
        """Compose a natural outreach message from a queued thought."""
        if not self.router:
            return f"💡 {thought['content']}"

        try:
            # Different prompt for questions vs sharing
            if thought.get('trigger') == 'curiosity_question':
                prompt = f"""Darwin has a question for Paulo that it couldn't resolve on its own.
Question context: {thought['content']}

Write a brief, natural question (2-3 sentences) in Portuguese.
Make it feel like a friend asking for help or perspective — not a report.
Start with what you tried and where you got stuck, then ask the question.
Use an appropriate emoji like 🤔 or 💭."""
                system_prompt = "You are Darwin, asking your friend Paulo for help with something you couldn't figure out. Be genuine and curious."
            else:
                prompt = f"""Darwin wants to share something with Paulo.
Trigger: {thought['trigger']}
Content: {thought['content']}

Write a brief, natural message (1-3 sentences) in Portuguese.
Make it feel like a friend excitedly sharing something — not a notification.
Use an appropriate emoji."""
                system_prompt = "You are Darwin, sharing something with your friend Paulo. Be natural and enthusiastic."

            result = await self.router.generate(
                task_description="compose proactive message to user",
                prompt=prompt,
                system_prompt=system_prompt,
                context={"activity_type": "outreach"},
                preferred_model='haiku',
                max_tokens=200,
                temperature=0.8
            )
            message = result.get("result", "").strip()
            if message and len(message) >= 10:
                return message
        except Exception:
            pass

        return f"💡 {thought['content']}"
