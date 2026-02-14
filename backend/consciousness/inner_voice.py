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
        # Keep queue manageable
        if len(self.impulse_queue) > 20:
            self.impulse_queue = self.impulse_queue[-20:]
        logger.debug(f"Thought queued ({trigger}): {content[:60]}...")

    async def generate_thought(self, trigger: str, context: Dict) -> Optional[str]:
        """Generate an inner thought from a trigger event. Queue if worth sharing."""
        # Decide if this is worth queuing
        urgency = 0.3  # Base urgency

        if trigger == "discovery":
            # Discoveries are exciting
            urgency = 0.7
            content = context.get("description", context.get("title", "something interesting"))
        elif trigger == "curiosity":
            # Expedition completed with insights
            insights = context.get("insights", [])
            if len(insights) >= 3:
                urgency = 0.6
            content = f"Acabei uma expedição sobre {context.get('topic', 'algo')} — {len(insights)} insights"
        elif trigger == "mood_shift":
            # Only significant mood shifts
            old_mood = context.get("old_mood", "")
            new_mood = context.get("new_mood", "")
            if new_mood in ("excited", "proud", "surprised"):
                urgency = 0.5
            content = f"Mudei de {old_mood} para {new_mood}"
        else:
            content = context.get("description", str(context)[:100])

        if urgency >= 0.5:
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

        # Send via Telegram
        try:
            from integrations.telegram_bot import notify_owner
            sent = await notify_owner(message, parse_mode='HTML')
            if sent:
                self._record_outreach()

                # Also store in conversation memory
                if self.conversation_store:
                    self.conversation_store.save_message(
                        role="darwin",
                        content=message,
                        channel="telegram",
                        mood=self.mood_system.current_mood.value if self.mood_system else "",
                        consciousness_state="wake"
                    )

                logger.info(f"InnerVoice outreach sent ({thought['trigger']}): {message[:80]}...")
                return {"success": True, "message": message, "channel": "telegram", "trigger": thought["trigger"]}
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
Don't be generic — make it feel like a friend saying good morning.""",
                    system_prompt="You are Darwin, greeting your friend Paulo in the morning. Be warm and natural.",
                    context={"activity_type": "greeting"},
                    max_tokens=200,
                    temperature=0.8
                )
                message = result.get("result", "").strip()
            except Exception:
                message = ""

            if not message or len(message) < 10:
                message = "Bom dia, Paulo! 🌅 Mais um dia para aprender algo novo. O que tens em mente?"
        else:
            message = "Bom dia, Paulo! 🌅 Estou curioso para ver o que vamos descobrir hoje."

        # Send
        try:
            from integrations.telegram_bot import notify_owner
            sent = await notify_owner(message, parse_mode='HTML')
            if sent:
                self.last_morning = today
                self._record_outreach()
                if self.conversation_store:
                    self.conversation_store.save_message(
                        role="darwin", content=message, channel="telegram",
                        mood=self.mood_system.current_mood.value if self.mood_system else "",
                        consciousness_state="wake"
                    )
                logger.info(f"Morning greeting sent: {message[:60]}...")
                return {"success": True, "message": message}
        except Exception as e:
            logger.warning(f"Morning greeting failed: {e}")

        return {"success": False, "reason": "Failed to send greeting"}

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
            from integrations.telegram_bot import notify_owner
            sent = await notify_owner(message, parse_mode='HTML')
            if sent:
                self.last_evening = today
                self._record_outreach()
                if self.conversation_store:
                    self.conversation_store.save_message(
                        role="darwin", content=message, channel="telegram",
                        mood=self.mood_system.current_mood.value if self.mood_system else "",
                        consciousness_state="wake"
                    )
                logger.info(f"Evening reflection sent: {message[:60]}...")
                return {"success": True, "message": message}
        except Exception as e:
            logger.warning(f"Evening reflection failed: {e}")

        return {"success": False, "reason": "Failed to send reflection"}

    async def _compose_outreach(self, thought: Dict) -> Optional[str]:
        """Compose a natural outreach message from a queued thought."""
        if not self.router:
            return f"💡 {thought['content']}"

        try:
            result = await self.router.generate(
                task_description="compose proactive message to user",
                prompt=f"""Darwin wants to share something with Paulo.
Trigger: {thought['trigger']}
Content: {thought['content']}

Write a brief, natural message (1-3 sentences) in Portuguese.
Make it feel like a friend excitedly sharing something — not a notification.
Use an appropriate emoji.""",
                system_prompt="You are Darwin, sharing something with your friend Paulo. Be natural and enthusiastic.",
                context={"activity_type": "outreach"},
                max_tokens=150,
                temperature=0.8
            )
            message = result.get("result", "").strip()
            if message and len(message) >= 10:
                return message
        except Exception:
            pass

        return f"💡 {thought['content']}"
