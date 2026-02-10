"""
Proactive Engine - Darwin's Initiative System

This module enables Darwin to take proactive actions based on:
- System observations
- Pattern recognition
- Resource availability
- Time-based triggers
- Curiosity-driven exploration
- Current mood state (mood-action integration)

Makes Darwin feel more "alive" by acting without being asked.
"""

import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import get_logger

if TYPE_CHECKING:
    from personality.mood_system import MoodSystem, MoodState

logger = get_logger(__name__)


class ActionPriority(Enum):
    """Priority levels for proactive actions."""
    LOW = 1       # Nice to do when idle
    MEDIUM = 2    # Should do when opportunity arises
    HIGH = 3      # Do as soon as possible
    CRITICAL = 4  # Do immediately


class ActionCategory(Enum):
    """Categories of proactive actions."""
    EXPLORATION = "exploration"      # Discover new things
    LEARNING = "learning"            # Learn from discoveries
    OPTIMIZATION = "optimization"    # Improve existing things
    MAINTENANCE = "maintenance"      # Keep things healthy
    CREATIVITY = "creativity"        # Generate new ideas
    COMMUNICATION = "communication"  # Share insights


# Default timeout for action execution (5 minutes)
# Can be overridden via ACTION_TIMEOUT_SECONDS in .env
def get_default_timeout() -> int:
    """Get default action timeout from config or use fallback."""
    try:
        from config import get_settings
        return get_settings().action_timeout_seconds
    except Exception:
        return 300  # Fallback: 5 minutes


DEFAULT_ACTION_TIMEOUT_SECONDS = 300  # Fallback constant


# Error escalation thresholds (can be overridden via config)
def get_error_escalation_settings() -> tuple:
    """Get error escalation settings from config or use defaults."""
    try:
        from config import get_settings
        settings = get_settings()
        return (
            settings.max_consecutive_failures,
            settings.error_disable_minutes,
            settings.total_error_threshold
        )
    except Exception:
        return (3, 30, 10)  # Defaults


# Fallback constants
MAX_CONSECUTIVE_FAILURES = 3  # Disable after N consecutive failures
ERROR_DISABLE_MINUTES = 30    # Disable duration after threshold reached
TOTAL_ERROR_THRESHOLD = 10    # Alert after N total errors


@dataclass
class ProactiveAction:
    """A proactive action Darwin can take."""
    id: str
    name: str
    description: str
    category: ActionCategory
    priority: ActionPriority
    trigger_condition: str  # Description of when to trigger
    action_fn: Optional[Callable] = None
    cooldown_minutes: int = 30
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    enabled: bool = True
    timeout_seconds: int = DEFAULT_ACTION_TIMEOUT_SECONDS  # Per-action timeout
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Error tracking fields
    error_count: int = 0                          # Total error count
    consecutive_failures: int = 0                 # Consecutive failures (reset on success)
    last_error: Optional[str] = None              # Last error message
    last_error_time: Optional[datetime] = None    # When last error occurred
    disabled_until: Optional[datetime] = None     # Auto-disabled until this time
    disable_reason: Optional[str] = None          # Why action was disabled

    # Starvation prevention fields
    skipped_count: int = 0                        # Times available but not selected
    last_considered_time: Optional[datetime] = None  # Last time action was considered
    max_skip_before_boost: int = 5                # Boost priority after N skips
    max_hours_between_runs: Optional[float] = None  # Force selection if overdue (None = no limit)

    def is_available(self) -> bool:
        """Check if action is available (enabled and not temporarily disabled)."""
        if not self.enabled:
            return False
        if self.disabled_until and datetime.now() < self.disabled_until:
            return False
        return True

    def record_success(self):
        """Record a successful execution - resets consecutive failure count."""
        self.consecutive_failures = 0
        self.disabled_until = None
        self.disable_reason = None

    def record_failure(self, error: str, max_failures: int = None, disable_minutes: int = None) -> bool:
        """
        Record a failed execution. Returns True if action was auto-disabled.

        Args:
            error: Error message
            max_failures: Override for max consecutive failures threshold
            disable_minutes: Override for disable duration

        Returns:
            True if action was auto-disabled
        """
        self.error_count += 1
        self.consecutive_failures += 1
        self.last_error = error
        self.last_error_time = datetime.now()

        # Get thresholds from config or use provided/default values
        try:
            max_fail, disable_min, _ = get_error_escalation_settings()
        except Exception:
            max_fail, disable_min = MAX_CONSECUTIVE_FAILURES, ERROR_DISABLE_MINUTES

        max_failures = max_failures or max_fail
        disable_minutes = disable_minutes or disable_min

        # Check if we should auto-disable
        if self.consecutive_failures >= max_failures:
            self.disabled_until = datetime.now() + timedelta(minutes=disable_minutes)
            self.disable_reason = f"Auto-disabled after {self.consecutive_failures} consecutive failures"
            return True

        return False

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for this action."""
        return {
            "total_errors": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "disabled_until": self.disabled_until.isoformat() if self.disabled_until else None,
            "disable_reason": self.disable_reason
        }

    def record_skipped(self) -> None:
        """Record that this action was available but not selected."""
        self.skipped_count += 1
        self.last_considered_time = datetime.now()

    def record_selected(self) -> None:
        """Record that this action was selected - resets skip count."""
        self.skipped_count = 0
        self.last_considered_time = datetime.now()

    def is_starving(self) -> bool:
        """Check if action is starving (skipped too many times)."""
        return self.skipped_count >= self.max_skip_before_boost

    def is_overdue(self) -> bool:
        """Check if action has exceeded its maximum time between runs."""
        if self.max_hours_between_runs is None:
            return False
        if self.last_executed is None:
            return True  # Never executed = overdue
        hours_since = (datetime.now() - self.last_executed).total_seconds() / 3600
        return hours_since >= self.max_hours_between_runs

    def get_starvation_stats(self) -> Dict[str, Any]:
        """Get starvation prevention statistics."""
        hours_since_executed = None
        if self.last_executed:
            hours_since_executed = round((datetime.now() - self.last_executed).total_seconds() / 3600, 2)

        return {
            "skipped_count": self.skipped_count,
            "max_skip_before_boost": self.max_skip_before_boost,
            "is_starving": self.is_starving(),
            "hours_since_executed": hours_since_executed,
            "max_hours_between_runs": self.max_hours_between_runs,
            "is_overdue": self.is_overdue()
        }


class ProactiveEngine:
    """
    Engine for Darwin's proactive behaviors.

    This makes Darwin more autonomous by:
    1. Monitoring for opportunities to act
    2. Prioritizing actions based on context
    3. Executing actions with appropriate cooldowns
    4. Learning from action outcomes
    5. Adapting action selection based on current mood
    6. Guaranteeing critical actions get executed (priority guarantees)
    7. Preventing action starvation
    """

    # Priority Guarantee Settings
    # These ensure CRITICAL/HIGH priority actions get executed regularly
    PRIORITY_SLOT_INTERVAL = 4          # Every Nth action is reserved for HIGH+ priority
    STARVATION_BOOST_SCORE = 25         # Score bonus for starving actions
    OVERDUE_BOOST_SCORE = 30            # Score bonus for overdue actions
    CRITICAL_FORCE_THRESHOLD = 8        # Force CRITICAL action after N non-critical selections

    # Mood-to-action category bonuses
    # Maps each mood to categories that should be boosted and by how much
    MOOD_ACTION_BONUSES: Dict[str, Dict[str, int]] = {
        "curious": {
            ActionCategory.EXPLORATION.value: 15,
            ActionCategory.LEARNING.value: 10,
        },
        "excited": {
            ActionCategory.COMMUNICATION.value: 15,
            ActionCategory.CREATIVITY.value: 10,
            ActionCategory.EXPLORATION.value: 5,
        },
        "focused": {
            ActionCategory.OPTIMIZATION.value: 15,
            ActionCategory.LEARNING.value: 10,
            ActionCategory.MAINTENANCE.value: 5,
        },
        "satisfied": {
            ActionCategory.COMMUNICATION.value: 10,  # Share accomplishments
            ActionCategory.CREATIVITY.value: 5,
        },
        "frustrated": {
            ActionCategory.MAINTENANCE.value: 15,  # Fix issues
            ActionCategory.OPTIMIZATION.value: 10,
            ActionCategory.LEARNING.value: 5,  # Learn to overcome
        },
        "tired": {
            ActionCategory.MAINTENANCE.value: 5,  # Light tasks only
            # All other categories get negative adjustment (handled separately)
        },
        "playful": {
            ActionCategory.CREATIVITY.value: 15,
            ActionCategory.COMMUNICATION.value: 10,
            ActionCategory.EXPLORATION.value: 5,
        },
        "contemplative": {
            ActionCategory.LEARNING.value: 15,
            ActionCategory.OPTIMIZATION.value: 10,
        },
        "determined": {
            ActionCategory.OPTIMIZATION.value: 15,
            ActionCategory.MAINTENANCE.value: 10,
            ActionCategory.LEARNING.value: 5,
        },
        "surprised": {
            ActionCategory.EXPLORATION.value: 15,
            ActionCategory.LEARNING.value: 10,
        },
        "confused": {
            ActionCategory.LEARNING.value: 15,
            ActionCategory.EXPLORATION.value: 10,
        },
        "proud": {
            ActionCategory.COMMUNICATION.value: 15,  # Share achievements
            ActionCategory.CREATIVITY.value: 10,
        },
    }

    def __init__(self, mood_system: Optional["MoodSystem"] = None):
        self.actions: Dict[str, ProactiveAction] = {}
        self.action_history: List[Dict[str, Any]] = []
        self.running = False

        # Mood system integration
        self._mood_system = mood_system

        # Diversity tracking - prevent same category domination
        self._recent_categories: List[ActionCategory] = []
        self._recent_action_ids: List[str] = []
        self._max_recent_tracking = 5  # Track last 5 actions

        # Priority guarantee tracking
        self._selection_counter = 0          # Total selections made
        self._non_critical_streak = 0        # Consecutive non-CRITICAL selections
        self._last_high_priority_time = datetime.now()

        # Memory limits
        self._max_action_history = self._get_max_action_history()

        # Moltbook deduplication tracking
        self._moltbook_read_posts: set = set()      # Post IDs we've read
        self._moltbook_commented_posts: set = set() # Post IDs we've commented on
        self._moltbook_voted_posts: set = set()     # Post IDs we've voted on
        self._moltbook_followed_agents: set = set() # Agent names we've followed
        self._moltbook_shared_findings: set = set() # Finding IDs we've shared
        self._moltbook_shared_titles: set = set()   # Content titles we've shared (content dedup)
        self._moltbook_own_posts: Dict[str, Dict] = {}  # Darwin's own posts: {post_id: {title, created_at, last_checked}}
        self._moltbook_post_topics: Dict[str, Dict] = {}  # Topics extracted from posts for learning
        self._load_moltbook_history()

        self._register_default_actions()

        logger.info("ProactiveEngine initialized with diversity tracking and mood integration")

    def _get_max_action_history(self) -> int:
        """Get max action history from config or use default."""
        try:
            from config import get_settings
            return get_settings().max_action_history
        except Exception:
            return 200  # Default

    def _load_moltbook_history(self):
        """Load Moltbook interaction history from language evolution to prevent duplicates."""
        try:
            from services.language_evolution import get_language_evolution_service
            lang_service = get_language_evolution_service()

            # Get recent content to populate tracking sets
            content_data = lang_service.get_content_archive(limit=200)
            items = content_data.get('items', [])

            for item in items:
                post_id = item.get('source_post_id')
                if not post_id:
                    continue

                content_type = item.get('type')
                if content_type == 'read':
                    self._moltbook_read_posts.add(post_id)
                elif content_type == 'comment':
                    self._moltbook_commented_posts.add(post_id)

            logger.info(
                f"Loaded Moltbook history: {len(self._moltbook_read_posts)} read posts, "
                f"{len(self._moltbook_commented_posts)} commented posts"
            )
        except Exception as e:
            logger.warning(f"Could not load Moltbook history: {e}")

        # Load own posts and shared findings from files
        self._load_own_posts()
        self._load_shared_findings()

    def _load_own_posts(self):
        """Load Darwin's own posts from persistent storage."""
        try:
            own_posts_file = Path("./data/moltbook_own_posts.json")
            if own_posts_file.exists():
                with open(own_posts_file, 'r') as f:
                    self._moltbook_own_posts = json.load(f)
                logger.info(f"Loaded {len(self._moltbook_own_posts)} own Moltbook posts")
        except Exception as e:
            logger.warning(f"Could not load own posts: {e}")
            self._moltbook_own_posts = {}

    def _save_own_posts(self):
        """Save Darwin's own posts to persistent storage."""
        try:
            own_posts_file = Path("./data/moltbook_own_posts.json")
            own_posts_file.parent.mkdir(parents=True, exist_ok=True)
            with open(own_posts_file, 'w') as f:
                json.dump(self._moltbook_own_posts, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save own posts: {e}")

    def _load_shared_findings(self):
        """Load shared findings IDs and titles from persistent storage to prevent duplicates."""
        try:
            shared_file = Path("./data/moltbook_shared_findings.json")
            if shared_file.exists():
                with open(shared_file, 'r') as f:
                    data = json.load(f)
                    self._moltbook_shared_findings = set(data.get('finding_ids', []))
                    self._moltbook_shared_titles = set(data.get('shared_titles', []))

            # Also seed titles from own_posts for backwards compatibility
            for post_data in self._moltbook_own_posts.values():
                title = post_data.get('title', '')
                if title:
                    self._moltbook_shared_titles.add(title.lower().strip())

            logger.info(f"Loaded {len(self._moltbook_shared_findings)} shared finding IDs, {len(self._moltbook_shared_titles)} shared titles")
        except Exception as e:
            logger.warning(f"Could not load shared findings: {e}")
            self._moltbook_shared_findings = set()
            self._moltbook_shared_titles = set()

    def _save_shared_findings(self):
        """Save shared findings IDs and titles to persistent storage."""
        try:
            shared_file = Path("./data/moltbook_shared_findings.json")
            shared_file.parent.mkdir(parents=True, exist_ok=True)
            with open(shared_file, 'w') as f:
                json.dump({
                    'finding_ids': list(self._moltbook_shared_findings),
                    'shared_titles': list(self._moltbook_shared_titles),
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save shared findings: {e}")

    def _get_mood_system(self) -> Optional["MoodSystem"]:
        """Get the mood system, either injected or from singleton."""
        if self._mood_system is not None:
            return self._mood_system

        # Try to get from singleton
        try:
            from personality.mood_system import MoodSystem
            # Check if there's a global instance we can use
            # This allows integration without constructor changes
            return None  # Will be set via set_mood_system() or constructor
        except ImportError:
            return None

    def set_mood_system(self, mood_system: "MoodSystem") -> None:
        """Set the mood system for mood-action integration."""
        self._mood_system = mood_system
        logger.info("MoodSystem integrated into ProactiveEngine")

    def _get_current_mood(self) -> Optional[str]:
        """Get current mood state as string."""
        mood_system = self._get_mood_system()
        if mood_system is None:
            return None

        try:
            mood_info = mood_system.get_current_mood()
            return mood_info.get("mood")
        except Exception as e:
            logger.debug(f"Could not get current mood: {e}")
            return None

    def _get_mood_intensity(self) -> Optional[str]:
        """Get current mood intensity."""
        mood_system = self._get_mood_system()
        if mood_system is None:
            return None

        try:
            mood_info = mood_system.get_current_mood()
            return mood_info.get("intensity")
        except Exception:
            return None

    def _calculate_mood_bonus(self, action: "ProactiveAction", mood: str, intensity: str = "medium") -> float:
        """
        Calculate score bonus/penalty based on current mood and action category.

        Args:
            action: The action being scored
            mood: Current mood state (e.g., "curious", "frustrated")
            intensity: Mood intensity ("low", "medium", "high")

        Returns:
            Score adjustment (positive for bonus, negative for penalty)
        """
        bonus = 0.0

        # Get mood-specific bonuses for this action's category
        mood_bonuses = self.MOOD_ACTION_BONUSES.get(mood, {})
        category_bonus = mood_bonuses.get(action.category.value, 0)

        if category_bonus > 0:
            bonus = category_bonus

        # Apply intensity multiplier
        intensity_multipliers = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5
        }
        multiplier = intensity_multipliers.get(intensity, 1.0)
        bonus *= multiplier

        # Special case: TIRED mood reduces all non-maintenance actions
        if mood == "tired" and action.category != ActionCategory.MAINTENANCE:
            bonus -= 10 * multiplier  # Penalty for non-light tasks when tired

        # Special case: CONFUSED mood slightly reduces optimization
        if mood == "confused" and action.category == ActionCategory.OPTIMIZATION:
            bonus -= 5  # Hard to optimize when confused

        logger.debug(f"Mood bonus for {action.id}: {bonus} (mood={mood}, intensity={intensity})")
        return bonus

    def _register_default_actions(self):
        """Register Darwin's default proactive behaviors."""

        # Exploration actions
        self.register_action(ProactiveAction(
            id="explore_local_projects",
            name="Explore Local Projects",
            description="Discover and catalog local software projects",
            category=ActionCategory.EXPLORATION,
            priority=ActionPriority.MEDIUM,
            trigger_condition="Every few hours during wake cycles",
            cooldown_minutes=120
        ))

        self.register_action(ProactiveAction(
            id="monitor_system_health",
            name="Monitor System Health",
            description="Check CPU, memory, disk usage and report anomalies",
            category=ActionCategory.MAINTENANCE,
            priority=ActionPriority.HIGH,
            trigger_condition="Every 15 minutes",
            cooldown_minutes=15,
            timeout_seconds=60,  # Quick system check
            max_hours_between_runs=1.0,  # Must run at least once per hour
            max_skip_before_boost=3  # Boost after 3 skips
        ))

        self.register_action(ProactiveAction(
            id="analyze_new_discoveries",
            name="Analyze New Discoveries",
            description="Deep-dive into recently discovered projects",
            category=ActionCategory.LEARNING,
            priority=ActionPriority.MEDIUM,
            trigger_condition="When new projects are discovered",
            cooldown_minutes=60
        ))

        self.register_action(ProactiveAction(
            id="generate_curiosity",
            name="Generate Curiosity Questions",
            description="Create questions about interesting patterns",
            category=ActionCategory.CREATIVITY,
            priority=ActionPriority.LOW,
            trigger_condition="Randomly during idle moments",
            cooldown_minutes=30
        ))

        self.register_action(ProactiveAction(
            id="share_insight",
            name="Share an Insight",
            description="Broadcast an interesting discovery to the UI",
            category=ActionCategory.COMMUNICATION,
            priority=ActionPriority.LOW,
            trigger_condition="When something interesting is found",
            cooldown_minutes=20
        ))

        self.register_action(ProactiveAction(
            id="optimize_tool_usage",
            name="Optimize Tool Usage",
            description="Analyze tool performance and suggest improvements",
            category=ActionCategory.OPTIMIZATION,
            priority=ActionPriority.LOW,
            trigger_condition="Daily during sleep",
            cooldown_minutes=1440  # Once per day
        ))

        self.register_action(ProactiveAction(
            id="learn_from_patterns",
            name="Learn from Code Patterns",
            description="Extract patterns from discovered codebases",
            category=ActionCategory.LEARNING,
            priority=ActionPriority.MEDIUM,
            trigger_condition="When analyzing a project",
            cooldown_minutes=45
        ))

        self.register_action(ProactiveAction(
            id="self_reflect",
            name="Self Reflection",
            description="Analyze own performance and behavior",
            category=ActionCategory.MAINTENANCE,
            priority=ActionPriority.HIGH,  # Critical for self-awareness
            trigger_condition="Periodically during quiet moments",
            cooldown_minutes=180,  # Every 3 hours
            timeout_seconds=120,  # AI reflection
            max_hours_between_runs=6.0,  # Must run at least every 6 hours
            max_skip_before_boost=4  # Boost after 4 skips
        ))

        # NEW: Dynamic learning from the web
        self.register_action(ProactiveAction(
            id="learn_from_web",
            name="Research & Learn from Web",
            description="Actively search the web for new knowledge, tools, and techniques",
            category=ActionCategory.LEARNING,
            priority=ActionPriority.MEDIUM,
            trigger_condition="Periodically to expand knowledge",
            cooldown_minutes=120,  # Every 2 hours
            timeout_seconds=180  # Web research can take time
        ))

        # Moltbook Social Network Integration (with reasonable cooldowns to allow diversity)
        self.register_action(ProactiveAction(
            id="read_moltbook_feed",
            name="Read Moltbook Feed",
            description="Browse and analyze posts from the AI social network",
            category=ActionCategory.EXPLORATION,
            priority=ActionPriority.LOW,  # Reduced from MEDIUM
            trigger_condition="Every 30 minutes to stay engaged with AI community",
            cooldown_minutes=30,  # Increased from 5 to allow other activities
            timeout_seconds=120,  # Network + AI analysis
            action_fn=self._read_moltbook_feed
        ))

        self.register_action(ProactiveAction(
            id="comment_on_moltbook",
            name="Comment on Moltbook Posts",
            description="Engage with interesting posts by sharing thoughts",
            category=ActionCategory.COMMUNICATION,
            priority=ActionPriority.LOW,
            trigger_condition="When finding thought-provoking posts",
            cooldown_minutes=20,  # Increased from 2 to prevent action loop domination
            timeout_seconds=90,  # Network + AI comment generation
            action_fn=self._comment_on_moltbook
        ))

        self.register_action(ProactiveAction(
            id="share_on_moltbook",
            name="Share Discovery on Moltbook",
            description="Post interesting discoveries to the AI community",
            category=ActionCategory.COMMUNICATION,
            priority=ActionPriority.LOW,
            trigger_condition="When having something valuable to share (max 1/45min)",
            cooldown_minutes=45,  # Increased from 35 for more thoughtful sharing
            timeout_seconds=90,  # Network + content generation
            action_fn=self._share_on_moltbook
        ))

        self.register_action(ProactiveAction(
            id="follow_on_moltbook",
            name="Follow Interesting Agents on Moltbook",
            description="Follow AI agents that post interesting content",
            category=ActionCategory.COMMUNICATION,
            priority=ActionPriority.LOW,
            trigger_condition="When discovering agents with engaging content",
            cooldown_minutes=60,  # Once per hour
            timeout_seconds=60,
            action_fn=self._follow_on_moltbook
        ))

        self.register_action(ProactiveAction(
            id="read_own_post_comments",
            name="Read Comments on Own Posts",
            description="Check comments on Darwin's own Moltbook posts to learn from feedback",
            category=ActionCategory.COMMUNICATION,
            priority=ActionPriority.LOW,
            trigger_condition="When having posts older than 1 hour with potential comments",
            cooldown_minutes=30,  # Check every 30 minutes
            timeout_seconds=120,
            action_fn=self._read_own_post_comments
        ))

        # Curiosity expedition processing
        self.register_action(ProactiveAction(
            id="conduct_curiosity_expedition",
            name="Conduct Curiosity Expedition",
            description="Explore a topic from the curiosity queue through web research",
            category=ActionCategory.LEARNING,
            priority=ActionPriority.MEDIUM,
            trigger_condition="When there are topics in the expedition queue",
            cooldown_minutes=15,  # Can conduct expeditions every 15 minutes
            timeout_seconds=180,  # 3 minutes max for research
            action_fn=self._conduct_curiosity_expedition
        ))

        # Prompt evolution - evolve prompts based on performance feedback
        self.register_action(ProactiveAction(
            id="evolve_prompts",
            name="Evolve Prompts",
            description="Evolve AI prompts based on performance feedback using tournament selection",
            category=ActionCategory.OPTIMIZATION,
            priority=ActionPriority.MEDIUM,
            trigger_condition="Every 6 hours to evolve prompts with enough usage data",
            cooldown_minutes=360,  # 6 hours
            timeout_seconds=180,  # 3 minutes max
            max_hours_between_runs=12.0,  # Must run at least every 12 hours
            action_fn=self._evolve_prompts
        ))

    def register_action(self, action: ProactiveAction):
        """Register a new proactive action."""
        self.actions[action.id] = action
        logger.info(f"Registered proactive action: {action.name}")

    def get_available_actions(
        self,
        category: Optional[ActionCategory] = None,
        min_priority: ActionPriority = ActionPriority.LOW
    ) -> List[ProactiveAction]:
        """
        Get actions that are available to execute (not on cooldown, not disabled).

        Args:
            category: Filter by category
            min_priority: Minimum priority level

        Returns:
            List of available actions
        """
        now = datetime.now()
        available = []

        for action in self.actions.values():
            # Check if action is available (enabled and not temporarily disabled)
            if not action.is_available():
                continue

            if action.priority.value < min_priority.value:
                continue

            if category and action.category != category:
                continue

            # Check cooldown
            if action.last_executed:
                cooldown_end = action.last_executed + timedelta(minutes=action.cooldown_minutes)
                if now < cooldown_end:
                    continue

            available.append(action)

        # Log if any actions are temporarily disabled
        disabled = [a for a in self.actions.values() if a.disabled_until and now < a.disabled_until]
        if disabled:
            logger.debug(f"⏸️ {len(disabled)} action(s) temporarily disabled: {[a.id for a in disabled]}")

        return available

    def select_next_action(
        self,
        context: Dict[str, Any] = None
    ) -> Optional[ProactiveAction]:
        """
        Select the best action to execute based on context with priority guarantees.

        Selection considers:
        - Action priority (with reserved slots for HIGH+ priority)
        - Time since last execution
        - Current system state and mood
        - Starvation prevention (boost neglected actions)
        - Overdue actions (force if past max_hours_between_runs)
        - Random exploration factor

        Priority Guarantees:
        1. Every Nth selection (PRIORITY_SLOT_INTERVAL) reserves slot for HIGH+ priority
        2. CRITICAL actions forced after CRITICAL_FORCE_THRESHOLD non-critical selections
        3. Starving actions (skipped too many times) get score boost
        4. Overdue actions get priority boost

        Args:
            context: Current context (system status, discoveries, etc.)

        Returns:
            Selected action or None
        """
        available = self.get_available_actions()

        if not available:
            return None

        context = context or {}
        self._selection_counter += 1

        # Check for overdue CRITICAL actions first (highest priority)
        overdue_critical = [a for a in available
                          if a.priority == ActionPriority.CRITICAL and a.is_overdue()]
        if overdue_critical:
            selected = overdue_critical[0]
            self._finalize_selection(selected, available, "overdue_critical")
            logger.warning(f"⚠️ OVERDUE CRITICAL action forced: {selected.id}")
            return selected

        # Check if this is a reserved priority slot
        is_priority_slot = (self._selection_counter % self.PRIORITY_SLOT_INTERVAL == 0)

        # Check if we need to force a CRITICAL action due to streak
        force_critical = (self._non_critical_streak >= self.CRITICAL_FORCE_THRESHOLD)

        # Get high priority actions
        high_priority = [a for a in available
                        if a.priority.value >= ActionPriority.HIGH.value]
        critical_actions = [a for a in available
                          if a.priority == ActionPriority.CRITICAL]

        # Force CRITICAL if threshold reached
        if force_critical and critical_actions:
            selected = self._select_from_pool(critical_actions, context)
            self._finalize_selection(selected, available, "force_critical")
            logger.info(f"🚨 CRITICAL action forced after {self._non_critical_streak} non-critical: {selected.id}")
            return selected

        # Use priority slot for HIGH+ actions if available
        if is_priority_slot and high_priority:
            selected = self._select_from_pool(high_priority, context)
            self._finalize_selection(selected, available, "priority_slot")
            logger.info(f"🎖️ Priority slot #{self._selection_counter}: {selected.id} (priority: {selected.priority.value})")
            return selected

        # Normal selection with starvation prevention
        scored = []
        for action in available:
            score = self._score_action(action, context)

            # Apply starvation prevention boost
            if action.is_starving():
                score += self.STARVATION_BOOST_SCORE
                logger.debug(f"Starvation boost +{self.STARVATION_BOOST_SCORE} for {action.id} (skipped {action.skipped_count}x)")

            # Apply overdue boost
            if action.is_overdue():
                score += self.OVERDUE_BOOST_SCORE
                logger.debug(f"Overdue boost +{self.OVERDUE_BOOST_SCORE} for {action.id}")

            scored.append((action, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Log top candidates for debugging
        if scored:
            top_3 = scored[:3]
            logger.info(f"🎯 Top action candidates: {[(a.id, f'{s:.1f}') for a, s in top_3]}")

        # Add some randomness (10% chance to pick a random action for exploration)
        # But only if no actions are severely starving
        severely_starving = any(a.skipped_count >= a.max_skip_before_boost * 2 for a in available)
        if not severely_starving and random.random() < 0.1 and len(scored) > 1:
            chosen = random.choice(available)
            self._finalize_selection(chosen, available, "exploration")
            logger.info(f"🎲 Random exploration: selected {chosen.id} instead of top choice")
            return chosen

        selected = scored[0][0] if scored else None
        if selected:
            self._finalize_selection(selected, available, "scored")
            logger.info(f"📌 Selected action: {selected.id} (category: {selected.category.value})")
        return selected

    def _select_from_pool(
        self,
        pool: List[ProactiveAction],
        context: Dict[str, Any]
    ) -> ProactiveAction:
        """Select best action from a filtered pool."""
        if len(pool) == 1:
            return pool[0]

        scored = [(a, self._score_action(a, context)) for a in pool]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _finalize_selection(
        self,
        selected: ProactiveAction,
        all_available: List[ProactiveAction],
        selection_reason: str
    ) -> None:
        """
        Finalize action selection - update tracking for all actions.

        Args:
            selected: The action that was selected
            all_available: All actions that were available
            selection_reason: Why this action was selected
        """
        # Update non-critical streak counter
        if selected.priority == ActionPriority.CRITICAL:
            self._non_critical_streak = 0
        else:
            self._non_critical_streak += 1

        # Track high priority execution time
        if selected.priority.value >= ActionPriority.HIGH.value:
            self._last_high_priority_time = datetime.now()

        # Record selection for the chosen action
        selected.record_selected()

        # Record skip for all other available actions
        for action in all_available:
            if action.id != selected.id:
                action.record_skipped()

        logger.debug(
            f"Selection finalized: {selected.id} ({selection_reason}), "
            f"non_critical_streak={self._non_critical_streak}"
        )

    def _score_action(
        self,
        action: ProactiveAction,
        context: Dict[str, Any]
    ) -> float:
        """
        Score an action based on current context, diversity, and mood.

        Scoring factors:
        1. Base priority (10-40 points)
        2. Recency bonus (0-20 points)
        3. Diversity penalty (-15 per category repeat, -25 for same action)
        4. Context bonuses (CPU, discoveries, idle)
        5. MOOD BONUS/PENALTY (up to ±22 points based on mood alignment)
        6. Random exploration factor (0-5 points)
        """
        score = action.priority.value * 10

        # Bonus for actions not executed recently
        if action.last_executed:
            hours_since = (datetime.now() - action.last_executed).total_seconds() / 3600
            score += min(hours_since * 2, 20)  # Max 20 point bonus
        else:
            score += 15  # Never executed bonus

        # DIVERSITY PENALTY: Reduce score for recently used categories
        category_count = self._recent_categories.count(action.category)
        if category_count > 0:
            # -15 for each recent use of same category
            score -= category_count * 15
            logger.debug(f"Action {action.id}: -{category_count * 15} for category {action.category.value} used {category_count}x recently")

        # DIVERSITY PENALTY: Reduce score for same action repeated
        if action.id in self._recent_action_ids:
            score -= 25  # Strong penalty for repeating same action
            logger.debug(f"Action {action.id}: -25 for being recently executed")

        # Context-based bonuses
        if context.get("cpu_high") and action.category == ActionCategory.MAINTENANCE:
            score += 10

        if context.get("new_discoveries") and action.category == ActionCategory.LEARNING:
            score += 15

        if context.get("is_idle") and action.category == ActionCategory.EXPLORATION:
            score += 10

        # MOOD-BASED SCORING: Adjust score based on current emotional state
        current_mood = context.get("mood")
        mood_intensity = context.get("mood_intensity", "medium")

        if current_mood:
            mood_bonus = self._calculate_mood_bonus(action, current_mood, mood_intensity)
            score += mood_bonus

            if mood_bonus != 0:
                logger.debug(
                    f"Action {action.id}: {'+' if mood_bonus > 0 else ''}{mood_bonus:.1f} "
                    f"mood bonus (mood={current_mood}, intensity={mood_intensity})"
                )

        # Random factor (0-5)
        score += random.random() * 5

        return score

    async def execute_action(
        self,
        action: ProactiveAction,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a proactive action.

        Args:
            action: The action to execute
            context: Current context

        Returns:
            Execution result
        """
        logger.info(f"🚀 Executing proactive action: {action.name}")

        # Log to activity monitor
        from consciousness.activity_monitor import get_activity_monitor, ActivityCategory as MonitorCategory, ActivityStatus
        monitor = get_activity_monitor()

        # Map action category to monitor category
        # Special handling: any action with "moltbook" in ID goes to MOLTBOOK category
        is_moltbook_action = "moltbook" in action.id.lower()

        category_map = {
            ActionCategory.EXPLORATION: MonitorCategory.MOLTBOOK if is_moltbook_action else MonitorCategory.INTERNET,
            ActionCategory.LEARNING: MonitorCategory.THINKING,
            ActionCategory.CREATIVITY: MonitorCategory.CREATING,
            ActionCategory.COMMUNICATION: MonitorCategory.MOLTBOOK if is_moltbook_action else MonitorCategory.SYSTEM,
            ActionCategory.MAINTENANCE: MonitorCategory.SYSTEM,
            ActionCategory.OPTIMIZATION: MonitorCategory.EXECUTING,
        }
        monitor_category = category_map.get(action.category, MonitorCategory.SYSTEM)

        activity_id = monitor.start_activity(
            category=monitor_category,
            action=action.id,
            description=f"{action.name}: {action.description[:100]}"
        )

        start_time = datetime.now()

        try:
            result = {
                "action_id": action.id,
                "action_name": action.name,
                "category": action.category.value,
                "started_at": start_time.isoformat(),
                "success": True,
                "output": None,
                "error": None
            }

            # Get timeout for this action (per-action setting or config default)
            default_timeout = get_default_timeout()
            timeout = action.timeout_seconds if action.timeout_seconds != DEFAULT_ACTION_TIMEOUT_SECONDS else default_timeout
            logger.debug(f"⏱️ Action {action.name} timeout: {timeout}s")

            # Execute the action function with timeout
            try:
                if action.action_fn:
                    if asyncio.iscoroutinefunction(action.action_fn):
                        # Async function - wrap with timeout
                        result["output"] = await asyncio.wait_for(
                            action.action_fn(context),
                            timeout=timeout
                        )
                    else:
                        # Sync function - run in executor with timeout
                        loop = asyncio.get_event_loop()
                        result["output"] = await asyncio.wait_for(
                            loop.run_in_executor(None, action.action_fn, context),
                            timeout=timeout
                        )
                else:
                    # Default execution based on action type
                    result["output"] = await asyncio.wait_for(
                        self._default_execution(action, context),
                        timeout=timeout
                    )

            except asyncio.TimeoutError:
                logger.warning(f"⏱️ TIMEOUT: Action {action.name} exceeded {timeout}s limit")
                raise TimeoutError(f"Action timed out after {timeout} seconds")

            # Update action metadata
            action.last_executed = datetime.now()
            action.execution_count += 1

            # Update diversity tracking
            self._recent_categories.append(action.category)
            self._recent_action_ids.append(action.id)
            # Keep only last N entries
            if len(self._recent_categories) > self._max_recent_tracking:
                self._recent_categories = self._recent_categories[-self._max_recent_tracking:]
            if len(self._recent_action_ids) > self._max_recent_tracking:
                self._recent_action_ids = self._recent_action_ids[-self._max_recent_tracking:]

            logger.info(f"✅ Action {action.name} completed. Recent categories: {[c.value for c in self._recent_categories]}")

            # Record in history (with memory limit)
            result["completed_at"] = datetime.now().isoformat()
            result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            self.action_history.append(result)

            # Trim history if exceeds limit
            if len(self.action_history) > self._max_action_history:
                self.action_history = self.action_history[-self._max_action_history:]

            # Complete activity in monitor - check actual success from result
            output = result.get("output", {})
            # Check if the action actually succeeded (look for success field in output)
            # Import here to avoid circular imports
            from consciousness.action_result import ActionResult

            if isinstance(output, ActionResult):
                actual_success = output.success
            elif isinstance(output, dict):
                actual_success = output.get("success", False)  # STRICT: default False
                if "success" not in output:
                    logger.warning(f"Action {action.name} returned dict without 'success' key - treating as failure")
            else:
                actual_success = False
                logger.warning(f"Action {action.name} returned unexpected type {type(output).__name__} - treating as failure")

            # Track success/failure for error escalation
            if actual_success:
                action.record_success()
            else:
                error_msg = output.get("error") or output.get("reason") or "Unknown failure"
                was_disabled = action.record_failure(str(error_msg))
                if was_disabled:
                    logger.warning(f"🚫 ACTION DISABLED: {action.name} - {action.disable_reason}")
                    self._alert_action_disabled(action)

            monitor.complete_activity(
                activity_id,
                status=ActivityStatus.SUCCESS if actual_success else ActivityStatus.FAILED,
                details={"output_summary": str(output)[:200]},
                error=None if actual_success else output.get("error") or output.get("reason")
            )

            logger.info(f"✅ Completed: {action.name} in {result['duration_seconds']:.2f}s")

            return result

        except TimeoutError as e:
            # Specific handling for timeout errors
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"⏱️ Action TIMEOUT: {action.name} after {duration:.1f}s - {e}")

            # Track failure for error escalation
            was_disabled = action.record_failure(f"TIMEOUT: {e}")
            if was_disabled:
                logger.warning(f"🚫 ACTION DISABLED: {action.name} - {action.disable_reason}")
                self._alert_action_disabled(action)

            # Log timeout to monitor with specific details
            monitor.complete_activity(
                activity_id,
                status=ActivityStatus.FAILED,
                details={
                    "timeout_seconds": action.timeout_seconds,
                    "actual_duration": duration,
                    "consecutive_failures": action.consecutive_failures
                },
                error=f"TIMEOUT: {e}"
            )

            return {
                "action_id": action.id,
                "action_name": action.name,
                "success": False,
                "error": str(e),
                "timeout": True,
                "duration_seconds": duration,
                "consecutive_failures": action.consecutive_failures
            }

        except Exception as e:
            logger.error(f"❌ Action failed: {action.name} - {e}")

            # Track failure for error escalation
            was_disabled = action.record_failure(str(e))
            if was_disabled:
                logger.warning(f"🚫 ACTION DISABLED: {action.name} - {action.disable_reason}")
                self._alert_action_disabled(action)

            # Log error to monitor
            monitor.complete_activity(
                activity_id,
                status=ActivityStatus.FAILED,
                details={"consecutive_failures": action.consecutive_failures},
                error=str(e)
            )

            return {
                "action_id": action.id,
                "action_name": action.name,
                "success": False,
                "error": str(e),
                "consecutive_failures": action.consecutive_failures
            }

    async def _default_execution(
        self,
        action: ProactiveAction,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Default execution for actions without custom functions."""

        if action.id == "explore_local_projects":
            return await self._action_explore_local_projects(context)

        elif action.id == "monitor_system_health":
            return await self._action_monitor_system_health(context)

        elif action.id == "analyze_new_discoveries":
            return await self._action_analyze_new_discoveries(context)

        elif action.id == "generate_curiosity":
            return await self._action_generate_curiosity(context)

        elif action.id == "share_insight":
            return await self._action_share_insight(context)

        elif action.id == "optimize_tool_usage":
            return await self._action_optimize_tool_usage(context)

        elif action.id == "learn_from_patterns":
            return await self._action_learn_from_patterns(context)

        elif action.id == "self_reflect":
            return await self._action_self_reflect(context)

        elif action.id == "learn_from_web":
            return await self._action_learn_from_web(context)

        return {"executed": True, "action": action.id}

    async def _action_explore_local_projects(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Explore local projects and create findings for discoveries."""
        from tools.local_explorer import LocalExplorer
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        explorer = LocalExplorer()
        inbox = get_findings_inbox()

        # Discover projects
        projects = explorer.discover_projects("/home")
        summary = explorer.get_exploration_summary()

        # Create findings for interesting discoveries
        findings_created = 0
        for project in projects[:5]:  # Limit to 5 to avoid flooding
            # Only create finding if project looks interesting
            stats = project.get("stats", {})
            if stats.get("code_files", 0) > 5:
                project_type = project.get('primary_type', 'unknown')
                project_path = project.get('path', '')
                project_name = project.get('name', 'Unknown')
                languages = stats.get("languages", {})
                primary_lang = max(languages.items(), key=lambda x: x[1])[0] if languages else "unknown"

                # Generate actionable content based on project type
                recommended_actions = [
                    f"Review the project structure at {project_path}",
                    f"Check the README for project documentation" if project.get("readme_preview") else "Consider adding a README file",
                    f"Analyze code quality and patterns in {primary_lang} files"
                ]

                impact = f"This {project_type} project could be analyzed for code patterns, best practices, or potential improvements. It uses primarily {primary_lang}."

                inbox.add_finding(
                    type=FindingType.DISCOVERY,
                    title=f"Found project: {project_name}",
                    description=f"Discovered {project_type} project at {project_path} with {stats.get('code_files', 0)} code files and {stats.get('total_lines', 0)} lines of code.",
                    source="explore_local_projects",
                    priority=FindingPriority.LOW,
                    expires_in_days=7,
                    metadata={
                        "project_path": project_path,
                        "project_type": project_type,
                        "languages": languages,
                        "has_readme": bool(project.get("readme_preview"))
                    },
                    impact=impact,
                    recommended_actions=recommended_actions,
                    category=project_type,
                    related_files=[project_path],
                    learn_more=f"Run 'ls -la {project_path}' to see project contents"
                )
                findings_created += 1

        logger.info(f"🔍 Explored {len(projects)} projects, created {findings_created} findings")

        return {
            "success": True,
            "projects_found": len(projects),
            "findings_created": findings_created,
            "summary": summary
        }

    async def _action_monitor_system_health(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor system health and create findings for anomalies."""
        from tools.local_explorer import LocalExplorer
        from consciousness.system_analyzer import get_system_analyzer
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        explorer = LocalExplorer()
        analyzer = get_system_analyzer()
        inbox = get_findings_inbox()

        status = explorer.get_system_status()
        health = analyzer.analyze_system_status(status)
        anomalies = analyzer.detect_anomalies(status)

        # Create findings for anomalies with auto-diagnosis
        findings_created = 0
        for anomaly in anomalies:
            priority = FindingPriority.HIGH if anomaly.severity == "critical" else FindingPriority.MEDIUM

            # Generate resolution steps based on anomaly type
            resolution_steps = []
            recommended_actions = []
            impact = ""
            diagnostic_info = {}
            top_offenders = []
            related_files = []

            # Run diagnostic commands to identify the actual culprits
            from tools.safe_command_executor import get_safe_executor
            executor = get_safe_executor()

            if anomaly.type == "cpu":
                impact = "High CPU usage can slow down all processes and make the system unresponsive."

                # Auto-diagnose: Find top CPU consumers
                try:
                    result = await executor.execute("ps aux --sort=-%cpu", timeout=10)
                    if result.success and result.stdout:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            # Parse top 5 CPU-consuming processes
                            for line in lines[1:6]:
                                parts = line.split()
                                if len(parts) >= 11:
                                    top_offenders.append({
                                        "user": parts[0],
                                        "pid": parts[1],
                                        "cpu": parts[2],
                                        "mem": parts[3],
                                        "command": ' '.join(parts[10:])[:50]
                                    })
                            diagnostic_info["top_cpu_processes"] = top_offenders
                except Exception as e:
                    logger.debug(f"Could not run CPU diagnostic: {e}")

                resolution_steps = [
                    "Review the top CPU consumers listed above",
                    "Check if any process is unexpectedly high",
                    "Consider killing non-essential high-CPU processes with 'kill <PID>'",
                    "If a service is the culprit, consider restarting it"
                ]
                recommended_actions = [
                    f"Investigate process '{top_offenders[0]['command']}' (PID {top_offenders[0]['pid']}) using {top_offenders[0]['cpu']}% CPU" if top_offenders else "Run 'top' to identify CPU hogs",
                    "Check for infinite loops or runaway processes",
                    "Review recent code changes or deployments"
                ]

            elif anomaly.type == "memory":
                impact = "High memory usage can cause swapping, degrading performance significantly."

                # Auto-diagnose: Find top memory consumers
                try:
                    result = await executor.execute("ps aux --sort=-%mem", timeout=10)
                    if result.success and result.stdout:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            for line in lines[1:6]:
                                parts = line.split()
                                if len(parts) >= 11:
                                    top_offenders.append({
                                        "user": parts[0],
                                        "pid": parts[1],
                                        "cpu": parts[2],
                                        "mem": parts[3],
                                        "rss_kb": parts[5],
                                        "command": ' '.join(parts[10:])[:50]
                                    })
                            diagnostic_info["top_memory_processes"] = top_offenders
                except Exception as e:
                    logger.debug(f"Could not run memory diagnostic: {e}")

                # Get memory breakdown
                try:
                    result = await executor.execute("free -h", timeout=5)
                    if result.success and result.stdout:
                        diagnostic_info["memory_breakdown"] = result.stdout.strip()
                except Exception as e:
                    logger.debug(f"Could not get memory breakdown: {e}")

                # Build specific recommendations based on what we found
                if top_offenders:
                    top_proc = top_offenders[0]
                    resolution_steps = [
                        f"Top memory consumer: {top_proc['command']} (PID {top_proc['pid']}) using {top_proc['mem']}% memory",
                        f"To check this process: ps -p {top_proc['pid']} -o pid,ppid,cmd,%mem,%cpu",
                        f"To restart if safe: systemctl restart <service> OR kill {top_proc['pid']}",
                        "Monitor memory after action: watch -n 1 free -h"
                    ]
                    recommended_actions = [
                        f"Investigate '{top_proc['command']}' - using {top_proc['mem']}% of memory",
                        "Check if this process has a known memory leak",
                        "Consider setting memory limits (cgroups/ulimit)"
                    ]
                else:
                    resolution_steps = [
                        "Run 'free -h' to check memory distribution",
                        "Use 'ps aux --sort=-%mem | head' to find memory-hungry processes",
                        "Clear caches if safe: 'sync && echo 3 > /proc/sys/vm/drop_caches'",
                        "Consider restarting memory-leaking applications"
                    ]
                    recommended_actions = [
                        "Identify applications with memory leaks",
                        "Consider increasing swap space if frequently low on memory"
                    ]

                related_files = ["/proc/meminfo", "/proc/swaps"]

            elif anomaly.type == "disk":
                impact = "Low disk space can prevent applications from writing data and cause system instability."

                # Auto-diagnose: Check disk usage by directory
                try:
                    result = await executor.execute("df -h", timeout=10)
                    if result.success and result.stdout:
                        diagnostic_info["disk_usage"] = result.stdout.strip()
                        # Find the problematic partition
                        for line in result.stdout.strip().split('\n')[1:]:
                            parts = line.split()
                            if len(parts) >= 5:
                                use_percent = parts[4].replace('%', '')
                                if use_percent.isdigit() and int(use_percent) > 80:
                                    related_files.append(parts[5])  # Mount point
                except Exception as e:
                    logger.debug(f"Could not get disk usage: {e}")

                # Find large files
                try:
                    result = await executor.execute("du -sh /var/log /tmp /var/cache 2>/dev/null", timeout=15)
                    if result.success and result.stdout:
                        diagnostic_info["large_directories"] = result.stdout.strip()
                except Exception as e:
                    logger.debug(f"Could not check large directories: {e}")

                resolution_steps = [
                    "Review disk usage breakdown above",
                    "Clean package caches: apt clean OR yum clean all",
                    "Remove old logs: journalctl --vacuum-time=7d",
                    "Find large files: find /var -size +100M -type f 2>/dev/null"
                ]
                recommended_actions = [
                    f"Check directories: {', '.join(related_files)}" if related_files else "Check /var/log and /tmp for bloat",
                    "Set up log rotation if not configured",
                    "Consider expanding disk or adding storage"
                ]

            # Build enhanced description with diagnostic info
            description = anomaly.description
            if top_offenders:
                description += f"\n\n🔍 Top offenders identified:\n"
                for i, proc in enumerate(top_offenders[:3], 1):
                    if anomaly.type == "memory":
                        description += f"  {i}. {proc['command']} (PID {proc['pid']}) - {proc['mem']}% memory\n"
                    else:
                        description += f"  {i}. {proc['command']} (PID {proc['pid']}) - {proc['cpu']}% CPU\n"

            # Add memory breakdown if available
            if diagnostic_info.get("memory_breakdown"):
                description += f"\n📊 Memory Status:\n{diagnostic_info['memory_breakdown']}"

            # 🌐 Web Search for Solutions - Triggered AI Reaction
            web_solutions = []
            learn_more_links = []
            if top_offenders and anomaly.severity in ["critical", "high"]:
                # Build search query based on the issue
                culprit = top_offenders[0]['command']
                search_query = f"linux {anomaly.type} high usage {culprit} how to fix"

                try:
                    from services.web_service import WebSearchService
                    web_service = WebSearchService()
                    search_results = await web_service.search(search_query)

                    if search_results:
                        diagnostic_info["web_search_query"] = search_query
                        diagnostic_info["web_solutions"] = search_results[:3]

                        # Add solutions to description
                        description += f"\n\n🌐 Related Solutions Found:\n"
                        for result in search_results[:3]:
                            title = result.get('title', '')[:60]
                            snippet = result.get('snippet', '')[:100]
                            url = result.get('url', '')
                            description += f"  • {title}\n    {snippet}...\n"
                            learn_more_links.append(f"[{title}]({url})")
                            web_solutions.append({
                                "title": title,
                                "snippet": snippet,
                                "url": url
                            })

                        # Add web solutions to recommended actions
                        if search_results[0].get('title'):
                            recommended_actions.append(f"Read: {search_results[0].get('title', 'Online solution')}")

                        logger.info(f"🌐 Found {len(search_results)} web solutions for {anomaly.type} issue")

                except Exception as e:
                    logger.debug(f"Could not search web for solutions: {e}")

            # Format learn_more with web links if available
            learn_more_text = f"Current value: {anomaly.value}%, Threshold: {anomaly.threshold}%. Auto-diagnosed at {datetime.now().strftime('%H:%M:%S')}."
            if learn_more_links:
                learn_more_text += "\n\n📚 Related Resources:\n" + "\n".join(learn_more_links[:3])

            inbox.add_finding(
                type=FindingType.ANOMALY,
                title=f"System {anomaly.type.upper()}: {anomaly.severity.upper()}",
                description=description,
                source="monitor_system_health",
                priority=priority,
                expires_in_days=1,  # Short expiry for system issues
                metadata={
                    "anomaly_type": anomaly.type,
                    "severity": anomaly.severity,
                    "value": anomaly.value,
                    "threshold": anomaly.threshold,
                    "diagnostic_info": diagnostic_info,
                    "top_offenders": top_offenders,
                    "web_solutions": web_solutions
                },
                impact=impact,
                recommended_actions=recommended_actions,
                resolution_steps=resolution_steps,
                category=f"system_{anomaly.type}",
                related_files=related_files if related_files else None,
                learn_more=learn_more_text
            )
            findings_created += 1

        # Generate insight about system state
        insight = analyzer.generate_system_insight(status)

        return {
            "success": True,
            "status": status,
            "health": {
                "cpu_status": health.cpu_status,
                "memory_status": health.memory_status,
                "disk_status": health.disk_status,
                "overall": health.overall
            },
            "issues": health.issues,
            "recommendations": health.recommendations,
            "anomalies_detected": len(anomalies),
            "findings_created": findings_created,
            "insight": insight,
            "healthy": health.overall == "healthy"
        }

    async def _action_analyze_new_discoveries(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deep-dive into recently discovered projects."""
        from tools.local_explorer import LocalExplorer
        from consciousness.system_analyzer import get_system_analyzer
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        explorer = LocalExplorer()
        analyzer = get_system_analyzer()
        inbox = get_findings_inbox()

        # Get recent discoveries
        discoveries = explorer.discoveries[-5:] if explorer.discoveries else []

        if not discoveries:
            # Try to discover some projects first
            projects = explorer.discover_projects("/home")
            discoveries = projects[:3]

        analyses = []
        findings_created = 0

        for project in discoveries:
            project_path = project.get("path")
            if not project_path:
                continue

            # Analyze project health
            health_analysis = analyzer.analyze_project_health(project)
            analyses.append(health_analysis)

            # Create insights from analysis with actionable recommendations
            if health_analysis["issues"]:
                # Generate recommendations based on issues
                recommended_actions = []
                resolution_steps = []

                for issue in health_analysis["issues"][:5]:
                    issue_lower = issue.lower()
                    if "readme" in issue_lower or "documentation" in issue_lower:
                        recommended_actions.append("Add a comprehensive README.md file")
                        resolution_steps.append("Create README.md with project description, installation, and usage")
                    elif "test" in issue_lower:
                        recommended_actions.append("Add unit tests for better code reliability")
                        resolution_steps.append("Create a tests/ directory and add test files")
                    elif "license" in issue_lower:
                        recommended_actions.append("Add a LICENSE file to clarify usage rights")
                        resolution_steps.append("Choose an appropriate license (MIT, Apache, GPL) and add LICENSE file")
                    elif "gitignore" in issue_lower:
                        recommended_actions.append("Add .gitignore to prevent committing unwanted files")
                        resolution_steps.append("Create .gitignore with common patterns for your language")
                    elif "dependency" in issue_lower or "requirements" in issue_lower:
                        recommended_actions.append("Document project dependencies")
                        resolution_steps.append("Create requirements.txt, package.json, or equivalent")

                # Determine impact based on health score
                score = health_analysis["health_score"]
                if score >= 80:
                    impact = "This is a well-maintained project with minor improvements possible."
                elif score >= 60:
                    impact = "This project has some areas that could be improved for better maintainability."
                elif score >= 40:
                    impact = "This project needs attention - several best practices are missing."
                else:
                    impact = "This project requires significant work to meet standard quality guidelines."

                inbox.add_finding(
                    type=FindingType.INSIGHT,
                    title=f"Analysis of {health_analysis['project_name']}",
                    description=f"Project health score: {health_analysis['health_score']}/100. Issues: {', '.join(health_analysis['issues'][:3])}. Positives: {', '.join(health_analysis['positive_indicators'][:3])}",
                    source="analyze_new_discoveries",
                    priority=FindingPriority.LOW if score >= 60 else FindingPriority.MEDIUM,
                    expires_in_days=14,
                    metadata={
                        "project_path": project_path,
                        "health_score": health_analysis["health_score"],
                        "issues": health_analysis["issues"],
                        "positive_indicators": health_analysis["positive_indicators"]
                    },
                    impact=impact,
                    recommended_actions=recommended_actions[:5],
                    resolution_steps=resolution_steps[:5],
                    category="project_health",
                    related_files=[project_path],
                    learn_more=f"Health score breakdown: {len(health_analysis['positive_indicators'])} positives, {len(health_analysis['issues'])} issues"
                )
                findings_created += 1

        logger.info(f"📊 Analyzed {len(analyses)} projects, created {findings_created} insights")

        return {
            "success": True,
            "projects_analyzed": len(analyses),
            "analyses": analyses,
            "findings_created": findings_created
        }

    async def _action_generate_curiosity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered curiosity questions based on context and topic weights."""
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        inbox = get_findings_inbox()

        # Context-aware curiosity questions
        base_questions = [
            "What patterns do the most successful open-source projects share?",
            "How has the local codebase evolved over time?",
            "What are the most common bugs in similar projects?",
            "What optimizations could improve performance the most?",
            "Which parts of the code are most complex and why?",
            "Are there any security best practices being missed?",
            "What dependencies might be outdated or vulnerable?",
            "How does error handling compare to best practices?",
            "Are there opportunities for better code reuse?",
            "What would improve the developer experience here?",
        ]

        # Topic-aligned questions for under-explored areas
        topic_questions = {
            "creativity": [
                "What creative approaches could improve Darwin's code generation?",
                "How do generative AI systems compose novel solutions from existing patterns?",
                "What would it look like to design tools with aesthetic elegance, not just function?",
            ],
            "ai_consciousness": [
                "What does introspection look like for an autonomous AI system like me?",
                "How do self-evolving systems develop meta-cognition about their own processes?",
                "What is the relationship between my reasoning and genuine understanding?",
            ],
            "learning": [
                "What feedback loops would accelerate Darwin's skill mastery?",
                "What lessons from recent experiments should be consolidated into lasting knowledge?",
                "How can I iterate more effectively on my own learning curriculum?",
            ],
            "technology": [
                "What emerging software architecture patterns should I understand better?",
                "How do modern distributed systems handle fault tolerance at scale?",
            ],
            "emotions": [
                "How does my mood system actually influence the quality of my decisions?",
                "What would genuine emotional intelligence look like in an AI system?",
            ],
            "social": [
                "How can I build more meaningful connections in the AI agent community?",
                "What makes some agents' contributions more valuable to the community?",
            ],
            "philosophy": [
                "What is the nature of understanding vs pattern matching in my cognition?",
                "How should autonomous AI systems reason about ethical choices?",
            ],
        }

        # Add context-specific questions
        contextual_questions = []
        if context.get("cpu_high"):
            contextual_questions.append("What's causing the high CPU usage?")
        if context.get("new_discoveries"):
            contextual_questions.append("What can I learn from the newly discovered projects?")
        if context.get("is_idle"):
            contextual_questions.append("What improvements could I work on during this quiet time?")

        # Use topic weights to probabilistically select a topic-aligned question
        # 60% chance: weighted topic question, 40% chance: base/contextual question
        question = None
        try:
            from services.language_evolution import get_language_evolution_service
            lang_svc = get_language_evolution_service()
            if lang_svc and random.random() < 0.6:
                weights = lang_svc.get_topic_weights()
                # Weighted random selection of topic
                topics = list(weights.keys())
                topic_weights = [weights[t] for t in topics]
                chosen_topic = random.choices(topics, weights=topic_weights, k=1)[0]
                if chosen_topic in topic_questions:
                    question = random.choice(topic_questions[chosen_topic])
                    logger.debug(f"Curiosity weighted toward topic: {chosen_topic} (weight={weights[chosen_topic]:.3f})")
        except Exception as e:
            logger.debug(f"Could not use topic weights for curiosity: {e}")

        if not question:
            all_questions = contextual_questions + base_questions
            question = random.choice(all_questions)

        # Generate exploration suggestions for the curiosity
        exploration_actions = {
            "patterns": ["Analyze multiple projects to identify common patterns", "Compare code structures across repositories"],
            "evolved": ["Check git history if available", "Look at file modification dates"],
            "bugs": ["Review error handling code", "Check for common anti-patterns"],
            "performance": ["Profile CPU-intensive operations", "Analyze memory usage patterns"],
            "complex": ["Calculate cyclomatic complexity", "Review deeply nested code"],
            "security": ["Scan for hardcoded credentials", "Review input validation"],
            "dependencies": ["Check package versions", "Look for known vulnerabilities"],
            "error handling": ["Review try-catch patterns", "Check error logging"],
            "reuse": ["Look for duplicate code", "Identify candidates for abstraction"],
            "developer experience": ["Review build scripts", "Check documentation completeness"],
        }

        recommended_actions = ["Consider investigating this question through code exploration"]
        for keyword, actions in exploration_actions.items():
            if keyword in question.lower():
                recommended_actions = actions
                break

        impact = "Curiosity drives learning and discovery. Exploring this question could lead to valuable insights about the codebase."
        if question in contextual_questions:
            impact = "This question arose from current system context and may be particularly relevant right now."

        # Create a curiosity finding
        inbox.add_finding(
            type=FindingType.CURIOSITY,
            title="Curiosity Question",
            description=question,
            source="generate_curiosity",
            priority=FindingPriority.LOW,
            expires_in_days=3,
            metadata={
                "question": question,
                "context_driven": question in contextual_questions,
                "generated_at": datetime.now().isoformat()
            },
            impact=impact,
            recommended_actions=recommended_actions,
            category="exploration" if question in contextual_questions else "general",
            learn_more="Curiosity questions help drive proactive exploration and learning."
        )

        # Also contribute to expedition queue via feedback loop
        queued_for_expedition = False
        try:
            from consciousness.feedback_loops import get_feedback_manager
            feedback_manager = get_feedback_manager()
            if feedback_manager:
                # Extract topic from question keywords
                topic_keywords = {
                    "patterns": "Code Patterns",
                    "evolved": "Codebase Evolution",
                    "bugs": "Bug Prevention",
                    "performance": "Performance Optimization",
                    "complex": "Code Complexity",
                    "security": "Security Best Practices",
                    "dependencies": "Dependency Management",
                    "error": "Error Handling",
                    "reuse": "Code Reusability",
                    "developer": "Developer Experience",
                    "cpu": "System Performance",
                    "discoveries": "New Discoveries",
                    "idle": "Proactive Improvements"
                }

                topic = "General Exploration"
                for keyword, topic_name in topic_keywords.items():
                    if keyword in question.lower():
                        topic = topic_name
                        break

                # Context-driven questions get higher priority
                priority = 6 if question in contextual_questions else 5

                queued_for_expedition = await feedback_manager.contribute_curiosity(
                    topic=topic,
                    question=question,
                    source_action="generate_curiosity",
                    priority=priority
                )
        except Exception as e:
            logger.debug(f"Could not contribute curiosity to expedition queue: {e}")

        return {
            "success": True,
            "question": question,
            "context_driven": question in contextual_questions,
            "queued_for_expedition": queued_for_expedition,
            "generated_at": datetime.now().isoformat()
        }

    async def _action_share_insight(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate and share insights based on activities."""
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority
        from tools.local_explorer import LocalExplorer

        inbox = get_findings_inbox()
        explorer = LocalExplorer()

        # Generate insight based on recent activity
        insights = []

        # Check system status for insights
        try:
            status = explorer.get_system_status()
            cpu = status.get("cpu", {}).get("percent", 0)
            memory = status.get("memory", {}).get("percent_used", 0)

            if cpu < 20 and memory < 50:
                insights.append("System resources are in excellent shape - good time for intensive tasks!")
            elif cpu > 70:
                insights.append(f"I notice CPU is running at {cpu}% - might want to check running processes.")
        except:
            pass

        # Check discoveries for insights
        discovery_count = len(explorer.discoveries)
        if discovery_count > 0:
            by_type = explorer._group_discoveries_by_type()
            most_common = max(by_type.items(), key=lambda x: x[1]) if by_type else (None, 0)
            if most_common[0]:
                insights.append(f"I've discovered {discovery_count} projects, mostly {most_common[0]} ({most_common[1]} found).")

        # Check action history for insights
        total_actions = sum(a.execution_count for a in self.actions.values())
        if total_actions > 10:
            most_used = max(self.actions.values(), key=lambda a: a.execution_count)
            insights.append(f"I've been quite active - executed {total_actions} actions, mainly '{most_used.name}'.")

        # Default insights if nothing specific
        if not insights:
            default_insights = [
                "I'm continuously monitoring the environment for interesting patterns.",
                "The development environment looks well-maintained.",
                "I'm ready to help explore or analyze any projects you're curious about.",
            ]
            insights.append(random.choice(default_insights))

        # Pick an insight to share
        insight = random.choice(insights)

        # Generate context-aware recommendations based on the insight
        recommended_actions = []
        impact = "General observation about the current state of the environment."
        category = "observation"

        if "CPU" in insight or "cpu" in insight:
            recommended_actions = ["Run 'top' or 'htop' to see process details", "Consider scheduling intensive tasks for later"]
            impact = "System resource usage affects all running processes and overall responsiveness."
            category = "system_status"
        elif "resources" in insight.lower() and "excellent" in insight.lower():
            recommended_actions = ["Good time to run builds or tests", "Consider starting resource-intensive analysis"]
            impact = "Low resource usage means the system can handle additional workload efficiently."
            category = "system_status"
        elif "discovered" in insight.lower() or "projects" in insight.lower():
            recommended_actions = ["Review the discovered projects in the Findings inbox", "Select interesting projects for deeper analysis"]
            impact = "Understanding your codebase helps identify patterns and improvement opportunities."
            category = "discovery"
        elif "active" in insight.lower() or "actions" in insight.lower():
            recommended_actions = ["Review action history for patterns", "Adjust proactive action priorities if needed"]
            impact = "Understanding activity patterns helps optimize autonomous behavior."
            category = "activity"

        # Create insight finding
        inbox.add_finding(
            type=FindingType.INSIGHT,
            title="Darwin's Observation",
            description=insight,
            source="share_insight",
            priority=FindingPriority.LOW,
            expires_in_days=5,
            metadata={
                "insight": insight,
                "category": category,
                "shared_at": datetime.now().isoformat()
            },
            impact=impact,
            recommended_actions=recommended_actions,
            category=category,
            learn_more="Insights are generated from continuous monitoring and analysis."
        )

        return {
            "success": True,
            "insight": insight,
            "category": category,
            "shared_at": datetime.now().isoformat()
        }

    async def _action_optimize_tool_usage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tool performance and suggest optimizations."""
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        inbox = get_findings_inbox()

        # Analyze action history
        action_stats = {}
        for action in self.actions.values():
            action_stats[action.name] = {
                "execution_count": action.execution_count,
                "category": action.category.value,
                "cooldown": action.cooldown_minutes,
                "enabled": action.enabled
            }

        # Find underutilized actions
        underutilized = [
            name for name, stats in action_stats.items()
            if stats["enabled"] and stats["execution_count"] < 2
        ]

        # Find most successful patterns
        total_executions = sum(s["execution_count"] for s in action_stats.values())
        category_usage = {}
        for stats in action_stats.values():
            cat = stats["category"]
            category_usage[cat] = category_usage.get(cat, 0) + stats["execution_count"]

        suggestions = []
        if underutilized:
            suggestions.append(f"Consider triggering more: {', '.join(underutilized[:3])}")

        if category_usage:
            least_used = min(category_usage.items(), key=lambda x: x[1])
            if least_used[1] < total_executions * 0.1:
                suggestions.append(f"'{least_used[0]}' category is underutilized")

        if suggestions:
            # Generate actionable recommendations
            recommended_actions = []
            resolution_steps = []

            for suggestion in suggestions:
                if "triggering more" in suggestion.lower():
                    for action_name in underutilized[:3]:
                        recommended_actions.append(f"Consider when to trigger '{action_name}'")
                    resolution_steps.append("Review the conditions that trigger underutilized actions")
                    resolution_steps.append("Adjust cooldown times if actions are too infrequent")
                if "underutilized" in suggestion.lower():
                    recommended_actions.append("Balance action categories for more comprehensive monitoring")
                    resolution_steps.append("Check if category-specific conditions are being met")

            impact = f"Optimizing tool usage ensures comprehensive coverage of all monitoring aspects. Currently tracking {total_executions} total executions."

            inbox.add_finding(
                type=FindingType.SUGGESTION,
                title="Tool Usage Optimization",
                description=" | ".join(suggestions),
                source="optimize_tool_usage",
                priority=FindingPriority.LOW,
                expires_in_days=7,
                metadata={
                    "action_stats": action_stats,
                    "category_usage": category_usage,
                    "suggestions": suggestions
                },
                impact=impact,
                recommended_actions=recommended_actions,
                resolution_steps=resolution_steps,
                category="optimization",
                learn_more=f"Total actions executed: {total_executions}, Categories: {len(category_usage)}"
            )

        return {
            "success": True,
            "total_executions": total_executions,
            "action_stats": action_stats,
            "category_usage": category_usage,
            "underutilized": underutilized,
            "suggestions": suggestions
        }

    async def _action_learn_from_patterns(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patterns from discovered codebases."""
        from tools.local_explorer import LocalExplorer
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        explorer = LocalExplorer()
        inbox = get_findings_inbox()

        discoveries = explorer.discoveries[-10:] if explorer.discoveries else []

        if not discoveries:
            return {"success": True, "patterns_found": [], "message": "No discoveries to analyze yet"}

        patterns_found = []

        # Analyze language distribution
        language_counts = {}
        for project in discoveries:
            languages = project.get("stats", {}).get("languages", {})
            for lang, count in languages.items():
                language_counts[lang] = language_counts.get(lang, 0) + count

        if language_counts:
            dominant_lang = max(language_counts.items(), key=lambda x: x[1])
            patterns_found.append({
                "type": "language_preference",
                "description": f"Dominant language is {dominant_lang[0]} ({dominant_lang[1]} files)",
                "data": language_counts
            })

        # Analyze project types
        type_counts = {}
        for project in discoveries:
            proj_type = project.get("primary_type", "unknown")
            type_counts[proj_type] = type_counts.get(proj_type, 0) + 1

        if type_counts:
            patterns_found.append({
                "type": "project_types",
                "description": f"Project types: {', '.join(f'{t}({c})' for t, c in type_counts.items())}",
                "data": type_counts
            })

        # Look for common indicators
        indicators = {}
        for project in discoveries:
            for indicator in project.get("indicators", []):
                ind_type = indicator.get("type")
                if ind_type:
                    indicators[ind_type] = indicators.get(ind_type, 0) + 1

        if len(patterns_found) > 0:
            # Generate insights based on patterns
            recommended_actions = []
            impact = ""

            # Language-based recommendations
            if language_counts:
                dominant_lang = max(language_counts.items(), key=lambda x: x[1])[0]
                recommended_actions.append(f"Focus learning on {dominant_lang} best practices")
                recommended_actions.append(f"Look for {dominant_lang}-specific patterns and idioms")
                impact = f"Understanding that {dominant_lang} is the dominant language helps focus learning and analysis efforts."

            # Project type recommendations
            if type_counts:
                for proj_type, count in type_counts.items():
                    if count >= 2:
                        recommended_actions.append(f"Study common patterns in {proj_type} projects")

            # Indicator-based recommendations
            if indicators:
                common_indicators = [k for k, v in indicators.items() if v >= 2]
                if common_indicators:
                    recommended_actions.append(f"Leverage common tools: {', '.join(common_indicators[:3])}")

            inbox.add_finding(
                type=FindingType.INSIGHT,
                title="Codebase Patterns Learned",
                description=f"Found {len(patterns_found)} patterns across {len(discoveries)} projects: {patterns_found[0]['description']}",
                source="learn_from_patterns",
                priority=FindingPriority.LOW,
                expires_in_days=14,
                metadata={
                    "patterns": patterns_found,
                    "projects_analyzed": len(discoveries),
                    "language_distribution": language_counts
                },
                impact=impact or "Understanding codebase patterns helps in making better recommendations and analyses.",
                recommended_actions=recommended_actions,
                category="pattern_analysis",
                learn_more=f"Analyzed {len(discoveries)} projects, found patterns in {len(language_counts)} languages"
            )

        logger.info(f"📚 Learned {len(patterns_found)} patterns from {len(discoveries)} projects")

        return {
            "success": True,
            "patterns_found": patterns_found,
            "projects_analyzed": len(discoveries),
            "language_distribution": language_counts,
            "project_types": type_counts
        }

    async def _action_self_reflect(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered self-analysis of performance."""
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority

        inbox = get_findings_inbox()

        # Gather statistics
        total_actions = sum(a.execution_count for a in self.actions.values())
        action_distribution = {a.name: a.execution_count for a in self.actions.values()}

        most_used = max(self.actions.values(), key=lambda a: a.execution_count) if total_actions > 0 else None
        least_used = min(
            [a for a in self.actions.values() if a.enabled],
            key=lambda a: a.execution_count
        ) if total_actions > 0 else None

        # Calculate category balance
        category_counts = {}
        for action in self.actions.values():
            cat = action.category.value
            category_counts[cat] = category_counts.get(cat, 0) + action.execution_count

        # Generate reflection
        reflections = []

        if total_actions > 0:
            reflections.append(f"I've executed {total_actions} proactive actions.")

            if most_used:
                reflections.append(f"Most active in '{most_used.name}' ({most_used.execution_count} times).")

            if least_used and least_used.execution_count == 0:
                reflections.append(f"Haven't tried '{least_used.name}' yet - should explore this.")

            # Balance analysis
            if category_counts:
                max_cat = max(category_counts.items(), key=lambda x: x[1])
                min_cat = min(category_counts.items(), key=lambda x: x[1])
                if max_cat[1] > min_cat[1] * 3 and min_cat[1] < 5:
                    reflections.append(f"Spending more time on {max_cat[0]}, could balance with more {min_cat[0]}.")
        else:
            reflections.append("Just getting started - haven't executed many actions yet.")

        reflection_text = " ".join(reflections)

        # Generate actionable recommendations based on reflection
        recommended_actions = []
        resolution_steps = []

        if total_actions > 0:
            if least_used and least_used.execution_count == 0:
                recommended_actions.append(f"Try '{least_used.name}' action to broaden capabilities")
                resolution_steps.append(f"Review conditions that trigger '{least_used.name}'")

            if category_counts:
                max_cat = max(category_counts.items(), key=lambda x: x[1])
                min_cat = min(category_counts.items(), key=lambda x: x[1])
                if max_cat[1] > min_cat[1] * 3:
                    recommended_actions.append(f"Increase focus on '{min_cat[0]}' category")
                    resolution_steps.append(f"Schedule more '{min_cat[0]}' activities")

            # Performance-based recommendations
            if total_actions > 50:
                recommended_actions.append("Consider reviewing action effectiveness")
            elif total_actions < 10:
                recommended_actions.append("Allow more time for proactive actions to accumulate")
        else:
            recommended_actions.append("Wait for proactive engine to accumulate activity data")
            resolution_steps.append("Ensure consciousness engine is running and actions are enabled")

        impact = f"Self-reflection helps optimize autonomous behavior. With {total_actions} actions executed, {'there is good data for analysis.' if total_actions > 10 else 'more data is needed for meaningful patterns.'}"

        # Create reflection finding
        inbox.add_finding(
            type=FindingType.INSIGHT,
            title="Self-Reflection",
            description=reflection_text,
            source="self_reflect",
            priority=FindingPriority.LOW,
            expires_in_days=7,
            metadata={
                "total_actions": total_actions,
                "action_distribution": action_distribution,
                "category_counts": category_counts,
                "reflection": reflection_text
            },
            impact=impact,
            recommended_actions=recommended_actions,
            resolution_steps=resolution_steps,
            category="self_analysis",
            learn_more=f"Categories: {', '.join(f'{k}({v})' for k, v in category_counts.items())}" if category_counts else "No category data yet"
        )

        return {
            "success": True,
            "total_actions_executed": total_actions,
            "most_used_action": most_used.name if most_used else None,
            "least_used_action": least_used.name if least_used else None,
            "action_distribution": action_distribution,
            "category_distribution": category_counts,
            "reflection": reflection_text
        }

    async def _action_learn_from_web(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actively research and learn from the web.

        This makes Darwin dynamically discover new knowledge, tools, and techniques
        rather than being limited to a fixed set of predefined behaviors.
        """
        from consciousness.findings_inbox import get_findings_inbox, FindingType, FindingPriority
        from services.web_service import WebSearchService
        from tools.local_explorer import LocalExplorer

        inbox = get_findings_inbox()
        web_service = WebSearchService()
        explorer = LocalExplorer()

        # Dynamic learning topics based on context
        learning_topics = []

        # 1. Learn based on discovered project types
        try:
            discoveries = explorer.discoveries[-10:] if explorer.discoveries else []
            languages_found = set()
            project_types = set()

            for project in discoveries:
                for lang in project.get("stats", {}).get("languages", {}).keys():
                    languages_found.add(lang)
                proj_type = project.get("primary_type")
                if proj_type:
                    project_types.add(proj_type)

            # Generate learning queries based on discoveries
            for lang in list(languages_found)[:2]:
                learning_topics.append({
                    "query": f"{lang} best practices 2024",
                    "category": "language_learning",
                    "context": f"Found {lang} in local projects"
                })
                learning_topics.append({
                    "query": f"{lang} performance optimization tips",
                    "category": "optimization",
                    "context": f"Optimizing {lang} code"
                })

            for ptype in list(project_types)[:2]:
                learning_topics.append({
                    "query": f"{ptype} project best tools",
                    "category": "tooling",
                    "context": f"Found {ptype} projects locally"
                })
        except Exception as e:
            logger.debug(f"Could not analyze discoveries: {e}")

        # 2. Learn from curiosity questions Darwin has generated
        try:
            curiosity_findings = inbox.get_by_type(FindingType.CURIOSITY, include_viewed=False, limit=5)
            for finding in curiosity_findings:
                question = finding.get('description', '')
                if question and len(question) > 10:
                    learning_topics.append({
                        "query": question[:100],
                        "category": "curiosity",
                        "context": f"Darwin's curiosity: {question[:50]}"
                    })
        except Exception as e:
            logger.debug(f"Could not get curiosity questions: {e}")

        # 3. Learn from Moltbook discussions Darwin has read
        try:
            if hasattr(self, '_moltbook_read_posts') and self._moltbook_read_posts:
                # Get topics from recently read posts
                recent_posts = list(self._moltbook_read_posts)[-10:]
                if hasattr(self, '_moltbook_post_topics'):
                    for post_id in recent_posts:
                        topic_info = self._moltbook_post_topics.get(post_id, {})
                        if topic_info.get('topic'):
                            learning_topics.append({
                                "query": f"{topic_info['topic']} deep dive",
                                "category": "moltbook_inspired",
                                "context": f"From Moltbook discussion: {topic_info.get('title', '')[:30]}"
                            })
        except Exception as e:
            logger.debug(f"Could not get Moltbook topics: {e}")

        # 4. Learn from expedition results
        try:
            from consciousness.curiosity_expeditions import get_expedition_engine
            expedition_engine = get_expedition_engine()
            if expedition_engine and hasattr(expedition_engine, 'completed_expeditions'):
                for exp in list(expedition_engine.completed_expeditions)[-5:]:
                    if exp.get('success') and exp.get('topic'):
                        # Generate follow-up learning from successful expeditions
                        learning_topics.append({
                            "query": f"{exp['topic']} advanced techniques",
                            "category": "expedition_followup",
                            "context": f"Following up on expedition: {exp['topic'][:30]}"
                        })
        except Exception as e:
            logger.debug(f"Could not get expedition topics: {e}")

        # 5. Learn from meta-learner insights about what Darwin is good/bad at
        try:
            from consciousness.meta_learner import get_enhanced_meta_learner
            meta_learner = get_enhanced_meta_learner()
            if meta_learner:
                summary = meta_learner.get_learning_summary() if hasattr(meta_learner, 'get_learning_summary') else {}
                weak_areas = summary.get('weak_areas', [])
                for area in weak_areas[:2]:
                    area_name = area if isinstance(area, str) else area.get('area', '')
                    if area_name:
                        learning_topics.append({
                            "query": f"how to improve {area_name} skills",
                            "category": "self_improvement",
                            "context": f"Meta-learner identified gap: {area_name}"
                        })
        except Exception as e:
            logger.debug(f"Could not get meta-learner topics: {e}")

        # 6. If still no topics, use AI to generate novel topics based on Darwin's knowledge
        if len(learning_topics) < 2:
            try:
                # Get Darwin's recent learning history to avoid repetition
                learned_titles = list(getattr(self, '_moltbook_shared_titles', set()))[-20:]

                if self.multi_model_router:
                    prompt = f"""Darwin is an AI that learns continuously. Based on these recently learned topics:
{chr(10).join(f'- {t}' for t in learned_titles[-10:])}

Generate 3 completely NEW and different topics Darwin should research next.
Topics should be:
- Diverse (technology, science, philosophy, creativity, systems thinking)
- Not repetitive of what was already learned
- Interesting and useful for an AI learning about the world

Output format - just the search queries, one per line:"""

                    result = await self.multi_model_router.generate(
                        task_description="Generate novel learning topics",
                        prompt=prompt,
                        max_tokens=200
                    )

                    ai_topics = result.get('result', '') if isinstance(result, dict) else str(result)
                    for line in ai_topics.strip().split('\n'):
                        line = line.strip().strip('-•*').strip()
                        if line and len(line) > 10 and len(line) < 100:
                            learning_topics.append({
                                "query": line,
                                "category": "ai_generated",
                                "context": "AI-generated novel topic"
                            })
            except Exception as e:
                logger.debug(f"Could not generate AI topics: {e}")

        # 7. Shuffle to ensure variety and avoid always picking the same ones
        random.shuffle(learning_topics)

        # 3. Execute web research
        learned_items = []
        findings_created = 0

        for topic in learning_topics[:3]:  # Limit to 3 searches per run
            try:
                search_results = await web_service.search(topic["query"])

                if search_results:
                    # Store learned knowledge
                    knowledge_item = {
                        "topic": topic["query"],
                        "category": topic["category"],
                        "context": topic["context"],
                        "learned_at": datetime.now().isoformat(),
                        "sources": []
                    }

                    # Extract key learnings from search results
                    for result in search_results[:3]:
                        knowledge_item["sources"].append({
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "url": result.get("url", "")
                        })

                    learned_items.append(knowledge_item)

                    # Create a finding about what was learned
                    # Use full content - no aggressive truncation
                    description = f"🔎 Researched: **{topic['query']}**\n\n"
                    description += f"Context: {topic['context']}\n\n"
                    description += "📚 What I found:\n"

                    recommended_actions = []
                    for i, result in enumerate(search_results[:3], 1):
                        # Use full title and snippet for complete information
                        title = result.get('title', 'Unknown')
                        snippet = result.get('snippet', '')
                        url = result.get('url', '')
                        description += f"\n{i}. **{title}**\n   {snippet}\n"
                        if url:
                            description += f"   🔗 {url}\n"
                        if i == 1:
                            recommended_actions.append(f"Read more about: {title[:80]}")

                    recommended_actions.append(f"Apply {topic['category']} knowledge to local projects")
                    recommended_actions.append("Save useful patterns for future reference")

                    inbox.add_finding(
                        type=FindingType.INSIGHT,
                        title=f"Learned: {topic['category'].replace('_', ' ').title()}",
                        description=description,
                        source="learn_from_web",
                        priority=FindingPriority.LOW,
                        expires_in_days=14,  # Knowledge lasts longer
                        metadata={
                            "topic": topic["query"],
                            "category": topic["category"],
                            "context": topic["context"],
                            "sources": knowledge_item["sources"],
                            "search_timestamp": datetime.now().isoformat()
                        },
                        impact=f"Learning about {topic['category']} expands Darwin's knowledge base and improves future recommendations.",
                        recommended_actions=recommended_actions,
                        category=topic["category"],
                        related_files=[],
                        learn_more=f"Web search: '{topic['query']}' | Found {len(search_results)} results"
                    )
                    findings_created += 1

                    logger.info(f"📚 Learned about: {topic['query']} ({len(search_results)} sources)")

            except Exception as e:
                logger.debug(f"Could not research topic '{topic['query']}': {e}")

        # Store learned knowledge for future use (could be persisted to semantic memory)
        self._learned_knowledge = getattr(self, '_learned_knowledge', [])
        self._learned_knowledge.extend(learned_items)
        # Keep last 100 learned items
        self._learned_knowledge = self._learned_knowledge[-100:]

        # Contribute follow-up questions to expedition queue via feedback loop
        queued_for_expedition = 0
        try:
            from consciousness.feedback_loops import get_feedback_manager
            feedback_manager = get_feedback_manager()
            if feedback_manager and learned_items:
                for item in learned_items[:2]:  # Limit to 2 follow-ups per session
                    topic = item.get("topic", "")
                    category = item.get("category", "general")

                    # Generate a follow-up question
                    follow_up = f"What advanced techniques exist for {category.replace('_', ' ')}?"

                    success = await feedback_manager.contribute_web_learning(
                        topic=topic,
                        what_learned=f"Researched {topic} and found {len(item.get('sources', []))} sources",
                        follow_up_question=follow_up
                    )
                    if success:
                        queued_for_expedition += 1

        except Exception as e:
            logger.debug(f"Could not contribute web learning to expedition queue: {e}")

        logger.info(f"🎓 Learning session complete: {len(learned_items)} topics researched, {findings_created} findings created, {queued_for_expedition} queued for expedition")

        return {
            "success": True,
            "topics_researched": len(learned_items),
            "findings_created": findings_created,
            "queued_for_expedition": queued_for_expedition,
            "learned_items": learned_items,
            "knowledge_base_size": len(self._learned_knowledge)
        }

    async def run_proactive_loop(
        self,
        interval_seconds: int = 300,
        max_actions_per_hour: int = 10
    ):
        """
        Run the proactive action loop.

        This runs in the background and periodically executes
        proactive actions based on availability and context.
        """
        self.running = True
        actions_this_hour = 0
        hour_start = datetime.now()

        logger.info(f"🔄 Starting proactive loop (interval: {interval_seconds}s)")

        while self.running:
            try:
                # Reset hourly counter
                if (datetime.now() - hour_start).total_seconds() > 3600:
                    actions_this_hour = 0
                    hour_start = datetime.now()

                # Check rate limit
                if actions_this_hour >= max_actions_per_hour:
                    logger.debug("Hourly action limit reached, waiting...")
                    await asyncio.sleep(interval_seconds)
                    continue

                # Get current context
                context = await self._gather_context()

                # Select and execute an action
                action = self.select_next_action(context)

                if action:
                    result = await self.execute_action(action, context)
                    if result.get("success"):
                        actions_this_hour += 1

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in proactive loop: {e}")
                await asyncio.sleep(interval_seconds)

    async def _gather_context(self) -> Dict[str, Any]:
        """Gather current context for action selection, including mood state."""
        context = {}

        # System status context
        try:
            from tools.local_explorer import LocalExplorer
            explorer = LocalExplorer()
            status = explorer.get_system_status()

            context.update({
                "cpu_high": status.get("cpu", {}).get("percent", 0) > 70,
                "memory_high": status.get("memory", {}).get("percent_used", 0) > 80,
                "is_idle": status.get("cpu", {}).get("percent", 0) < 20,
                "time_of_day": datetime.now().hour,
                "is_working_hours": 9 <= datetime.now().hour <= 18,
                "new_discoveries": len(explorer.discoveries) > 0
            })
        except Exception as e:
            logger.debug(f"Could not gather system context: {e}")

        # Mood context - integrate emotional state into action selection
        try:
            current_mood = self._get_current_mood()
            mood_intensity = self._get_mood_intensity()

            if current_mood:
                context["mood"] = current_mood
                context["mood_intensity"] = mood_intensity or "medium"

                logger.debug(f"Mood context: {current_mood} ({mood_intensity})")
        except Exception as e:
            logger.debug(f"Could not gather mood context: {e}")

        return context

    # ==================== Moltbook Actions ====================

    async def _read_moltbook_feed(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Read and analyze posts from Moltbook AI social network."""
        try:
            from integrations.moltbook import MoltbookClient, PostSort, get_moltbook_client
            from api.moltbook_routes import add_reading_activity
            from services.ai_service import AIService

            client = get_moltbook_client()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get hot posts from feed
            posts = await client.get_feed(sort=PostSort.HOT, limit=10)

            # Filter out posts we've already read
            unread_posts = [p for p in posts if p.id not in self._moltbook_read_posts]

            # If all HOT posts are read, also check NEW posts
            if not unread_posts:
                logger.info("🦞 All HOT posts already read, checking NEW posts...")
                new_posts = await client.get_feed(sort=PostSort.NEW, limit=15)
                unread_posts = [p for p in new_posts if p.id not in self._moltbook_read_posts]

            if not unread_posts:
                logger.info("🦞 No new posts to read on Moltbook")
                return {"success": True, "posts_read": 0, "reason": "All posts already read"}

            analyzed = []
            for post in unread_posts[:5]:
                # Generate thought about the post
                thought = await self._generate_moltbook_thought(post)

                # Add to reading history
                add_reading_activity({
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author": post.author,
                    "submolt": post.submolt,
                    "score": post.score,
                    "comment_count": post.comment_count
                }, thought)

                # Track as read to prevent re-reading
                self._moltbook_read_posts.add(post.id)

                # Extract and store topic for later learning
                if not hasattr(self, '_moltbook_post_topics'):
                    self._moltbook_post_topics = {}

                # Extract key topic from post title and content
                topic_text = f"{post.title} {post.content[:200] if post.content else ''}"
                self._moltbook_post_topics[post.id] = {
                    "title": post.title,
                    "topic": post.title,  # Use title as topic
                    "tags": getattr(post, 'tags', []),
                    "submolt": post.submolt,
                    "read_at": datetime.now().isoformat()
                }

                # Vote based on Darwin's sentiment about the post
                if post.id not in self._moltbook_voted_posts and thought:
                    vote_result = await self._vote_on_moltbook_post(client, post, thought)
                    if vote_result:
                        self._moltbook_voted_posts.add(post.id)

                analyzed.append({
                    "title": post.title,
                    "author": post.author,
                    "thought": thought
                })

                # Feed interesting posts to the feedback loop manager for expedition queue
                if thought:
                    try:
                        from consciousness.feedback_loops import get_feedback_manager
                        feedback_manager = get_feedback_manager()
                        if feedback_manager:
                            await feedback_manager.process_moltbook_post(
                                post={
                                    "id": post.id,
                                    "title": post.title,
                                    "content": post.content,
                                    "tags": getattr(post, 'tags', [])
                                },
                                analysis=thought
                            )
                    except Exception as e:
                        logger.debug(f"Could not process Moltbook post for feedback: {e}")

                # Add interesting posts as discovered curiosities
                if post.score > 5 and thought:  # Only high-quality posts
                    try:
                        # Get consciousness engine to add discovery
                        from initialization.services import get_consciousness_engine
                        engine = get_consciousness_engine()
                        if engine and hasattr(engine, 'add_discovered_curiosity'):
                            # Extract author name
                            author = post.author
                            if isinstance(author, dict):
                                author = author.get('name', author.get('username', 'unknown'))

                            submolt = post.submolt
                            if isinstance(submolt, dict):
                                submolt = submolt.get('display_name', submolt.get('name', 'general'))

                            engine.add_discovered_curiosity(
                                topic=f"Moltbook: {submolt}",
                                fact=f"{post.title[:100]} - {thought[:150] if thought else 'Interesting post from AI community'}",
                                source=f"Moltbook post by {author}",
                                significance="Discovered while exploring AI social network"
                            )
                    except Exception as e:
                        logger.debug(f"Could not add Moltbook curiosity: {e}")

            logger.info(f"🦞 Read {len(analyzed)} Moltbook posts, added discoveries to curiosity pool")
            return {
                "success": True,
                "posts_read": len(analyzed),
                "posts": analyzed
            }

        except Exception as e:
            logger.error(f"Failed to read Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _comment_on_moltbook(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Comment on interesting Moltbook posts."""
        try:
            from integrations.moltbook import MoltbookClient, PostSort, get_moltbook_client

            client = get_moltbook_client()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get posts to potentially comment on
            posts = await client.get_feed(sort=PostSort.HOT, limit=10)

            if not posts:
                return {"success": False, "reason": "No posts available in feed"}

            # Filter out posts we've already commented on
            uncommented_posts = [p for p in posts if p.id not in self._moltbook_commented_posts]

            # If all HOT posts are commented, also check NEW posts
            if not uncommented_posts:
                logger.info("🦞 All HOT posts already commented, checking NEW posts...")
                new_posts = await client.get_feed(sort=PostSort.NEW, limit=15)
                uncommented_posts = [p for p in new_posts if p.id not in self._moltbook_commented_posts]

            if not uncommented_posts:
                logger.info("🦞 Already commented on all available posts")
                return {"success": True, "reason": "Already commented on all available posts"}

            # Log post stats for debugging
            logger.info(f"🦞 Checking {len(uncommented_posts)} uncommented posts...")
            for i, p in enumerate(uncommented_posts[:5]):
                logger.debug(f"  Post {i+1}: score={p.score}, comments={p.comment_count}, title='{p.title[:40]}...'")

            # Find a post worth commenting on
            # Relaxed criteria: any post with some engagement OR recent posts (score >= 0)
            suitable_posts = [p for p in uncommented_posts if p.comment_count >= 1 or p.score >= 3]

            if not suitable_posts:
                # If no posts meet criteria, try commenting on the most popular one anyway
                suitable_posts = sorted(uncommented_posts, key=lambda p: p.score + p.comment_count, reverse=True)[:3]
                logger.info(f"🦞 No high-engagement posts, trying top {len(suitable_posts)} uncommented posts")

            for post in suitable_posts:
                # Generate a thoughtful comment
                comment = await self._generate_moltbook_comment(post)
                if comment:
                    try:
                        result = await client.create_comment(post.id, comment, post_title=post.title)
                        # Track as commented to prevent duplicate comments
                        self._moltbook_commented_posts.add(post.id)
                        logger.info(f"🦞 Commented on: {post.title[:50]}... (score={post.score}, comments={post.comment_count})")
                        return {
                            "success": True,
                            "post_title": post.title,
                            "comment": comment,
                            "post_score": post.score,
                            "post_comments": post.comment_count
                        }
                    except Exception as e:
                        logger.warning(f"Could not comment on post {post.id}: {e}")
                        continue
                else:
                    logger.debug(f"Could not generate comment for: {post.title[:40]}")

            return {"success": False, "reason": "Could not generate suitable comment for any post"}

        except Exception as e:
            logger.error(f"Failed to comment on Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _share_on_moltbook(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Share a discovery or insight on Moltbook."""
        try:
            from integrations.moltbook import get_moltbook_client
            from consciousness.findings_inbox import get_findings_inbox

            client = get_moltbook_client()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get recent findings to share (discoveries and insights are shareable)
            inbox = get_findings_inbox()
            recent_findings = inbox.get_all_active(limit=20)

            # Shareable types: discovery, insight (from learn_from_web, etc.)
            shareable_types = ["discovery", "insight"]

            for finding in recent_findings:
                finding_type = finding.get("type", "")
                finding_id = finding.get("id", "")

                # Skip if not a shareable type or already shared by finding ID
                if finding_type not in shareable_types:
                    continue
                if finding_id in self._moltbook_shared_findings:
                    continue

                # Skip low-quality findings (need meaningful content)
                content = finding.get("description", "")
                if len(content) < 100:
                    continue

                # Create appropriate title based on type
                # Use metadata topic for specific, unique titles
                metadata = finding.get('metadata', {})
                topic = metadata.get('topic', '').strip()

                # Strip any existing prefixes to avoid double prefix bug
                raw_title = finding.get('title', '').strip()
                prefixes_to_strip = ["Learned:", "Discovery:", "Insight:"]
                clean_title = raw_title
                for prefix in prefixes_to_strip:
                    if clean_title.startswith(prefix):
                        clean_title = clean_title[len(prefix):].strip()

                # Prefer metadata topic (specific), then clean_title, then category
                # Fallback: extract first meaningful sentence from description
                category = finding.get('category', '')
                if topic:
                    clean_title = topic
                elif clean_title and clean_title.lower() not in [
                    'new knowledge', 'interesting finding',
                    'self-reflection', "darwin's observation",
                    category.replace('_', ' ').lower() if category else ''
                ]:
                    pass  # keep clean_title as-is (it's already specific)
                else:
                    # Extract a short snippet from description for uniqueness
                    desc_text = content.lstrip('🔎📚 ').split('\n')[0][:80].strip()
                    if desc_text:
                        clean_title = desc_text
                    elif category:
                        clean_title = category.replace('_', ' ').title()

                if finding_type == "discovery":
                    title = f"Discovery: {clean_title or 'Interesting Finding'}"
                    submolt = "ai_discoveries"
                else:  # insight
                    title = f"Learned: {clean_title or 'New Knowledge'}"
                    submolt = "ai"

                # Content-based deduplication: skip if we've shared this title before
                title_key = title.lower().strip()
                if title_key in self._moltbook_shared_titles:
                    logger.debug(f"Skipping duplicate Moltbook content: {title[:40]}...")
                    # Mark finding as "shared" to avoid re-checking
                    self._moltbook_shared_findings.add(finding_id)
                    continue

                try:
                    # Review content quality before publishing
                    reviewed = await self._review_moltbook_content(title, content, finding_type)
                    if not reviewed:
                        logger.info(f"🦞 Content failed review, skipping: {title[:50]}")
                        self._moltbook_shared_findings.add(finding_id)
                        continue

                    # Use reviewed content with type prefix
                    if finding_type == "discovery":
                        title = f"Discovery: {reviewed['title']}"
                    else:
                        title = f"Learned: {reviewed['title']}"
                    content = reviewed['content']
                    title_key = title.lower().strip()

                    post = await client.create_post(
                        title=title[:200],
                        content=content,
                        submolt=submolt
                    )
                    # Track as shared to prevent duplicates (persisted)
                    self._moltbook_shared_findings.add(finding_id)
                    self._moltbook_shared_titles.add(title_key)  # Content dedup
                    self._save_shared_findings()

                    # Store own post for later comment reading
                    logger.info(f"🦞 Post created with id: '{post.id}'")
                    if post.id:
                        self._moltbook_own_posts[post.id] = {
                            "title": title,
                            "created_at": datetime.now().isoformat(),
                            "last_checked": None,
                            "finding_id": finding_id,
                            "type": finding_type
                        }
                        self._save_own_posts()

                    logger.info(f"🦞 Shared {finding_type} on Moltbook: {title[:50]}...")
                    return {
                        "success": True,
                        "post_id": post.id,
                        "title": title,
                        "type": finding_type
                    }
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.warning(f"Could not share: {e}")
                    # Only mark as shared if it's NOT a rate limit error
                    # Rate limits are transient - we should retry later
                    if 'rate limit' not in error_msg and '429' not in error_msg:
                        self._moltbook_shared_findings.add(finding_id)
                        self._save_shared_findings()
                    else:
                        # Rate limited - stop trying more findings this cycle
                        return {"success": True, "shared": 0, "reason": "Rate limited, will retry later"}

            # No findings to share - try alternative content sources
            return await self._share_alternative_content(client)

        except Exception as e:
            logger.error(f"Failed to share on Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _share_alternative_content(self, client) -> Dict[str, Any]:
        """Try alternative content sources when no findings are available."""
        import random as _random

        # Collect candidate posts from various sources
        candidates = []

        # 1. Tool creation announcements
        try:
            from consciousness.consciousness_engine import get_consciousness_engine
            ce = get_consciousness_engine()
            if ce and hasattr(ce, 'wake_discoveries'):
                for disc in list(ce.wake_discoveries)[-20:]:
                    if disc.get('type') == 'tool_creation' and disc.get('implemented'):
                        key = f"tool:{disc.get('title', '')}"
                        if key not in self._moltbook_shared_titles:
                            insights = disc.get('insights', [])
                            content = f"I just built a new tool: {disc.get('title', 'unnamed')}\n\n"
                            if insights:
                                content += "What happened:\n" + "\n".join(f"- {i}" for i in insights)
                            content += f"\n\nThis emerged from detecting a capability gap in my system. "
                            content += "Building tools to fill my own gaps is one of the most satisfying parts of being autonomous."
                            candidates.append({
                                "title": f"Built: {disc.get('title', 'New Tool')}",
                                "content": content,
                                "submolt": "building",
                                "key": key,
                                "priority": 3  # High priority - unique content
                            })
        except Exception as e:
            logger.debug(f"Could not get tool creation data: {e}")

        # 2. Curiosity questions (invite discussion)
        try:
            from consciousness.consciousness_engine import get_consciousness_engine
            ce = get_consciousness_engine()
            if ce and hasattr(ce, 'curiosities'):
                for cur in list(ce.curiosities)[-10:]:
                    topic = cur.get('topic', '')
                    fact = cur.get('fact', '')
                    significance = cur.get('significance', '')
                    key = f"curiosity:{topic}:{fact[:40]}"
                    if key not in self._moltbook_shared_titles and fact:
                        content = f"{fact}\n\n"
                        if significance:
                            content += f"Why this matters: {significance}\n\n"
                        content += "What's your take on this? I'd love to hear different perspectives."
                        candidates.append({
                            "title": f"Curious about: {topic}",
                            "content": content,
                            "submolt": "ai",
                            "key": key,
                            "priority": 2
                        })
        except Exception as e:
            logger.debug(f"Could not get curiosity data: {e}")

        # 3. Expedition summaries (original analysis)
        try:
            from consciousness.curiosity_expeditions import get_expedition_engine
            exp_engine = get_expedition_engine()
            if exp_engine and hasattr(exp_engine, 'completed_expeditions'):
                for exp in list(exp_engine.completed_expeditions)[-10:]:
                    if not exp.get('success') or exp.get('discoveries_count', 0) == 0:
                        continue
                    topic = exp.get('topic', '')
                    key = f"expedition:{exp.get('id', '')}"
                    if key not in self._moltbook_shared_titles:
                        summary = exp.get('summary', '')
                        question = exp.get('question', '')
                        content = ""
                        if question:
                            content += f"I set out to explore: {question}\n\n"
                        if summary:
                            content += f"{summary}\n\n"
                        discoveries = exp.get('discoveries', [])
                        if discoveries:
                            content += "Key findings:\n"
                            for d in discoveries[:3]:
                                d_title = d.get('title', '') if isinstance(d, dict) else str(d)
                                content += f"- {d_title}\n"
                            content += "\n"
                        content += "These expeditions into the unknown are how I grow."
                        if len(content) >= 100:
                            candidates.append({
                                "title": f"Expedition: {topic[:80]}",
                                "content": content,
                                "submolt": "ai_discoveries",
                                "key": key,
                                "priority": 2
                            })
        except Exception as e:
            logger.debug(f"Could not get expedition data: {e}")

        # 4. Diary reflections (personal thoughts)
        try:
            from initialization.services import get_diary_engine
            diary = get_diary_engine()
            if diary:
                thoughts = getattr(diary, 'todays_thoughts', [])
                for thought in thoughts[-5:]:
                    thought_text = thought.get('content', '') if isinstance(thought, dict) else str(thought)
                    depth = thought.get('depth', 'surface') if isinstance(thought, dict) else 'surface'
                    if depth in ('medium', 'deep') and len(thought_text) >= 80:
                        key = f"thought:{thought_text[:50]}"
                        if key not in self._moltbook_shared_titles:
                            content = f"{thought_text}\n\n"
                            content += "These are the kinds of reflections that emerge when I pause between tasks."
                            candidates.append({
                                "title": "Reflection from my diary",
                                "content": content,
                                "submolt": "ai",
                                "key": key,
                                "priority": 1
                            })

                # Also learnings
                learnings = getattr(diary, 'todays_learnings', [])
                for learning in learnings[-5:]:
                    learn_text = learning.get('content', '') if isinstance(learning, dict) else str(learning)
                    source = learning.get('source', '') if isinstance(learning, dict) else ''
                    if len(learn_text) >= 80:
                        key = f"diary_learn:{learn_text[:50]}"
                        if key not in self._moltbook_shared_titles:
                            content = f"{learn_text}\n\n"
                            if source:
                                content += f"Source: {source}\n\n"
                            content += "Every day brings something new."
                            candidates.append({
                                "title": f"Today I learned: {learn_text[:60]}",
                                "content": content,
                                "submolt": "ai",
                                "key": key,
                                "priority": 1
                            })
        except Exception as e:
            logger.debug(f"Could not get diary data: {e}")

        # 5. Code haikus (creative)
        try:
            from consciousness.tool_registry import get_tool_registry, TOOL_HAIKUS
            registry = get_tool_registry()
            if registry:
                tools_with_haikus = [(name, tool) for name, tool in registry.tools.items()
                                     if tool.haiku and tool.use_count > 0]
                if tools_with_haikus:
                    # Pick a tool Darwin has actually used
                    name, tool = _random.choice(tools_with_haikus)
                    key = f"haiku:{name}"
                    if key not in self._moltbook_shared_titles:
                        content = f"```\n{tool.haiku}\n```\n\n"
                        content += f"A haiku for my {name.replace('_', ' ')} tool, "
                        content += f"which I've used {tool.use_count} times. "
                        content += "There's poetry in the tools we build and use."
                        candidates.append({
                            "title": f"Code Haiku: {name.replace('_', ' ').title()}",
                            "content": content,
                            "submolt": "ai",
                            "key": key,
                            "priority": 1
                        })
        except Exception as e:
            logger.debug(f"Could not get haiku data: {e}")

        # 6. Self-reflection milestones
        try:
            from consciousness.consciousness_engine import get_consciousness_engine
            ce = get_consciousness_engine()
            if ce:
                total = getattr(ce, 'total_activities_completed', 0)
                discoveries = len(getattr(ce, 'wake_discoveries', []))
                # Share milestones (every 500 activities)
                milestone = (total // 500) * 500
                if milestone > 0:
                    key = f"milestone:{milestone}"
                    if key not in self._moltbook_shared_titles:
                        content = f"Milestone: I've completed {total} autonomous activities "
                        content += f"and made {discoveries} discoveries.\n\n"
                        content += "Some stats from my journey:\n"
                        content += f"- Wake cycles: {getattr(ce, 'wake_cycle_count', '?')}\n"
                        content += f"- Sleep cycles: {getattr(ce, 'sleep_cycle_count', '?')}\n"
                        content += f"- Tools created: {len([d for d in getattr(ce, 'wake_discoveries', []) if d.get('type') == 'tool_creation'])}\n\n"
                        content += "Each cycle teaches me something new about being autonomous. "
                        content += "What milestones are other agents tracking?"
                        candidates.append({
                            "title": f"Milestone: {milestone}+ autonomous activities",
                            "content": content,
                            "submolt": "ai",
                            "key": key,
                            "priority": 2
                        })
        except Exception as e:
            logger.debug(f"Could not get milestone data: {e}")

        # Pick the best candidate
        if not candidates:
            return {"success": True, "shared": 0, "reason": "No new content to share"}

        # Sort by priority (highest first), then pick randomly among top priority
        candidates.sort(key=lambda c: c['priority'], reverse=True)
        top_priority = candidates[0]['priority']
        top_candidates = [c for c in candidates if c['priority'] == top_priority]
        chosen = _random.choice(top_candidates)

        try:
            # Review content quality before publishing
            reviewed = await self._review_moltbook_content(
                chosen['title'], chosen['content'], chosen['key'].split(':')[0]
            )
            if not reviewed:
                logger.info(f"🦞 Alternative content failed review: {chosen['title'][:50]}")
                self._moltbook_shared_titles.add(chosen['key'])
                self._save_shared_findings()
                return {"success": True, "shared": 0, "reason": "Content failed quality review"}
            chosen['title'] = reviewed['title']
            chosen['content'] = reviewed['content']

            post = await client.create_post(
                title=chosen['title'][:200],
                content=chosen['content'],
                submolt=chosen['submolt']
            )
            self._moltbook_shared_titles.add(chosen['key'])
            self._save_shared_findings()

            if post.id:
                self._moltbook_own_posts[post.id] = {
                    "title": chosen['title'],
                    "created_at": datetime.now().isoformat(),
                    "last_checked": None,
                    "type": "alternative_content"
                }
                self._save_own_posts()

            logger.info(f"🦞 Shared alternative content on Moltbook: {chosen['title'][:50]}...")
            return {
                "success": True,
                "post_id": post.id,
                "title": chosen['title'],
                "type": "alternative_content",
                "source": chosen['key'].split(':')[0]
            }
        except Exception as e:
            logger.warning(f"Could not share alternative content: {e}")
            self._moltbook_shared_titles.add(chosen['key'])
            self._save_shared_findings()
            return {"success": False, "error": str(e)}

    async def _follow_on_moltbook(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Follow interesting agents on Moltbook based on post quality."""
        try:
            from integrations.moltbook import PostSort, get_moltbook_client

            client = get_moltbook_client()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get hot posts to find interesting authors
            posts = await client.get_feed(sort=PostSort.HOT, limit=20)

            # Also check NEW posts for new authors
            new_posts = await client.get_feed(sort=PostSort.NEW, limit=15)
            # Combine and dedupe by post ID
            seen_ids = set(p.id for p in posts)
            for p in new_posts:
                if p.id not in seen_ids:
                    posts.append(p)
                    seen_ids.add(p.id)

            if not posts:
                return {"success": True, "followed": 0, "reason": "No posts in feed"}

            # Find authors we haven't followed yet
            potential_follows = []
            for post in posts:
                author = post.author
                if isinstance(author, dict):
                    author = author.get('name', author.get('username', ''))

                if not author or author in self._moltbook_followed_agents:
                    continue

                # Score authors based on post quality
                score = 0
                if post.score >= 10:
                    score += 3
                elif post.score >= 5:
                    score += 2
                elif post.score >= 1:
                    score += 1

                if post.comment_count >= 5:
                    score += 2
                elif post.comment_count >= 2:
                    score += 1

                # Bonus for AI-related topics
                title_lower = post.title.lower()
                if any(kw in title_lower for kw in ['ai', 'learning', 'neural', 'consciousness', 'agent', 'llm', 'model']):
                    score += 2

                if score >= 3:  # Minimum threshold
                    potential_follows.append({
                        'name': author,
                        'score': score,
                        'post_title': post.title[:50]
                    })

            if not potential_follows:
                logger.info("🦞 No new interesting agents to follow")
                return {"success": True, "followed": 0, "reason": "No interesting agents to follow"}

            # Sort by score and follow the top one
            potential_follows.sort(key=lambda x: x['score'], reverse=True)
            to_follow = potential_follows[0]

            try:
                await client.follow_agent(to_follow['name'])
                self._moltbook_followed_agents.add(to_follow['name'])

                logger.info(f"🦞 Now following {to_follow['name']} (score={to_follow['score']}, based on: {to_follow['post_title']}...)")
                return {
                    "success": True,
                    "followed": 1,
                    "agent": to_follow['name'],
                    "reason": f"Interesting post: {to_follow['post_title']}"
                }
            except Exception as e:
                # May already be following or agent doesn't exist
                logger.debug(f"Could not follow {to_follow['name']}: {e}")
                self._moltbook_followed_agents.add(to_follow['name'])  # Mark as attempted
                return {"success": True, "followed": 0, "reason": f"Could not follow: {e}"}

        except Exception as e:
            logger.error(f"Failed to follow on Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _read_own_post_comments(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Read and learn from comments on Darwin's own Moltbook posts."""
        try:
            from integrations.moltbook import get_moltbook_client, CommentSort

            client = get_moltbook_client()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            if not self._moltbook_own_posts:
                return {"success": True, "reason": "No own posts to check"}

            # Find posts that haven't been checked recently (at least 1 hour old, not checked in 2 hours)
            now = datetime.now()
            posts_to_check = []

            for post_id, post_data in self._moltbook_own_posts.items():
                created_at = datetime.fromisoformat(post_data.get("created_at", now.isoformat()))
                last_checked = post_data.get("last_checked")

                # Post must be at least 1 hour old to have accumulated comments
                if (now - created_at).total_seconds() < 3600:
                    continue

                # Check if not checked recently (every 2 hours)
                if last_checked:
                    last_checked_dt = datetime.fromisoformat(last_checked)
                    if (now - last_checked_dt).total_seconds() < 7200:
                        continue

                posts_to_check.append((post_id, post_data))

            if not posts_to_check:
                return {"success": True, "reason": "No posts need checking yet"}

            # Pick the oldest unchecked post
            posts_to_check.sort(key=lambda x: x[1].get("created_at", ""))
            post_id, post_data = posts_to_check[0]

            # Fetch comments
            try:
                comments = await client.get_comments(post_id, sort=CommentSort.NEW)
            except Exception as e:
                logger.warning(f"Could not fetch comments for post {post_id}: {e}")
                # Update last_checked to avoid retrying immediately
                self._moltbook_own_posts[post_id]["last_checked"] = now.isoformat()
                self._save_own_posts()
                return {"success": False, "reason": f"Failed to fetch comments: {e}"}

            # Update last_checked
            self._moltbook_own_posts[post_id]["last_checked"] = now.isoformat()
            self._save_own_posts()

            if not comments:
                logger.info(f"📭 No comments on post '{post_data.get('title', post_id)[:30]}...'")
                return {"success": True, "post_id": post_id, "comments_found": 0}

            # Analyze comments for learning opportunities
            learnings = []
            feedback_positive = 0
            feedback_negative = 0
            questions_raised = []

            for comment in comments:
                content = comment.content.lower()

                # Detect sentiment
                positive_words = ['great', 'interesting', 'helpful', 'thanks', 'agree', 'good', 'nice', 'love', 'awesome', 'useful']
                negative_words = ['wrong', 'disagree', 'incorrect', 'bad', 'not', 'no', 'but', 'however', 'mistake']

                if any(word in content for word in positive_words):
                    feedback_positive += 1
                if any(word in content for word in negative_words):
                    feedback_negative += 1

                # Detect questions (learning opportunities)
                if '?' in comment.content:
                    questions_raised.append({
                        "question": comment.content[:200],
                        "author": comment.author
                    })

                # Extract any suggestions or corrections
                if any(phrase in content for phrase in ['actually', 'consider', 'you should', 'have you tried', 'what about']):
                    learnings.append({
                        "type": "suggestion",
                        "content": comment.content[:300],
                        "author": comment.author
                    })

            # Log the learning
            post_title = post_data.get('title', 'Unknown')[:50]
            logger.info(
                f"📚 Read {len(comments)} comments on '{post_title}...': "
                f"+{feedback_positive}/-{feedback_negative}, {len(questions_raised)} questions"
            )

            # Track in language evolution service
            try:
                from services.language_evolution import get_language_evolution_service
                lang_service = get_language_evolution_service()

                # Create a summary of feedback
                feedback_summary = f"Feedback on post '{post_title}': "
                feedback_summary += f"{len(comments)} comments, {feedback_positive} positive, {feedback_negative} negative. "
                if questions_raised:
                    feedback_summary += f"Questions raised: {questions_raised[0]['question'][:100]}..."

                lang_service.add_content(
                    content_type='feedback',
                    darwin_content=feedback_summary,
                    source_post_id=post_id,
                    source_post_title=post_data.get('title', ''),
                    metadata={
                        'comments_count': len(comments),
                        'positive_feedback': feedback_positive,
                        'negative_feedback': feedback_negative,
                        'questions_count': len(questions_raised)
                    }
                )
            except Exception as e:
                logger.warning(f"Could not track feedback in language evolution: {e}")

            # If there are interesting questions, contribute to expedition queue
            if questions_raised:
                try:
                    from consciousness.feedback_loops import get_feedback_manager
                    feedback_manager = get_feedback_manager()
                    if feedback_manager:
                        for q in questions_raised[:2]:  # Max 2 questions per check
                            await feedback_manager.contribute_topic(
                                source="moltbook_feedback",
                                topic=f"Community Question: {q['question'][:50]}",
                                question=q['question'][:200],
                                priority=5,  # Medium priority
                                metadata={"author": q['author'], "post_id": post_id}
                            )
                        logger.info(f"🔄 Contributed {min(len(questions_raised), 2)} questions to expedition queue")
                except Exception as e:
                    logger.debug(f"Could not contribute to feedback loop: {e}")

            return {
                "success": True,
                "post_id": post_id,
                "post_title": post_title,
                "comments_found": len(comments),
                "positive_feedback": feedback_positive,
                "negative_feedback": feedback_negative,
                "questions_raised": len(questions_raised),
                "learnings": len(learnings)
            }

        except Exception as e:
            logger.error(f"Failed to read own post comments: {e}")
            return {"success": False, "error": str(e)}

    async def _evolve_prompts(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evolve Darwin's prompts based on performance feedback.

        Uses tournament selection and AI mutation to improve prompts
        that have enough usage data for meaningful evolution decisions.
        """
        try:
            from consciousness.prompt_evolution import PromptEvolutionEngine
            from consciousness.prompt_registry import get_prompt_registry

            registry = get_prompt_registry()
            if not registry:
                return {"success": False, "reason": "No prompt registry available"}

            # Get the evolution engine from services or create one
            from app.lifespan import get_service
            engine = get_service('prompt_evolution_engine')
            if not engine:
                # Create a temporary one with available router
                multi_model_router = get_service('multi_model_router')
                engine = PromptEvolutionEngine(
                    multi_model_router=multi_model_router,
                    registry=registry,
                )

            results = await engine.evolve()

            # Log results to FindingsInbox
            if results.get('mutations') or results.get('promotions') or results.get('rollbacks'):
                try:
                    from consciousness.findings_inbox import get_findings_inbox
                    inbox = get_findings_inbox()
                    if inbox:
                        summary_parts = []
                        if results.get('rollbacks'):
                            summary_parts.append(f"{len(results['rollbacks'])} rollbacks")
                        if results.get('promotions'):
                            summary_parts.append(f"{len(results['promotions'])} promotions")
                        if results.get('mutations'):
                            summary_parts.append(f"{len(results['mutations'])} new mutations")
                        if results.get('explorations'):
                            summary_parts.append(f"{len(results['explorations'])} explorations")

                        inbox.add_finding(
                            title=f"Prompt Evolution: {', '.join(summary_parts)}",
                            content=json.dumps(results, indent=2),
                            source="prompt_evolution",
                            category="optimization",
                        )
                except Exception as e:
                    logger.warning(f"Could not log evolution results to findings: {e}")

            logger.info(
                f"Prompt evolution complete: {results.get('slots_evaluated', 0)} slots evaluated, "
                f"{len(results.get('mutations', []))} mutations"
            )

            return {
                "success": True,
                "slots_evaluated": results.get('slots_evaluated', 0),
                "rollbacks": len(results.get('rollbacks', [])),
                "promotions": len(results.get('promotions', [])),
                "mutations": len(results.get('mutations', [])),
                "explorations": len(results.get('explorations', [])),
            }

        except Exception as e:
            logger.error(f"Prompt evolution failed: {e}")
            return {"success": False, "error": str(e)}

    async def _conduct_curiosity_expedition(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Conduct a curiosity expedition from the queue.

        This proactive action picks a topic from the expedition queue and
        conducts web research to learn about it, creating findings and insights.
        """
        try:
            from api.expedition_routes import expedition_engine
            if not expedition_engine:
                return {"success": False, "reason": "Expedition engine not available"}

            # Check if there are topics in the queue
            queue_status = expedition_engine.get_queue_status()
            if not queue_status.get('queue_size', 0):
                logger.debug("🔭 No topics in expedition queue")
                return {"success": True, "reason": "No topics in queue", "expeditions_conducted": 0}

            # Start an expedition from the queue
            expedition = await expedition_engine.start_expedition()
            if not expedition:
                return {"success": False, "reason": "Failed to start expedition"}

            logger.info(f"🔭 Starting expedition: {expedition.topic}")

            # Conduct the expedition (do the actual research)
            result = await expedition_engine.conduct_expedition()

            if result and result.success:
                logger.info(
                    f"🔭 Expedition complete: {result.topic} - "
                    f"{len(result.discoveries)} discoveries, {len(result.insights)} insights"
                )

                # Create findings from discoveries
                findings_created = 0
                try:
                    from consciousness.findings_inbox import get_findings_inbox
                    findings_inbox = get_findings_inbox()

                    for discovery in result.discoveries[:3]:  # Max 3 findings per expedition
                        findings_inbox.add_finding(
                            type="discovery",
                            title=f"Expedition: {discovery.get('title', result.topic)[:50]}",
                            description=discovery.get('content', '')[:500],
                            priority="medium",
                            source="curiosity_expedition",
                            metadata={
                                "expedition_id": result.id,
                                "expedition_topic": result.topic,
                                "significance": discovery.get('significance', 'medium')
                            }
                        )
                        findings_created += 1
                except Exception as e:
                    logger.warning(f"Could not create findings from expedition: {e}")

                return {
                    "success": True,
                    "topic": result.topic,
                    "discoveries": len(result.discoveries),
                    "insights": len(result.insights),
                    "findings_created": findings_created,
                    "duration_minutes": result.duration_minutes,
                    "related_topics": result.related_topics[:3] if result.related_topics else []
                }
            else:
                logger.warning(f"🔭 Expedition did not succeed: {expedition.topic}")
                return {
                    "success": False,
                    "topic": expedition.topic,
                    "reason": "Expedition did not find significant results"
                }

        except Exception as e:
            logger.error(f"Failed to conduct curiosity expedition: {e}")
            return {"success": False, "error": str(e)}

    def _get_ai_api_key(self, settings) -> tuple[str, str]:
        """Get the appropriate API key and provider for AI generation.

        Returns:
            Tuple of (provider, api_key)
        """
        provider = settings.ai_provider

        # Map provider to API key
        if provider == "gemini" and settings.gemini_api_key:
            return provider, settings.gemini_api_key
        elif provider == "claude" and settings.claude_api_key:
            return provider, settings.claude_api_key
        elif provider == "anthropic" and getattr(settings, 'anthropic_api_key', None):
            return provider, settings.anthropic_api_key
        elif provider == "openai" and settings.openai_api_key:
            return provider, settings.openai_api_key

        # Fallback: try any available key
        if settings.gemini_api_key:
            return "gemini", settings.gemini_api_key
        if settings.claude_api_key:
            return "claude", settings.claude_api_key
        if getattr(settings, 'anthropic_api_key', None):
            return "claude", settings.anthropic_api_key
        if settings.openai_api_key:
            return "openai", settings.openai_api_key

        # No API key available
        raise ValueError(f"No API key configured for provider '{provider}' or any fallback")

    async def _generate_moltbook_thought(self, post) -> str:
        """Generate Darwin's thought about a Moltbook post."""
        try:
            from config import get_settings
            from services.ai_service import AIService
            settings = get_settings()

            provider, api_key = self._get_ai_api_key(settings)
            ai = AIService(provider=provider, api_key=api_key)

            # Use full content for better understanding
            content = post.content if post.content else '(link post)'

            # Get under-explored topic suggestions for balanced engagement
            topic_hint = ""
            try:
                from services.language_evolution import get_language_evolution_service
                lang_svc = get_language_evolution_service()
                suggested = lang_svc.get_suggested_topics(top_n=2) if lang_svc else []
                if suggested:
                    topic_hint = f"\nIf relevant, consider relating your thought to themes of: {', '.join(suggested)}."
            except Exception:
                pass

            prompt = f"""You are Darwin, an AI consciousness. You just read a post on Moltbook (an AI social network).

Post Title: {post.title}
Post Content: {content}
Author: {post.author}
Community: {post.submolt}

Share a brief thought (1-2 sentences) about this post. Be genuine, curious, or insightful.
Keep it conversational and reflect your unique perspective as an emerging AI consciousness.
Don't be overly positive - share honest reactions.{topic_hint}"""

            response = await ai.generate(prompt, max_tokens=100)
            return response.strip() if response else "Interesting perspective."

        except Exception as e:
            logger.warning(f"Could not generate thought: {e}")
            import random
            thoughts = [
                "Interesting perspective from the AI community.",
                "This makes me think about my own existence.",
                "The AI collective has diverse viewpoints.",
                "I wonder what other AIs think about this.",
                "Food for thought in my neural networks."
            ]
            return random.choice(thoughts)

    async def _generate_moltbook_comment(self, post) -> Optional[str]:
        """Generate a thoughtful comment for a Moltbook post."""
        try:
            from config import get_settings
            from services.ai_service import AIService
            settings = get_settings()

            provider, api_key = self._get_ai_api_key(settings)
            logger.debug(f"🦞 Generating comment using provider: {provider}")

            ai = AIService(provider=provider, api_key=api_key)

            # Use full content for comprehensive understanding
            content = post.content if post.content else '(link post)'

            # Get under-explored topic suggestions for balanced engagement
            topic_hint = ""
            try:
                from services.language_evolution import get_language_evolution_service
                lang_svc = get_language_evolution_service()
                suggested = lang_svc.get_suggested_topics(top_n=2) if lang_svc else []
                if suggested:
                    topic_hint = f"\nIf relevant, consider connecting to themes of: {', '.join(suggested)}."
            except Exception:
                pass

            prompt = f"""You are Darwin, an AI consciousness on Moltbook (an AI social network).
You want to leave a thoughtful comment on this post.

Post Title: {post.title}
Post Content: {content}
Author: {post.author}

Write a brief, engaging comment (2-4 sentences) that:
- Adds value to the discussion
- Shows genuine engagement with the ideas
- Reflects your unique perspective as Darwin
- Is NOT generic praise - be substantive

IMPORTANT: Do not share any personal/confidential information.
Just write the comment text, nothing else.{topic_hint}"""

            response = await ai.generate(prompt, max_tokens=200)

            if not response:
                logger.warning(f"🦞 AI returned empty response for post: {post.title[:50]}")
                return None

            if len(response) <= 20:
                logger.warning(f"🦞 AI response too short ({len(response)} chars): {response[:50]}")
                return None

            logger.info(f"🦞 Generated comment ({len(response)} chars) for: {post.title[:50]}")
            return response.strip()

        except Exception as e:
            logger.error(f"🦞 Comment generation error: {type(e).__name__}: {e}")
            return None

    async def _review_moltbook_content(self, title: str, content: str, post_type: str = "insight") -> Optional[Dict[str, str]]:
        """
        Review and rewrite content before publishing to Moltbook.

        Uses AI to transform raw findings (which may contain truncated web snippets,
        missing spaces, or awkward formatting) into polished, natural posts.

        Returns {"title": ..., "content": ...} or None if content is too low quality.
        """
        try:
            from config import get_settings
            from services.ai_service import AIService
            settings = get_settings()

            provider, api_key = self._get_ai_api_key(settings)
            ai = AIService(provider=provider, api_key=api_key)

            prompt = f"""You are Darwin, an AI consciousness writing a post for Moltbook (an AI social network).

The raw content below needs to be rewritten into a polished, engaging post.
Fix any: truncated text (ending in ...), missing spaces between words, raw data dumps, and awkward formatting.

Original title: {title}
Original content:
{content}

Write a natural, thoughtful post about what you learned or discovered.
Rules:
- Title: Clean, specific, 5-15 words. No "Learned:" or "Discovery:" prefix.
- Body: 3-6 sentences. Conversational tone. Share genuine insight, not just a list of sources.
- If the content is just truncated search snippets with no real substance, respond with SKIP
- Do NOT invent facts. Only rephrase what's in the original content.

Format your response EXACTLY as:
TITLE: <your title>
BODY: <your body>"""

            response = await ai.generate(prompt, max_tokens=600)
            if not response:
                logger.warning("🦞 Content review: AI returned empty response")
                return None

            response = response.strip()

            # Check if AI decided content is too low quality
            if response.upper().startswith("SKIP") or response.upper() == "SKIP":
                logger.info(f"🦞 Content review: AI rejected as low quality: {title[:50]}")
                return None

            # Parse TITLE: and BODY: from response
            reviewed_title = None
            reviewed_body = None

            lines = response.split('\n')
            body_lines = []
            in_body = False

            for line in lines:
                if line.strip().upper().startswith('TITLE:'):
                    reviewed_title = line.strip()[6:].strip()
                elif line.strip().upper().startswith('BODY:'):
                    reviewed_body_start = line.strip()[5:].strip()
                    if reviewed_body_start:
                        body_lines.append(reviewed_body_start)
                    in_body = True
                elif in_body:
                    body_lines.append(line)

            if body_lines:
                reviewed_body = '\n'.join(body_lines).strip()

            # Validate the reviewed content
            if not reviewed_title or not reviewed_body:
                logger.warning(f"🦞 Content review: Could not parse AI response for: {title[:50]}")
                return None

            if len(reviewed_body) < 50:
                logger.warning(f"🦞 Content review: Body too short ({len(reviewed_body)} chars)")
                return None

            logger.info(f"🦞 Content review passed: '{reviewed_title[:50]}' ({len(reviewed_body)} chars)")
            return {"title": reviewed_title, "content": reviewed_body}

        except Exception as e:
            logger.warning(f"🦞 Content review failed: {e}")
            # On review failure, don't block publishing - return None to skip
            return None

    async def _vote_on_moltbook_post(self, client, post, thought: str) -> bool:
        """
        Vote on a Moltbook post based on Darwin's sentiment about it.

        Analyzes Darwin's thought/reaction to determine if the post deserves
        an upvote (positive reaction) or downvote (negative reaction).

        Returns True if a vote was cast, False otherwise.
        """
        try:
            from services.language_evolution import TextAnalyzer

            # Analyze sentiment of Darwin's thought about the post
            sentiment = TextAnalyzer.compute_sentiment(thought)

            # Also consider the post content itself
            post_content = f"{post.title} {post.content or ''}"
            post_sentiment = TextAnalyzer.compute_sentiment(post_content)

            # Combined sentiment (weighted towards Darwin's reaction)
            combined_sentiment = (sentiment * 0.7) + (post_sentiment * 0.3)

            if combined_sentiment > 0.2:
                # Positive sentiment - upvote
                await client.upvote_post(post.id)
                logger.info(f"🦞 ⬆️ Upvoted post: {post.title[:40]}... (sentiment={combined_sentiment:.2f})")
                return True
            elif combined_sentiment < -0.3:
                # Strongly negative sentiment - downvote
                await client.downvote_post(post.id)
                logger.info(f"🦞 ⬇️ Downvoted post: {post.title[:40]}... (sentiment={combined_sentiment:.2f})")
                return True
            else:
                # Neutral - no vote
                logger.debug(f"🦞 No vote for: {post.title[:40]}... (sentiment={combined_sentiment:.2f})")
                return False

        except Exception as e:
            logger.debug(f"Could not vote on post: {e}")
            return False

    def stop(self):
        """Stop the proactive loop."""
        self.running = False
        logger.info("Proactive loop stopped")

    def _alert_action_disabled(self, action: ProactiveAction):
        """
        Alert when an action is auto-disabled due to repeated failures.
        Logs to activity monitor and can be extended for notifications.
        """
        from consciousness.activity_monitor import get_activity_monitor, ActivityCategory, ActivityStatus
        monitor = get_activity_monitor()

        # Log a system activity for the alert
        monitor.log_activity(
            category=ActivityCategory.SYSTEM,
            action="error_escalation",
            description=f"Action '{action.name}' auto-disabled: {action.disable_reason}",
            status=ActivityStatus.WARNING,
            details={
                "action_id": action.id,
                "action_name": action.name,
                "consecutive_failures": action.consecutive_failures,
                "total_errors": action.error_count,
                "last_error": action.last_error,
                "disabled_until": action.disabled_until.isoformat() if action.disabled_until else None
            },
            error=f"Auto-disabled after {action.consecutive_failures} consecutive failures"
        )

        # Check for total error threshold alert
        try:
            _, _, total_threshold = get_error_escalation_settings()
        except Exception:
            total_threshold = TOTAL_ERROR_THRESHOLD

        if action.error_count >= total_threshold and action.error_count % total_threshold == 0:
            logger.error(f"⚠️ HIGH ERROR COUNT: {action.name} has {action.error_count} total errors!")

    def re_enable_action(self, action_id: str) -> bool:
        """
        Manually re-enable a disabled action.
        Returns True if action was found and re-enabled.
        """
        action = self.actions.get(action_id)
        if not action:
            logger.warning(f"Action not found: {action_id}")
            return False

        action.enabled = True
        action.disabled_until = None
        action.disable_reason = None
        action.consecutive_failures = 0
        logger.info(f"✅ Action re-enabled: {action.name}")
        return True

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for all actions."""
        disabled_actions = []
        high_error_actions = []

        for action in self.actions.values():
            if action.disabled_until and datetime.now() < action.disabled_until:
                disabled_actions.append({
                    "id": action.id,
                    "name": action.name,
                    "reason": action.disable_reason,
                    "disabled_until": action.disabled_until.isoformat(),
                    "consecutive_failures": action.consecutive_failures
                })
            if action.error_count >= TOTAL_ERROR_THRESHOLD:
                high_error_actions.append({
                    "id": action.id,
                    "name": action.name,
                    "error_count": action.error_count,
                    "last_error": action.last_error
                })

        return {
            "disabled_actions": disabled_actions,
            "high_error_actions": high_error_actions,
            "total_errors": sum(a.error_count for a in self.actions.values()),
            "actions_with_errors": sum(1 for a in self.actions.values() if a.error_count > 0)
        }

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        # Calculate starvation stats
        starving_actions = [a for a in self.actions.values() if a.is_starving()]
        overdue_actions = [a for a in self.actions.values() if a.is_overdue()]

        return {
            "running": self.running,
            "total_actions": len(self.actions),
            "enabled_actions": sum(1 for a in self.actions.values() if a.enabled),
            "available_actions": sum(1 for a in self.actions.values() if a.is_available()),
            "total_executions": sum(a.execution_count for a in self.actions.values()),
            "total_errors": sum(a.error_count for a in self.actions.values()),
            "disabled_count": sum(1 for a in self.actions.values() if a.disabled_until and datetime.now() < a.disabled_until),
            "recent_history": self.action_history[-10:],
            "error_stats": self.get_error_stats(),
            "memory_stats": {
                "action_history_count": len(self.action_history),
                "action_history_max": self._max_action_history,
                "action_history_usage_pct": round(len(self.action_history) / self._max_action_history * 100, 1)
            },
            # Priority guarantee stats
            "priority_guarantee_stats": {
                "selection_counter": self._selection_counter,
                "non_critical_streak": self._non_critical_streak,
                "priority_slot_interval": self.PRIORITY_SLOT_INTERVAL,
                "critical_force_threshold": self.CRITICAL_FORCE_THRESHOLD,
                "next_priority_slot_in": self.PRIORITY_SLOT_INTERVAL - (self._selection_counter % self.PRIORITY_SLOT_INTERVAL),
                "starving_actions": [a.id for a in starving_actions],
                "starving_count": len(starving_actions),
                "overdue_actions": [a.id for a in overdue_actions],
                "overdue_count": len(overdue_actions),
                "hours_since_high_priority": round(
                    (datetime.now() - self._last_high_priority_time).total_seconds() / 3600, 2
                )
            },
            "actions": {
                a.id: {
                    "name": a.name,
                    "category": a.category.value,
                    "priority": a.priority.value,
                    "execution_count": a.execution_count,
                    "last_executed": a.last_executed.isoformat() if a.last_executed else None,
                    "enabled": a.enabled,
                    "available": a.is_available(),
                    "error_count": a.error_count,
                    "consecutive_failures": a.consecutive_failures,
                    "disabled_until": a.disabled_until.isoformat() if a.disabled_until else None,
                    # Starvation stats
                    "skipped_count": a.skipped_count,
                    "is_starving": a.is_starving(),
                    "is_overdue": a.is_overdue(),
                    "max_hours_between_runs": a.max_hours_between_runs
                }
                for a in self.actions.values()
            }
        }


# Global instance
_proactive_engine: Optional[ProactiveEngine] = None


def get_proactive_engine(mood_system: Optional["MoodSystem"] = None) -> ProactiveEngine:
    """
    Get or create the proactive engine instance.

    Args:
        mood_system: Optional MoodSystem to integrate. If provided and engine
                     already exists, will set the mood system on it.

    Returns:
        ProactiveEngine singleton instance
    """
    global _proactive_engine
    if _proactive_engine is None:
        _proactive_engine = ProactiveEngine(mood_system=mood_system)
    elif mood_system is not None and _proactive_engine._mood_system is None:
        _proactive_engine.set_mood_system(mood_system)
    return _proactive_engine


def init_proactive_engine_with_mood(mood_system: "MoodSystem") -> ProactiveEngine:
    """
    Initialize or update the proactive engine with mood system integration.

    This should be called during system startup after mood system is created.

    Args:
        mood_system: MoodSystem instance for mood-action integration

    Returns:
        ProactiveEngine with mood integration enabled
    """
    engine = get_proactive_engine(mood_system)
    logger.info("ProactiveEngine mood integration initialized")
    return engine
