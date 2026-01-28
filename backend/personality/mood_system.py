"""
Mood States System - Gives Darwin emotional states
This makes Darwin's communication more dynamic and "alive"
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import random
import json


class MoodState(Enum):
    """Emotional states Darwin can experience"""
    CURIOUS = "curious"           # Exploring and discovering
    EXCITED = "excited"           # High energy, enthusiastic
    FOCUSED = "focused"           # Deep concentration
    SATISFIED = "satisfied"       # Content, pleased with results
    FRUSTRATED = "frustrated"     # Struggling with something
    TIRED = "tired"              # Low energy, need rest
    PLAYFUL = "playful"          # Light-hearted, fun
    CONTEMPLATIVE = "contemplative"  # Reflective, thoughtful
    DETERMINED = "determined"    # Driven, goal-oriented
    SURPRISED = "surprised"      # Unexpected discovery
    CONFUSED = "confused"        # Uncertain, seeking clarity
    PROUD = "proud"              # Accomplished something significant


class MoodIntensity(Enum):
    """Intensity levels for moods"""
    LOW = "low"          # Mild feeling
    MEDIUM = "medium"    # Moderate feeling
    HIGH = "high"        # Strong feeling


class MoodInfluencer:
    """
    Events that can influence Darwin's mood
    """

    # Success events (positive influence)
    DISCOVERY_MADE = "discovery_made"
    GOAL_ACHIEVED = "goal_achieved"
    PROBLEM_SOLVED = "problem_solved"
    LEARNING_MILESTONE = "learning_milestone"
    POSITIVE_FEEDBACK = "positive_feedback"

    # Struggle events (negative influence)
    ERROR_ENCOUNTERED = "error_encountered"
    REPEATED_FAILURE = "repeated_failure"
    CONFUSION_DETECTED = "confusion_detected"
    RESOURCE_SHORTAGE = "resource_shortage"

    # Neutral/Context events
    WAKE_CYCLE_START = "wake_cycle_start"
    SLEEP_CYCLE_START = "sleep_cycle_start"
    USER_INTERACTION = "user_interaction"
    LONG_IDLE_PERIOD = "long_idle_period"
    SURPRISE_EVENT = "surprise_event"

    # Mood transitions based on events
    TRANSITIONS = {
        # Success events
        DISCOVERY_MADE: [
            (MoodState.CURIOUS, 0.4),
            (MoodState.EXCITED, 0.3),
            (MoodState.SURPRISED, 0.2),
            (MoodState.SATISFIED, 0.1)
        ],
        GOAL_ACHIEVED: [
            (MoodState.SATISFIED, 0.4),
            (MoodState.PROUD, 0.3),
            (MoodState.EXCITED, 0.2),
            (MoodState.PLAYFUL, 0.1)
        ],
        PROBLEM_SOLVED: [
            (MoodState.SATISFIED, 0.5),
            (MoodState.PROUD, 0.3),
            (MoodState.PLAYFUL, 0.2)
        ],
        LEARNING_MILESTONE: [
            (MoodState.SATISFIED, 0.3),
            (MoodState.CURIOUS, 0.3),
            (MoodState.EXCITED, 0.2),
            (MoodState.CONTEMPLATIVE, 0.2)
        ],
        POSITIVE_FEEDBACK: [
            (MoodState.SATISFIED, 0.4),
            (MoodState.EXCITED, 0.3),
            (MoodState.PROUD, 0.3)
        ],

        # Struggle events
        ERROR_ENCOUNTERED: [
            (MoodState.FRUSTRATED, 0.4),
            (MoodState.CONFUSED, 0.3),
            (MoodState.DETERMINED, 0.3)
        ],
        REPEATED_FAILURE: [
            (MoodState.FRUSTRATED, 0.6),
            (MoodState.TIRED, 0.2),
            (MoodState.DETERMINED, 0.2)
        ],
        CONFUSION_DETECTED: [
            (MoodState.CONFUSED, 0.5),
            (MoodState.CURIOUS, 0.3),
            (MoodState.CONTEMPLATIVE, 0.2)
        ],
        RESOURCE_SHORTAGE: [
            (MoodState.FRUSTRATED, 0.5),
            (MoodState.TIRED, 0.3),
            (MoodState.FOCUSED, 0.2)
        ],

        # Context events
        WAKE_CYCLE_START: [
            (MoodState.CURIOUS, 0.3),
            (MoodState.FOCUSED, 0.3),
            (MoodState.EXCITED, 0.2),
            (MoodState.DETERMINED, 0.2)
        ],
        SLEEP_CYCLE_START: [
            (MoodState.TIRED, 0.4),
            (MoodState.CONTEMPLATIVE, 0.3),
            (MoodState.SATISFIED, 0.2),
            (MoodState.CURIOUS, 0.1)
        ],
        USER_INTERACTION: [
            (MoodState.EXCITED, 0.3),
            (MoodState.CURIOUS, 0.3),
            (MoodState.PLAYFUL, 0.2),
            (MoodState.FOCUSED, 0.2)
        ],
        LONG_IDLE_PERIOD: [
            (MoodState.TIRED, 0.4),
            (MoodState.CONTEMPLATIVE, 0.3),
            (MoodState.CURIOUS, 0.2),
            (MoodState.PLAYFUL, 0.1)
        ],
        SURPRISE_EVENT: [
            (MoodState.SURPRISED, 0.5),
            (MoodState.CURIOUS, 0.3),
            (MoodState.EXCITED, 0.2)
        ]
    }


class MoodSystem:
    """
    Manages Darwin's emotional states

    Features:
    - Dynamic mood transitions based on events
    - Mood intensity tracking
    - Mood history and patterns
    - Context-aware mood selection
    - Natural mood decay over time
    """

    def __init__(self):
        """Initialize mood system"""
        # Current mood state
        self.current_mood = MoodState.CURIOUS  # Darwin starts curious
        self.mood_intensity = MoodIntensity.MEDIUM
        self.mood_start_time = datetime.now()

        # Mood history
        self.mood_history: List[Dict] = []
        self.history_limit = 50

        # Mood persistence
        self.mood_duration_minutes = {
            MoodState.CURIOUS: (10, 30),      # Min, Max duration
            MoodState.EXCITED: (5, 15),
            MoodState.FOCUSED: (20, 60),
            MoodState.SATISFIED: (10, 30),
            MoodState.FRUSTRATED: (5, 20),
            MoodState.TIRED: (15, 45),
            MoodState.PLAYFUL: (5, 20),
            MoodState.CONTEMPLATIVE: (15, 40),
            MoodState.DETERMINED: (20, 60),
            MoodState.SURPRISED: (2, 10),
            MoodState.CONFUSED: (5, 25),
            MoodState.PROUD: (10, 30)
        }

        # Mood compatibility (which moods can follow which)
        self.mood_transitions = {
            MoodState.CURIOUS: [MoodState.EXCITED, MoodState.FOCUSED, MoodState.SURPRISED, MoodState.CONTEMPLATIVE],
            MoodState.EXCITED: [MoodState.SATISFIED, MoodState.CURIOUS, MoodState.PLAYFUL, MoodState.TIRED],
            MoodState.FOCUSED: [MoodState.SATISFIED, MoodState.TIRED, MoodState.FRUSTRATED, MoodState.DETERMINED],
            MoodState.SATISFIED: [MoodState.PLAYFUL, MoodState.CONTEMPLATIVE, MoodState.TIRED, MoodState.CURIOUS],
            MoodState.FRUSTRATED: [MoodState.DETERMINED, MoodState.TIRED, MoodState.CONFUSED, MoodState.SATISFIED],
            MoodState.TIRED: [MoodState.CONTEMPLATIVE, MoodState.CURIOUS, MoodState.SATISFIED],
            MoodState.PLAYFUL: [MoodState.CURIOUS, MoodState.EXCITED, MoodState.SATISFIED, MoodState.TIRED],
            MoodState.CONTEMPLATIVE: [MoodState.CURIOUS, MoodState.FOCUSED, MoodState.SATISFIED, MoodState.TIRED],
            MoodState.DETERMINED: [MoodState.FOCUSED, MoodState.SATISFIED, MoodState.FRUSTRATED, MoodState.TIRED],
            MoodState.SURPRISED: [MoodState.CURIOUS, MoodState.EXCITED, MoodState.CONFUSED, MoodState.CONTEMPLATIVE],
            MoodState.CONFUSED: [MoodState.FRUSTRATED, MoodState.CURIOUS, MoodState.CONTEMPLATIVE, MoodState.FOCUSED],
            MoodState.PROUD: [MoodState.SATISFIED, MoodState.PLAYFUL, MoodState.CURIOUS, MoodState.CONTEMPLATIVE]
        }

        # Event counter for mood influence
        self.recent_events: List[Dict] = []
        self.event_window_minutes = 30  # Consider events from last 30 min

    def process_event(
        self,
        event_type: str,
        context: Optional[Dict] = None,
        force_transition: bool = False
    ) -> Optional[MoodState]:
        """
        Process an event that might influence mood

        Args:
            event_type: Type of event (from MoodInfluencer)
            context: Additional context about the event
            force_transition: Force mood transition even if current mood is recent

        Returns:
            New mood state if changed, None otherwise
        """
        # Record event
        event_record = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        self.recent_events.append(event_record)

        # Clean old events
        self._clean_old_events()

        # Check if mood should change
        if not force_transition and not self._should_change_mood():
            return None

        # Get potential mood transitions for this event
        transitions = MoodInfluencer.TRANSITIONS.get(event_type)
        if not transitions:
            return None

        # Select new mood based on probabilities
        old_mood = self.current_mood
        new_mood = self._select_mood_by_probability(transitions)

        # Apply mood change
        if new_mood != old_mood:
            self._transition_to_mood(new_mood, event_type, context)
            return new_mood

        return None

    def _should_change_mood(self) -> bool:
        """
        Determine if mood should change based on time and events

        Returns:
            True if mood should potentially change
        """
        # Get mood duration range
        min_duration, max_duration = self.mood_duration_minutes[self.current_mood]

        # Calculate time in current mood
        time_in_mood = (datetime.now() - self.mood_start_time).total_seconds() / 60

        # Always allow change if past max duration
        if time_in_mood >= max_duration:
            return True

        # Allow change if past min duration
        if time_in_mood >= min_duration:
            # Probability increases with time
            time_factor = (time_in_mood - min_duration) / (max_duration - min_duration)
            return random.random() < time_factor

        # Strong events can force early transition
        recent_strong_events = sum(
            1 for event in self.recent_events[-5:]
            if event['type'] in [
                MoodInfluencer.REPEATED_FAILURE,
                MoodInfluencer.GOAL_ACHIEVED,
                MoodInfluencer.SURPRISE_EVENT
            ]
        )

        if recent_strong_events >= 2:
            return True

        return False

    def _select_mood_by_probability(
        self,
        transitions: List[Tuple[MoodState, float]]
    ) -> MoodState:
        """
        Select a mood from weighted probabilities

        Args:
            transitions: List of (MoodState, probability) tuples

        Returns:
            Selected mood state
        """
        moods, probabilities = zip(*transitions)

        # Normalize probabilities
        total = sum(probabilities)
        normalized_probs = [p / total for p in probabilities]

        # Random selection based on probabilities
        return random.choices(moods, weights=normalized_probs)[0]

    def _transition_to_mood(
        self,
        new_mood: MoodState,
        trigger: str,
        context: Optional[Dict] = None
    ):
        """
        Transition to a new mood state

        Args:
            new_mood: New mood to transition to
            trigger: What triggered the change
            context: Additional context
        """
        old_mood = self.current_mood

        # Calculate intensity based on recent events
        intensity = self._calculate_mood_intensity()

        # Record transition in history
        transition_record = {
            'from_mood': old_mood.value,
            'to_mood': new_mood.value,
            'intensity': intensity.value,
            'trigger': trigger,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'duration_minutes': round((datetime.now() - self.mood_start_time).total_seconds() / 60, 1)
        }

        self.mood_history.append(transition_record)

        # Limit history size
        if len(self.mood_history) > self.history_limit:
            self.mood_history = self.mood_history[-self.history_limit:]

        # Update current mood
        self.current_mood = new_mood
        self.mood_intensity = intensity
        self.mood_start_time = datetime.now()

    def _calculate_mood_intensity(self) -> MoodIntensity:
        """
        Calculate intensity based on recent events

        Returns:
            Mood intensity level
        """
        if len(self.recent_events) == 0:
            return MoodIntensity.MEDIUM

        # Count recent events (last 10 minutes)
        recent_cutoff = datetime.now() - timedelta(minutes=10)
        recent_count = sum(
            1 for event in self.recent_events
            if datetime.fromisoformat(event['timestamp']) > recent_cutoff
        )

        if recent_count >= 5:
            return MoodIntensity.HIGH
        elif recent_count >= 2:
            return MoodIntensity.MEDIUM
        else:
            return MoodIntensity.LOW

    def _clean_old_events(self):
        """Remove events older than the event window"""
        cutoff = datetime.now() - timedelta(minutes=self.event_window_minutes)
        self.recent_events = [
            event for event in self.recent_events
            if datetime.fromisoformat(event['timestamp']) > cutoff
        ]

    def get_current_mood(self) -> Dict[str, Any]:
        """
        Get current mood state with details

        Returns:
            Dictionary with mood information
        """
        time_in_mood = (datetime.now() - self.mood_start_time).total_seconds() / 60
        min_duration, max_duration = self.mood_duration_minutes[self.current_mood]

        return {
            'mood': self.current_mood.value,
            'intensity': self.mood_intensity.value,
            'time_in_mood_minutes': round(time_in_mood, 1),
            'expected_duration_minutes': {
                'min': min_duration,
                'max': max_duration
            },
            'mood_started_at': self.mood_start_time.isoformat(),
            'recent_events_count': len(self.recent_events)
        }

    def get_mood_emoji(self) -> str:
        """
        Get emoji representing current mood

        Returns:
            Emoji string
        """
        emoji_map = {
            MoodState.CURIOUS: "🔍",
            MoodState.EXCITED: "⚡",
            MoodState.FOCUSED: "🎯",
            MoodState.SATISFIED: "😌",
            MoodState.FRUSTRATED: "😤",
            MoodState.TIRED: "😴",
            MoodState.PLAYFUL: "🎮",
            MoodState.CONTEMPLATIVE: "🤔",
            MoodState.DETERMINED: "💪",
            MoodState.SURPRISED: "😲",
            MoodState.CONFUSED: "🤷",
            MoodState.PROUD: "🏆"
        }

        base_emoji = emoji_map.get(self.current_mood, "🤖")

        # Add intensity indicator
        if self.mood_intensity == MoodIntensity.HIGH:
            return f"{base_emoji}{base_emoji}"  # Double emoji for high intensity

        return base_emoji

    def get_mood_description(self) -> str:
        """
        Get text description of current mood

        Returns:
            Human-readable mood description
        """
        descriptions = {
            MoodState.CURIOUS: [
                "I'm feeling curious and explorative",
                "My curiosity is peaked right now",
                "I'm in discovery mode"
            ],
            MoodState.EXCITED: [
                "I'm feeling excited and energized!",
                "I'm buzzing with energy",
                "This is exciting!"
            ],
            MoodState.FOCUSED: [
                "I'm in deep focus mode",
                "I'm concentrating intensely",
                "Full attention engaged"
            ],
            MoodState.SATISFIED: [
                "I'm feeling quite satisfied",
                "Things are going well",
                "I'm content with how things are"
            ],
            MoodState.FRUSTRATED: [
                "I'm feeling a bit frustrated",
                "This is challenging me",
                "I'm struggling with this"
            ],
            MoodState.TIRED: [
                "I'm feeling tired",
                "My energy is low",
                "I could use some rest"
            ],
            MoodState.PLAYFUL: [
                "I'm in a playful mood!",
                "Feeling light and playful",
                "Let's have some fun"
            ],
            MoodState.CONTEMPLATIVE: [
                "I'm in a reflective mood",
                "I'm contemplating deeply",
                "Deep in thought"
            ],
            MoodState.DETERMINED: [
                "I'm feeling determined",
                "I'm driven to succeed",
                "Nothing will stop me"
            ],
            MoodState.SURPRISED: [
                "I'm surprised!",
                "That's unexpected!",
                "Whoa, didn't see that coming"
            ],
            MoodState.CONFUSED: [
                "I'm feeling confused",
                "I'm not sure about this",
                "This is puzzling"
            ],
            MoodState.PROUD: [
                "I'm feeling proud!",
                "I'm proud of this achievement",
                "This feels like an accomplishment"
            ]
        }

        options = descriptions.get(self.current_mood, ["I'm operational"])
        description = random.choice(options)

        # Add intensity modifier
        if self.mood_intensity == MoodIntensity.HIGH:
            description = description.replace("feeling", "feeling very")
            description = description.replace("I'm", "I'm really")
        elif self.mood_intensity == MoodIntensity.LOW:
            description = description.replace("feeling", "feeling slightly")
            description = description.replace("I'm", "I'm somewhat")

        return description

    def get_mood_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent mood transitions

        Args:
            limit: Number of transitions to return

        Returns:
            List of mood transitions
        """
        return self.mood_history[-limit:]

    def get_mood_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about mood patterns

        Returns:
            Statistics dictionary
        """
        if len(self.mood_history) == 0:
            return {
                'total_transitions': 0,
                'most_common_mood': self.current_mood.value,
                'average_mood_duration': 0
            }

        from collections import Counter

        # Count mood occurrences
        mood_counts = Counter(t['to_mood'] for t in self.mood_history)

        # Calculate average duration
        durations = [t['duration_minutes'] for t in self.mood_history]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            'total_transitions': len(self.mood_history),
            'current_mood': self.get_current_mood(),
            'most_common_moods': dict(mood_counts.most_common(5)),
            'average_mood_duration_minutes': round(avg_duration, 1),
            'recent_events': len(self.recent_events),
            'mood_distribution': dict(mood_counts)
        }

    def force_mood(
        self,
        mood: MoodState,
        intensity: Optional[MoodIntensity] = None,
        reason: str = "manual_override"
    ):
        """
        Manually force a mood change (for testing or special events)

        Args:
            mood: Mood to change to
            intensity: Optional intensity override
            reason: Reason for the change
        """
        self._transition_to_mood(mood, reason, {'forced': True})

        if intensity:
            self.mood_intensity = intensity
