"""
Inquiry Routes - API endpoints for Question Engine, Answer Pursuer, and Socratic Dialogue

Provides endpoints for:
- Generating deep questions
- Pursuing answers autonomously
- Starting Socratic dialogues
- Viewing inquiry history and statistics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/inquiry", tags=["inquiry"])

# Global instances (set by initialize_inquiry)
question_engine = None
answer_pursuer = None
socratic_dialogue = None


def initialize_inquiry(qe, ap, sd):
    """Initialize inquiry routes with system instances"""
    global question_engine, answer_pursuer, socratic_dialogue
    question_engine = qe
    answer_pursuer = ap
    socratic_dialogue = sd
    logger.info("Inquiry routes initialized")


@router.post("/questions/generate")
async def generate_questions(
    context: Dict[str, Any],
    depth: str = "medium",
    max_questions: int = 10
):
    """
    Generate deep questions based on context

    Args:
        context: Current context (recent_learnings, current_task, etc.)
        depth: Question depth (surface, medium, deep, philosophical)
        max_questions: Maximum number of questions to generate

    Returns:
        List of generated questions with priorities
    """
    if not question_engine:
        raise HTTPException(503, "Question Engine not initialized")

    try:
        from inquiry.question_engine import QuestionDepth

        depth_enum = QuestionDepth(depth)

        questions = await question_engine.generate_questions(
            context=context,
            depth=depth_enum,
            max_questions=max_questions
        )

        return {
            'success': True,
            'questions': [q.to_dict() for q in questions],
            'count': len(questions),
            'depth': depth,
            'context_summary': {
                'recent_learnings': len(context.get('recent_learnings', [])),
                'curiosities': len(context.get('curiosities', [])),
                'current_task': context.get('current_task', 'None')
            }
        }

    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise HTTPException(500, f"Error generating questions: {str(e)}")


@router.get("/questions/pending")
async def get_pending_questions(limit: int = 10):
    """
    Get pending (unanswered) questions

    Args:
        limit: Maximum number of questions to return

    Returns:
        List of pending questions ordered by priority
    """
    if not question_engine:
        raise HTTPException(503, "Question Engine not initialized")

    try:
        questions = question_engine.get_pending_questions(limit)

        return {
            'success': True,
            'questions': [q.to_dict() for q in questions],
            'count': len(questions),
            'total_pending': len([q for q in question_engine.questions if not q.answered])
        }

    except Exception as e:
        logger.error(f"Error getting pending questions: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/questions/answered")
async def get_answered_questions(limit: int = 10):
    """
    Get recently answered questions

    Args:
        limit: Maximum number of questions to return

    Returns:
        List of answered questions with answers and confidence
    """
    if not question_engine:
        raise HTTPException(503, "Question Engine not initialized")

    try:
        questions = question_engine.get_answered_questions(limit)

        return {
            'success': True,
            'questions': [q.to_dict() for q in questions],
            'count': len(questions)
        }

    except Exception as e:
        logger.error(f"Error getting answered questions: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/questions/{question_id}/pursue")
async def pursue_question(question_id: str, context: Optional[Dict[str, Any]] = None):
    """
    Pursue an answer for a specific question

    Args:
        question_id: ID of the question to pursue
        context: Additional context for pursuit

    Returns:
        Answer with sources, confidence, and follow-up questions
    """
    if not question_engine or not answer_pursuer:
        raise HTTPException(503, "Inquiry systems not initialized")

    try:
        # Find question
        question = next(
            (q for q in question_engine.questions if q.id == question_id),
            None
        )

        if not question:
            raise HTTPException(404, f"Question {question_id} not found")

        # Pursue answer
        answer = await answer_pursuer.pursue_answer(
            question=question.question,
            question_id=question_id,
            context=context or {},
            depth=0
        )

        # Mark as answered
        question_engine.mark_answered(
            question_id=question_id,
            answer=answer.answer,
            confidence=answer.confidence,
            related_questions=answer.follow_up_questions
        )

        return {
            'success': True,
            'question': question.question,
            'answer': answer.to_dict(),
            'marked_answered': True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pursuing question: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/dialogue/start")
async def start_socratic_dialogue(
    topic: str,
    initial_question: str,
    context: Optional[Dict[str, Any]] = None,
    duration_minutes: int = 10
):
    """
    Start a Socratic dialogue session

    Darwin will question itself about the topic, revealing insights and gaps.

    Args:
        topic: Topic to explore
        initial_question: Initial question to start the dialogue
        context: Current context
        duration_minutes: Maximum duration for dialogue

    Returns:
        Complete dialogue session with insights and understanding
    """
    if not socratic_dialogue:
        raise HTTPException(503, "Socratic Dialogue not initialized")

    try:
        session = await socratic_dialogue.internal_dialogue(
            topic=topic,
            initial_question=initial_question,
            context=context or {},
            duration_minutes=duration_minutes
        )

        return {
            'success': True,
            'session': session.to_dict(),
            'summary': {
                'turns': len(session.turns),
                'insights': len(session.insights_gained),
                'gaps': len(session.knowledge_gaps),
                'contradictions': len(session.contradictions_found)
            }
        }

    except Exception as e:
        logger.error(f"Error starting dialogue: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/dialogue/sessions")
async def get_dialogue_sessions(limit: int = 5):
    """
    Get recent Socratic dialogue sessions

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of recent dialogue sessions
    """
    if not socratic_dialogue:
        raise HTTPException(503, "Socratic Dialogue not initialized")

    try:
        sessions = socratic_dialogue.get_recent_sessions(limit)

        return {
            'success': True,
            'sessions': [s.to_dict() for s in sessions],
            'count': len(sessions)
        }

    except Exception as e:
        logger.error(f"Error getting sessions: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/dialogue/sessions/{session_id}")
async def get_dialogue_session(session_id: str):
    """
    Get a specific dialogue session

    Args:
        session_id: ID of the session

    Returns:
        Complete dialogue session with all turns
    """
    if not socratic_dialogue:
        raise HTTPException(503, "Socratic Dialogue not initialized")

    try:
        session = socratic_dialogue.get_session(session_id)

        if not session:
            raise HTTPException(404, f"Session {session_id} not found")

        return {
            'success': True,
            'session': session.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/dialogue/insights")
async def get_all_insights():
    """
    Get all insights from all Socratic dialogues

    Returns:
        List of all insights gained through dialogues
    """
    if not socratic_dialogue:
        raise HTTPException(503, "Socratic Dialogue not initialized")

    try:
        insights = socratic_dialogue.get_all_insights()

        return {
            'success': True,
            'insights': insights,
            'count': len(insights)
        }

    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/dialogue/gaps")
async def get_all_gaps():
    """
    Get all knowledge gaps identified through dialogues

    Returns:
        List of all knowledge gaps found
    """
    if not socratic_dialogue:
        raise HTTPException(503, "Socratic Dialogue not initialized")

    try:
        gaps = socratic_dialogue.get_all_gaps()

        return {
            'success': True,
            'gaps': gaps,
            'count': len(gaps)
        }

    except Exception as e:
        logger.error(f"Error getting gaps: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/statistics")
async def get_inquiry_statistics():
    """
    Get comprehensive statistics from all inquiry systems

    Returns:
        Statistics from Question Engine, Answer Pursuer, and Socratic Dialogue
    """
    try:
        stats = {}

        if question_engine:
            stats['question_engine'] = question_engine.get_statistics()

        if answer_pursuer:
            stats['answer_pursuer'] = answer_pursuer.get_statistics()

        if socratic_dialogue:
            stats['socratic_dialogue'] = socratic_dialogue.get_statistics()

        return {
            'success': True,
            'statistics': stats,
            'systems_active': {
                'question_engine': question_engine is not None,
                'answer_pursuer': answer_pursuer is not None,
                'socratic_dialogue': socratic_dialogue is not None
            }
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.post("/debug/test-question")
async def test_question_generation():
    """
    Debug endpoint: Test question generation with sample context

    Returns:
        Sample questions generated from test context
    """
    if not question_engine:
        raise HTTPException(503, "Question Engine not initialized")

    try:
        from inquiry.question_engine import QuestionDepth

        test_context = {
            'recent_learnings': [
                'list comprehensions are faster than for loops',
                'async/await improves performance'
            ],
            'current_task': 'optimizing Darwin code',
            'curiosities': [
                'Why are comprehensions faster?',
                'How does Python optimize bytecode?'
            ],
            'mentioned_concepts': ['bytecode', 'optimization', 'async']
        }

        questions = await question_engine.generate_questions(
            context=test_context,
            depth=QuestionDepth.DEEP,
            max_questions=5
        )

        return {
            'success': True,
            'test_context': test_context,
            'questions_generated': [q.to_dict() for q in questions],
            'count': len(questions)
        }

    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


@router.get("/health")
async def inquiry_health():
    """
    Health check for inquiry systems

    Returns:
        Status of all inquiry components
    """
    return {
        'status': 'healthy' if all([question_engine, answer_pursuer, socratic_dialogue]) else 'partial',
        'components': {
            'question_engine': {
                'status': 'active' if question_engine else 'inactive',
                'questions_total': len(question_engine.questions) if question_engine else 0,
                'questions_answered': len([q for q in question_engine.questions if q.answered]) if question_engine else 0
            },
            'answer_pursuer': {
                'status': 'active' if answer_pursuer else 'inactive',
                'pursuits_total': len(answer_pursuer.pursuit_history) if answer_pursuer else 0
            },
            'socratic_dialogue': {
                'status': 'active' if socratic_dialogue else 'inactive',
                'sessions_total': len(socratic_dialogue.sessions) if socratic_dialogue else 0
            }
        }
    }
