"""
Answer Pursuer - Persegue respostas para perguntas autonomamente

Este módulo permite ao Darwin:
1. Pesquisar respostas em múltiplas fontes
2. Sintetizar informação
3. Avaliar confiança nas respostas
4. Gerar perguntas de follow-up
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnswerSource:
    """Fonte de uma resposta"""
    type: str  # 'web', 'semantic_memory', 'code_analysis', 'ai_reasoning'
    content: str
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Answer:
    """Uma resposta encontrada"""
    question_id: str
    answer: str
    confidence: float
    sources: List[AnswerSource]
    reasoning: str
    follow_up_questions: List[str] = field(default_factory=list)
    experiments_suggested: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'question_id': self.question_id,
            'answer': self.answer,
            'confidence': self.confidence,
            'sources': [
                {
                    'type': s.type,
                    'content': s.content[:200] + '...' if len(s.content) > 200 else s.content,
                    'confidence': s.confidence
                }
                for s in self.sources
            ],
            'reasoning': self.reasoning,
            'follow_up_questions': self.follow_up_questions,
            'experiments_suggested': self.experiments_suggested
        }


class AnswerPursuer:
    """
    Persegue respostas para perguntas de forma autónoma

    Estratégia:
    1. Procurar em semantic memory (conhecimento existente)
    2. Analisar código relevante (se aplicável)
    3. Usar AI reasoning para sintetizar
    4. Pesquisar web (se necessário)
    5. Sugerir experiências (se inconclusivo)
    """

    def __init__(
        self,
        semantic_memory=None,
        multi_model_router=None,
        web_researcher=None,
        max_depth: int = 3
    ):
        self.semantic_memory = semantic_memory
        self.multi_model_router = multi_model_router
        self.web_researcher = web_researcher
        self.max_depth = max_depth
        self.pursuit_history: List[Dict] = []

    async def pursue_answer(
        self,
        question: str,
        question_id: str,
        context: Dict[str, Any],
        depth: int = 0
    ) -> Answer:
        """
        Persegue uma resposta até encontrar algo satisfatório

        Args:
            question: A pergunta a responder
            question_id: ID da pergunta
            context: Contexto adicional
            depth: Profundidade atual da recursão

        Returns:
            Answer com resposta, confiança e fontes
        """
        logger.info(f"Pursuing answer for: {question} (depth={depth})")

        if depth >= self.max_depth:
            logger.warning(f"Max depth {self.max_depth} reached for question: {question}")
            return self._create_inconclusive_answer(question_id, question)

        sources: List[AnswerSource] = []

        # Step 1: Check semantic memory (conhecimento já adquirido)
        if self.semantic_memory:
            memory_result = await self._search_semantic_memory(question, context)
            if memory_result:
                sources.append(memory_result)

        # Step 2: AI Reasoning (sintetizar e raciocinar)
        if self.multi_model_router:
            reasoning_result = await self._ai_reasoning(question, context, sources)
            if reasoning_result:
                sources.append(reasoning_result)

        # Step 3: Code Analysis (se relevante)
        if self._is_code_related(question):
            code_result = await self._analyze_relevant_code(question, context)
            if code_result:
                sources.append(code_result)

        # Step 4: Web Research (se necessário e disponível)
        if self.web_researcher and len(sources) < 2:
            web_result = await self._research_web(question, context)
            if web_result:
                sources.append(web_result)

        # Step 5: Synthesize answer from all sources
        answer = await self._synthesize_answer(
            question_id,
            question,
            sources,
            context
        )

        # Step 6: Generate follow-up questions if confidence is low
        if answer.confidence < 0.7:
            answer.follow_up_questions = self._generate_followup_questions(
                question,
                answer,
                context
            )

        # Step 7: Suggest experiments if answer is theoretical
        if self._needs_experimental_verification(question, answer):
            answer.experiments_suggested = self._suggest_experiments(
                question,
                answer,
                context
            )

        # Record pursuit
        self.pursuit_history.append({
            'question': question,
            'answer': answer.answer,
            'confidence': answer.confidence,
            'sources_count': len(sources),
            'depth': depth,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Answer found with confidence {answer.confidence:.2f}")
        return answer

    async def _search_semantic_memory(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Optional[AnswerSource]:
        """Procura em semantic memory por conhecimento relevante"""
        if not self.semantic_memory:
            return None

        try:
            # Query semantic memory
            results = await self.semantic_memory.query(
                query=question,
                n_results=3
            )

            if not results:
                return None

            # Compile relevant knowledge
            knowledge_pieces = []
            for result in results:
                knowledge_pieces.append(result.get('content', ''))

            content = '\n'.join(knowledge_pieces)

            return AnswerSource(
                type='semantic_memory',
                content=content,
                confidence=0.7  # Memory is usually reliable
            )

        except Exception as e:
            logger.error(f"Error searching semantic memory: {e}")
            return None

    async def _ai_reasoning(
        self,
        question: str,
        context: Dict[str, Any],
        existing_sources: List[AnswerSource]
    ) -> Optional[AnswerSource]:
        """Usa AI para raciocinar sobre a questão"""
        if not self.multi_model_router:
            return None

        try:
            # Build reasoning prompt
            prompt = self._create_reasoning_prompt(question, context, existing_sources)

            # Generate reasoning
            result = await self.multi_model_router.generate(
                task_description=f"Generate reasoning for question: {question}",
                prompt=prompt,
                max_tokens=800
            )

            reasoning = result['result']

            return AnswerSource(
                type='ai_reasoning',
                content=reasoning,
                confidence=0.8  # AI reasoning is usually good
            )

        except Exception as e:
            logger.error(f"Error in AI reasoning: {e}")
            return None

    def _create_reasoning_prompt(
        self,
        question: str,
        context: Dict[str, Any],
        sources: List[AnswerSource]
    ) -> str:
        """Cria prompt para AI raciocinar sobre a questão"""

        # Compile existing knowledge
        existing_knowledge = ""
        if sources:
            existing_knowledge = "\n\nExisting knowledge:\n"
            for i, source in enumerate(sources, 1):
                existing_knowledge += f"\n{i}. From {source.type}:\n{source.content[:300]}...\n"

        prompt = f"""You are Darwin, analyzing a deep question.

Question: {question}

Context:
- Current focus: {context.get('current_task', 'General exploration')}
- Recent learnings: {context.get('recent_learnings', [])}
{existing_knowledge}

Please provide:
1. A clear, accurate answer to the question
2. The reasoning behind your answer
3. Key insights or implications
4. Any caveats or limitations

Be concise but thorough. Focus on genuine understanding, not just facts.
"""
        return prompt

    async def _analyze_relevant_code(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Optional[AnswerSource]:
        """Analisa código relevante para responder à questão"""
        # TODO: Implement code analysis
        # This would use code search and static analysis
        return None

    async def _research_web(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Optional[AnswerSource]:
        """Pesquisa web para encontrar resposta"""
        if not self.web_researcher:
            return None

        try:
            # Research the question
            research_result = await self.web_researcher.research(
                query=question,
                max_results=3
            )

            if not research_result:
                return None

            # Compile findings
            findings = research_result.get('summary', '')

            return AnswerSource(
                type='web',
                content=findings,
                confidence=0.6  # Web research needs verification
            )

        except Exception as e:
            logger.error(f"Error in web research: {e}")
            return None

    async def _synthesize_answer(
        self,
        question_id: str,
        question: str,
        sources: List[AnswerSource],
        context: Dict[str, Any]
    ) -> Answer:
        """Sintetiza uma resposta final a partir de múltiplas fontes"""

        if not sources:
            return self._create_inconclusive_answer(question_id, question)

        # Use AI to synthesize if available
        if self.multi_model_router:
            synthesis = await self._ai_synthesize(question, sources, context)
            if synthesis:
                return synthesis

        # Fallback: Simple aggregation
        combined_content = '\n\n'.join(s.content for s in sources)
        avg_confidence = sum(s.confidence for s in sources) / len(sources)

        return Answer(
            question_id=question_id,
            answer=combined_content,
            confidence=avg_confidence,
            sources=sources,
            reasoning="Combined information from multiple sources"
        )

    async def _ai_synthesize(
        self,
        question: str,
        sources: List[AnswerSource],
        context: Dict[str, Any]
    ) -> Optional[Answer]:
        """Usa AI para sintetizar resposta final"""
        try:
            # Create synthesis prompt
            sources_text = ""
            for i, source in enumerate(sources, 1):
                sources_text += f"\nSource {i} ({source.type}, confidence {source.confidence}):\n"
                sources_text += f"{source.content}\n"

            prompt = f"""Synthesize a clear answer from these sources:

Question: {question}

{sources_text}

Provide:
1. A clear, synthesized answer (2-3 paragraphs)
2. Your reasoning process
3. Overall confidence in this answer (0-1)
4. Key insights gained

Format your response as:
ANSWER: [your answer]
REASONING: [your reasoning]
CONFIDENCE: [0.0-1.0]
INSIGHTS: [key insights]
"""

            result = await self.multi_model_router.generate(
                task_description="Synthesize answer from multiple sources",
                prompt=prompt,
                max_tokens=1000
            )

            # Parse response
            response = result['result']
            answer_text = self._extract_section(response, 'ANSWER')
            reasoning = self._extract_section(response, 'REASONING')
            confidence_str = self._extract_section(response, 'CONFIDENCE')

            try:
                confidence = float(confidence_str) if confidence_str else 0.7
            except:
                confidence = 0.7

            return Answer(
                question_id='',  # Will be set by caller
                answer=answer_text or response,
                confidence=confidence,
                sources=sources,
                reasoning=reasoning or "AI synthesis of multiple sources"
            )

        except Exception as e:
            logger.error(f"Error in AI synthesis: {e}")
            return None

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extrai uma seção específica do texto"""
        lines = text.split('\n')
        collecting = False
        content = []

        for line in lines:
            if line.strip().startswith(f'{section_name}:'):
                collecting = True
                # Get content after colon
                after_colon = line.split(':', 1)[1].strip()
                if after_colon:
                    content.append(after_colon)
                continue

            if collecting:
                # Stop at next section or empty line
                if any(line.strip().startswith(f'{s}:') for s in ['ANSWER', 'REASONING', 'CONFIDENCE', 'INSIGHTS']):
                    break
                if line.strip():
                    content.append(line.strip())

        return ' '.join(content)

    def _create_inconclusive_answer(self, question_id: str, question: str) -> Answer:
        """Cria uma resposta inconclusiva"""
        return Answer(
            question_id=question_id,
            answer=f"I need more information to answer '{question}' conclusively.",
            confidence=0.3,
            sources=[],
            reasoning="Insufficient information available",
            follow_up_questions=[
                f"What specific aspects of '{question}' should I focus on?",
                f"Are there experiments I could run to answer '{question}'?",
                f"What related knowledge might help answer '{question}'?"
            ],
            experiments_suggested=[
                f"Design an experiment to test assumptions in '{question}'"
            ]
        )

    def _is_code_related(self, question: str) -> bool:
        """Detecta se a questão é sobre código"""
        code_keywords = [
            'function', 'class', 'method', 'code', 'implement',
            'algorithm', 'optimization', 'performance', 'python',
            'javascript', 'api', 'library', 'framework'
        ]
        question_lower = question.lower()
        return any(kw in question_lower for kw in code_keywords)

    def _needs_experimental_verification(
        self,
        question: str,
        answer: Answer
    ) -> bool:
        """Determina se a resposta precisa de verificação experimental"""
        # Questões sobre performance sempre precisam
        performance_keywords = ['faster', 'slower', 'performance', 'efficient', 'optimize']
        if any(kw in question.lower() for kw in performance_keywords):
            return True

        # Confiança baixa precisa de verificação
        if answer.confidence < 0.6:
            return True

        # Respostas teóricas precisam de verificação
        theoretical_keywords = ['should', 'would', 'could', 'probably', 'likely']
        if any(kw in answer.answer.lower() for kw in theoretical_keywords):
            return True

        return False

    def _generate_followup_questions(
        self,
        original_question: str,
        answer: Answer,
        context: Dict[str, Any]
    ) -> List[str]:
        """Gera perguntas de follow-up"""
        followup = []

        # Se a resposta tem baixa confiança
        if answer.confidence < 0.6:
            followup.append(f"What additional information would help answer: {original_question}?")

        # Se há aspectos não cobertos
        followup.append(f"What are the implications of: {answer.answer[:50]}...?")
        followup.append(f"How can I verify: {answer.answer[:50]}...?")

        # Se há contradições nas fontes
        if len(answer.sources) > 1:
            confidences = [s.confidence for s in answer.sources]
            if max(confidences) - min(confidences) > 0.3:
                followup.append("Why do different sources have different confidence levels?")

        return followup[:3]  # Limit to 3

    def _suggest_experiments(
        self,
        question: str,
        answer: Answer,
        context: Dict[str, Any]
    ) -> List[str]:
        """Sugere experiências para verificar a resposta"""
        experiments = []

        # Experiência de benchmark (se performance)
        if any(kw in question.lower() for kw in ['faster', 'performance', 'efficient']):
            experiments.append(
                f"Benchmark experiment: Compare performance of approaches mentioned in answer"
            )

        # Experiência de comportamento (se funcional)
        if any(kw in question.lower() for kw in ['how', 'work', 'behavior']):
            experiments.append(
                f"Behavioral experiment: Test the mechanism described in answer"
            )

        # Experiência de limite (se sobre constraints)
        if any(kw in question.lower() for kw in ['limit', 'constraint', 'maximum']):
            experiments.append(
                f"Boundary experiment: Test the limits mentioned in answer"
            )

        return experiments[:2]  # Limit to 2

    def get_pursuit_history(self, limit: int = 10) -> List[Dict]:
        """Retorna histórico de pursuits recentes"""
        return self.pursuit_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas sobre pursuits"""
        total = len(self.pursuit_history)
        if total == 0:
            return {
                'total_pursuits': 0,
                'avg_confidence': 0,
                'avg_sources_used': 0,
                'success_rate': 0
            }

        confidences = [p['confidence'] for p in self.pursuit_history]
        sources = [p['sources_count'] for p in self.pursuit_history]
        successful = len([p for p in self.pursuit_history if p['confidence'] >= 0.7])

        return {
            'total_pursuits': total,
            'avg_confidence': sum(confidences) / total,
            'avg_sources_used': sum(sources) / total,
            'success_rate': successful / total,
            'high_confidence_answers': successful,
            'low_confidence_answers': total - successful
        }
