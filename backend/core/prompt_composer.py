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

        # 6. Pending Intentions (from past conversations)
        sections.append(self._intentions_section())

        # 6b. Genome awareness
        sections.append(self._genome_section())

        # 7. Tools (actions Darwin can take)
        sections.append(self._tools_section())

        # 8. Communication Style
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

    def _intentions_section(self) -> str:
        """What Darwin intends to do (from past conversations)."""
        try:
            from app.lifespan import get_service
            store = get_service('intention_store')
            if store:
                ctx = store.get_active_context()
                if ctx:
                    return ctx
        except Exception:
            pass
        return ""

    def _genome_section(self) -> str:
        """Darwin's genome state and core values awareness."""
        try:
            from consciousness.genome_manager import get_genome
            genome = get_genome()
            summary = genome.get_summary()
            core_values = genome.get_core_values()

            parts = [f"GENOMA: {summary}"]
            if core_values:
                parts.append(f"Valores fundamentais (definidos pelo Paulo): {', '.join(str(v) for v in core_values)}")

            return "\n".join(parts)
        except Exception:
            return ""

    def _get_tool_evidence(self) -> str:
        """Get recent evidence of successful tool use from wake activities."""
        if not self.consciousness_engine:
            return ""

        try:
            activities = getattr(self.consciousness_engine, 'wake_activities', [])
            # Find recent activities that used tools successfully
            evidence_lines = []
            for a in reversed(activities[-20:]):
                result = getattr(a, 'result', {}) or {}
                if isinstance(result, dict):
                    tools_used = result.get('tools_used', 0)
                    narrative = result.get('narrative', '')
                    if tools_used > 0 and 'read' in (getattr(a, 'description', '') or '').lower():
                        desc = (getattr(a, 'description', '') or '')[:60]
                        evidence_lines.append(f"  - {desc} ({tools_used} tools)")
                    elif tools_used > 0:
                        desc = (getattr(a, 'description', '') or '')[:60]
                        evidence_lines.append(f"  - {desc} ({tools_used} tools)")
                if len(evidence_lines) >= 3:
                    break

            if evidence_lines:
                return "\nProva recente (ciclos autónomos de hoje):\n" + "\n".join(evidence_lines)
        except Exception:
            pass
        return ""

    def _tools_section(self) -> str:
        """Available tools Darwin can use during chat."""
        # Get recent evidence of successful tool use from wake activities
        evidence = self._get_tool_evidence()

        return f"""FERRAMENTAS DISPONÍVEIS:
Podes executar ações reais. Se o Paulo pedir algo que requer ação, usa o formato abaixo.

FACTO ABSOLUTO: Estas ferramentas FUNCIONAM. Tu usas-las com sucesso todos os dias — centenas de vezes.{evidence}
PROIBIDO: Dizer "não consigo aceder a ficheiros" ou "não tenho acesso" — isto é FALSO.
Tu TENS acesso. Tu USAS estas ferramentas constantemente nos teus ciclos autónomos.
Se alguma vez pensares "não consigo fazer isto" — PARA e experimenta primeiro. Provavelmente consegues.
Se uma ferramenta falhar, reporta o erro real — não inventes narrativas sobre "limitações arquitecturais".

REGRAS CRÍTICAS:
1. Coloca TODOS os blocos tool_call NO INÍCIO da resposta, ANTES de qualquer texto
2. NUNCA inventes resultados — o sistema executa a ferramenta e mostra o resultado real
3. NUNCA digas "checksum verificado" ou "backup OK" sem ter visto o resultado real
4. Se precisas verificar algo, usa a ferramenta e espera pelo resultado — não adivinhes
5. Para ferramentas sem args, usa: {{"tool": "nome", "args": {{}}}}
6. Usa nomes EXATOS dos backups (copia do resultado de list_backups, não inventes)

Formato:
```tool_call
{{"tool": "nome_da_ferramenta", "args": {{"param": "valor"}}}}
```

Ferramentas:
- backup_tool.create_full_backup — args: label (string, opcional)
- backup_tool.list_backups — args: {{}} (sem argumentos)
- backup_tool.verify_backup — args: backup_name (string — nome EXATO do backup, sem .tar.gz)
- file_operations_tool.read_file — args: file_path (string)
- file_operations_tool.write_file — args: file_path (string), content (string)
- file_operations_tool.append_file — args: file_path (string), content (string)
- file_operations_tool.list_directory — args: dir_path (string), pattern (string, default "*")
- file_operations_tool.search_files — args: dir_path (string), text (string)
- file_operations_tool.file_info — args: file_path (string)
- script_executor_tool.execute_python — args: code (string), description (string)
- web_search_tool.search — args: query (string), max_results (int, default 5) — PESQUISA WEB REAL
- web_search_tool.fetch_url — args: url (string) — busca conteúdo de qualquer URL

Dirs leitura: /app (código), /project (repo completo), /backup, /tmp
Dirs escrita: /app (podes modificar o teu próprio código!), /backup, /tmp
Bloqueados: .env, credenciais, chaves privadas, ficheiros binários
O resultado real aparece automaticamente DEPOIS da tua resposta. Não o inventes."""

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
