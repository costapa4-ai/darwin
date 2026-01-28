"""
Question System - Allows Darwin to ask questions when uncertain
This makes Darwin more interactive and collaborative
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid


class QuestionType(Enum):
    """Types of questions Darwin can ask"""
    CLARIFICATION = "clarification"       # Needs clarification on something
    CONFIRMATION = "confirmation"         # Wants to confirm understanding
    PREFERENCE = "preference"             # Asking user preference
    DECISION = "decision"                 # Needs user to make a decision
    FEEDBACK = "feedback"                 # Asking for feedback
    PERMISSION = "permission"             # Requesting permission
    SUGGESTION = "suggestion"             # Suggesting and asking if ok
    CURIOSITY = "curiosity"               # Curious about something
    TROUBLESHOOTING = "troubleshooting"   # Stuck on a problem
    VALIDATION = "validation"             # Wants validation of approach


class QuestionPriority(Enum):
    """Priority levels for questions"""
    LOW = "low"              # Nice to know
    MEDIUM = "medium"        # Should answer soon
    HIGH = "high"            # Important for progress
    URGENT = "urgent"        # Blocking, needs immediate answer


class QuestionStatus(Enum):
    """Status of questions"""
    PENDING = "pending"      # Waiting for answer
    ANSWERED = "answered"    # User provided answer
    DISMISSED = "dismissed"  # User dismissed/skipped
    EXPIRED = "expired"      # Question became irrelevant


@dataclass
class QuestionOption:
    """An option for multiple choice questions"""
    value: str
    label: str
    description: Optional[str] = None


@dataclass
class Question:
    """A question Darwin wants to ask"""
    id: str
    type: QuestionType
    priority: QuestionPriority
    question: str
    context: Dict[str, Any]

    # For multiple choice
    options: Optional[List[QuestionOption]] = None
    allow_multiple: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    status: QuestionStatus = QuestionStatus.PENDING

    # Answer
    answer: Optional[Any] = None
    answered_at: Optional[datetime] = None

    # Callbacks
    on_answer: Optional[Callable] = None

    # Tags for filtering
    tags: List[str] = field(default_factory=list)

    # Related mood (if question affects mood)
    mood_trigger: Optional[str] = None


class QuestionSystem:
    """
    Manages Darwin's questions to the user

    Features:
    - Question queue with priorities
    - Multiple choice and free text questions
    - Question expiration
    - Answer callbacks
    - Question history
    - Statistics
    """

    def __init__(self):
        """Initialize question system"""
        self.questions: Dict[str, Question] = {}  # Active questions
        self.history: List[Question] = []  # Answered/dismissed questions
        self.history_limit = 100

        # Settings
        self.max_pending_questions = 10  # Don't overwhelm user
        self.default_expiry_minutes = 60  # Questions expire after 1 hour

    def ask_question(
        self,
        question: str,
        type: QuestionType,
        priority: QuestionPriority = QuestionPriority.MEDIUM,
        context: Optional[Dict] = None,
        options: Optional[List[QuestionOption]] = None,
        allow_multiple: bool = False,
        expires_in_minutes: Optional[int] = None,
        on_answer: Optional[Callable] = None,
        tags: Optional[List[str]] = None,
        mood_trigger: Optional[str] = None
    ) -> str:
        """
        Ask a question to the user

        Args:
            question: The question text
            type: Type of question
            priority: Priority level
            context: Additional context
            options: For multiple choice questions
            allow_multiple: Allow selecting multiple options
            expires_in_minutes: Question expiry time
            on_answer: Callback when answered
            tags: Tags for filtering
            mood_trigger: Mood event to trigger on answer

        Returns:
            Question ID
        """
        # Check if we have too many pending questions
        pending_count = sum(
            1 for q in self.questions.values()
            if q.status == QuestionStatus.PENDING
        )

        if pending_count >= self.max_pending_questions:
            # Remove oldest low priority question
            self._cleanup_low_priority()

        # Create question
        question_id = str(uuid.uuid4())

        expires_at = None
        if expires_in_minutes or self.default_expiry_minutes:
            minutes = expires_in_minutes or self.default_expiry_minutes
            expires_at = datetime.now() + timedelta(minutes=minutes)

        q = Question(
            id=question_id,
            type=type,
            priority=priority,
            question=question,
            context=context or {},
            options=options,
            allow_multiple=allow_multiple,
            expires_at=expires_at,
            on_answer=on_answer,
            tags=tags or [],
            mood_trigger=mood_trigger
        )

        self.questions[question_id] = q

        # Clean up expired questions
        self._cleanup_expired()

        return question_id

    def answer_question(
        self,
        question_id: str,
        answer: Any
    ) -> Optional[Question]:
        """
        Provide answer to a question

        Args:
            question_id: ID of question to answer
            answer: The answer

        Returns:
            Question object if found and answered, None otherwise
        """
        question = self.questions.get(question_id)

        if not question:
            return None

        if question.status != QuestionStatus.PENDING:
            return None

        # Validate multiple choice
        if question.options:
            if question.allow_multiple:
                # Answer should be list of values
                if not isinstance(answer, list):
                    answer = [answer]
                valid_values = [opt.value for opt in question.options]
                if not all(a in valid_values for a in answer):
                    return None
            else:
                # Answer should be single value
                valid_values = [opt.value for opt in question.options]
                if answer not in valid_values:
                    return None

        # Record answer
        question.answer = answer
        question.answered_at = datetime.now()
        question.status = QuestionStatus.ANSWERED

        # Call callback if provided
        if question.on_answer:
            try:
                question.on_answer(answer)
            except Exception as e:
                print(f"⚠️ Error in question callback: {e}")

        # Move to history
        self._archive_question(question_id)

        return question

    def dismiss_question(self, question_id: str) -> Optional[Question]:
        """
        Dismiss/skip a question

        Args:
            question_id: ID of question to dismiss

        Returns:
            Question object if found, None otherwise
        """
        question = self.questions.get(question_id)

        if not question:
            return None

        question.status = QuestionStatus.DISMISSED
        question.answered_at = datetime.now()

        # Move to history
        self._archive_question(question_id)

        return question

    def get_pending_questions(
        self,
        priority: Optional[QuestionPriority] = None,
        type: Optional[QuestionType] = None,
        tags: Optional[List[str]] = None
    ) -> List[Question]:
        """
        Get pending questions with optional filters

        Args:
            priority: Filter by priority
            type: Filter by type
            tags: Filter by tags (any match)

        Returns:
            List of pending questions
        """
        questions = [
            q for q in self.questions.values()
            if q.status == QuestionStatus.PENDING
        ]

        # Apply filters
        if priority:
            questions = [q for q in questions if q.priority == priority]

        if type:
            questions = [q for q in questions if q.type == type]

        if tags:
            questions = [
                q for q in questions
                if any(tag in q.tags for tag in tags)
            ]

        # Sort by priority (urgent first)
        priority_order = {
            QuestionPriority.URGENT: 0,
            QuestionPriority.HIGH: 1,
            QuestionPriority.MEDIUM: 2,
            QuestionPriority.LOW: 3
        }

        questions.sort(key=lambda q: (
            priority_order.get(q.priority, 999),
            q.created_at
        ))

        return questions

    def get_question(self, question_id: str) -> Optional[Question]:
        """
        Get specific question by ID

        Args:
            question_id: Question ID

        Returns:
            Question if found, None otherwise
        """
        return self.questions.get(question_id) or next(
            (q for q in self.history if q.id == question_id),
            None
        )

    def _cleanup_expired(self):
        """Mark expired questions as expired"""
        now = datetime.now()

        for question in list(self.questions.values()):
            if question.expires_at and question.expires_at < now:
                question.status = QuestionStatus.EXPIRED
                self._archive_question(question.id)

    def _cleanup_low_priority(self):
        """Remove oldest low priority question to make room"""
        low_priority = [
            q for q in self.questions.values()
            if q.priority == QuestionPriority.LOW
            and q.status == QuestionStatus.PENDING
        ]

        if low_priority:
            # Sort by age
            low_priority.sort(key=lambda q: q.created_at)
            oldest = low_priority[0]
            oldest.status = QuestionStatus.EXPIRED
            self._archive_question(oldest.id)

    def _archive_question(self, question_id: str):
        """Move question from active to history"""
        question = self.questions.pop(question_id, None)

        if question:
            self.history.append(question)

            # Limit history size
            if len(self.history) > self.history_limit:
                self.history = self.history[-self.history_limit:]

    def get_history(
        self,
        limit: int = 20,
        status: Optional[QuestionStatus] = None
    ) -> List[Question]:
        """
        Get question history

        Args:
            limit: Max number of questions
            status: Filter by status

        Returns:
            List of historical questions
        """
        questions = self.history

        if status:
            questions = [q for q in questions if q.status == status]

        return questions[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about questions

        Returns:
            Statistics dictionary
        """
        from collections import Counter

        # Pending questions
        pending = self.get_pending_questions()

        # History stats
        answered = [q for q in self.history if q.status == QuestionStatus.ANSWERED]
        dismissed = [q for q in self.history if q.status == QuestionStatus.DISMISSED]
        expired = [q for q in self.history if q.status == QuestionStatus.EXPIRED]

        # Response times (for answered questions)
        response_times = []
        for q in answered:
            if q.answered_at:
                delta = (q.answered_at - q.created_at).total_seconds() / 60
                response_times.append(delta)

        avg_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0
        )

        # Question types
        type_counts = Counter(q.type.value for q in self.history)

        # Priority distribution
        priority_counts = Counter(q.priority.value for q in pending)

        return {
            'pending_questions': len(pending),
            'total_asked': len(self.history),
            'answered': len(answered),
            'dismissed': len(dismissed),
            'expired': len(expired),
            'answer_rate': (
                len(answered) / len(self.history) * 100
                if self.history else 0
            ),
            'average_response_time_minutes': round(avg_response_time, 1),
            'by_type': dict(type_counts),
            'pending_by_priority': dict(priority_counts)
        }

    def clear_pending(self):
        """Clear all pending questions (for testing)"""
        for question in list(self.questions.values()):
            if question.status == QuestionStatus.PENDING:
                question.status = QuestionStatus.DISMISSED
                self._archive_question(question.id)

    # Convenience methods for common question types

    def ask_confirmation(
        self,
        question: str,
        context: Optional[Dict] = None,
        priority: QuestionPriority = QuestionPriority.MEDIUM,
        on_answer: Optional[Callable] = None
    ) -> str:
        """
        Ask a yes/no confirmation question

        Args:
            question: Question text
            context: Additional context
            priority: Priority level
            on_answer: Callback when answered

        Returns:
            Question ID
        """
        return self.ask_question(
            question=question,
            type=QuestionType.CONFIRMATION,
            priority=priority,
            context=context,
            options=[
                QuestionOption(value="yes", label="Yes"),
                QuestionOption(value="no", label="No")
            ],
            on_answer=on_answer
        )

    def ask_choice(
        self,
        question: str,
        choices: List[Dict[str, str]],
        context: Optional[Dict] = None,
        priority: QuestionPriority = QuestionPriority.MEDIUM,
        allow_multiple: bool = False,
        on_answer: Optional[Callable] = None
    ) -> str:
        """
        Ask a multiple choice question

        Args:
            question: Question text
            choices: List of dicts with 'value', 'label', optional 'description'
            context: Additional context
            priority: Priority level
            allow_multiple: Allow multiple selections
            on_answer: Callback when answered

        Returns:
            Question ID
        """
        options = [
            QuestionOption(
                value=c['value'],
                label=c['label'],
                description=c.get('description')
            )
            for c in choices
        ]

        return self.ask_question(
            question=question,
            type=QuestionType.PREFERENCE,
            priority=priority,
            context=context,
            options=options,
            allow_multiple=allow_multiple,
            on_answer=on_answer
        )

    def ask_permission(
        self,
        action: str,
        reason: str,
        context: Optional[Dict] = None,
        priority: QuestionPriority = QuestionPriority.HIGH,
        on_answer: Optional[Callable] = None
    ) -> str:
        """
        Ask permission to perform an action

        Args:
            action: Action to perform
            reason: Why it's needed
            context: Additional context
            priority: Priority level
            on_answer: Callback when answered

        Returns:
            Question ID
        """
        return self.ask_question(
            question=f"Can I {action}? {reason}",
            type=QuestionType.PERMISSION,
            priority=priority,
            context=context or {'action': action, 'reason': reason},
            options=[
                QuestionOption(value="allow", label="Yes, go ahead"),
                QuestionOption(value="deny", label="No, don't do it"),
                QuestionOption(value="ask_later", label="Ask me later")
            ],
            on_answer=on_answer
        )

    def ask_feedback(
        self,
        subject: str,
        context: Optional[Dict] = None,
        priority: QuestionPriority = QuestionPriority.LOW
    ) -> str:
        """
        Ask for user feedback on something

        Args:
            subject: What to get feedback on
            context: Additional context
            priority: Priority level

        Returns:
            Question ID
        """
        return self.ask_question(
            question=f"How did I do on {subject}?",
            type=QuestionType.FEEDBACK,
            priority=priority,
            context=context or {'subject': subject},
            options=[
                QuestionOption(value="great", label="Great! 🎉"),
                QuestionOption(value="good", label="Good 👍"),
                QuestionOption(value="ok", label="OK 😐"),
                QuestionOption(value="poor", label="Could be better 😕"),
                QuestionOption(value="bad", label="Not good ❌")
            ]
        )
