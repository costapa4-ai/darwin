"""
Question System API Routes
Endpoints for Darwin's question asking and answering
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List, Any
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

# Global communicator instance (set from main.py)
communicator = None


def initialize_questions(comm):
    """Initialize question routes with communicator"""
    global communicator
    communicator = comm
    print("✅ Question Routes initialized")


class AnswerRequest(BaseModel):
    """Request to answer a question"""
    question_id: str
    answer: Any


class DismissRequest(BaseModel):
    """Request to dismiss a question"""
    question_id: str


class AskQuestionRequest(BaseModel):
    """Request to ask a question (for testing)"""
    question: str
    context: Optional[dict] = None
    urgency: str = "medium"
    question_type: Optional[str] = None
    options: Optional[List[dict]] = None


@router.get("/pending")
async def get_pending_questions(
    priority: Optional[str] = None,
    type: Optional[str] = None
):
    """
    🤔 Get pending questions

    Args:
        priority: Filter by priority (low, medium, high, urgent)
        type: Filter by type (clarification, confirmation, etc.)

    Returns list of questions waiting for answers
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        from personality.question_system import QuestionPriority, QuestionType

        # Parse filters
        priority_filter = None
        if priority:
            try:
                priority_filter = QuestionPriority(priority)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")

        type_filter = None
        if type:
            try:
                type_filter = QuestionType(type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid type: {type}")

        # Get questions
        questions = communicator.questions.get_pending_questions(
            priority=priority_filter,
            type=type_filter
        )

        return {
            'success': True,
            'questions': [
                {
                    'id': q.id,
                    'question': q.question,
                    'type': q.type.value,
                    'priority': q.priority.value,
                    'created_at': q.created_at.isoformat(),
                    'expires_at': q.expires_at.isoformat() if q.expires_at else None,
                    'options': [
                        {
                            'value': opt.value,
                            'label': opt.label,
                            'description': opt.description
                        }
                        for opt in q.options
                    ] if q.options else None,
                    'allow_multiple': q.allow_multiple,
                    'context': q.context,
                    'tags': q.tags
                }
                for q in questions
            ],
            'count': len(questions)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting questions: {str(e)}")


@router.post("/answer")
async def answer_question(request: AnswerRequest):
    """
    ✅ Answer a question

    Provide an answer to Darwin's question

    Args:
        question_id: ID of the question
        answer: The answer (can be string, list, etc.)

    Returns confirmation and question details
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        # Answer the question
        success = communicator.answer_question(
            question_id=request.question_id,
            answer=request.answer
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found or already answered: {request.question_id}"
            )

        # Get the answered question
        question = communicator.questions.get_question(request.question_id)

        return {
            'success': True,
            'message': 'Question answered successfully',
            'question': {
                'id': question.id,
                'question': question.question,
                'answer': question.answer,
                'answered_at': question.answered_at.isoformat() if question.answered_at else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@router.post("/dismiss")
async def dismiss_question(request: DismissRequest):
    """
    ⏭️ Dismiss a question

    Skip/dismiss a question without answering

    Args:
        question_id: ID of the question to dismiss

    Returns confirmation
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        success = communicator.dismiss_question(request.question_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Question not found: {request.question_id}"
            )

        return {
            'success': True,
            'message': 'Question dismissed successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error dismissing question: {str(e)}")


@router.get("/history")
async def get_question_history(
    limit: int = 20,
    status: Optional[str] = None
):
    """
    📊 Get question history

    Args:
        limit: Number of questions to return (default 20)
        status: Filter by status (answered, dismissed, expired)

    Returns historical questions
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        from personality.question_system import QuestionStatus

        status_filter = None
        if status:
            try:
                status_filter = QuestionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        history = communicator.questions.get_history(
            limit=limit,
            status=status_filter
        )

        return {
            'success': True,
            'questions': [
                {
                    'id': q.id,
                    'question': q.question,
                    'type': q.type.value,
                    'priority': q.priority.value,
                    'status': q.status.value,
                    'created_at': q.created_at.isoformat(),
                    'answered_at': q.answered_at.isoformat() if q.answered_at else None,
                    'answer': q.answer,
                    'context': q.context
                }
                for q in history
            ],
            'count': len(history)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


@router.get("/statistics")
async def get_question_statistics():
    """
    📈 Get question statistics

    Returns:
    - Pending questions count
    - Total questions asked
    - Answer rate
    - Average response time
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        stats = communicator.questions.get_statistics()

        return {
            'success': True,
            'statistics': stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.get("/info")
async def get_questions_info():
    """
    ℹ️ Get complete question information

    Returns both pending questions and statistics
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        info = communicator.get_questions_info()

        return {
            'success': True,
            **info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting info: {str(e)}")


@router.post("/ask")
async def ask_question(request: AskQuestionRequest):
    """
    ❓ Ask a question (for testing)

    Manually trigger Darwin to ask a question

    Args:
        question: The question text
        context: Optional context
        urgency: Priority level (low, medium, high, urgent)
        question_type: Type of question
        options: Options for multiple choice

    Returns question ID
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        from personality.question_system import QuestionType, QuestionOption

        # Parse question type
        q_type = None
        if request.question_type:
            try:
                q_type = QuestionType(request.question_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid question type: {request.question_type}"
                )

        # Parse options
        options = None
        if request.options:
            options = [
                QuestionOption(
                    value=opt.get('value'),
                    label=opt.get('label'),
                    description=opt.get('description')
                )
                for opt in request.options
            ]

        # Ask the question
        question_id = await communicator.ask_question(
            question=request.question,
            context=request.context,
            urgency=request.urgency,
            question_type=q_type,
            options=options
        )

        return {
            'success': True,
            'question_id': question_id,
            'message': 'Question asked successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error asking question: {str(e)}")


@router.get("/types")
async def get_question_types():
    """
    📋 Get available question types

    Returns all possible question types
    """
    from personality.question_system import QuestionType, QuestionPriority, QuestionStatus

    types = {
        qt.value: qt.name.replace('_', ' ').title()
        for qt in QuestionType
    }

    priorities = {
        qp.value: qp.name.replace('_', ' ').title()
        for qp in QuestionPriority
    }

    statuses = {
        qs.value: qs.name.replace('_', ' ').title()
        for qs in QuestionStatus
    }

    return {
        'success': True,
        'types': types,
        'priorities': priorities,
        'statuses': statuses
    }


@router.delete("/clear")
async def clear_pending_questions():
    """
    🗑️ Clear all pending questions (for testing)

    Dismisses all pending questions
    """
    if not communicator:
        raise HTTPException(status_code=503, detail="Question system not initialized")

    try:
        communicator.questions.clear_pending()

        return {
            'success': True,
            'message': 'All pending questions cleared'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing questions: {str(e)}")
