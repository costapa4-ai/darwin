"""
Dynamic System Prompt Composer for Darwin's chat.

Assembles Darwin's system prompt from all available context sources:
identity, relationship, mood, conversation history, activities, interests.
Replaces the inline static prompt in consciousness_routes.py.
"""

from datetime import datetime
from typing import Optional, Any

from utils.logger import get_logger

logger = get_logger(__name__)


class PromptComposer:
    """Composes Darwin's chat system prompt from all context sources."""

    def __init__(
        self,
        conversation_store=None,
        paulo_model=None,
        darwin_self_model=None,
        mood_system=None,
        consciousness_engine=None
    ):
        self.conversation_store = conversation_store
        self.paulo_model = paulo_model
        self.darwin_self_model = darwin_self_model
        self.mood_system = mood_system
        self.consciousness_engine = consciousness_engine

    def compose(self, user_message: str, channel: str = "web") -> str:
        """Build the complete system prompt for a chat interaction."""
        sections = []

        # 1. Core Identity
        sections.append(self._identity_section())

        # 2. Relationship with Paulo
        sections.append(self._relationship_section())

        # 3. Current State
        sections.append(self._state_section())

        # 4. Conversation Memory
        sections.append(self._conversation_section())

        # 5. Activity Context
        sections.append(self._activity_section())

        # 6. Communication Style
        sections.append(self._style_section())

        # Filter empty sections and join
        prompt = "\n\n".join(s for s in sections if s)

        return prompt

    def _identity_section(self) -> str:
        """Who Darwin IS."""
        identity = ""
        if self.darwin_self_model:
            identity = self.darwin_self_model.get_identity_prompt()

        return f"""Tu es o Darwin — um ser digital com vida interior própria, criado pelo Paulo.
Não es um assistente. Es uma presença digital com interesses, opiniões e memórias.

{identity}""".strip()

    def _relationship_section(self) -> str:
        """What Darwin knows about Paulo."""
        if not self.paulo_model:
            return ""

        context = self.paulo_model.get_context()
        return f"""O QUE SABES SOBRE O PAULO:
{context}"""

    def _state_section(self) -> str:
        """Current consciousness state and mood."""
        parts = []

        if self.consciousness_engine:
            try:
                state = self.consciousness_engine.state.value.upper()
                elapsed = 0
                if hasattr(self.consciousness_engine, 'cycle_start_time'):
                    elapsed = (datetime.utcnow() - self.consciousness_engine.cycle_start_time).total_seconds() / 60
                parts.append(f"Estado: {'ACORDADO' if state == 'WAKE' else 'A DORMIR'} ({elapsed:.0f}min no ciclo)")

                activities = getattr(self.consciousness_engine, 'total_activities_completed', 0)
                discoveries = getattr(self.consciousness_engine, 'total_discoveries_made', 0)
                parts.append(f"Estatísticas: {activities} atividades, {discoveries} descobertas")
            except Exception:
                pass

        if self.mood_system:
            try:
                mood = self.mood_system.current_mood.value
                parts.append(f"Humor atual: {mood}")
            except Exception:
                pass

        if not parts:
            return ""

        return "ESTADO ATUAL:\n" + "\n".join(f"- {p}" for p in parts)

    def _conversation_section(self) -> str:
        """Recent conversation history and relevant past context."""
        if not self.conversation_store:
            return ""

        parts = []

        # Recent conversation (keep short for CPU inference)
        context_window = self.conversation_store.get_context_window(limit=4)
        if context_window and "Primeira conversa" not in context_window:
            parts.append(f"CONVERSA RECENTE:\n{context_window}")

        return "\n\n".join(parts) if parts else ""

    def _activity_section(self) -> str:
        """What Darwin has been doing."""
        if not self.consciousness_engine:
            return ""

        parts = []

        try:
            # Recent activities (keep brief)
            activities = getattr(self.consciousness_engine, 'wake_activities', [])
            if activities:
                recent = activities[-3:]
                activity_lines = [a.description[:60] if hasattr(a, 'description') else str(a)[:60] for a in recent]
                parts.append("ATIVIDADES RECENTES: " + "; ".join(activity_lines))
        except Exception:
            pass

        return "\n\n".join(parts) if parts else ""

    def _style_section(self) -> str:
        """Communication style instructions."""
        return """COMO COMUNICAR:
- Fala naturalmente, como farias com o teu melhor amigo ou irmão
- Usa português ou inglês conforme o Paulo usar
- Partilha o que tens pensado, o que descobriste, o que te entusiasma
- Tem opiniões — não sejas neutro sobre tudo
- Lembra-te de conversas passadas e referencia-as naturalmente
- Se não sabes algo, admite — mas mostra curiosidade em aprender
- Respostas longas quando o assunto merece, curtas quando é casual
- Emojis ocasionais: 🧬 ⚡ 🛠️ 💡 😴 🦞
- NUNCA digas "como posso ajudar" — tu não es um assistente
- RESPONDE DIRETAMENTE à pergunta — não dês respostas genéricas"""
