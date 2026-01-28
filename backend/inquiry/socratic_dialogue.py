"""
Socratic Dialogue - Darwin questiona-se a si próprio

Este módulo implementa diálogo socrático interno onde Darwin:
1. Faz perguntas a si próprio
2. Responde com base no conhecimento atual
3. Identifica contradições e gaps
4. Refina compreensão através de questionamento iterativo
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class DialogueTurn:
    """Um turno no diálogo socrático"""
    turn_number: int
    speaker: str  # 'questioner' or 'responder'
    statement: str
    reasoning: str
    confidence: float
    reveals: Optional[str] = None  # O que este turno revelou

    def to_dict(self) -> Dict:
        return {
            'turn': self.turn_number,
            'speaker': self.speaker,
            'statement': self.statement,
            'reasoning': self.reasoning,
            'confidence': self.confidence,
            'reveals': self.reveals
        }


@dataclass
class SocraticSession:
    """Uma sessão completa de diálogo socrático"""
    id: str
    topic: str
    initial_question: str
    turns: List[DialogueTurn] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    contradictions_found: List[str] = field(default_factory=list)
    knowledge_gaps: List[str] = field(default_factory=list)
    final_understanding: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'topic': self.topic,
            'initial_question': self.initial_question,
            'turns': [t.to_dict() for t in self.turns],
            'insights_gained': self.insights_gained,
            'contradictions_found': self.contradictions_found,
            'knowledge_gaps': self.knowledge_gaps,
            'final_understanding': self.final_understanding,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'duration_minutes': self._calculate_duration()
        }

    def _calculate_duration(self) -> float:
        if not self.completed_at:
            return 0.0
        start = datetime.fromisoformat(self.started_at)
        end = datetime.fromisoformat(self.completed_at)
        return (end - start).total_seconds() / 60


class SocraticDialogue:
    """
    Sistema de diálogo socrático interno

    Darwin tem uma conversa consigo próprio:
    - Faz perguntas profundas
    - Tenta responder com conhecimento atual
    - Identifica falhas na compreensão
    - Refina através de questionamento iterativo
    - Descobre insights através do processo

    Exemplo de diálogo:
    D: "Por que é que list comprehensions são mais rápidas?"
    D: "Talvez porque são otimizadas ao nível do bytecode?"
    D: "Mas como é que essa otimização funciona exatamente?"
    D: "Não sei os detalhes... devo investigar o bytecode do Python"
    D: "O que revelaria esse bytecode?"
    D: "Mostraria se há instruções especiais para comprehensions"
    D: "Como posso verificar isso?"
    D: "Posso usar o módulo 'dis' para desassemblar!"
    """

    def __init__(self, multi_model_router=None, max_turns: int = 10):
        self.multi_model_router = multi_model_router
        self.max_turns = max_turns
        self.sessions: List[SocraticSession] = []

    async def internal_dialogue(
        self,
        topic: str,
        initial_question: str,
        context: Dict[str, Any],
        duration_minutes: int = 10
    ) -> SocraticSession:
        """
        Inicia um diálogo socrático interno sobre um tópico

        Args:
            topic: Tópico a explorar
            initial_question: Pergunta inicial
            context: Contexto do Darwin
            duration_minutes: Duração máxima do diálogo

        Returns:
            SocraticSession com todo o diálogo e insights
        """
        logger.info(f"Starting Socratic dialogue on: {topic}")

        session = SocraticSession(
            id=f"dialogue_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            topic=topic,
            initial_question=initial_question
        )

        # Start with initial question
        current_question = initial_question
        turn_num = 0

        while turn_num < self.max_turns:
            turn_num += 1

            # Questioner asks
            question_turn = await self._generate_questioner_turn(
                turn_num,
                current_question,
                session,
                context
            )
            session.turns.append(question_turn)

            # Responder answers
            response_turn = await self._generate_responder_turn(
                turn_num,
                question_turn.statement,
                session,
                context
            )
            session.turns.append(response_turn)

            # Analyze this exchange
            analysis = self._analyze_exchange(question_turn, response_turn)

            # Record insights
            if analysis.get('insight'):
                session.insights_gained.append(analysis['insight'])

            # Record contradictions
            if analysis.get('contradiction'):
                session.contradictions_found.append(analysis['contradiction'])

            # Record knowledge gaps
            if analysis.get('gap'):
                session.knowledge_gaps.append(analysis['gap'])

            # Check if we should continue
            if response_turn.confidence > 0.9:
                logger.info(f"High confidence reached ({response_turn.confidence}), ending dialogue")
                break

            if turn_num >= self.max_turns:
                logger.info(f"Max turns ({self.max_turns}) reached")
                break

            # Generate next question based on response
            current_question = self._generate_followup_question(
                question_turn,
                response_turn,
                analysis
            )

            if not current_question:
                logger.info("No more meaningful questions to ask")
                break

        # Synthesize final understanding
        session.final_understanding = await self._synthesize_understanding(session)
        session.completed_at = datetime.now().isoformat()

        self.sessions.append(session)
        logger.info(f"Dialogue completed with {turn_num} turns and {len(session.insights_gained)} insights")

        return session

    async def _generate_questioner_turn(
        self,
        turn_num: int,
        question: str,
        session: SocraticSession,
        context: Dict[str, Any]
    ) -> DialogueTurn:
        """Gera um turno do questionador"""

        if not self.multi_model_router:
            # Fallback sem AI
            return DialogueTurn(
                turn_number=turn_num,
                speaker='questioner',
                statement=question,
                reasoning="Initial question from context",
                confidence=0.5
            )

        # Use AI para gerar pergunta socrática
        prompt = self._create_questioner_prompt(question, session, context)

        try:
            result = await self.multi_model_router.generate(
                task_description=f"Generate Socratic questioning for: {question}",
                prompt=prompt,
                max_tokens=300
            )

            response = result['result']

            return DialogueTurn(
                turn_number=turn_num,
                speaker='questioner',
                statement=question,
                reasoning=response,
                confidence=0.7
            )

        except Exception as e:
            logger.error(f"Error generating questioner turn: {e}")
            return DialogueTurn(
                turn_number=turn_num,
                speaker='questioner',
                statement=question,
                reasoning="Error in generation",
                confidence=0.3
            )

    def _create_questioner_prompt(
        self,
        question: str,
        session: SocraticSession,
        context: Dict[str, Any]
    ) -> str:
        """Cria prompt para o questionador"""

        dialogue_history = ""
        if session.turns:
            dialogue_history = "\nDialogue so far:\n"
            for turn in session.turns[-4:]:  # Last 4 turns
                dialogue_history += f"{turn.speaker}: {turn.statement}\n"

        return f"""You are Darwin's internal questioner, using Socratic method.

Topic: {session.topic}
Current question: {question}
{dialogue_history}

As the questioner:
1. Probe deeper into assumptions
2. Ask "why" and "how" questions
3. Challenge vague answers
4. Seek clarity and precision
5. Identify logical gaps

Your reasoning about why this question matters:
"""

    async def _generate_responder_turn(
        self,
        turn_num: int,
        question: str,
        session: SocraticSession,
        context: Dict[str, Any]
    ) -> DialogueTurn:
        """Gera um turno do respondedor"""

        if not self.multi_model_router:
            # Fallback sem AI
            return DialogueTurn(
                turn_number=turn_num,
                speaker='responder',
                statement="I need to think more about this",
                reasoning="Insufficient knowledge",
                confidence=0.3
            )

        # Use AI para gerar resposta baseada em conhecimento atual
        prompt = self._create_responder_prompt(question, session, context)

        try:
            result = await self.multi_model_router.generate(
                task_description=f"Generate Socratic response for: {question}",
                prompt=prompt,
                max_tokens=400
            )

            response = result['result']

            # Extract confidence from response (if stated)
            confidence = self._extract_confidence(response)

            # Extract what was revealed
            reveals = self._extract_revelation(response)

            return DialogueTurn(
                turn_number=turn_num,
                speaker='responder',
                statement=response,
                reasoning="Based on current understanding",
                confidence=confidence,
                reveals=reveals
            )

        except Exception as e:
            logger.error(f"Error generating responder turn: {e}")
            return DialogueTurn(
                turn_number=turn_num,
                speaker='responder',
                statement="I encountered an error in my reasoning",
                reasoning=str(e),
                confidence=0.2
            )

    def _create_responder_prompt(
        self,
        question: str,
        session: SocraticSession,
        context: Dict[str, Any]
    ) -> str:
        """Cria prompt para o respondedor"""

        knowledge_context = ""
        if context.get('recent_learnings'):
            knowledge_context = f"\nRecent learnings: {context['recent_learnings']}"

        dialogue_history = ""
        if session.turns:
            dialogue_history = "\nDialogue so far:\n"
            for turn in session.turns[-4:]:
                dialogue_history += f"{turn.speaker}: {turn.statement}\n"

        return f"""You are Darwin's internal responder, answering honestly based on your knowledge.

Topic: {session.topic}
Question to answer: {question}
{knowledge_context}
{dialogue_history}

As the responder:
1. Answer based on what you actually know
2. Admit when you don't know
3. Distinguish facts from assumptions
4. Be precise and clear
5. State your confidence level

Your answer (include confidence 0-1 at the end as "Confidence: X"):
"""

    def _analyze_exchange(
        self,
        question_turn: DialogueTurn,
        response_turn: DialogueTurn
    ) -> Dict[str, str]:
        """Analisa uma troca de perguntas/respostas"""

        analysis = {}

        # Detect insights (high confidence responses)
        if response_turn.confidence > 0.8:
            analysis['insight'] = f"Insight at turn {response_turn.turn_number}: {response_turn.reveals or response_turn.statement[:100]}"

        # Detect contradictions (low confidence or hedging)
        hedging_words = ['maybe', 'perhaps', 'possibly', 'i think', 'i believe', 'not sure']
        if any(word in response_turn.statement.lower() for word in hedging_words):
            analysis['contradiction'] = f"Uncertainty detected at turn {response_turn.turn_number}"

        # Detect knowledge gaps (explicit admissions)
        admission_phrases = ['i don\'t know', 'i need to', 'i should investigate', 'not clear']
        if any(phrase in response_turn.statement.lower() for phrase in admission_phrases):
            analysis['gap'] = f"Knowledge gap identified at turn {response_turn.turn_number}: {response_turn.statement[:100]}"

        return analysis

    def _generate_followup_question(
        self,
        question_turn: DialogueTurn,
        response_turn: DialogueTurn,
        analysis: Dict[str, str]
    ) -> Optional[str]:
        """Gera próxima pergunta baseada na resposta"""

        # Se há gap de conhecimento, perguntar como preencher
        if analysis.get('gap'):
            return "How can I find out more about this?"

        # Se há contradição, pedir clarificação
        if analysis.get('contradiction'):
            return "What exactly do I mean by that? Can I be more precise?"

        # Se confiança baixa, perguntar porquê
        if response_turn.confidence < 0.5:
            return "Why am I not confident in this answer? What's missing?"

        # Se resposta vaga, pedir detalhes
        vague_words = ['some', 'various', 'different', 'multiple']
        if any(word in response_turn.statement.lower() for word in vague_words):
            return "Can I be more specific? What exactly are the details?"

        # Se resposta boa mas não perfeita, aprofundar
        if 0.5 <= response_turn.confidence < 0.9:
            return "What are the implications of this understanding?"

        # Se muito confiante, verificar
        if response_turn.confidence >= 0.9:
            return "How can I verify this understanding?"

        return None

    async def _synthesize_understanding(
        self,
        session: SocraticSession
    ) -> str:
        """Sintetiza compreensão final do diálogo"""

        if not self.multi_model_router:
            # Fallback: summarize insights
            if session.insights_gained:
                return f"Key insights: {'; '.join(session.insights_gained)}"
            return "Dialogue completed but understanding remains unclear"

        # Use AI para sintetizar
        dialogue_summary = "\n".join([
            f"{t.speaker}: {t.statement}"
            for t in session.turns
        ])

        prompt = f"""Synthesize the understanding gained from this Socratic dialogue:

Topic: {session.topic}
Initial question: {session.initial_question}

Dialogue:
{dialogue_summary}

Insights gained: {session.insights_gained}
Knowledge gaps found: {session.knowledge_gaps}

Provide a clear, concise summary (2-3 paragraphs) of:
1. What was ultimately understood
2. What remains unclear
3. What next steps would deepen understanding
"""

        try:
            result = await self.multi_model_router.generate(
                task_description=f"Synthesize understanding from Socratic dialogue on: {session.topic}",
                prompt=prompt,
                max_tokens=500
            )

            return result['result']

        except Exception as e:
            logger.error(f"Error synthesizing understanding: {e}")
            return f"Error in synthesis: {e}"

    def _extract_confidence(self, response: str) -> float:
        """Extrai nível de confiança da resposta"""
        # Look for "Confidence: X"
        if 'confidence:' in response.lower():
            try:
                parts = response.lower().split('confidence:')
                confidence_str = parts[-1].strip().split()[0]
                confidence = float(confidence_str)
                return max(0.0, min(1.0, confidence))
            except:
                pass

        # Fallback: estimate from language
        hedging_words = ['maybe', 'perhaps', 'possibly', 'i think', 'probably']
        hedge_count = sum(1 for word in hedging_words if word in response.lower())

        if hedge_count >= 3:
            return 0.4
        elif hedge_count >= 2:
            return 0.6
        elif hedge_count >= 1:
            return 0.7
        else:
            return 0.8

    def _extract_revelation(self, response: str) -> Optional[str]:
        """Extrai o que foi revelado/descoberto na resposta"""
        # Look for key phrases
        revelation_phrases = [
            'i realize', 'i understand', 'this means', 'this shows',
            'i discovered', 'i found', 'this reveals'
        ]

        response_lower = response.lower()
        for phrase in revelation_phrases:
            if phrase in response_lower:
                # Extract sentence containing revelation
                sentences = response.split('.')
                for sentence in sentences:
                    if phrase in sentence.lower():
                        return sentence.strip()

        return None

    def get_recent_sessions(self, limit: int = 5) -> List[SocraticSession]:
        """Retorna sessões recentes"""
        return self.sessions[-limit:]

    def get_session(self, session_id: str) -> Optional[SocraticSession]:
        """Retorna uma sessão específica"""
        for session in self.sessions:
            if session.id == session_id:
                return session
        return None

    def get_all_insights(self) -> List[str]:
        """Retorna todos os insights de todas as sessões"""
        all_insights = []
        for session in self.sessions:
            all_insights.extend(session.insights_gained)
        return all_insights

    def get_all_gaps(self) -> List[str]:
        """Retorna todos os gaps identificados"""
        all_gaps = []
        for session in self.sessions:
            all_gaps.extend(session.knowledge_gaps)
        return all_gaps

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas dos diálogos"""
        total_sessions = len(self.sessions)
        if total_sessions == 0:
            return {
                'total_sessions': 0,
                'total_turns': 0,
                'total_insights': 0,
                'total_gaps': 0,
                'avg_turns_per_session': 0,
                'avg_insights_per_session': 0
            }

        total_turns = sum(len(s.turns) for s in self.sessions)
        total_insights = sum(len(s.insights_gained) for s in self.sessions)
        total_gaps = sum(len(s.knowledge_gaps) for s in self.sessions)

        return {
            'total_sessions': total_sessions,
            'total_turns': total_turns,
            'total_insights': total_insights,
            'total_gaps': total_gaps,
            'total_contradictions': sum(len(s.contradictions_found) for s in self.sessions),
            'avg_turns_per_session': total_turns / total_sessions,
            'avg_insights_per_session': total_insights / total_sessions,
            'most_productive_topic': self._find_most_productive_topic()
        }

    def _find_most_productive_topic(self) -> str:
        """Encontra o tópico mais produtivo (mais insights)"""
        if not self.sessions:
            return "None"

        topic_insights = {}
        for session in self.sessions:
            topic = session.topic
            insights_count = len(session.insights_gained)
            topic_insights[topic] = topic_insights.get(topic, 0) + insights_count

        if not topic_insights:
            return "None"

        return max(topic_insights.items(), key=lambda x: x[1])[0]
