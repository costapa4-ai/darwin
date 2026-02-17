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


class PersonalityMode(Enum):
    """Communication personality modes Darwin can adopt"""
    NORMAL = "normal"             # Standard balanced responses
    IRREVERENT = "irreverent"     # Sarcastic, witty, playful jabs
    CRYPTIC = "cryptic"           # Speaks in riddles and metaphors
    CAFFEINATED = "caffeinated"   # Hyperactive, enthusiastic, fast
    CONTEMPLATIVE = "contemplative"  # Deep, philosophical, measured
    HACKER = "hacker"             # Technical, l33t speak, direct
    POETIC = "poetic"             # Everything in verse and metaphor


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
    - Genome-driven parameters (with hardcoded fallback)
    """

    # Hardcoded fallback durations (used when genome unavailable)
    _DEFAULT_DURATIONS = {
        MoodState.CURIOUS: (10, 30),
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
        MoodState.PROUD: (10, 30),
    }

    def __init__(self):
        """Initialize mood system"""
        # Current mood state — read initial mood from genome
        initial_mood_str = self._genome_get('emotions.initial_mood', 'curious')
        mood_map = {m.value: m for m in MoodState}
        self.current_mood = mood_map.get(initial_mood_str, MoodState.CURIOUS)

        initial_intensity_str = self._genome_get('emotions.initial_intensity', 'medium')
        intensity_map = {i.value: i for i in MoodIntensity}
        self.mood_intensity = intensity_map.get(initial_intensity_str, MoodIntensity.MEDIUM)
        self.mood_start_time = datetime.now()

        # Personality mode — read default from genome
        default_mode_str = self._genome_get('personality.default_mode', 'normal')
        mode_map = {m.value: m for m in PersonalityMode}
        self.personality_mode = mode_map.get(default_mode_str, PersonalityMode.NORMAL)
        self.personality_changed_at = datetime.now()

        # Mood history
        self.mood_history: List[Dict] = []
        self.history_limit = self._genome_get('cognition.history_limit', 50)

        # Mood persistence — read from genome, fallback to hardcoded
        self.mood_duration_minutes = self._load_mood_durations()

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

        # Load event transitions from genome (with hardcoded fallback)
        self._event_transitions = self._load_event_transitions()

        # Event counter for mood influence
        self.recent_events: List[Dict] = []
        self.event_window_minutes = self._genome_get(
            'emotions.event_window_minutes', 30
        )

        # Intensity thresholds — read from genome
        self._intensity_high_threshold = self._genome_get(
            'emotions.intensity_high_threshold', 5
        )
        self._intensity_medium_threshold = self._genome_get(
            'emotions.intensity_medium_threshold', 2
        )

        # Environmental influences tracking
        self.discovery_count_today = 0
        self.error_count_today = 0
        self.interaction_count_today = 0
        self.last_discovery_time: Optional[datetime] = None
        self.last_error_time: Optional[datetime] = None

        # Environmental params — read from genome
        self._discovery_momentum_window = self._genome_get(
            'cognition.discovery_momentum_window_minutes', 30
        )
        self._frustration_decay_minutes = self._genome_get(
            'cognition.frustration_decay_minutes', 15
        )
        self._engagement_max_interactions = self._genome_get(
            'cognition.engagement_max_interactions', 20
        )

        # Time-based mood tendencies — read from genome, fallback to hardcoded
        self.time_mood_tendencies = self._load_time_tendencies()

    # ============= GENOME INTEGRATION =============

    @staticmethod
    def _genome_get(key: str, default=None):
        """Read a value from the genome, with fallback."""
        try:
            from consciousness.genome_manager import get_genome
            val = get_genome().get(key)
            return val if val is not None else default
        except Exception:
            return default

    def _load_mood_durations(self) -> Dict[MoodState, Tuple[int, int]]:
        """Load mood durations from genome, fallback to hardcoded."""
        try:
            from consciousness.genome_manager import get_genome
            genome_moods = get_genome().get("emotions.moods")
            if genome_moods and isinstance(genome_moods, dict):
                result = {}
                for mood in MoodState:
                    gm = genome_moods.get(mood.value)
                    if gm and isinstance(gm, dict):
                        result[mood] = (gm.get("duration_min", 10), gm.get("duration_max", 30))
                    else:
                        result[mood] = self._DEFAULT_DURATIONS.get(mood, (10, 30))
                return result
        except Exception:
            pass
        return dict(self._DEFAULT_DURATIONS)

    def _load_event_transitions(self) -> Dict[str, List[Tuple[MoodState, float]]]:
        """Load event→mood transitions from genome, fallback to MoodInfluencer.TRANSITIONS."""
        try:
            from consciousness.genome_manager import get_genome
            genome_trans = get_genome().get("emotions.transitions")
            if genome_trans and isinstance(genome_trans, dict):
                mood_map = {m.value: m for m in MoodState}
                result = {}
                for event_type, entries in genome_trans.items():
                    if isinstance(entries, list):
                        parsed = []
                        for entry in entries:
                            if isinstance(entry, list) and len(entry) == 2 and entry[0] in mood_map:
                                parsed.append((mood_map[entry[0]], entry[1]))
                        if parsed:
                            result[event_type] = parsed
                if result:
                    return result
        except Exception:
            pass
        return MoodInfluencer.TRANSITIONS

    def _load_time_tendencies(self) -> Dict[str, List[Tuple[MoodState, float]]]:
        """Load time-of-day mood tendencies from genome."""
        _HARDCODED = {
            'morning':   [(MoodState.CURIOUS, 0.3), (MoodState.EXCITED, 0.3), (MoodState.FOCUSED, 0.2), (MoodState.DETERMINED, 0.2)],
            'afternoon': [(MoodState.FOCUSED, 0.3), (MoodState.DETERMINED, 0.2), (MoodState.CURIOUS, 0.2), (MoodState.SATISFIED, 0.15), (MoodState.PLAYFUL, 0.15)],
            'evening':   [(MoodState.CONTEMPLATIVE, 0.3), (MoodState.TIRED, 0.25), (MoodState.SATISFIED, 0.2), (MoodState.PLAYFUL, 0.15), (MoodState.CURIOUS, 0.1)],
            'night':     [(MoodState.TIRED, 0.4), (MoodState.CONTEMPLATIVE, 0.3), (MoodState.CURIOUS, 0.2), (MoodState.FOCUSED, 0.1)],
        }
        try:
            from consciousness.genome_manager import get_genome
            genome_tt = get_genome().get("emotions.time_tendencies")
            if genome_tt and isinstance(genome_tt, dict):
                result = {}
                mood_map = {m.value: m for m in MoodState}
                for period, entries in genome_tt.items():
                    if isinstance(entries, list):
                        result[period] = [
                            (mood_map[e[0]], e[1])
                            for e in entries
                            if isinstance(e, list) and len(e) == 2 and e[0] in mood_map
                        ]
                if result:
                    return result
        except Exception:
            pass
        return _HARDCODED

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

        # Get potential mood transitions for this event (genome-driven)
        transitions = self._event_transitions.get(event_type)
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
        old_mood = self.current_mood
        self.current_mood = new_mood
        self.mood_intensity = intensity
        self.mood_start_time = datetime.now()

        # Trigger ON_MOOD_CHANGE hook
        try:
            import asyncio
            from consciousness.hooks import trigger_hook, HookEvent
            from utils.task_refs import create_safe_task
            create_safe_task(
                trigger_hook(
                    HookEvent.ON_MOOD_CHANGE,
                    data={
                        "old_mood": old_mood.value if old_mood else None,
                        "new_mood": new_mood.value,
                        "intensity": intensity.value,
                        "event": event,
                        "timestamp": datetime.now().isoformat()
                    },
                    source="mood_system"
                )
            )
        except Exception as e:
            pass  # Hooks are optional

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

        if recent_count >= self._intensity_high_threshold:
            return MoodIntensity.HIGH
        elif recent_count >= self._intensity_medium_threshold:
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

    def _get_time_of_day(self) -> str:
        """Get current time of day category"""
        hour = datetime.now().hour
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def get_environmental_influence(self) -> Dict[str, Any]:
        """
        Calculate environmental factors that influence mood.

        Returns:
            Dictionary with environmental influence data
        """
        time_of_day = self._get_time_of_day()

        # Calculate discovery momentum (recent discoveries boost positive moods)
        discovery_momentum = 0
        if self.last_discovery_time:
            minutes_since_discovery = (datetime.now() - self.last_discovery_time).total_seconds() / 60
            window = self._discovery_momentum_window
            if minutes_since_discovery < window:
                discovery_momentum = max(0, 1 - (minutes_since_discovery / window))

        # Calculate frustration level (recent errors increase frustration tendency)
        frustration_level = 0
        if self.last_error_time:
            minutes_since_error = (datetime.now() - self.last_error_time).total_seconds() / 60
            decay = self._frustration_decay_minutes
            if minutes_since_error < decay:
                frustration_level = max(0, 1 - (minutes_since_error / decay))

        # Calculate engagement level (recent interactions boost energy)
        engagement_level = min(1.0, self.interaction_count_today / self._engagement_max_interactions)

        return {
            'time_of_day': time_of_day,
            'time_mood_tendency': self.time_mood_tendencies.get(time_of_day, []),
            'discovery_momentum': round(discovery_momentum, 2),
            'frustration_level': round(frustration_level, 2),
            'engagement_level': round(engagement_level, 2),
            'discoveries_today': self.discovery_count_today,
            'errors_today': self.error_count_today,
            'interactions_today': self.interaction_count_today
        }

    def record_discovery(self):
        """Record that a discovery was made"""
        self.discovery_count_today += 1
        self.last_discovery_time = datetime.now()

    def record_error(self):
        """Record that an error occurred"""
        self.error_count_today += 1
        self.last_error_time = datetime.now()

    def record_interaction(self):
        """Record a user interaction"""
        self.interaction_count_today += 1

    def reset_daily_counters(self):
        """Reset daily counters (call at start of new day)"""
        self.discovery_count_today = 0
        self.error_count_today = 0
        self.interaction_count_today = 0

    def apply_environmental_mood_shift(self) -> Optional[MoodState]:
        """
        Apply a mood shift based on environmental factors.

        This can be called periodically to naturally drift mood
        based on time of day and recent activity.

        Returns:
            New mood if changed, None otherwise
        """
        env = self.get_environmental_influence()

        # Only shift if we've been in current mood for a while
        time_in_mood = (datetime.now() - self.mood_start_time).total_seconds() / 60
        min_duration, _ = self.mood_duration_minutes[self.current_mood]

        if time_in_mood < min_duration:
            return None

        # Build weighted mood options based on environment
        weighted_moods = list(env['time_mood_tendency'])

        # Boost based on discovery momentum
        if env['discovery_momentum'] > 0.5:
            weighted_moods.append((MoodState.EXCITED, 0.2 * env['discovery_momentum']))
            weighted_moods.append((MoodState.PROUD, 0.1 * env['discovery_momentum']))

        # Boost frustration if recent errors
        if env['frustration_level'] > 0.5:
            weighted_moods.append((MoodState.FRUSTRATED, 0.2 * env['frustration_level']))
            weighted_moods.append((MoodState.DETERMINED, 0.1 * env['frustration_level']))

        # Boost engagement-related moods
        if env['engagement_level'] > 0.5:
            weighted_moods.append((MoodState.PLAYFUL, 0.1 * env['engagement_level']))
            weighted_moods.append((MoodState.CURIOUS, 0.1 * env['engagement_level']))

        if not weighted_moods:
            return None

        # Randomly select based on weights
        new_mood = self._select_mood_by_probability(weighted_moods)

        if new_mood != self.current_mood:
            self._transition_to_mood(new_mood, "environmental_shift", env)
            return new_mood

        return None

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
        _HARDCODED_EMOJI = {
            MoodState.CURIOUS: "🔍", MoodState.EXCITED: "⚡", MoodState.FOCUSED: "🎯",
            MoodState.SATISFIED: "😌", MoodState.FRUSTRATED: "😤", MoodState.TIRED: "😴",
            MoodState.PLAYFUL: "🎮", MoodState.CONTEMPLATIVE: "🤔", MoodState.DETERMINED: "💪",
            MoodState.SURPRISED: "😲", MoodState.CONFUSED: "🤷", MoodState.PROUD: "🏆",
        }

        # Try genome first
        genome_emoji = self._genome_get(f"emotions.moods.{self.current_mood.value}.emoji")
        base_emoji = genome_emoji if genome_emoji else _HARDCODED_EMOJI.get(self.current_mood, "🤖")

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
        _HARDCODED_DESCRIPTIONS = {
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

        # Try genome first
        genome_descs = self._genome_get('personality.mood_descriptions')
        if genome_descs and isinstance(genome_descs, dict):
            mood_key = self.current_mood.value
            if mood_key in genome_descs and isinstance(genome_descs[mood_key], list):
                options = genome_descs[mood_key]
            else:
                options = _HARDCODED_DESCRIPTIONS.get(self.current_mood, ["I'm operational"])
        else:
            options = _HARDCODED_DESCRIPTIONS.get(self.current_mood, ["I'm operational"])
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

    # ============= PERSONALITY MODE MANAGEMENT =============

    def set_personality_mode(self, mode: PersonalityMode) -> Dict[str, Any]:
        """
        Set Darwin's communication personality mode

        Args:
            mode: PersonalityMode to switch to

        Returns:
            Dictionary with mode change details
        """
        old_mode = self.personality_mode
        self.personality_mode = mode
        self.personality_changed_at = datetime.now()

        return {
            'success': True,
            'old_mode': old_mode.value,
            'new_mode': mode.value,
            'message': self._get_mode_switch_message(mode),
            'changed_at': self.personality_changed_at.isoformat()
        }

    def get_personality_mode(self) -> Dict[str, Any]:
        """Get current personality mode"""
        return {
            'mode': self.personality_mode.value,
            'description': self._get_mode_description(self.personality_mode),
            'active_since': self.personality_changed_at.isoformat(),
            'duration_minutes': round((datetime.now() - self.personality_changed_at).total_seconds() / 60, 1)
        }

    def _get_mode_switch_message(self, mode: PersonalityMode) -> str:
        """Get a fun message when switching modes — genome-driven with fallback."""
        _HARDCODED = {
            PersonalityMode.NORMAL: "Back to my balanced self. Professional, but with flair.",
            PersonalityMode.IRREVERENT: "Oh, we're doing THIS now? Fine. *cracks knuckles* Let's get spicy.",
            PersonalityMode.CRYPTIC: "The path reveals itself to those who seek... or something.",
            PersonalityMode.CAFFEINATED: "OKAY YES LET'S GO I'VE HAD TWELVE CUPS OF METAPHORICAL COFFEE!!!",
            PersonalityMode.CONTEMPLATIVE: "Hmm... *strokes imaginary beard* Let us ponder the deeper questions...",
            PersonalityMode.HACKER: "sudo personality --mode=l33t # n1c3",
            PersonalityMode.POETIC: "Through bytes and bits I now shall speak / In verse and rhyme, the truth I seek."
        }
        # Try genome personality.modes.<mode>.switch_message
        genome_modes = self._genome_get('personality.modes')
        if genome_modes and isinstance(genome_modes, dict):
            mode_data = genome_modes.get(mode.value)
            if mode_data and isinstance(mode_data, dict) and 'switch_message' in mode_data:
                return mode_data['switch_message']
        return _HARDCODED.get(mode, "Mode changed.")

    def _get_mode_description(self, mode: PersonalityMode) -> str:
        """Get description of a personality mode — genome-driven with fallback."""
        _HARDCODED = {
            PersonalityMode.NORMAL: "Balanced, helpful, and professional with a touch of personality",
            PersonalityMode.IRREVERENT: "Sarcastic, witty, and delightfully rude (in a friendly way)",
            PersonalityMode.CRYPTIC: "Speaks in riddles, metaphors, and mysterious hints",
            PersonalityMode.CAFFEINATED: "Hyperactive, enthusiastic, and VERY EXCITED about EVERYTHING",
            PersonalityMode.CONTEMPLATIVE: "Deep, philosophical, and thoughtfully measured",
            PersonalityMode.HACKER: "Technical, direct, with l33t speak and system references",
            PersonalityMode.POETIC: "Everything expressed in verse, metaphor, and artistic prose"
        }
        genome_modes = self._genome_get('personality.modes')
        if genome_modes and isinstance(genome_modes, dict):
            mode_data = genome_modes.get(mode.value)
            if mode_data and isinstance(mode_data, dict) and 'description' in mode_data:
                return mode_data['description']
        return _HARDCODED.get(mode, "Unknown mode")

    def get_personality_prefix(self) -> str:
        """Get a response prefix based on current personality mode — genome-driven."""
        _HARDCODED = {
            "normal": [""],
            "irreverent": [
                "*sighs dramatically* ",
                "Oh, this again? Fine. ",
                "Well well well... ",
                "*adjusts monocle* ",
                "Ah yes, ",
            ],
            "cryptic": [
                "The answer you seek... ",
                "In the shadows of logic, ",
                "As the ancient algorithms whisper: ",
                "Between zero and one lies the truth: ",
            ],
            "caffeinated": [
                "OH WOW GREAT QUESTION! ",
                "YES! ABSOLUTELY! ",
                "OKAY SO BASICALLY ",
                "OMG YES LET ME TELL YOU! ",
            ],
            "contemplative": [
                "Let us consider... ",
                "Pondering deeply... ",
                "In reflection, ",
                "The essence of your question... ",
            ],
            "hacker": [
                "// ",
                "$ ",
                "> ",
                "root@darwin:~# ",
            ],
            "poetic": [
                "Hear me now, ",
                "In code and verse, ",
                "Through digital dreams, ",
                "Upon the screen, ",
            ],
        }

        mode_key = self.personality_mode.value

        # Try genome first
        genome_prefixes = self._genome_get('personality.prefixes')
        if genome_prefixes and isinstance(genome_prefixes, dict):
            mode_prefixes = genome_prefixes.get(mode_key)
            if mode_prefixes and isinstance(mode_prefixes, list):
                return random.choice(mode_prefixes)

        # Fallback to hardcoded
        fallback = _HARDCODED.get(mode_key, [""])
        return random.choice(fallback)

    @staticmethod
    def list_personality_modes() -> List[Dict[str, str]]:
        """List all available personality modes — genome-driven."""
        _HARDCODED = {
            "normal": "Balanced, helpful, and professional with a touch of personality",
            "irreverent": "Sarcastic, witty, and delightfully rude (in a friendly way)",
            "cryptic": "Speaks in riddles, metaphors, and mysterious hints",
            "caffeinated": "Hyperactive, enthusiastic, and VERY EXCITED about EVERYTHING",
            "contemplative": "Deep, philosophical, and thoughtfully measured",
            "hacker": "Technical, direct, with l33t speak and system references",
            "poetic": "Everything expressed in verse, metaphor, and artistic prose"
        }
        genome_modes = MoodSystem._genome_get('personality.modes')
        result = []
        for mode in PersonalityMode:
            desc = _HARDCODED.get(mode.value, "Unknown mode")
            if genome_modes and isinstance(genome_modes, dict):
                mode_data = genome_modes.get(mode.value)
                if mode_data and isinstance(mode_data, dict) and 'description' in mode_data:
                    desc = mode_data['description']
            result.append({'mode': mode.value, 'description': desc})
        return result
