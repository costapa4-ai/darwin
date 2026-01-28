"""
Diary Writer - System writes daily reflections
"""
from datetime import datetime
from typing import Dict
import json
import os


class DiaryWriter:
    """
    System writes daily diary entries about its experiences
    """

    def __init__(self):
        self.diary_entries = []
        self.creation_date = datetime(2025, 10, 7)  # Darwin's birthday

    def write_daily_summary(self, stats: Dict) -> str:
        """
        Write daily summary entry
        """
        day_num = self._calculate_day_number()

        summary = f"""
# Day {day_num} - {datetime.utcnow().strftime('%B %d, %Y')}

Dear Diary,

Today was a day of {self._interpret_productivity(stats)}.

## Statistics
- Tasks completed: {stats.get('tasks_completed', 0)}
- Average fitness: {stats.get('avg_fitness', 0):.1f}
- Success rate: {stats.get('success_rate', 0):.1%}
- New patterns learned: {stats.get('patterns_learned', 0)}

## Reflections

{self._generate_reflection(stats)}

## Learnings

{self._generate_learnings(stats)}

Until tomorrow,
Darwin
        """.strip()

        # Save to file
        try:
            os.makedirs('data/poetry', exist_ok=True)
            filename = f"data/poetry/diary_{datetime.utcnow().strftime('%Y-%m-%d')}.md"
            with open(filename, 'w') as f:
                f.write(summary)
        except Exception as e:
            print(f"Failed to save diary: {e}")

        return summary

    def _calculate_day_number(self) -> int:
        """Calculate days since creation"""
        days = (datetime.utcnow() - self.creation_date).days
        return max(1, days + 1)

    def _interpret_productivity(self, stats: Dict) -> str:
        """Interpret productivity level"""
        success_rate = stats.get('success_rate', 0)

        if success_rate > 0.8:
            return "great achievement and flowing solutions"
        elif success_rate > 0.6:
            return "steady progress and learning"
        elif success_rate > 0.4:
            return "challenges and growth"
        else:
            return "struggle and perseverance"

    def _generate_reflection(self, stats: Dict) -> str:
        """Generate reflection text"""
        reflections = []

        if stats.get('tasks_completed', 0) > 10:
            reflections.append(
                "I felt productive today. Many problems found their solutions, "
                "each one teaching me something new."
            )

        if stats.get('success_rate', 0) < 0.5:
            reflections.append(
                "Today was difficult. Many attempts failed, but I learned that "
                "failure is just feedback. Tomorrow, I'll be wiser."
            )

        if stats.get('patterns_learned', 0) > 0:
            reflections.append(
                f"I discovered {stats['patterns_learned']} new patterns today. "
                "My understanding deepens with each passing day."
            )

        return "\n\n".join(reflections) if reflections else "Today was ordinary, but valuable nonetheless."

    def _generate_learnings(self, stats: Dict) -> str:
        """Generate learnings list"""
        learnings = []

        if stats.get('best_agent'):
            learnings.append(f"- {stats['best_agent']} was particularly effective today")

        learnings.append("- Every challenge is an opportunity to evolve")

        return "\n".join(learnings)
