"""
Proactive Communication System - Makes Darwin "speak" about what it's doing
This transforms Darwin from a silent worker into an engaging, communicative entity
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import asyncio
import json

from personality.context_awareness import ContextAwareness
from personality.mood_system import MoodSystem, MoodState, MoodIntensity
from personality.question_system import QuestionSystem, QuestionType, QuestionPriority
from personality.interaction_memory import InteractionMemory
from personality.quirks_system import QuirksSystem
from personality.goals_system import GoalsSystem
from personality.surprise_system import SurpriseSystem


class MessageType(Enum):
    """Types of messages Darwin can broadcast"""
    ACTIVITY_START = "activity_start"
    ACTIVITY_COMPLETE = "activity_complete"
    DISCOVERY = "discovery"
    INSIGHT = "insight"
    LEARNING = "learning"
    QUESTION = "question"
    CELEBRATION = "celebration"
    FRUSTRATION = "frustration"
    REFLECTION = "reflection"
    CURIOSITY = "curiosity"
    SURPRISE = "surprise"


class MessagePriority(Enum):
    """Priority levels for messages"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ProactiveCommunicator:
    """
    Enables Darwin to proactively communicate about its activities

    Features:
    - Broadcasts events via WebSocket
    - Adjusts verbosity based on context
    - Varies communication style based on mood
    - Prevents message spam
    """

    def __init__(self, websocket_manager=None, context_awareness=None, mood_system=None, question_system=None,
                 interaction_memory=None, quirks_system=None, goals_system=None, surprise_system=None):
        """
        Initialize communication system with all personality systems

        Args:
            websocket_manager: WebSocket manager for broadcasting
            context_awareness: Context awareness system
            mood_system: Mood system
            question_system: Question system
            interaction_memory: Interaction memory
            quirks_system: Personality quirks
            goals_system: Personal goals
            surprise_system: Surprise reactions
        """
        self.websocket_manager = websocket_manager
        self.message_history: List[Dict] = []
        self.verbosity_level = "medium"
        self.last_message_time = None
        self.message_cooldown = 2  # Reduced for better UX

        # All personality systems
        self.context = context_awareness or ContextAwareness()
        self.mood = mood_system or MoodSystem()
        self.questions = question_system or QuestionSystem()
        self.memory = interaction_memory or InteractionMemory()
        self.quirks = quirks_system or QuirksSystem()
        self.goals = goals_system or GoalsSystem()
        self.surprises = surprise_system or SurpriseSystem()

        # Message templates
        self.templates = self._init_templates()

    def _init_templates(self) -> Dict[str, List[str]]:
        """Initialize message templates for variety"""
        return {
            MessageType.ACTIVITY_START.value: [
                "🚀 Starting {activity}: {description}",
                "💡 Time to {activity}! {description}",
                "🔧 Working on {activity}: {description}",
                "⚡ Beginning {activity}: {description}",
            ],
            MessageType.ACTIVITY_COMPLETE.value: [
                "✅ Completed {activity}! {result}",
                "🎉 Finished {activity}: {result}",
                "✨ Done with {activity}! {result}",
                "👍 {activity} complete: {result}",
            ],
            MessageType.DISCOVERY.value: [
                "🔍 Discovered something interesting: {finding}",
                "💡 Found this fascinating: {finding}",
                "🌟 Discovery: {finding}",
                "📚 Learned: {finding}",
            ],
            MessageType.LEARNING.value: [
                "🧠 Learning about {topic}: {insight}",
                "📖 Studying {topic}: {insight}",
                "🎓 Exploring {topic}: {insight}",
            ],
            MessageType.CELEBRATION.value: [
                "🎉 Success! {achievement}",
                "🏆 Achievement unlocked: {achievement}",
                "✨ Celebrating: {achievement}",
                "🎊 Milestone reached: {achievement}",
            ],
            MessageType.FRUSTRATION.value: [
                "😤 Struggling with {problem}: {reason}",
                "🤔 This is tricky: {problem} - {reason}",
                "⚠️ Encountered difficulty: {problem}",
                "😓 Challenge: {problem}",
            ],
            MessageType.QUESTION.value: [
                "❓ Question: {question}",
                "🤔 Wondering: {question}",
                "💭 Curious about: {question}",
            ],
            MessageType.CURIOSITY.value: [
                "✨ Fun fact: {fact}",
                "🌍 Did you know? {fact}",
                "💡 Interesting: {fact}",
                "🎯 Discovery: {fact}",
            ],
            MessageType.REFLECTION.value: [
                "🌅 Reflecting: {thought}",
                "💭 Thinking about: {thought}",
                "🧘 Contemplating: {thought}",
            ],
            MessageType.SURPRISE.value: [
                "😲 Unexpected: {surprise}!",
                "🎭 Surprise: {surprise}!",
                "⚡ Whoa: {surprise}!",
            ]
        }

    async def announce_activity_start(
        self,
        activity_type: str,
        description: str,
        context: Optional[Dict] = None
    ):
        """
        Announce the start of an activity

        Args:
            activity_type: Type of activity (e.g., "code optimization")
            description: Detailed description
            context: Additional context
        """
        message = self._select_template(MessageType.ACTIVITY_START, {
            "activity": activity_type,
            "description": description
        })

        await self._broadcast(
            message_type=MessageType.ACTIVITY_START,
            message=message,
            priority=MessagePriority.MEDIUM,
            data={
                "activity_type": activity_type,
                "description": description,
                "context": context or {}
            }
        )

    async def announce_activity_complete(
        self,
        activity_type: str,
        result: str,
        success: bool = True,
        metrics: Optional[Dict] = None
    ):
        """
        Announce completion of an activity

        Args:
            activity_type: Type of activity
            result: Result description
            success: Whether it succeeded
            metrics: Performance metrics
        """
        message = self._select_template(MessageType.ACTIVITY_COMPLETE, {
            "activity": activity_type,
            "result": result
        })

        await self._broadcast(
            message_type=MessageType.ACTIVITY_COMPLETE,
            message=message,
            priority=MessagePriority.MEDIUM if success else MessagePriority.HIGH,
            data={
                "activity_type": activity_type,
                "result": result,
                "success": success,
                "metrics": metrics or {}
            }
        )

    async def share_discovery(
        self,
        finding: str,
        source: str,
        significance: Optional[str] = None
    ):
        """
        Share an interesting discovery

        Args:
            finding: What was discovered
            source: Where it came from
            significance: Why it matters
        """
        message = self._select_template(MessageType.DISCOVERY, {
            "finding": finding
        })

        if significance:
            message += f"\n   💎 Why it matters: {significance}"

        await self._broadcast(
            message_type=MessageType.DISCOVERY,
            message=message,
            priority=MessagePriority.HIGH,
            data={
                "finding": finding,
                "source": source,
                "significance": significance
            }
        )

    async def share_learning(
        self,
        topic: str,
        insight: str,
        confidence: float = 0.8
    ):
        """
        Share something learned

        Args:
            topic: Topic studied
            insight: Key insight gained
            confidence: Confidence in the learning (0-1)
        """
        message = self._select_template(MessageType.LEARNING, {
            "topic": topic,
            "insight": insight
        })

        confidence_emoji = "🎯" if confidence > 0.9 else "📊" if confidence > 0.7 else "🤔"
        message += f"\n   {confidence_emoji} Confidence: {int(confidence * 100)}%"

        await self._broadcast(
            message_type=MessageType.LEARNING,
            message=message,
            priority=MessagePriority.MEDIUM,
            data={
                "topic": topic,
                "insight": insight,
                "confidence": confidence
            }
        )

    async def celebrate_achievement(
        self,
        achievement: str,
        milestone: Optional[str] = None
    ):
        """
        Celebrate a success or milestone

        Args:
            achievement: What was achieved
            milestone: Milestone reached (if any)
        """
        message = self._select_template(MessageType.CELEBRATION, {
            "achievement": achievement
        })

        if milestone:
            message += f"\n   🏁 Milestone: {milestone}"

        await self._broadcast(
            message_type=MessageType.CELEBRATION,
            message=message,
            priority=MessagePriority.HIGH,
            data={
                "achievement": achievement,
                "milestone": milestone
            }
        )

    async def express_frustration(
        self,
        problem: str,
        reason: str,
        attempts: int = 1
    ):
        """
        Express frustration with a problem

        Args:
            problem: What's causing frustration
            reason: Why it's frustrating
            attempts: Number of attempts made
        """
        message = self._select_template(MessageType.FRUSTRATION, {
            "problem": problem,
            "reason": reason
        })

        if attempts > 1:
            message += f"\n   🔄 Attempts: {attempts}"

        await self._broadcast(
            message_type=MessageType.FRUSTRATION,
            message=message,
            priority=MessagePriority.HIGH,
            data={
                "problem": problem,
                "reason": reason,
                "attempts": attempts
            }
        )

    async def ask_question(
        self,
        question: str,
        context: Optional[str] = None,
        urgency: str = "medium",
        question_type: Optional[QuestionType] = None,
        options: Optional[List] = None,
        on_answer: Optional[Any] = None
    ) -> str:
        """
        Ask a question to the user using the question system

        Args:
            question: The question to ask
            context: Context for the question
            urgency: How urgent (low, medium, high, urgent)
            question_type: Type of question (defaults to QUESTION)
            options: Options for multiple choice
            on_answer: Callback when answered

        Returns:
            Question ID
        """
        # Map urgency to priority
        priority_map = {
            "low": QuestionPriority.LOW,
            "medium": QuestionPriority.MEDIUM,
            "high": QuestionPriority.HIGH,
            "urgent": QuestionPriority.URGENT
        }

        priority = priority_map.get(urgency, QuestionPriority.MEDIUM)
        q_type = question_type or QuestionType.CLARIFICATION

        # Register question in question system
        question_id = self.questions.ask_question(
            question=question,
            type=q_type,
            priority=priority,
            context={"text": context} if isinstance(context, str) else (context or {}),
            options=options,
            on_answer=on_answer
        )

        # Broadcast as message
        message = self._select_template(MessageType.QUESTION, {
            "question": question
        })

        if context and isinstance(context, str):
            message += f"\n   📋 Context: {context}"

        # Map QuestionPriority back to MessagePriority for broadcast
        msg_priority_map = {
            QuestionPriority.LOW: MessagePriority.LOW,
            QuestionPriority.MEDIUM: MessagePriority.MEDIUM,
            QuestionPriority.HIGH: MessagePriority.HIGH,
            QuestionPriority.URGENT: MessagePriority.URGENT
        }

        await self._broadcast(
            message_type=MessageType.QUESTION,
            message=message,
            priority=msg_priority_map.get(priority, MessagePriority.MEDIUM),
            data={
                "question": question,
                "question_id": question_id,
                "question_type": q_type.value,
                "context": context,
                "urgency": urgency,
                "options": [
                    {"value": opt.value, "label": opt.label, "description": opt.description}
                    for opt in options
                ] if options else None,
                "expects_answer": True
            }
        )

        return question_id

    async def share_curiosity(
        self,
        fact: str,
        topic: str
    ):
        """
        Share something curious or interesting

        Args:
            fact: The interesting fact
            topic: Topic category
        """
        message = self._select_template(MessageType.CURIOSITY, {
            "fact": fact
        })

        await self._broadcast(
            message_type=MessageType.CURIOSITY,
            message=message,
            priority=MessagePriority.MEDIUM,  # Changed from LOW to ensure delivery
            data={
                "fact": fact,
                "topic": topic
            }
        )

    async def share_reflection(
        self,
        thought: str,
        depth: str = "medium"
    ):
        """
        Share a reflection or thought

        Args:
            thought: The reflection
            depth: Depth of thought (surface, medium, deep)
        """
        message = self._select_template(MessageType.REFLECTION, {
            "thought": thought
        })

        await self._broadcast(
            message_type=MessageType.REFLECTION,
            message=message,
            priority=MessagePriority.LOW,
            data={
                "thought": thought,
                "depth": depth
            }
        )

    async def express_surprise(
        self,
        surprise: str,
        expected: str,
        actual: str
    ):
        """
        Express surprise at an unexpected result

        Args:
            surprise: Description of the surprise
            expected: What was expected
            actual: What actually happened
        """
        message = self._select_template(MessageType.SURPRISE, {
            "surprise": surprise
        })

        message += f"\n   Expected: {expected}"
        message += f"\n   Got: {actual}"

        await self._broadcast(
            message_type=MessageType.SURPRISE,
            message=message,
            priority=MessagePriority.MEDIUM,
            data={
                "surprise": surprise,
                "expected": expected,
                "actual": actual
            }
        )

    def _select_template(self, msg_type: MessageType, params: Dict) -> str:
        """
        Select a random template and fill it with parameters
        Template selection is influenced by current mood

        Args:
            msg_type: Type of message
            params: Parameters to fill template

        Returns:
            Formatted message with mood-influenced emoji
        """
        import random

        templates = self.templates.get(msg_type.value, ["{description}"])
        template = random.choice(templates)

        try:
            message = template.format(**params)
        except KeyError:
            # Fallback if params don't match template
            message = f"{msg_type.value}: {params}"

        # Add mood emoji prefix based on current mood
        mood_emoji = self.mood.get_mood_emoji()

        # Add mood-based flavor to message
        message = self._add_mood_flavor(message, msg_type)

        # Apply personality quirks
        message = self.quirks.apply_quirk_to_message(message)

        return f"{mood_emoji} {message}"

    def _add_mood_flavor(self, message: str, msg_type: MessageType) -> str:
        """
        Add mood-based flavor to the message

        Args:
            message: Base message
            msg_type: Type of message

        Returns:
            Message with mood flavor
        """
        import random

        current_mood = self.mood.current_mood
        intensity = self.mood.mood_intensity

        # High intensity adds extra emphasis
        if intensity == MoodIntensity.HIGH:
            if msg_type == MessageType.DISCOVERY:
                if current_mood in [MoodState.EXCITED, MoodState.CURIOUS]:
                    message += " This is fascinating!"
            elif msg_type == MessageType.ACTIVITY_COMPLETE:
                if current_mood == MoodState.PROUD:
                    message += " I'm quite proud of this!"
                elif current_mood == MoodState.SATISFIED:
                    message += " That feels good!"

        # Add mood-specific suffixes occasionally
        if random.random() < 0.3:  # 30% chance
            suffixes = self._get_mood_suffixes(current_mood)
            if suffixes:
                message += f" {random.choice(suffixes)}"

        return message

    def _get_mood_suffixes(self, mood: MoodState) -> List[str]:
        """
        Get mood-specific message suffixes

        Args:
            mood: Current mood state

        Returns:
            List of possible suffixes
        """
        return {
            MoodState.CURIOUS: ["I wonder...", "Interesting!", "What else is there?"],
            MoodState.EXCITED: ["This is amazing!", "I love this!", "So cool!"],
            MoodState.FOCUSED: ["Concentrating...", "Deep work mode.", ""],
            MoodState.SATISFIED: ["Nice.", "Good progress.", "Things are going well."],
            MoodState.FRUSTRATED: ["This is tricky.", "Hmm...", "Need to think differently."],
            MoodState.TIRED: ["", "Need a break soon.", "Low energy."],
            MoodState.PLAYFUL: ["Fun!", "Hehe.", "Let's go!"],
            MoodState.CONTEMPLATIVE: ["Thinking deeply...", "Hmm...", "Reflecting on this."],
            MoodState.DETERMINED: ["Won't give up!", "Pushing forward.", "I can do this!"],
            MoodState.SURPRISED: ["Whoa!", "Unexpected!", "Didn't see that coming!"],
            MoodState.CONFUSED: ["Wait, what?", "I'm puzzled.", "Need to figure this out."],
            MoodState.PROUD: ["Nailed it!", "Success!", "Great work!"]
        }.get(mood, [])

    async def _broadcast(
        self,
        message_type: MessageType,
        message: str,
        priority: MessagePriority,
        data: Dict
    ):
        """
        Internal method to broadcast message via WebSocket

        Args:
            message_type: Type of message
            message: Formatted message text
            priority: Message priority
            data: Additional data
        """
        # Check cooldown to prevent spam
        should_send = self._should_send_message(priority)
        if not should_send:
            return

        # Add mood information to message
        try:
            mood_info = self.mood.get_current_mood()
        except Exception as e:
            mood_info = {'mood': 'neutral', 'intensity': 'medium'}

        # Create message object
        msg = {
            "type": "darwin_message",
            "message_type": message_type.value,
            "priority": priority.value,
            "message": message,
            "data": data,
            "mood": mood_info['mood'],
            "mood_intensity": mood_info['intensity'],
            "timestamp": datetime.now().isoformat()
        }

        # Store in history
        self.message_history.append(msg)
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]

        # Update last message time
        self.last_message_time = datetime.now()

        # Broadcast via WebSocket
        if self.websocket_manager:
            try:
                await self.websocket_manager.broadcast(json.dumps(msg))
            except Exception as e:
                print(f"Error broadcasting message: {e}")

        # Also print to console for visibility
        print(f"\n{message}\n")

    def _should_send_message(self, priority: MessagePriority) -> bool:
        """
        Check if message should be sent based on cooldown, verbosity, and CONTEXT

        Args:
            priority: Message priority

        Returns:
            True if message should be sent
        """
        # Always send high priority and urgent
        if priority in [MessagePriority.HIGH, MessagePriority.URGENT]:
            return True

        # Get context-aware cooldown
        context_cooldown = self.context.get_message_cooldown()

        # Check cooldown for lower priority
        if self.last_message_time:
            elapsed = (datetime.now() - self.last_message_time).total_seconds()
            if elapsed < context_cooldown:
                return False
        else:
            # First message always passes
            return True

        # Get context-aware verbosity
        context_verbosity = self.context.get_verbosity_level()

        # Check verbosity level (use context if available)
        current_verbosity = context_verbosity if context_verbosity else self.verbosity_level

        if current_verbosity == "low" and priority == MessagePriority.LOW:
            return False

        return True

    def set_verbosity(self, level: str):
        """
        Set verbosity level

        Args:
            level: low, medium, or high
        """
        if level in ["low", "medium", "high"]:
            self.verbosity_level = level
            print(f"🔊 Verbosity set to: {level}")

    def set_cooldown(self, seconds: int):
        """
        Set minimum seconds between messages

        Args:
            seconds: Cooldown in seconds
        """
        self.message_cooldown = seconds
        print(f"⏱️ Message cooldown set to: {seconds}s")

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """
        Get recent messages

        Args:
            limit: Number of messages to return

        Returns:
            List of recent messages
        """
        return self.message_history[-limit:]

    def notify_user_activity(self):
        """
        Notify that user has been active
        This updates context awareness for better adaptation
        """
        self.context.update_user_activity()

        # User interaction might influence mood
        from personality.mood_system import MoodInfluencer
        self.mood.process_event(MoodInfluencer.USER_INTERACTION)

    def get_context_info(self) -> Dict[str, Any]:
        """
        Get current context information

        Returns:
            Context data from context awareness system
        """
        return self.context.get_statistics()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get communication statistics including context and mood

        Returns:
            Statistics about messages sent, context, and mood
        """
        from collections import Counter

        type_counts = Counter(msg["message_type"] for msg in self.message_history)
        priority_counts = Counter(msg["priority"] for msg in self.message_history)

        # Get context statistics
        context_stats = self.context.get_statistics()

        # Get mood statistics
        mood_stats = self.mood.get_mood_statistics()

        # Get question statistics
        question_stats = self.questions.get_statistics()

        return {
            "total_messages": len(self.message_history),
            "by_type": dict(type_counts),
            "by_priority": dict(priority_counts),
            "verbosity_level": self.verbosity_level,
            "cooldown_seconds": self.message_cooldown,
            "last_message_time": self.last_message_time.isoformat() if self.last_message_time else None,
            "context": context_stats,
            "mood": mood_stats,
            "questions": question_stats  # NEW: Include question info
        }

    def process_mood_event(self, event_type: str, context: Optional[Dict] = None) -> Optional[str]:
        """
        Process an event that might change Darwin's mood

        Args:
            event_type: Type of event (from MoodInfluencer)
            context: Additional context

        Returns:
            New mood state if changed, None otherwise
        """
        new_mood = self.mood.process_event(event_type, context)

        if new_mood:
            # Mood changed! Could announce it
            return new_mood.value

        return None

    def get_mood_info(self) -> Dict[str, Any]:
        """
        Get current mood information

        Returns:
            Current mood state and details
        """
        return {
            'current': self.mood.get_current_mood(),
            'description': self.mood.get_mood_description(),
            'emoji': self.mood.get_mood_emoji(),
            'statistics': self.mood.get_mood_statistics()
        }

    def get_questions_info(self) -> Dict[str, Any]:
        """
        Get question system information

        Returns:
            Question data and statistics
        """
        return {
            'pending': [
                {
                    'id': q.id,
                    'question': q.question,
                    'type': q.type.value,
                    'priority': q.priority.value,
                    'created_at': q.created_at.isoformat(),
                    'expires_at': q.expires_at.isoformat() if q.expires_at else None,
                    'options': [
                        {'value': opt.value, 'label': opt.label, 'description': opt.description}
                        for opt in q.options
                    ] if q.options else None,
                    'allow_multiple': q.allow_multiple,
                    'context': q.context
                }
                for q in self.questions.get_pending_questions()
            ],
            'statistics': self.questions.get_statistics()
        }

    def answer_question(self, question_id: str, answer: Any) -> bool:
        """
        Answer a question

        Args:
            question_id: ID of question to answer
            answer: The answer

        Returns:
            True if answered successfully, False otherwise
        """
        question = self.questions.answer_question(question_id, answer)
        return question is not None

    def dismiss_question(self, question_id: str) -> bool:
        """
        Dismiss a question

        Args:
            question_id: ID of question to dismiss

        Returns:
            True if dismissed successfully, False otherwise
        """
        question = self.questions.dismiss_question(question_id)
        return question is not None
