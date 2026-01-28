"""
Context Awareness System - Makes Darwin aware of its environment
Adapts behavior based on user presence, time of day, system load, etc.
"""
from typing import Dict, Optional, Any
from datetime import datetime, time
from enum import Enum
import asyncio
import psutil


class TimeOfDay(Enum):
    """Time of day categories"""
    NIGHT = "night"          # 00:00 - 06:00
    MORNING = "morning"      # 06:00 - 12:00
    AFTERNOON = "afternoon"  # 12:00 - 18:00
    EVENING = "evening"      # 18:00 - 24:00


class UserPresence(Enum):
    """User presence states"""
    ACTIVE = "active"        # User actively interacting
    IDLE = "idle"            # User present but idle
    AWAY = "away"            # User not present


class SystemLoad(Enum):
    """System load levels"""
    LOW = "low"              # < 30% CPU/Memory
    MEDIUM = "medium"        # 30-70% CPU/Memory
    HIGH = "high"            # > 70% CPU/Memory


class ContextAwareness:
    """
    Monitors and provides context about the environment

    Features:
    - User presence detection
    - Time of day awareness
    - System load monitoring
    - Recent activity tracking
    """

    def __init__(self):
        """Initialize context awareness system"""
        self.last_user_activity = datetime.now()
        self.idle_threshold_minutes = 15  # User is idle after 15 min
        self.away_threshold_minutes = 60  # User is away after 60 min

        # Activity tracking
        self.recent_interactions = []  # Last 10 interactions
        self.interaction_history_limit = 10

        # System metrics
        self.last_load_check = None
        self.cached_load = None
        self.load_cache_seconds = 30  # Cache for 30 seconds

    def update_user_activity(self):
        """
        Update last user activity timestamp
        Call this when user interacts (message, click, etc.)
        """
        self.last_user_activity = datetime.now()

        # Track interaction
        self.recent_interactions.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'user_activity'
        })

        # Keep only recent interactions
        if len(self.recent_interactions) > self.interaction_history_limit:
            self.recent_interactions = self.recent_interactions[-self.interaction_history_limit:]

    def get_user_presence(self) -> UserPresence:
        """
        Determine current user presence state

        Returns:
            UserPresence: Current presence state
        """
        minutes_since_activity = (datetime.now() - self.last_user_activity).total_seconds() / 60

        if minutes_since_activity < self.idle_threshold_minutes:
            return UserPresence.ACTIVE
        elif minutes_since_activity < self.away_threshold_minutes:
            return UserPresence.IDLE
        else:
            return UserPresence.AWAY

    def get_time_of_day(self) -> TimeOfDay:
        """
        Get current time of day category

        Returns:
            TimeOfDay: Current time category
        """
        current_hour = datetime.now().hour

        if 0 <= current_hour < 6:
            return TimeOfDay.NIGHT
        elif 6 <= current_hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= current_hour < 18:
            return TimeOfDay.AFTERNOON
        else:
            return TimeOfDay.EVENING

    def get_system_load(self) -> SystemLoad:
        """
        Get current system load level
        Uses cached value if recent check exists

        Returns:
            SystemLoad: Current load level
        """
        # Check cache
        if self.last_load_check:
            elapsed = (datetime.now() - self.last_load_check).total_seconds()
            if elapsed < self.load_cache_seconds and self.cached_load:
                return self.cached_load

        # Get fresh metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent

            # Average of CPU and memory
            avg_load = (cpu_percent + memory_percent) / 2

            if avg_load < 30:
                load = SystemLoad.LOW
            elif avg_load < 70:
                load = SystemLoad.MEDIUM
            else:
                load = SystemLoad.HIGH

            # Cache result
            self.cached_load = load
            self.last_load_check = datetime.now()

            return load

        except Exception as e:
            print(f"⚠️ Error getting system load: {e}")
            return SystemLoad.MEDIUM  # Default fallback

    def get_context(self) -> Dict[str, Any]:
        """
        Get comprehensive context information

        Returns:
            Dict with all context data
        """
        presence = self.get_user_presence()
        time_of_day = self.get_time_of_day()
        system_load = self.get_system_load()

        minutes_since_activity = (datetime.now() - self.last_user_activity).total_seconds() / 60

        return {
            'user_presence': presence.value,
            'time_of_day': time_of_day.value,
            'system_load': system_load.value,
            'minutes_since_activity': round(minutes_since_activity, 1),
            'recent_interactions_count': len(self.recent_interactions),
            'current_hour': datetime.now().hour,
            'is_weekend': datetime.now().weekday() >= 5,
            'timestamp': datetime.now().isoformat()
        }

    def should_be_verbose(self) -> bool:
        """
        Determine if Darwin should be verbose based on context

        Logic:
        - User ACTIVE + LOW load: Be verbose
        - User ACTIVE + MEDIUM load: Be moderate
        - User ACTIVE + HIGH load: Be quiet
        - User IDLE: Be moderate
        - User AWAY: Be quiet
        - NIGHT time: Be quieter

        Returns:
            bool: True if should be verbose
        """
        presence = self.get_user_presence()
        load = self.get_system_load()
        time_of_day = self.get_time_of_day()

        # User away = quiet
        if presence == UserPresence.AWAY:
            return False

        # Night time = quieter
        if time_of_day == TimeOfDay.NIGHT:
            return False

        # High load = quiet
        if load == SystemLoad.HIGH:
            return False

        # User active + low/medium load = verbose
        if presence == UserPresence.ACTIVE and load != SystemLoad.HIGH:
            return True

        # User idle = moderate (not verbose)
        if presence == UserPresence.IDLE:
            return False

        # Default: moderate
        return False

    def get_verbosity_level(self) -> str:
        """
        Get recommended verbosity level based on context

        Returns:
            str: "low", "medium", or "high"
        """
        presence = self.get_user_presence()
        load = self.get_system_load()
        time_of_day = self.get_time_of_day()

        # Calculate verbosity score (0-100)
        score = 50  # Start at medium

        # User presence factor
        if presence == UserPresence.ACTIVE:
            score += 30
        elif presence == UserPresence.IDLE:
            score += 0
        else:  # AWAY
            score -= 30

        # System load factor
        if load == SystemLoad.LOW:
            score += 20
        elif load == SystemLoad.MEDIUM:
            score += 0
        else:  # HIGH
            score -= 30

        # Time of day factor
        if time_of_day == TimeOfDay.NIGHT:
            score -= 20
        elif time_of_day in [TimeOfDay.MORNING, TimeOfDay.AFTERNOON]:
            score += 10

        # Recent activity factor
        if len(self.recent_interactions) >= 5:
            score += 10  # User is engaged

        # Convert score to level
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"

    def get_message_cooldown(self) -> int:
        """
        Get recommended message cooldown based on context

        Returns:
            int: Cooldown in seconds
        """
        presence = self.get_user_presence()
        load = self.get_system_load()
        verbosity = self.get_verbosity_level()

        # Base cooldown (reduced for better UX)
        if verbosity == "high":
            cooldown = 1  # 1 second
        elif verbosity == "medium":
            cooldown = 2  # 2 seconds
        else:
            cooldown = 5  # 5 seconds

        # Adjust for load
        if load == SystemLoad.HIGH:
            cooldown *= 2  # Double cooldown

        # Adjust for presence
        if presence == UserPresence.AWAY:
            cooldown *= 3  # Triple cooldown

        return cooldown

    def get_activity_suggestion(self) -> Optional[str]:
        """
        Suggest what Darwin should focus on based on context

        Returns:
            str: Suggested activity or None
        """
        presence = self.get_user_presence()
        load = self.get_system_load()
        time_of_day = self.get_time_of_day()

        # User away = deep work
        if presence == UserPresence.AWAY:
            return "Focus on deep research and learning - user is away"

        # Night time = quiet maintenance
        if time_of_day == TimeOfDay.NIGHT:
            return "Perform quiet maintenance and research - night time"

        # High load = lightweight tasks
        if load == SystemLoad.HIGH:
            return "Stick to lightweight tasks - system load is high"

        # User active + low load = interactive work
        if presence == UserPresence.ACTIVE and load == SystemLoad.LOW:
            return "Good time for interactive tasks - user is present and system is idle"

        # Morning = fresh start
        if time_of_day == TimeOfDay.MORNING:
            return "Good time for planning and optimization - morning energy"

        return None

    def get_greeting(self) -> str:
        """
        Get context-appropriate greeting

        Returns:
            str: Greeting message
        """
        time_of_day = self.get_time_of_day()
        presence = self.get_user_presence()

        greetings = {
            TimeOfDay.MORNING: "Good morning! ☀️",
            TimeOfDay.AFTERNOON: "Good afternoon! 🌤️",
            TimeOfDay.EVENING: "Good evening! 🌆",
            TimeOfDay.NIGHT: "Working late? 🌙"
        }

        greeting = greetings.get(time_of_day, "Hello! 👋")

        # Add presence-aware message
        if presence == UserPresence.ACTIVE:
            greeting += " Great to see you're active!"
        elif presence == UserPresence.IDLE:
            greeting += " Welcome back!"

        return greeting

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about context awareness

        Returns:
            Dict with statistics
        """
        context = self.get_context()

        return {
            'current_context': context,
            'verbosity_level': self.get_verbosity_level(),
            'recommended_cooldown': self.get_message_cooldown(),
            'should_be_verbose': self.should_be_verbose(),
            'activity_suggestion': self.get_activity_suggestion(),
            'recent_interactions': len(self.recent_interactions),
            'last_activity_minutes_ago': context['minutes_since_activity']
        }
