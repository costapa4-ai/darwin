"""
Idle Detection System
Monitors system activity and detects idle periods
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque


class IdleDetector:
    """
    Detects periods of system inactivity
    """

    def __init__(self, idle_threshold_minutes: int = 5):
        self.idle_threshold = timedelta(minutes=idle_threshold_minutes)
        self.last_activity = datetime.utcnow()
        self.activity_history = deque(maxlen=100)  # Keep last 100 activities

    def record_activity(self, activity_type: str = 'general', metadata: Optional[Dict] = None):
        """
        Record user/system activity

        Args:
            activity_type: Type of activity (task_creation, api_call, etc.)
            metadata: Additional activity data
        """
        self.last_activity = datetime.utcnow()

        activity_record = {
            'type': activity_type,
            'timestamp': self.last_activity,
            'metadata': metadata or {}
        }

        self.activity_history.append(activity_record)

    def is_idle(self) -> bool:
        """
        Check if system is currently idle

        Returns:
            True if idle period exceeds threshold
        """
        time_since_last = datetime.utcnow() - self.last_activity
        return time_since_last > self.idle_threshold

    def get_idle_duration(self) -> timedelta:
        """
        Get duration of current idle period

        Returns:
            Time since last activity
        """
        return datetime.utcnow() - self.last_activity

    def get_activity_pattern(self) -> Dict:
        """
        Analyze activity patterns

        Returns:
            Pattern analysis including peak hours, frequency, etc.
        """
        if not self.activity_history:
            return {
                'pattern': 'no_data',
                'total_activities': 0
            }

        # Convert to list for analysis
        activities = list(self.activity_history)

        # Hourly distribution
        hours = [a['timestamp'].hour for a in activities]
        if hours:
            most_active_hour = max(set(hours), key=hours.count)
        else:
            most_active_hour = None

        # Activity frequency
        if len(activities) > 1:
            total_time = (activities[-1]['timestamp'] - activities[0]['timestamp']).total_seconds()
            avg_interval = total_time / (len(activities) - 1)
        else:
            avg_interval = 0

        # Activity types distribution
        types = {}
        for activity in activities:
            activity_type = activity['type']
            types[activity_type] = types.get(activity_type, 0) + 1

        # Determine pattern
        if avg_interval < 60:  # Activity every minute
            pattern = 'very_active'
        elif avg_interval < 300:  # Activity every 5 minutes
            pattern = 'active'
        elif avg_interval < 900:  # Activity every 15 minutes
            pattern = 'moderate'
        else:
            pattern = 'sporadic'

        return {
            'pattern': pattern,
            'total_activities': len(activities),
            'most_active_hour': most_active_hour,
            'avg_interval_seconds': avg_interval,
            'activity_types': types,
            'time_span_hours': total_time / 3600 if len(activities) > 1 else 0
        }

    def should_enter_dream_mode(self) -> bool:
        """
        Determine if system should enter dream mode

        Returns:
            True if conditions are met for dreaming
        """
        # Must be idle
        if not self.is_idle():
            return False

        # Check activity pattern - don't dream if very active recently
        pattern = self.get_activity_pattern()
        if pattern['pattern'] == 'very_active':
            # Give more time before dreaming if recently very active
            return self.get_idle_duration() > timedelta(minutes=10)

        return True

    def get_status(self) -> Dict:
        """
        Get current idle detector status

        Returns:
            Status dictionary with all relevant info
        """
        idle_duration = self.get_idle_duration()

        return {
            'is_idle': self.is_idle(),
            'idle_duration_seconds': idle_duration.total_seconds(),
            'idle_duration_minutes': idle_duration.total_seconds() / 60,
            'last_activity': self.last_activity.isoformat(),
            'idle_threshold_minutes': self.idle_threshold.total_seconds() / 60,
            'should_dream': self.should_enter_dream_mode(),
            'activity_pattern': self.get_activity_pattern(),
            'recent_activities': [
                {
                    'type': a['type'],
                    'timestamp': a['timestamp'].isoformat()
                }
                for a in list(self.activity_history)[-5:]  # Last 5 activities
            ]
        }
