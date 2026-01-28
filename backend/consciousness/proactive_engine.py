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
    metadata: Dict[str, Any] = field(default_factory=dict)


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
        self._register_default_actions()

        logger.info("ProactiveEngine initialized")

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
            cooldown_minutes=15
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
            cooldown_minutes=180  # Every 3 hours
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
        Get actions that are available to execute (not on cooldown).

        Args:
            category: Filter by category
            min_priority: Minimum priority level

        Returns:
            List of available actions
        """
        now = datetime.now()
        available = []

        for action in self.actions.values():
            if not action.enabled:
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

        # Add some randomness (10% chance to pick a random action)
        if random.random() < 0.1 and len(scored) > 1:
            return random.choice(available)

        return scored[0][0] if scored else None

    def _score_action(
        self,
        action: ProactiveAction,
        context: Dict[str, Any]
    ) -> float:
        """Score an action based on current context."""
        score = action.priority.value * 10

        # Bonus for actions not executed recently
        if action.last_executed:
            hours_since = (datetime.now() - action.last_executed).total_seconds() / 3600
            score += min(hours_since * 2, 20)  # Max 20 point bonus
        else:
            score += 15  # Never executed bonus

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

            # Execute the action function if provided
            if action.action_fn:
                if asyncio.iscoroutinefunction(action.action_fn):
                    result["output"] = await action.action_fn(context)
                else:
                    result["output"] = action.action_fn(context)
            else:
                # Default execution based on action type
                result["output"] = await self._default_execution(action, context)

            # Update action metadata
            action.last_executed = datetime.now()
            action.execution_count += 1

            # Record in history
            result["completed_at"] = datetime.now().isoformat()
            result["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            self.action_history.append(result)

            logger.info(f"✅ Completed: {action.name} in {result['duration_seconds']:.2f}s")

            return result

        except Exception as e:
            logger.error(f"❌ Action failed: {action.name} - {e}")
            return {
                "action_id": action.id,
                "action_name": action.name,
                "success": False,
                "error": str(e)
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
                inbox.add_finding(
                    type=FindingType.DISCOVERY,
                    title=f"Found project: {project.get('name', 'Unknown')}",
                    description=f"Discovered {project.get('primary_type', 'unknown')} project at {project.get('path')} with {stats.get('code_files', 0)} code files and {stats.get('total_lines', 0)} lines of code.",
                    source="explore_local_projects",
                    priority=FindingPriority.LOW,
                    expires_in_days=7,
                    metadata={
                        "project_path": project.get("path"),
                        "project_type": project.get("primary_type"),
                        "languages": stats.get("languages", {}),
                        "has_readme": bool(project.get("readme_preview"))
                    }
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

        # Create findings for anomalies
        findings_created = 0
        for anomaly in anomalies:
            priority = FindingPriority.HIGH if anomaly.severity == "critical" else FindingPriority.MEDIUM
            inbox.add_finding(
                type=FindingType.ANOMALY,
                title=f"System {anomaly.type.upper()}: {anomaly.severity.upper()}",
                description=anomaly.description,
                source="monitor_system_health",
                priority=priority,
                expires_in_days=1,  # Short expiry for system issues
                metadata={
                    "anomaly_type": anomaly.type,
                    "severity": anomaly.severity,
                    "value": anomaly.value,
                    "threshold": anomaly.threshold
                }
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

            # Create insights from analysis
            if health_analysis["issues"]:
                inbox.add_finding(
                    type=FindingType.INSIGHT,
                    title=f"Analysis of {health_analysis['project_name']}",
                    description=f"Project health score: {health_analysis['health_score']}/100. Issues: {', '.join(health_analysis['issues'][:3])}. Positives: {', '.join(health_analysis['positive_indicators'][:3])}",
                    source="analyze_new_discoveries",
                    priority=FindingPriority.LOW,
                    expires_in_days=14,
                    metadata={
                        "project_path": project_path,
                        "health_score": health_analysis["health_score"],
                        "issues": health_analysis["issues"],
                        "positive_indicators": health_analysis["positive_indicators"]
                    }
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
            }
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
                "category": "observation",
                "shared_at": datetime.now().isoformat()
            }
        )

        return {
            "insight": insight,
            "category": "observation",
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
                }
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
                }
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
            }
        )

        return {
            "total_actions_executed": total_actions,
            "most_used_action": most_used.name if most_used else None,
            "least_used_action": least_used.name if least_used else None,
            "action_distribution": action_distribution,
            "category_distribution": category_counts,
            "reflection": reflection_text
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

    def stop(self):
        """Stop the proactive loop."""
        self.running = False
        logger.info("Proactive loop stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        return {
            "running": self.running,
            "total_actions": len(self.actions),
            "enabled_actions": sum(1 for a in self.actions.values() if a.enabled),
            "total_executions": sum(a.execution_count for a in self.actions.values()),
            "recent_history": self.action_history[-10:],
            "actions": {
                a.id: {
                    "name": a.name,
                    "category": a.category.value,
                    "priority": a.priority.value,
                    "execution_count": a.execution_count,
                    "last_executed": a.last_executed.isoformat() if a.last_executed else None,
                    "enabled": a.enabled
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
