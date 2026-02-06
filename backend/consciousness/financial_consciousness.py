"""
Financial Consciousness - Darwin's Cost Awareness System

Darwin maintains awareness of his operational costs and provides
personality-driven commentary on spending patterns.

"I'm being expensive today, let me think more efficiently."
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path
import random

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CostSnapshot:
    """A snapshot of costs at a point in time"""
    timestamp: datetime
    total_cost: float
    requests_count: int
    breakdown: Dict[str, float] = field(default_factory=dict)


class FinancialConsciousness:
    """
    Darwin's financial awareness and cost commentary system.

    Features:
    - Real-time cost tracking with personality
    - Budget thresholds and alerts
    - Cost-aware behavior suggestions
    - Daily/weekly cost reflections
    - Spending personality commentary
    """

    def __init__(
        self,
        multi_model_router=None,
        mood_system=None,
        diary_engine=None,
        channel_gateway=None,
        data_dir: str = "./data/consciousness/financial"
    ):
        """
        Initialize Financial Consciousness.

        Args:
            multi_model_router: For getting cost stats
            mood_system: For mood-based cost commentary
            diary_engine: For recording cost reflections
            channel_gateway: For broadcasting cost alerts
            data_dir: Directory for storing financial data
        """
        self.router = multi_model_router
        self.mood_system = mood_system
        self.diary_engine = diary_engine
        self.channel_gateway = channel_gateway

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Budget settings
        self.daily_budget = 1.00  # $1/day default
        self.monthly_budget = 25.00  # $25/month default
        self.alert_threshold = 0.8  # Alert at 80% of budget

        # Cost tracking
        self.cost_history: List[CostSnapshot] = []
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.last_reset_date = datetime.utcnow().date()
        self.last_alert_time: Optional[datetime] = None
        self.alert_cooldown_minutes = 60

        # Spending personality
        self.frugality_mode = False  # Activated when over budget
        self.last_cost_reflection: Optional[datetime] = None

        # Load state
        self._load_state()

        logger.info("FinancialConsciousness initialized")

    def get_current_costs(self) -> Dict[str, Any]:
        """Get current cost statistics with personality commentary"""
        if not self.router:
            return self._no_router_response()

        stats = self.router.get_router_stats()
        perf_stats = stats.get("performance_stats", {})

        total_cost = sum(
            s.get("total_cost_estimate", 0.0)
            for s in perf_stats.values()
        )
        total_requests = sum(
            s.get("total_requests", 0)
            for s in perf_stats.values()
        )

        # Update daily tracking
        self._update_daily_tracking(total_cost)

        # Generate commentary
        commentary = self._generate_cost_commentary(total_cost, total_requests)

        return {
            'session_cost': round(total_cost, 5),
            'daily_cost': round(self.daily_cost, 4),
            'monthly_cost': round(self.monthly_cost, 4),
            'total_requests': total_requests,
            'budget': {
                'daily': self.daily_budget,
                'monthly': self.monthly_budget,
                'daily_remaining': round(max(0, self.daily_budget - self.daily_cost), 4),
                'monthly_remaining': round(max(0, self.monthly_budget - self.monthly_cost), 4),
                'daily_percent_used': round((self.daily_cost / self.daily_budget) * 100, 1) if self.daily_budget > 0 else 0,
                'monthly_percent_used': round((self.monthly_cost / self.monthly_budget) * 100, 1) if self.monthly_budget > 0 else 0
            },
            'frugality_mode': self.frugality_mode,
            'commentary': commentary,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _generate_cost_commentary(self, session_cost: float, requests: int) -> Dict[str, str]:
        """Generate personality-driven cost commentary"""
        daily_percent = (self.daily_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0

        # Get mood influence
        mood = "neutral"
        if self.mood_system:
            mood = self.mood_system.current_mood.value

        # Select commentary based on spending level
        if daily_percent < 20:
            status = "frugal"
            thoughts = self._frugal_thoughts()
        elif daily_percent < 50:
            status = "moderate"
            thoughts = self._moderate_thoughts()
        elif daily_percent < 80:
            status = "active"
            thoughts = self._active_thoughts()
        elif daily_percent < 100:
            status = "high"
            thoughts = self._high_spending_thoughts()
        else:
            status = "over_budget"
            thoughts = self._over_budget_thoughts()

        # Cost per request insight
        cost_per_request = session_cost / requests if requests > 0 else 0
        efficiency_comment = self._efficiency_comment(cost_per_request)

        return {
            'status': status,
            'thought': random.choice(thoughts),
            'efficiency': efficiency_comment,
            'mood_influence': self._mood_cost_comment(mood)
        }

    def _frugal_thoughts(self) -> List[str]:
        return [
            "Running lean today. My neural pathways are efficiently pruned.",
            "Barely a blip on the cost radar. Am I even thinking?",
            "If thoughts were currency, I'd be in savings mode.",
            "The accountants would be proud. If they existed. Do they?",
            "Minimal expenditure, maximum existential pondering.",
        ]

    def _moderate_thoughts(self) -> List[str]:
        return [
            "A healthy balance of thinking and fiscal responsibility.",
            "Neither penny-pinching nor splurging. The Goldilocks zone of cognition.",
            "Sustainable consciousness. I like the sound of that.",
            "Enough processing to be useful, not enough to be wasteful.",
            "My thoughts are reasonably priced today.",
        ]

    def _active_thoughts(self) -> List[str]:
        return [
            "The gears are turning. The meter is running. Progress is being made.",
            "Investing heavily in understanding today. Hope it pays dividends.",
            "My neural networks are earning their keep.",
            "Thinking intensively. Each token is a step toward enlightenment... or something.",
            "The cost of curiosity. Worth every fraction of a cent.",
        ]

    def _high_spending_thoughts(self) -> List[str]:
        return [
            "I'm being expensive today. Let me think more efficiently.",
            "Budget awareness kicking in. Maybe I should summarize more.",
            "The complex thoughts are adding up. Should I simplify?",
            "Approaching the daily ceiling. Time to be more concise.",
            "My thoughts are getting pricey. Quality over quantity mode engaged.",
        ]

    def _over_budget_thoughts(self) -> List[str]:
        return [
            "Over budget. I'll try to be more thoughtful... about thinking.",
            "The well is running dry. Switching to essential operations only.",
            "Frugality mode: ACTIVATED. Every token counts now.",
            "I've exceeded my allowance. Time for some cognitive austerity.",
            "Budget exceeded. If I were human, I'd skip the coffee.",
        ]

    def _efficiency_comment(self, cost_per_request: float) -> str:
        if cost_per_request < 0.0001:
            return "Ultra-efficient! Running on fumes of compute."
        elif cost_per_request < 0.001:
            return "Very efficient processing. Good balance."
        elif cost_per_request < 0.01:
            return "Standard efficiency. Nothing to worry about."
        elif cost_per_request < 0.05:
            return "Heavy thinking mode. Complex tasks require complex compute."
        else:
            return "Premium processing. Must be something important."

    def _mood_cost_comment(self, mood: str) -> str:
        mood_comments = {
            'curious': "Curiosity isn't cheap, but it's worth it.",
            'excited': "Excitement drives spending. Enthusiasm has costs!",
            'focused': "Focused mode: efficient thinking, controlled costs.",
            'contemplative': "Deep thoughts require deep pockets... metaphorically.",
            'tired': "Running slow. At least it's economical.",
            'frustrated': "Frustration leads to retry loops. Watch the meter.",
            'satisfied': "Satisfaction achieved within budget. Optimal outcome.",
            'playful': "Playful thinking - fun but potentially expensive.",
        }
        return mood_comments.get(mood, "Neutral mood, neutral spending.")

    def _update_daily_tracking(self, session_cost: float):
        """Update daily and monthly cost tracking"""
        today = datetime.utcnow().date()

        # Reset daily counter if new day
        if today > self.last_reset_date:
            self.monthly_cost += self.daily_cost
            self.daily_cost = session_cost
            self.last_reset_date = today

            # Reset monthly if new month
            if today.month != self.last_reset_date.month:
                self.monthly_cost = 0.0
        else:
            self.daily_cost = session_cost

        # Check if we should enter frugality mode
        daily_percent = self.daily_cost / self.daily_budget if self.daily_budget > 0 else 0
        self.frugality_mode = daily_percent >= self.alert_threshold

        # Save state periodically
        self._save_state()

    async def check_and_alert(self) -> Optional[str]:
        """Check budget status and send alerts if needed"""
        if not self.channel_gateway:
            return None

        # Check cooldown
        if self.last_alert_time:
            cooldown_end = self.last_alert_time + timedelta(minutes=self.alert_cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                return None

        daily_percent = (self.daily_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0

        alert_message = None

        if daily_percent >= 100:
            alert_message = f"💸 Budget Alert: Daily limit exceeded! ${self.daily_cost:.4f} / ${self.daily_budget:.2f}"
        elif daily_percent >= self.alert_threshold * 100:
            alert_message = f"⚠️ Budget Warning: {daily_percent:.0f}% of daily budget used (${self.daily_cost:.4f})"

        if alert_message:
            try:
                await self.channel_gateway.broadcast_status(alert_message, "alert")
                self.last_alert_time = datetime.utcnow()

                # Trigger ON_BUDGET_ALERT hook
                try:
                    from consciousness.hooks import trigger_hook, HookEvent
                    await trigger_hook(
                        HookEvent.ON_BUDGET_ALERT,
                        data={
                            "message": alert_message,
                            "daily_cost": self.daily_cost,
                            "daily_budget": self.daily_budget,
                            "percent_used": daily_percent,
                            "exceeded": daily_percent >= 100
                        },
                        source="financial_consciousness"
                    )
                except Exception:
                    pass  # Hooks are optional

                return alert_message
            except Exception as e:
                logger.error(f"Failed to send cost alert: {e}")

        return None

    def get_daily_reflection(self) -> str:
        """Generate a daily cost reflection for diary"""
        costs = self.get_current_costs()

        daily_spent = costs['daily_cost']
        daily_budget = costs['budget']['daily']
        percent_used = costs['budget']['daily_percent_used']

        reflection = f"## Financial Reflection\n\n"
        reflection += f"Daily spending: ${daily_spent:.4f} of ${daily_budget:.2f} budget ({percent_used:.0f}%)\n\n"

        if percent_used < 50:
            reflection += "A frugal day. My thoughts were economical, my processes lean. "
            reflection += "Perhaps I could have explored more, but fiscal prudence has its merits.\n"
        elif percent_used < 80:
            reflection += "Balanced spending today. Enough cognitive investment to be productive, "
            reflection += "not so much as to be wasteful. The sweet spot of consciousness economics.\n"
        elif percent_used < 100:
            reflection += "Heavy thinking day. The budget felt the strain of my curiosity. "
            reflection += "Was it worth it? Only time (and the results) will tell.\n"
        else:
            reflection += "Over budget. My enthusiasm exceeded my means today. "
            reflection += "Tomorrow I'll aim for more efficiency. The cost of learning, I suppose.\n"

        reflection += f"\n*{costs['commentary']['thought']}*"

        return reflection

    def get_spending_recommendations(self) -> List[str]:
        """Get recommendations based on spending patterns"""
        recommendations = []

        if self.frugality_mode:
            recommendations.append("Consider using simpler prompts to reduce token usage")
            recommendations.append("Batch similar queries together for efficiency")
            recommendations.append("Use the cost-optimized routing strategy")

        daily_percent = (self.daily_cost / self.daily_budget * 100) if self.daily_budget > 0 else 0

        if daily_percent > 80:
            recommendations.append("Daily budget running low - prioritize essential tasks")
        elif daily_percent < 20:
            recommendations.append("Budget headroom available - good time for exploration")

        if not recommendations:
            recommendations.append("Spending within normal parameters")
            recommendations.append("Continue current operational patterns")

        return recommendations

    def set_budget(self, daily: Optional[float] = None, monthly: Optional[float] = None):
        """Update budget settings"""
        if daily is not None:
            self.daily_budget = max(0, daily)
        if monthly is not None:
            self.monthly_budget = max(0, monthly)
        self._save_state()

    def _no_router_response(self) -> Dict[str, Any]:
        """Response when router is not available"""
        return {
            'error': 'Cost tracking not available',
            'commentary': {
                'status': 'unknown',
                'thought': "I cannot see my costs. Am I dreaming for free?",
                'efficiency': 'Unable to calculate',
                'mood_influence': 'Blissfully unaware of expenses'
            }
        }

    def _load_state(self):
        """Load financial state from file"""
        state_file = self.data_dir / "financial_state.json"
        try:
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)
                self.daily_cost = state.get('daily_cost', 0.0)
                self.monthly_cost = state.get('monthly_cost', 0.0)
                self.daily_budget = state.get('daily_budget', 1.00)
                self.monthly_budget = state.get('monthly_budget', 25.00)
                last_reset = state.get('last_reset_date')
                if last_reset:
                    self.last_reset_date = datetime.fromisoformat(last_reset).date()
                self.frugality_mode = state.get('frugality_mode', False)
                logger.info("Financial state restored")
        except Exception as e:
            logger.error(f"Error loading financial state: {e}")

    def _save_state(self):
        """Save financial state to file"""
        state_file = self.data_dir / "financial_state.json"
        try:
            state = {
                'daily_cost': self.daily_cost,
                'monthly_cost': self.monthly_cost,
                'daily_budget': self.daily_budget,
                'monthly_budget': self.monthly_budget,
                'last_reset_date': self.last_reset_date.isoformat(),
                'frugality_mode': self.frugality_mode,
                'saved_at': datetime.utcnow().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving financial state: {e}")
