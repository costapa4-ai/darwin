"""
Interaction Memory System - Allows Darwin to remember user preferences and patterns
This makes Darwin learn from interactions and personalize behavior
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import json


@dataclass
class Interaction:
    """A single interaction with the user"""
    timestamp: datetime
    type: str  # message, question, feedback, etc.
    content: Any
    user_response: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Preference:
    """A learned user preference"""
    category: str
    preference: str
    confidence: float  # 0-1
    learned_from: List[str]  # Interaction IDs
    first_observed: datetime
    last_observed: datetime
    observation_count: int = 1


class InteractionMemory:
    """
    Manages Darwin's memory of user interactions and preferences

    Features:
    - Remembers user preferences
    - Learns communication patterns
    - Tracks feedback patterns
    - Identifies user habits
    - Personalizes behavior
    """

    def __init__(self):
        """Initialize interaction memory"""
        self.interactions: List[Interaction] = []
        self.preferences: Dict[str, Preference] = {}  # key: category_preference

        # Limits
        self.max_interactions = 1000
        self.preference_confidence_threshold = 0.7

        # Pattern tracking
        self.feedback_patterns: Dict[str, List[str]] = defaultdict(list)
        self.communication_patterns: Dict[str, int] = Counter()
        self.temporal_patterns: Dict[int, List[str]] = defaultdict(list)  # hour -> activities

    def record_interaction(
        self,
        type: str,
        content: Any,
        user_response: Optional[Any] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Record a new interaction

        Args:
            type: Type of interaction
            content: Content of interaction
            user_response: User's response (if any)
            metadata: Additional metadata

        Returns:
            Interaction ID (timestamp as string)
        """
        interaction = Interaction(
            timestamp=datetime.now(),
            type=type,
            content=content,
            user_response=user_response,
            metadata=metadata or {}
        )

        self.interactions.append(interaction)

        # Limit size
        if len(self.interactions) > self.max_interactions:
            self.interactions = self.interactions[-self.max_interactions:]

        # Update patterns
        self._update_patterns(interaction)

        # Try to learn preferences
        self._learn_from_interaction(interaction)

        return interaction.timestamp.isoformat()

    def _update_patterns(self, interaction: Interaction):
        """Update pattern tracking based on interaction"""
        # Communication pattern
        self.communication_patterns[interaction.type] += 1

        # Temporal pattern (what time of day user interacts)
        hour = interaction.timestamp.hour
        self.temporal_patterns[hour].append(interaction.type)

        # Feedback pattern
        if interaction.type == "feedback" and interaction.user_response:
            feedback = interaction.user_response
            self.feedback_patterns[interaction.metadata.get('subject', 'general')].append(feedback)

    def _learn_from_interaction(self, interaction: Interaction):
        """Learn preferences from interaction"""
        # Learn from question answers
        if interaction.type == "question_answer":
            question_type = interaction.metadata.get('question_type')
            answer = interaction.user_response

            if question_type == "preference":
                # Direct preference learning
                category = interaction.metadata.get('category', 'general')
                self._record_preference(
                    category=category,
                    preference=str(answer),
                    interaction_id=interaction.timestamp.isoformat()
                )

        # Learn from feedback
        elif interaction.type == "feedback":
            subject = interaction.metadata.get('subject')
            rating = interaction.user_response

            if subject and rating in ['great', 'good']:
                # Positive feedback = learn the approach
                approach = interaction.metadata.get('approach')
                if approach:
                    self._record_preference(
                        category=f"approach_{subject}",
                        preference=approach,
                        interaction_id=interaction.timestamp.isoformat()
                    )

        # Learn from dismissals (what user doesn't like)
        elif interaction.type == "question_dismissed":
            question_type = interaction.metadata.get('question_type')
            if question_type:
                self._record_preference(
                    category="avoid_questions",
                    preference=question_type,
                    interaction_id=interaction.timestamp.isoformat(),
                    negative=True
                )

    def _record_preference(
        self,
        category: str,
        preference: str,
        interaction_id: str,
        negative: bool = False
    ):
        """Record or update a preference"""
        key = f"{category}:{preference}"

        if key in self.preferences:
            # Update existing preference
            pref = self.preferences[key]
            pref.observation_count += 1
            pref.last_observed = datetime.now()
            pref.learned_from.append(interaction_id)

            # Increase confidence with more observations
            pref.confidence = min(0.99, pref.confidence + 0.1)

            if negative:
                # Negative observation decreases confidence
                pref.confidence = max(0.1, pref.confidence - 0.2)
        else:
            # New preference
            self.preferences[key] = Preference(
                category=category,
                preference=preference,
                confidence=0.5 if not negative else 0.3,
                learned_from=[interaction_id],
                first_observed=datetime.now(),
                last_observed=datetime.now()
            )

    def get_preference(
        self,
        category: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get user's preference for a category

        Args:
            category: Preference category
            default: Default if no preference found

        Returns:
            Preferred option or default
        """
        # Find all preferences for this category
        category_prefs = [
            (pref.preference, pref.confidence)
            for key, pref in self.preferences.items()
            if pref.category == category and pref.confidence >= self.preference_confidence_threshold
        ]

        if not category_prefs:
            return default

        # Return highest confidence preference
        category_prefs.sort(key=lambda x: x[1], reverse=True)
        return category_prefs[0][0]

    def get_all_preferences(
        self,
        min_confidence: float = 0.7
    ) -> Dict[str, List[Dict]]:
        """
        Get all learned preferences

        Args:
            min_confidence: Minimum confidence threshold

        Returns:
            Preferences grouped by category
        """
        result = defaultdict(list)

        for key, pref in self.preferences.items():
            if pref.confidence >= min_confidence:
                result[pref.category].append({
                    'preference': pref.preference,
                    'confidence': round(pref.confidence, 2),
                    'observations': pref.observation_count,
                    'first_seen': pref.first_observed.isoformat(),
                    'last_seen': pref.last_observed.isoformat()
                })

        # Sort by confidence
        for category in result:
            result[category].sort(key=lambda x: x['confidence'], reverse=True)

        return dict(result)

    def get_communication_insights(self) -> Dict[str, Any]:
        """
        Get insights about communication patterns

        Returns:
            Communication pattern insights
        """
        total_interactions = sum(self.communication_patterns.values())

        # Most common interaction type
        most_common = self.communication_patterns.most_common(1)
        most_common_type = most_common[0][0] if most_common else None

        # Active hours
        active_hours = sorted(
            self.temporal_patterns.keys(),
            key=lambda h: len(self.temporal_patterns[h]),
            reverse=True
        )[:3]

        # Feedback analysis
        positive_feedback = sum(
            1 for responses in self.feedback_patterns.values()
            for r in responses if r in ['great', 'good']
        )
        total_feedback = sum(len(responses) for responses in self.feedback_patterns.values())

        satisfaction_rate = (
            positive_feedback / total_feedback * 100
            if total_feedback > 0 else 0
        )

        return {
            'total_interactions': total_interactions,
            'most_common_type': most_common_type,
            'interaction_distribution': dict(self.communication_patterns),
            'active_hours': active_hours,
            'satisfaction_rate': round(satisfaction_rate, 1),
            'total_feedback': total_feedback,
            'positive_feedback': positive_feedback
        }

    def get_recent_interactions(
        self,
        limit: int = 20,
        type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get recent interactions

        Args:
            limit: Number to return
            type: Filter by type

        Returns:
            Recent interactions
        """
        interactions = self.interactions

        if type:
            interactions = [i for i in interactions if i.type == type]

        interactions = interactions[-limit:]

        return [
            {
                'timestamp': i.timestamp.isoformat(),
                'type': i.type,
                'content': i.content,
                'user_response': i.user_response,
                'metadata': i.metadata
            }
            for i in interactions
        ]

    def should_ask_question(self, question_type: str) -> bool:
        """
        Check if should ask a certain type of question based on history

        Args:
            question_type: Type of question

        Returns:
            True if should ask, False if user tends to dismiss these
        """
        # Check if user tends to dismiss this type
        avoid_key = f"avoid_questions:{question_type}"

        if avoid_key in self.preferences:
            pref = self.preferences[avoid_key]
            if pref.confidence > 0.6:
                return False

        return True

    def get_preferred_approach(self, task: str) -> Optional[str]:
        """
        Get preferred approach for a task based on past feedback

        Args:
            task: Task name

        Returns:
            Preferred approach if learned
        """
        return self.get_preference(f"approach_{task}")

    def get_interaction_frequency(self, days: int = 7) -> Dict[str, Any]:
        """
        Get interaction frequency statistics

        Args:
            days: Number of days to analyze

        Returns:
            Frequency statistics
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent = [i for i in self.interactions if i.timestamp > cutoff]

        if not recent:
            return {
                'period_days': days,
                'total_interactions': 0,
                'daily_average': 0,
                'most_active_day': None
            }

        # Group by day
        by_day = defaultdict(int)
        for interaction in recent:
            day = interaction.timestamp.date()
            by_day[day] += 1

        daily_avg = len(recent) / days
        most_active_day = max(by_day.items(), key=lambda x: x[1]) if by_day else None

        return {
            'period_days': days,
            'total_interactions': len(recent),
            'daily_average': round(daily_avg, 1),
            'most_active_day': most_active_day[0].isoformat() if most_active_day else None,
            'most_active_day_count': most_active_day[1] if most_active_day else 0,
            'by_day': {day.isoformat(): count for day, count in by_day.items()}
        }

    def forget_old_interactions(self, days: int = 30):
        """
        Remove interactions older than specified days

        Args:
            days: Keep interactions from last N days
        """
        cutoff = datetime.now() - timedelta(days=days)
        self.interactions = [
            i for i in self.interactions
            if i.timestamp > cutoff
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics

        Returns:
            Statistics dictionary
        """
        return {
            'total_interactions': len(self.interactions),
            'total_preferences': len(self.preferences),
            'high_confidence_preferences': len([
                p for p in self.preferences.values()
                if p.confidence >= self.preference_confidence_threshold
            ]),
            'communication_insights': self.get_communication_insights(),
            'interaction_frequency': self.get_interaction_frequency(7),
            'oldest_interaction': (
                self.interactions[0].timestamp.isoformat()
                if self.interactions else None
            ),
            'newest_interaction': (
                self.interactions[-1].timestamp.isoformat()
                if self.interactions else None
            )
        }

    def export_preferences(self) -> str:
        """
        Export preferences as JSON

        Returns:
            JSON string of all preferences
        """
        export_data = {
            'preferences': {
                key: {
                    'category': pref.category,
                    'preference': pref.preference,
                    'confidence': pref.confidence,
                    'observation_count': pref.observation_count,
                    'first_observed': pref.first_observed.isoformat(),
                    'last_observed': pref.last_observed.isoformat()
                }
                for key, pref in self.preferences.items()
            },
            'exported_at': datetime.now().isoformat()
        }

        return json.dumps(export_data, indent=2)
