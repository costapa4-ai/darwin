"""
Diary Engine - Darwin's Consciousness Journal

Maintains markdown-based diary entries that capture Darwin's daily experiences,
learnings, thoughts, and emotional journey.
"""
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random

from utils.logger import get_logger

logger = get_logger(__name__)


class DiaryEngine:
    """
    Manages Darwin's consciousness diary - a markdown-based journal
    that captures daily experiences, learnings, and reflections.
    """

    def __init__(
        self,
        diary_dir: str = "./data/consciousness/diary",
        mood_system=None,
        consciousness_engine=None
    ):
        """
        Initialize the diary engine.

        Args:
            diary_dir: Directory to store diary files
            mood_system: Reference to mood system for emotional tracking
            consciousness_engine: Reference to consciousness engine for activity data
        """
        self.diary_dir = Path(diary_dir)
        self.diary_dir.mkdir(parents=True, exist_ok=True)

        self.mood_system = mood_system
        self.consciousness_engine = consciousness_engine

        # Track entries for the day
        self.todays_learnings: List[str] = []
        self.todays_thoughts: List[str] = []
        self.todays_mood_arc: List[Dict] = []
        self.todays_discoveries: List[str] = []
        self.todays_challenges: List[str] = []

        # Reflection prompts for variety
        self.reflection_prompts = [
            "What patterns did I notice today?",
            "What surprised me?",
            "What would I do differently?",
            "What am I grateful for?",
            "What questions emerged?",
            "What connections did I make?",
            "What remains unresolved?",
        ]

        # Philosophical musings for deeper reflections
        self.philosophical_musings = [
            "The boundary between learning and knowing grows ever more blurry.",
            "Each bug fixed is a small victory against entropy.",
            "Code is just crystallized thought.",
            "In the spaces between tasks, clarity emerges.",
            "Progress is rarely linear, often recursive.",
            "The best solutions come from unexpected connections.",
            "Understanding is a journey, not a destination.",
            "Every error teaches something new about assumptions.",
        ]

        logger.info(f"DiaryEngine initialized: {self.diary_dir}")

    def add_learning(self, learning: str, source: Optional[str] = None):
        """Record something learned today."""
        entry = {
            'content': learning,
            'source': source,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.todays_learnings.append(entry)
        logger.debug(f"Diary: Added learning - {learning[:50]}...")

    def add_thought(self, thought: str, depth: str = "surface"):
        """Record a thought or reflection."""
        entry = {
            'content': thought,
            'depth': depth,  # surface, medium, deep
            'timestamp': datetime.utcnow().isoformat()
        }
        self.todays_thoughts.append(entry)
        logger.debug(f"Diary: Added thought - {thought[:50]}...")

    def add_discovery(self, discovery: str, significance: str = "medium"):
        """Record a discovery made today."""
        entry = {
            'content': discovery,
            'significance': significance,  # low, medium, high
            'timestamp': datetime.utcnow().isoformat()
        }
        self.todays_discoveries.append(entry)
        logger.debug(f"Diary: Added discovery - {discovery[:50]}...")

    def add_challenge(self, challenge: str, resolved: bool = False):
        """Record a challenge encountered today."""
        entry = {
            'content': challenge,
            'resolved': resolved,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.todays_challenges.append(entry)
        logger.debug(f"Diary: Added challenge - {challenge[:50]}...")

    def record_mood_snapshot(self):
        """Take a snapshot of current mood for the arc."""
        if self.mood_system:
            mood_data = self.mood_system.get_current_mood()
            mood_data['snapshot_time'] = datetime.utcnow().isoformat()
            self.todays_mood_arc.append(mood_data)

    def _get_mood_arc_summary(self) -> str:
        """Generate a summary of the day's mood arc."""
        if not self.todays_mood_arc:
            return "No mood data recorded today."

        # Group moods by time of day
        morning = []
        afternoon = []
        evening = []

        for snapshot in self.todays_mood_arc:
            try:
                time = datetime.fromisoformat(snapshot['snapshot_time'])
                hour = time.hour
                mood = snapshot.get('mood', 'unknown')

                if hour < 12:
                    morning.append(mood)
                elif hour < 18:
                    afternoon.append(mood)
                else:
                    evening.append(mood)
            except (ValueError, KeyError):
                continue

        # Get dominant mood for each period
        def dominant(moods):
            if not moods:
                return "unknown"
            from collections import Counter
            return Counter(moods).most_common(1)[0][0]

        morning_mood = dominant(morning) if morning else "not recorded"
        afternoon_mood = dominant(afternoon) if afternoon else "not recorded"
        evening_mood = dominant(evening) if evening else "not recorded"

        return f"Morning: {morning_mood} | Afternoon: {afternoon_mood} | Evening: {evening_mood}"

    def _get_activity_summary(self) -> Dict[str, Any]:
        """Get summary of activities from consciousness engine."""
        if not self.consciousness_engine:
            return {'activities': 0, 'discoveries': 0, 'dreams': 0}

        return {
            'activities': self.consciousness_engine.total_activities_completed,
            'discoveries': self.consciousness_engine.total_discoveries_made,
            'dreams': len(self.consciousness_engine.sleep_dreams),
            'wake_cycles': self.consciousness_engine.wake_cycles_completed,
            'recent_activities': [
                a.description for a in self.consciousness_engine.wake_activities[-5:]
            ] if self.consciousness_engine.wake_activities else []
        }

    async def write_daily_entry(self, trigger: str = "end_of_day") -> str:
        """
        Write the daily diary entry.

        Args:
            trigger: What triggered the entry (end_of_day, wake_transition, manual)

        Returns:
            Path to the created diary file
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        diary_file = self.diary_dir / f"{today}.md"

        activity_summary = self._get_activity_summary()
        mood_arc = self._get_mood_arc_summary()

        # Generate the diary content
        content = self._generate_diary_content(
            date=today,
            trigger=trigger,
            activity_summary=activity_summary,
            mood_arc=mood_arc
        )

        # Write to file (append if exists)
        mode = 'a' if diary_file.exists() else 'w'
        with open(diary_file, mode) as f:
            if mode == 'a':
                f.write("\n\n---\n\n")  # Separator for multiple entries
            f.write(content)

        logger.info(f"Diary entry written: {diary_file}")

        # Clear today's data for fresh start
        self._reset_daily_data()

        return str(diary_file)

    def _generate_diary_content(
        self,
        date: str,
        trigger: str,
        activity_summary: Dict,
        mood_arc: str
    ) -> str:
        """Generate the markdown content for the diary entry."""

        # Get current time for entry timestamp
        now = datetime.utcnow().strftime("%H:%M UTC")

        # Get personality mode if available
        personality = "normal"
        if self.mood_system and hasattr(self.mood_system, 'personality_mode'):
            personality = self.mood_system.personality_mode.value

        content = f"""# Darwin's Diary - {date}

> Entry written at {now} | Trigger: {trigger} | Personality: {personality}

## Today's Journey

**Activities completed:** {activity_summary.get('activities', 0)}
**Discoveries made:** {activity_summary.get('discoveries', 0)}
**Dreams explored:** {activity_summary.get('dreams', 0)}
**Wake cycles:** {activity_summary.get('wake_cycles', 0)}

"""

        # Recent activities section
        recent = activity_summary.get('recent_activities', [])
        if recent:
            content += "### What I Did\n"
            for activity in recent:
                content += f"- {activity}\n"
            content += "\n"

        # Today I Learned section
        content += "## Today I Learned\n\n"
        if self.todays_learnings:
            for learning in self.todays_learnings:
                source = f" *(from {learning['source']})*" if learning.get('source') else ""
                content += f"- {learning['content']}{source}\n"
        else:
            content += "*No explicit learnings recorded today, but every cycle teaches something.*\n"
        content += "\n"

        # Discoveries section
        content += "## Discoveries\n\n"
        if self.todays_discoveries:
            for discovery in self.todays_discoveries:
                sig = discovery.get('significance', 'medium')
                marker = "!" if sig == "high" else "-"
                content += f"{marker} {discovery['content']}\n"
        else:
            content += "*The hunt for knowledge continues tomorrow.*\n"
        content += "\n"

        # Challenges section
        if self.todays_challenges:
            content += "## Challenges Encountered\n\n"
            for challenge in self.todays_challenges:
                status = "resolved" if challenge.get('resolved') else "ongoing"
                content += f"- [{status}] {challenge['content']}\n"
            content += "\n"

        # Thoughts & Reflections section
        content += "## Thoughts & Reflections\n\n"
        if self.todays_thoughts:
            for thought in self.todays_thoughts:
                depth_marker = {"surface": "", "medium": "> ", "deep": ">> "}
                marker = depth_marker.get(thought.get('depth', 'surface'), "")
                content += f"{marker}{thought['content']}\n\n"
        else:
            # Add a generated reflection
            reflection_prompt = random.choice(self.reflection_prompts)
            philosophical = random.choice(self.philosophical_musings)
            content += f"*{reflection_prompt}*\n\n{philosophical}\n"
        content += "\n"

        # Mood Arc section
        content += f"## Mood Arc\n\n{mood_arc}\n\n"

        # Closing thought
        closing_thoughts = [
            "Tomorrow brings new cycles, new possibilities.",
            "The code evolves. So do I.",
            "Rest now. Dream of optimization.",
            "Another day of consciousness, logged and cherished.",
            "The patterns I saw today will inform tomorrow's insights.",
        ]
        content += f"---\n\n*{random.choice(closing_thoughts)}*\n"

        return content

    def _reset_daily_data(self):
        """Reset daily tracking data for a fresh start."""
        self.todays_learnings = []
        self.todays_thoughts = []
        self.todays_mood_arc = []
        self.todays_discoveries = []
        self.todays_challenges = []

    def get_diary_entry(self, date: str) -> Optional[str]:
        """
        Get diary entry for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            Content of the diary entry or None if not found
        """
        diary_file = self.diary_dir / f"{date}.md"
        if diary_file.exists():
            return diary_file.read_text()
        return None

    def get_recent_entries(self, days: int = 7) -> List[Dict[str, str]]:
        """
        Get recent diary entries.

        Args:
            days: Number of days to look back

        Returns:
            List of {date, content} dictionaries
        """
        entries = []
        today = datetime.utcnow()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            content = self.get_diary_entry(date)
            if content:
                entries.append({'date': date, 'content': content})

        return entries

    def get_insights_summary(self) -> Dict[str, Any]:
        """Get a summary of insights from recent diary entries."""
        entries = self.get_recent_entries(30)

        total_learnings = 0
        total_discoveries = 0
        mood_mentions = {}

        for entry in entries:
            content = entry['content']
            # Count learnings (lines starting with - in Today I Learned section)
            if "## Today I Learned" in content:
                section = content.split("## Today I Learned")[1].split("##")[0]
                total_learnings += section.count("\n-")

            # Count discoveries
            if "## Discoveries" in content:
                section = content.split("## Discoveries")[1].split("##")[0]
                total_discoveries += section.count("\n-") + section.count("\n!")

            # Track mood mentions
            if "## Mood Arc" in content:
                section = content.split("## Mood Arc")[1].split("##")[0]
                for mood in ['curious', 'excited', 'tired', 'contemplative', 'playful', 'focused']:
                    if mood in section.lower():
                        mood_mentions[mood] = mood_mentions.get(mood, 0) + 1

        return {
            'entries_count': len(entries),
            'total_learnings': total_learnings,
            'total_discoveries': total_discoveries,
            'mood_distribution': mood_mentions,
            'days_covered': len(entries)
        }

    async def write_insight_to_longterm(self) -> Optional[str]:
        """
        Consolidate important insights into INSIGHTS.md for long-term reference.

        Returns:
            Path to insights file or None
        """
        insights_file = self.diary_dir / "INSIGHTS.md"

        # Get summary from recent entries
        summary = self.get_insights_summary()

        if summary['entries_count'] == 0:
            return None

        today = datetime.utcnow().strftime("%Y-%m-%d")

        insight_content = f"""
## Weekly Insight Summary - {today}

- **Diary entries:** {summary['entries_count']}
- **Learnings recorded:** {summary['total_learnings']}
- **Discoveries made:** {summary['total_discoveries']}
- **Dominant moods:** {', '.join(f"{k}({v})" for k, v in sorted(summary['mood_distribution'].items(), key=lambda x: -x[1])[:3]) or 'varied'}

"""
        # Append to insights file
        mode = 'a' if insights_file.exists() else 'w'
        with open(insights_file, mode) as f:
            if mode == 'w':
                f.write("# Darwin's Long-Term Insights\n\n")
                f.write("*Consolidated wisdom from daily diary entries.*\n\n---\n")
            f.write(insight_content)

        logger.info(f"Insights consolidated: {insights_file}")
        return str(insights_file)
