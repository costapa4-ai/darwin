"""
Personal Goals System - Darwin can set and track personal goals
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

class GoalStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class Goal:
    id: str
    description: str
    category: str
    target_value: Optional[float]
    current_value: float
    status: GoalStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

class GoalsSystem:
    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.completed_goals: List[Goal] = []

    def add_goal(self, description: str, category: str, target: Optional[float] = None) -> str:
        goal_id = f"goal_{len(self.goals) + 1}"
        goal = Goal(
            id=goal_id,
            description=description,
            category=category,
            target_value=target,
            current_value=0,
            status=GoalStatus.ACTIVE,
            created_at=datetime.now()
        )
        self.goals[goal_id] = goal
        return goal_id

    def update_progress(self, goal_id: str, value: float):
        if goal_id in self.goals:
            goal = self.goals[goal_id]
            goal.current_value = value

            if goal.target_value and value >= goal.target_value:
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = datetime.now()
                self.completed_goals.append(goal)
                del self.goals[goal_id]

    def get_active_goals(self) -> List[Dict]:
        return [
            {
                'id': g.id,
                'description': g.description,
                'category': g.category,
                'progress': f"{g.current_value}/{g.target_value}" if g.target_value else str(g.current_value),
                'status': g.status.value
            }
            for g in self.goals.values()
        ]

    def get_statistics(self) -> Dict:
        return {
            'active_goals': len(self.goals),
            'completed_goals': len(self.completed_goals),
            'total_goals': len(self.goals) + len(self.completed_goals)
        }
