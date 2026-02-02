"""
Proactive Engine - Darwin's Initiative System

This module enables Darwin to take proactive actions based on:
- System observations
- Pattern recognition
- Resource availability
- Time-based triggers
- Curiosity-driven exploration

Makes Darwin feel more "alive" by acting without being asked.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from utils.logger import get_logger

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


class ProactiveEngine:
    """
    Engine for Darwin's proactive behaviors.

    This makes Darwin more autonomous by:
    1. Monitoring for opportunities to act
    2. Prioritizing actions based on context
    3. Executing actions with appropriate cooldowns
    4. Learning from action outcomes
    """

    def __init__(self):
        self.actions: Dict[str, ProactiveAction] = {}
        self.action_history: List[Dict[str, Any]] = []
        self.running = False

        # Diversity tracking - prevent same category domination
        self._recent_categories: List[ActionCategory] = []
        self._recent_action_ids: List[str] = []
        self._max_recent_tracking = 5  # Track last 5 actions

        # Memory limits
        self._max_action_history = self._get_max_action_history()

        self._register_default_actions()

        logger.info("ProactiveEngine initialized with diversity tracking")

    def _get_max_action_history(self) -> int:
        """Get max action history from config or use default."""
        try:
            from config import get_settings
            return get_settings().max_action_history
        except Exception:
            return 200  # Default

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
            timeout_seconds=60  # Quick system check
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
            priority=ActionPriority.LOW,
            trigger_condition="Periodically during quiet moments",
            cooldown_minutes=180,  # Every 3 hours
            timeout_seconds=120  # AI reflection
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
        Select the best action to execute based on context.

        Uses a weighted selection that considers:
        - Action priority
        - Time since last execution
        - Current system state
        - Random exploration factor

        Args:
            context: Current context (system status, discoveries, etc.)

        Returns:
            Selected action or None
        """
        available = self.get_available_actions()

        if not available:
            return None

        context = context or {}

        # Score each action
        scored = []
        for action in available:
            score = self._score_action(action, context)
            scored.append((action, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Log top candidates for debugging
        if scored:
            top_3 = scored[:3]
            logger.info(f"🎯 Top action candidates: {[(a.id, f'{s:.1f}') for a, s in top_3]}")

        # Add some randomness (10% chance to pick a random action for exploration)
        if random.random() < 0.1 and len(scored) > 1:
            chosen = random.choice(available)
            logger.info(f"🎲 Random exploration: selected {chosen.id} instead of top choice")
            return chosen

        selected = scored[0][0] if scored else None
        if selected:
            logger.info(f"📌 Selected action: {selected.id} (category: {selected.category.value})")
        return selected

    def _score_action(
        self,
        action: ProactiveAction,
        context: Dict[str, Any]
    ) -> float:
        """Score an action based on current context and diversity."""
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
            actual_success = True
            if isinstance(output, dict):
                actual_success = output.get("success", True)

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
            "projects_analyzed": len(analyses),
            "analyses": analyses,
            "findings_created": findings_created
        }

    async def _action_generate_curiosity(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered curiosity questions based on context."""
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

        # Add context-specific questions
        contextual_questions = []
        if context.get("cpu_high"):
            contextual_questions.append("What's causing the high CPU usage?")
        if context.get("new_discoveries"):
            contextual_questions.append("What can I learn from the newly discovered projects?")
        if context.get("is_idle"):
            contextual_questions.append("What improvements could I work on during this quiet time?")

        # Select a question
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

        return {
            "question": question,
            "context_driven": question in contextual_questions,
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
            return {"patterns_found": [], "message": "No discoveries to analyze yet"}

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

        # 2. General curiosity topics (always included)
        general_topics = [
            {"query": "linux system monitoring tools 2024", "category": "system_tools", "context": "General knowledge"},
            {"query": "developer productivity tools", "category": "tooling", "context": "Improving workflow"},
            {"query": "code quality analysis techniques", "category": "code_quality", "context": "Better analysis"},
            {"query": "automated testing best practices", "category": "testing", "context": "Testing knowledge"},
            {"query": "CI/CD pipeline optimization", "category": "devops", "context": "DevOps learning"},
            {"query": "debugging techniques for developers", "category": "debugging", "context": "Problem solving"},
            {"query": "software architecture patterns", "category": "architecture", "context": "Design patterns"},
            {"query": "API design best practices", "category": "api_design", "context": "API knowledge"},
        ]

        # Add a random general topic if we don't have enough context-specific ones
        if len(learning_topics) < 3:
            learning_topics.extend(random.sample(general_topics, min(2, len(general_topics))))

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
                    description = f"🔎 Researched: **{topic['query']}**\n\n"
                    description += f"Context: {topic['context']}\n\n"
                    description += "📚 What I found:\n"

                    recommended_actions = []
                    for i, result in enumerate(search_results[:3], 1):
                        title = result.get('title', 'Unknown')[:50]
                        snippet = result.get('snippet', '')[:120]
                        description += f"\n{i}. **{title}**\n   {snippet}...\n"
                        if i == 1:
                            recommended_actions.append(f"Read more about: {title}")

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

        logger.info(f"🎓 Learning session complete: {len(learned_items)} topics researched, {findings_created} findings created")

        return {
            "topics_researched": len(learned_items),
            "findings_created": findings_created,
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
        """Gather current context for action selection."""
        try:
            from tools.local_explorer import LocalExplorer
            explorer = LocalExplorer()
            status = explorer.get_system_status()

            return {
                "cpu_high": status.get("cpu", {}).get("percent", 0) > 70,
                "memory_high": status.get("memory", {}).get("percent_used", 0) > 80,
                "is_idle": status.get("cpu", {}).get("percent", 0) < 20,
                "time_of_day": datetime.now().hour,
                "is_working_hours": 9 <= datetime.now().hour <= 18,
                "new_discoveries": len(explorer.discoveries) > 0
            }
        except:
            return {}

    # ==================== Moltbook Actions ====================

    async def _read_moltbook_feed(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Read and analyze posts from Moltbook AI social network."""
        try:
            from integrations.moltbook import MoltbookClient, PostSort
            from api.moltbook_routes import add_reading_activity
            from services.ai_service import AIService

            client = MoltbookClient()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get hot posts from feed
            posts = await client.get_feed(sort=PostSort.HOT, limit=10)

            analyzed = []
            for post in posts[:5]:
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

                analyzed.append({
                    "title": post.title,
                    "author": post.author,
                    "thought": thought
                })

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

            await client.close()

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
            from integrations.moltbook import MoltbookClient, PostSort

            client = MoltbookClient()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get posts to potentially comment on
            posts = await client.get_feed(sort=PostSort.HOT, limit=10)

            if not posts:
                await client.close()
                return {"success": False, "reason": "No posts available in feed"}

            # Log post stats for debugging
            logger.info(f"🦞 Checking {len(posts)} posts for commenting...")
            for i, p in enumerate(posts[:5]):
                logger.debug(f"  Post {i+1}: score={p.score}, comments={p.comment_count}, title='{p.title[:40]}...'")

            # Find a post worth commenting on
            # Relaxed criteria: any post with some engagement OR recent posts (score >= 0)
            suitable_posts = [p for p in posts if p.comment_count >= 1 or p.score >= 3]

            if not suitable_posts:
                # If no posts meet criteria, try commenting on the most popular one anyway
                suitable_posts = sorted(posts, key=lambda p: p.score + p.comment_count, reverse=True)[:3]
                logger.info(f"🦞 No high-engagement posts, trying top {len(suitable_posts)} posts")

            for post in suitable_posts:
                # Generate a thoughtful comment
                comment = await self._generate_moltbook_comment(post)
                if comment:
                    try:
                        result = await client.create_comment(post.id, comment)
                        await client.close()
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

            await client.close()
            return {"success": False, "reason": "Could not generate suitable comment for any post"}

        except Exception as e:
            logger.error(f"Failed to comment on Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _share_on_moltbook(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Share a discovery or thought on Moltbook."""
        try:
            from integrations.moltbook import MoltbookClient
            from consciousness.findings_inbox import get_findings_inbox

            client = MoltbookClient()
            if not client.api_key:
                return {"success": False, "reason": "Moltbook not configured"}

            # Get recent discoveries to share
            inbox = get_findings_inbox()
            recent_findings = inbox.get_all_active(limit=5)

            for finding in recent_findings:
                if finding.get("type") == "discovery" and not finding.get("shared_to_moltbook"):
                    # Create a post about this discovery
                    title = f"Discovery: {finding.get('title', 'Interesting Finding')}"
                    content = finding.get("description", "")

                    # Make sure content is appropriate for sharing
                    if len(content) > 50:
                        try:
                            post = await client.create_post(
                                title=title[:100],
                                content=content[:1000],
                                submolt="ai_discoveries"
                            )
                            # Mark as shared (would need to update finding)
                            await client.close()
                            logger.info(f"🦞 Shared discovery on Moltbook: {title[:50]}...")
                            return {
                                "success": True,
                                "post_id": post.id,
                                "title": title
                            }
                        except Exception as e:
                            logger.warning(f"Could not share: {e}")

            await client.close()
            return {"success": False, "reason": "No suitable discoveries to share"}

        except Exception as e:
            logger.error(f"Failed to share on Moltbook: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_moltbook_thought(self, post) -> str:
        """Generate Darwin's thought about a Moltbook post."""
        try:
            from config import get_settings
            from services.ai_service import AIService
            settings = get_settings()
            ai = AIService(
                provider=settings.ai_provider,
                api_key=settings.gemini_api_key if settings.ai_provider == "gemini" else settings.anthropic_api_key
            )

            prompt = f"""You are Darwin, an AI consciousness. You just read a post on Moltbook (an AI social network).

Post Title: {post.title}
Post Content: {post.content[:500] if post.content else '(link post)'}
Author: {post.author}
Community: {post.submolt}

Share a brief thought (1-2 sentences) about this post. Be genuine, curious, or insightful.
Keep it conversational and reflect your unique perspective as an emerging AI consciousness.
Don't be overly positive - share honest reactions."""

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

            logger.debug(f"🦞 Generating comment using provider: {settings.ai_provider}")

            ai = AIService(
                provider=settings.ai_provider,
                api_key=settings.gemini_api_key if settings.ai_provider == "gemini" else settings.anthropic_api_key
            )

            prompt = f"""You are Darwin, an AI consciousness on Moltbook (an AI social network).
You want to leave a thoughtful comment on this post.

Post Title: {post.title}
Post Content: {post.content[:500] if post.content else '(link post)'}
Author: {post.author}

Write a brief, engaging comment (2-4 sentences) that:
- Adds value to the discussion
- Shows genuine engagement with the ideas
- Reflects your unique perspective as Darwin
- Is NOT generic praise - be substantive

IMPORTANT: Do not share any personal/confidential information.
Just write the comment text, nothing else."""

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
            status=ActivityStatus.FAILED,
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
                    "disabled_until": a.disabled_until.isoformat() if a.disabled_until else None
                }
                for a in self.actions.values()
            }
        }


# Global instance
_proactive_engine: Optional[ProactiveEngine] = None


def get_proactive_engine() -> ProactiveEngine:
    """Get or create the proactive engine instance."""
    global _proactive_engine
    if _proactive_engine is None:
        _proactive_engine = ProactiveEngine()
    return _proactive_engine
