"""
Question Engine - Generates deep, meaningful questions for Darwin to explore

This module enables Darwin to:
1. Identify knowledge gaps
2. Generate questions at different depths
3. Prioritize questions by importance
4. Pursue answers autonomously
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QuestionDepth(Enum):
    """Profundidade da questão"""
    SURFACE = "surface"           # "What is X?"
    MEDIUM = "medium"             # "How does X work?"
    DEEP = "deep"                 # "Why does X behave this way?"
    PHILOSOPHICAL = "philosophical"  # "What does X tell us about...?"


class QuestionType(Enum):
    """Tipos de perguntas"""
    WHY = "why"                   # "Why does X happen?"
    HOW = "how"                   # "How does X work internally?"
    WHAT_IF = "what_if"          # "What if we changed X to Y?"
    COMPARISON = "comparison"     # "How does X compare to Y?"
    OPTIMIZATION = "optimization" # "Can we make X better?"
    EXPLORATION = "exploration"   # "What else exists like X?"
    APPLICATION = "application"   # "Where can we use X?"
    LIMITATION = "limitation"     # "What are the limits of X?"


@dataclass
class Question:
    """Uma questão gerada pelo Darwin"""
    id: str
    question: str
    type: QuestionType
    depth: QuestionDepth
    context: Dict[str, Any]
    priority: float  # 0.0-1.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    answered: bool = False
    answer: Optional[str] = None
    confidence: float = 0.0
    related_questions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'question': self.question,
            'type': self.type.value,
            'depth': self.depth.value,
            'context': self.context,
            'priority': self.priority,
            'created_at': self.created_at,
            'answered': self.answered,
            'answer': self.answer,
            'confidence': self.confidence,
            'related_questions': self.related_questions
        }


class QuestionEngine:
    """
    Motor de geração de perguntas profundas

    Permite ao Darwin:
    - Identificar o que não sabe
    - Gerar perguntas em múltiplos níveis
    - Priorizar questões por relevância
    - Manter histórico de perguntas
    """

    def __init__(self, multi_model_router=None):
        self.multi_model_router = multi_model_router
        self.questions: List[Question] = []
        self.answered_questions: List[Question] = []

        # Templates de perguntas por tipo
        self.question_templates = {
            QuestionType.WHY: [
                "Why does {subject} {verb}?",
                "Why is {subject} {adjective}?",
                "What causes {subject} to {verb}?",
                "What is the reason behind {subject}?"
            ],
            QuestionType.HOW: [
                "How does {subject} work internally?",
                "How is {subject} implemented?",
                "What is the mechanism behind {subject}?",
                "How can we understand {subject}?"
            ],
            QuestionType.WHAT_IF: [
                "What if we changed {subject} to {alternative}?",
                "What would happen if {condition}?",
                "How would {subject} behave if {change}?",
                "What are the implications of {change}?"
            ],
            QuestionType.COMPARISON: [
                "How does {subject} compare to {alternative}?",
                "What are the differences between {subject} and {alternative}?",
                "When should we use {subject} vs {alternative}?",
                "What are the tradeoffs between {subject} and {alternative}?"
            ],
            QuestionType.OPTIMIZATION: [
                "Can we make {subject} faster?",
                "How can we improve {subject}?",
                "What bottlenecks exist in {subject}?",
                "Is there a better way to {action}?"
            ],
            QuestionType.EXPLORATION: [
                "What else works like {subject}?",
                "What alternatives exist to {subject}?",
                "What related concepts should I explore?",
                "What patterns are similar to {subject}?"
            ],
            QuestionType.APPLICATION: [
                "Where can we apply {subject}?",
                "What problems does {subject} solve?",
                "When is {subject} most useful?",
                "How can we use {subject} in practice?"
            ],
            QuestionType.LIMITATION: [
                "What are the limits of {subject}?",
                "When does {subject} fail?",
                "What can't {subject} do?",
                "What are the constraints of {subject}?"
            ]
        }

    async def generate_questions(
        self,
        context: Dict[str, Any],
        depth: QuestionDepth = QuestionDepth.MEDIUM,
        max_questions: int = 10
    ) -> List[Question]:
        """
        Gera perguntas baseadas no contexto atual

        Args:
            context: Contexto atual do Darwin (learnings, gaps, curiosities)
            depth: Profundidade desejada das perguntas
            max_questions: Número máximo de perguntas a gerar

        Returns:
            Lista de perguntas ordenadas por prioridade
        """
        logger.info(f"Generating questions with depth={depth.value}, max={max_questions}")

        questions = []

        # 1. Identificar gaps de conhecimento
        knowledge_gaps = self._identify_knowledge_gaps(context)
        logger.info(f"Identified {len(knowledge_gaps)} knowledge gaps")

        # 2. Gerar perguntas para cada gap
        for gap in knowledge_gaps[:max_questions]:
            # Gerar diferentes tipos de perguntas
            for q_type in QuestionType:
                question = await self._generate_question(gap, q_type, depth, context)
                if question:
                    questions.append(question)

        # 3. Usar AI para gerar perguntas mais sofisticadas se disponível
        if self.multi_model_router and depth in [QuestionDepth.DEEP, QuestionDepth.PHILOSOPHICAL]:
            ai_questions = await self._generate_ai_questions(context, depth)
            questions.extend(ai_questions)

        # 4. Calcular prioridades
        for q in questions:
            q.priority = self._calculate_priority(q, context)

        # 5. Ordenar por prioridade
        questions.sort(key=lambda x: x.priority, reverse=True)

        # 6. Guardar perguntas geradas
        self.questions.extend(questions[:max_questions])

        logger.info(f"Generated {len(questions[:max_questions])} questions")
        return questions[:max_questions]

    def _identify_knowledge_gaps(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identifica gaps de conhecimento no contexto atual

        Analisa:
        - Erros recentes
        - Conceitos mencionados mas não explicados
        - Padrões observados mas não compreendidos
        - Comparações com conhecimento existente
        """
        gaps = []

        # Gap 1: Recent learnings que levantam questões
        recent_learnings = context.get('recent_learnings', [])
        for learning in recent_learnings:
            gaps.append({
                'type': 'learning_question',
                'subject': learning,
                'context': 'Recently learned but need deeper understanding',
                'importance': 0.8
            })

        # Gap 2: Conceitos mencionados sem explicação
        mentioned_concepts = context.get('mentioned_concepts', [])
        for concept in mentioned_concepts:
            gaps.append({
                'type': 'unexplained_concept',
                'subject': concept,
                'context': 'Mentioned but not fully understood',
                'importance': 0.7
            })

        # Gap 3: Current task challenges
        current_task = context.get('current_task')
        if current_task:
            gaps.append({
                'type': 'task_challenge',
                'subject': current_task,
                'context': 'Current work raising questions',
                'importance': 0.9
            })

        # Gap 4: Explicit curiosities
        curiosities = context.get('curiosities', [])
        for curiosity in curiosities:
            gaps.append({
                'type': 'curiosity',
                'subject': curiosity,
                'context': 'Explicit curiosity to explore',
                'importance': 0.85
            })

        # Gap 5: Observed patterns sem explicação
        unexplained_patterns = context.get('unexplained_patterns', [])
        for pattern in unexplained_patterns:
            gaps.append({
                'type': 'pattern_mystery',
                'subject': pattern,
                'context': 'Pattern observed but not understood',
                'importance': 0.75
            })

        return gaps

    async def _generate_question(
        self,
        gap: Dict[str, Any],
        q_type: QuestionType,
        depth: QuestionDepth,
        context: Dict[str, Any]
    ) -> Optional[Question]:
        """
        Gera uma questão específica baseada num gap e tipo
        """
        subject = gap.get('subject', '')
        if not subject:
            return None

        # Selecionar template apropriado
        templates = self.question_templates.get(q_type, [])
        if not templates:
            return None

        # Escolher template baseado na profundidade
        template = templates[0]  # Simplificado por agora

        # Preencher template
        try:
            question_text = template.format(
                subject=subject,
                verb='work',  # Simplificado
                adjective='important',
                alternative='alternatives',
                condition='things changed',
                change='a modification',
                action='achieve this'
            )
        except KeyError:
            return None

        # Criar questão
        question = Question(
            id=f"q_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.questions)}",
            question=question_text,
            type=q_type,
            depth=depth,
            context={
                'gap': gap,
                'generated_at': datetime.now().isoformat(),
                'source': 'template'
            },
            priority=0.0  # Will be calculated later
        )

        return question

    async def _generate_ai_questions(
        self,
        context: Dict[str, Any],
        depth: QuestionDepth
    ) -> List[Question]:
        """
        Usa AI para gerar perguntas mais sofisticadas e profundas
        """
        if not self.multi_model_router:
            return []

        try:
            # Preparar prompt para AI
            prompt = self._create_question_prompt(context, depth)

            # Gerar com AI
            result = await self.multi_model_router.generate(
                task_description="Generate deep questions from context",
                prompt=prompt,
                max_tokens=500
            )

            # Parse resposta AI
            questions = self._parse_ai_questions(result['result'], depth, context)

            return questions

        except Exception as e:
            logger.error(f"Error generating AI questions: {e}")
            return []

    def _create_question_prompt(self, context: Dict[str, Any], depth: QuestionDepth) -> str:
        """Cria prompt para AI gerar perguntas"""

        prompt = f"""You are Darwin, a self-improving AI system. Generate {depth.value}-level questions to explore.

Context:
- Recent learnings: {context.get('recent_learnings', [])}
- Current focus: {context.get('current_task', 'General exploration')}
- Knowledge gaps: {context.get('gaps_in_knowledge', [])}

Generate 3-5 {depth.value} questions that would help you understand:
- WHY things work the way they do
- HOW to improve your understanding
- WHAT connections exist between concepts
- WHAT IF scenarios to explore

Format: One question per line, numbered.
Focus on questions that lead to genuine insight and understanding.
"""
        return prompt

    def _parse_ai_questions(
        self,
        ai_response: str,
        depth: QuestionDepth,
        context: Dict[str, Any]
    ) -> List[Question]:
        """Parse resposta da AI em questões estruturadas"""
        questions = []

        lines = ai_response.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove numeração
            if line[0].isdigit():
                line = line.split('.', 1)[-1].strip()

            # Remove marcadores
            if line.startswith('-') or line.startswith('*'):
                line = line[1:].strip()

            # Detectar tipo de pergunta
            q_type = self._detect_question_type(line)

            question = Question(
                id=f"q_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(questions)}",
                question=line,
                type=q_type,
                depth=depth,
                context={
                    'generated_at': datetime.now().isoformat(),
                    'source': 'ai',
                    'original_context': context
                },
                priority=0.0
            )
            questions.append(question)

        return questions

    def _detect_question_type(self, question: str) -> QuestionType:
        """Detecta o tipo de pergunta baseado no conteúdo"""
        question_lower = question.lower()

        if question_lower.startswith('why'):
            return QuestionType.WHY
        elif question_lower.startswith('how'):
            return QuestionType.HOW
        elif 'what if' in question_lower:
            return QuestionType.WHAT_IF
        elif 'compare' in question_lower or 'difference' in question_lower:
            return QuestionType.COMPARISON
        elif 'improve' in question_lower or 'optimize' in question_lower:
            return QuestionType.OPTIMIZATION
        elif 'where' in question_lower or 'when' in question_lower:
            return QuestionType.APPLICATION
        elif 'limit' in question_lower or 'constraint' in question_lower:
            return QuestionType.LIMITATION
        else:
            return QuestionType.EXPLORATION

    def _calculate_priority(self, question: Question, context: Dict[str, Any]) -> float:
        """
        Calcula prioridade da questão

        Fatores:
        - Relevância ao trabalho atual (0.3)
        - Profundidade da questão (0.2)
        - Importância do gap (0.3)
        - Novidade/originalidade (0.2)
        """
        priority = 0.0

        # Fator 1: Relevância
        current_task = context.get('current_task', '')
        if current_task and current_task.lower() in question.question.lower():
            priority += 0.3

        # Fator 2: Profundidade
        depth_weights = {
            QuestionDepth.SURFACE: 0.1,
            QuestionDepth.MEDIUM: 0.15,
            QuestionDepth.DEEP: 0.2,
            QuestionDepth.PHILOSOPHICAL: 0.2
        }
        priority += depth_weights.get(question.depth, 0.1)

        # Fator 3: Importância do gap
        gap_importance = question.context.get('gap', {}).get('importance', 0.5)
        priority += gap_importance * 0.3

        # Fator 4: Tipo de questão (alguns tipos são mais valiosos)
        type_weights = {
            QuestionType.WHY: 0.2,
            QuestionType.HOW: 0.18,
            QuestionType.WHAT_IF: 0.15,
            QuestionType.OPTIMIZATION: 0.17,
            QuestionType.COMPARISON: 0.14,
            QuestionType.EXPLORATION: 0.12,
            QuestionType.APPLICATION: 0.16,
            QuestionType.LIMITATION: 0.13
        }
        priority += type_weights.get(question.type, 0.1)

        # Normalizar para 0-1
        return min(1.0, priority)

    def get_pending_questions(self, limit: int = 10) -> List[Question]:
        """Retorna perguntas pendentes ordenadas por prioridade"""
        pending = [q for q in self.questions if not q.answered]
        pending.sort(key=lambda x: x.priority, reverse=True)
        return pending[:limit]

    def get_answered_questions(self, limit: int = 10) -> List[Question]:
        """Retorna perguntas respondidas recentes"""
        return self.answered_questions[-limit:]

    def mark_answered(
        self,
        question_id: str,
        answer: str,
        confidence: float,
        related_questions: List[str] = None
    ):
        """Marca uma questão como respondida"""
        for q in self.questions:
            if q.id == question_id:
                q.answered = True
                q.answer = answer
                q.confidence = confidence
                q.related_questions = related_questions or []
                self.answered_questions.append(q)
                logger.info(f"Question {question_id} marked as answered (confidence: {confidence})")
                break

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas sobre as perguntas"""
        total = len(self.questions)
        answered = len([q for q in self.questions if q.answered])
        pending = total - answered

        # Por tipo
        by_type = {}
        for q_type in QuestionType:
            count = len([q for q in self.questions if q.type == q_type])
            by_type[q_type.value] = count

        # Por profundidade
        by_depth = {}
        for depth in QuestionDepth:
            count = len([q for q in self.questions if q.depth == depth])
            by_depth[depth.value] = count

        return {
            'total_questions': total,
            'answered': answered,
            'pending': pending,
            'answer_rate': answered / total if total > 0 else 0,
            'by_type': by_type,
            'by_depth': by_depth,
            'avg_priority': sum(q.priority for q in self.questions) / total if total > 0 else 0,
            'avg_confidence': sum(q.confidence for q in self.questions if q.answered) / answered if answered > 0 else 0
        }
