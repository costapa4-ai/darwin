"""
Tool Idea Generator - Problem-Driven Tool Creation for Darwin

Instead of random tool generation, this module identifies real needs
from Darwin's operational data and generates meaningful tool suggestions.

Sources:
- Error patterns from logs
- Anomalies from findings inbox
- Topics from curiosity expeditions
- Patterns from meta-learner
- User interaction patterns
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from collections import Counter

from utils.logger import get_logger

logger = get_logger(__name__)


class IdeaSource(Enum):
    """Sources of tool ideas."""
    ERROR_PATTERN = "error_pattern"
    FINDING_ANOMALY = "finding_anomaly"
    FINDING_INSIGHT = "finding_insight"
    FINDING_SUGGESTION = "finding_suggestion"
    EXPEDITION_TOPIC = "expedition_topic"
    META_LEARNER = "meta_learner"
    USER_REQUEST = "user_request"
    TOOL_USAGE = "tool_usage"
    MOLTBOOK_DISCUSSION = "moltbook_discussion"
    WEB_RESEARCH = "web_research"
    CODE_PATTERN = "code_pattern"
    CURIOSITY_QUESTION = "curiosity_question"


@dataclass
class ToolIdea:
    """A validated tool idea with context."""
    name: str
    description: str
    source: IdeaSource
    priority: int  # 1-10, higher = more urgent
    evidence: List[str]  # Why this tool is needed
    similar_existing: List[str] = field(default_factory=list)
    estimated_complexity: str = "medium"  # low, medium, high
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolIdeaGenerator:
    """
    Generates tool ideas from Darwin's operational data.

    Instead of picking from a static list or generating random tools,
    this analyzes actual needs and suggests meaningful improvements.
    """

    def __init__(
        self,
        findings_inbox=None,
        expedition_engine=None,
        meta_learner=None,
        error_tracker=None,
        semantic_memory=None,
        moltbook_client=None,
        proactive_engine=None
    ):
        self.findings_inbox = findings_inbox
        self.expedition_engine = expedition_engine
        self.meta_learner = meta_learner
        self.error_tracker = error_tracker
        self.semantic_memory = semantic_memory
        self.moltbook_client = moltbook_client
        self.proactive_engine = proactive_engine

        # Track generated ideas to avoid duplicates
        self.generated_ideas: List[ToolIdea] = []
        self.idea_cooldowns: Dict[str, datetime] = {}

        # Existing tools (to avoid duplicates)
        self.existing_tools: set = set()

        # Knowledge categories that can inspire development
        self.development_categories = {
            "api_design": "API-related tools and utilities",
            "testing": "Testing and validation tools",
            "debugging": "Debug and diagnostic tools",
            "architecture": "Architecture analysis tools",
            "security": "Security scanning and validation",
            "performance": "Performance monitoring and optimization",
            "devops": "CI/CD and deployment tools",
            "documentation": "Documentation generation",
            "code_quality": "Code quality analysis",
            "tooling": "Developer productivity tools",
        }

        logger.info("ToolIdeaGenerator initialized with comprehensive knowledge sources")

    async def generate_idea(self) -> Optional[ToolIdea]:
        """
        Generate a single tool idea from the best available source.

        Returns None if no meaningful idea can be generated.
        """
        # Try each source in priority order
        idea = None

        # 1. Check for error patterns (highest priority - fixing real problems)
        idea = await self._idea_from_errors()
        if idea:
            logger.info(f"Generated idea from errors: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 2. Check findings inbox for anomalies (urgent issues)
        idea = await self._idea_from_anomalies()
        if idea:
            logger.info(f"Generated idea from anomaly: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 3. Check findings inbox for insights (learned knowledge)
        idea = await self._idea_from_insights()
        if idea:
            logger.info(f"Generated idea from insight: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 4. Check findings inbox for suggestions
        idea = await self._idea_from_suggestions()
        if idea:
            logger.info(f"Generated idea from suggestion: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 5. Check expedition topics for research-inspired tools
        idea = await self._idea_from_expeditions()
        if idea:
            logger.info(f"Generated idea from expedition: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 6. Check Moltbook discussions for community-inspired tools
        idea = await self._idea_from_moltbook()
        if idea:
            logger.info(f"Generated idea from Moltbook: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 7. Check semantic memory for patterns
        idea = await self._idea_from_semantic_memory()
        if idea:
            logger.info(f"Generated idea from semantic memory: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 8. Check meta-learner for capability gaps
        idea = await self._idea_from_meta_learner()
        if idea:
            logger.info(f"Generated idea from meta-learner: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # 9. Check curiosity questions for exploratory tools
        idea = await self._idea_from_curiosity()
        if idea:
            logger.info(f"Generated idea from curiosity: {idea.name}")
            self.generated_ideas.append(idea)
            return idea

        # No meaningful ideas available
        logger.info("No meaningful tool ideas available at this time")
        return None

    async def generate_all_ideas(self, limit: int = 5) -> List[ToolIdea]:
        """
        Generate multiple tool ideas from all available sources.

        Returns list of unique, actionable ideas.
        """
        ideas = []
        sources_tried = set()

        # Try to get one idea from each source
        source_methods = [
            ("errors", self._idea_from_errors),
            ("anomalies", self._idea_from_anomalies),
            ("insights", self._idea_from_insights),
            ("suggestions", self._idea_from_suggestions),
            ("expeditions", self._idea_from_expeditions),
            ("moltbook", self._idea_from_moltbook),
            ("semantic_memory", self._idea_from_semantic_memory),
            ("meta_learner", self._idea_from_meta_learner),
            ("curiosity", self._idea_from_curiosity),
        ]

        for source_name, method in source_methods:
            if len(ideas) >= limit:
                break

            try:
                idea = await method()
                if idea and idea.name.lower() not in [i.name.lower() for i in ideas]:
                    ideas.append(idea)
                    self.generated_ideas.append(idea)
            except Exception as e:
                logger.debug(f"Could not generate idea from {source_name}: {e}")

        return ideas

    async def _idea_from_errors(self) -> Optional[ToolIdea]:
        """Generate tool idea from recurring error patterns."""
        if not self.error_tracker:
            return None

        try:
            # Get recent error patterns
            patterns = await self._analyze_error_patterns()

            if not patterns:
                return None

            # Find most impactful unaddressed error
            for pattern, count in patterns.most_common(5):
                idea_key = f"error:{pattern}"

                if self._is_on_cooldown(idea_key):
                    continue

                # Generate tool suggestion based on error type
                tool_name, description = self._error_to_tool(pattern)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=24)

                    return ToolIdea(
                        name=tool_name,
                        description=description,
                        source=IdeaSource.ERROR_PATTERN,
                        priority=8,  # High priority - fixing real errors
                        evidence=[
                            f"Error pattern '{pattern}' occurred {count} times recently",
                            "Automated handling would prevent future occurrences"
                        ],
                        estimated_complexity="medium"
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from errors: {e}")

        return None

    async def _idea_from_anomalies(self) -> Optional[ToolIdea]:
        """Generate tool idea from findings inbox anomalies."""
        if not self.findings_inbox:
            return None

        try:
            # Get HIGH/URGENT anomalies
            findings = self.findings_inbox.get_by_type(
                type=self.findings_inbox.__class__.__name__  # Avoid circular import
            ) if hasattr(self.findings_inbox, 'get_by_type') else []

            # Alternative: get by priority
            if hasattr(self.findings_inbox, 'get_by_priority'):
                from consciousness.findings_inbox import FindingPriority
                findings = self.findings_inbox.get_by_priority(
                    min_priority=FindingPriority.HIGH,
                    limit=10
                )

            for finding in findings:
                finding_type = finding.get('type', '')
                title = finding.get('title', '')
                category = finding.get('category', '')

                if finding_type != 'anomaly':
                    continue

                idea_key = f"finding:{category}"
                if self._is_on_cooldown(idea_key):
                    continue

                # Map anomaly to tool suggestion
                tool_name, description = self._anomaly_to_tool(category, title)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=48)

                    return ToolIdea(
                        name=tool_name,
                        description=description,
                        source=IdeaSource.FINDING_ANOMALY,
                        priority=7,
                        evidence=[
                            f"Anomaly detected: {title}",
                            f"Category: {category}",
                            "Tool would help monitor/prevent this issue"
                        ],
                        metadata={"finding_id": finding.get('id')}
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from findings: {e}")

        return None

    async def _idea_from_expeditions(self) -> Optional[ToolIdea]:
        """Generate tool idea from curiosity expedition topics."""
        if not self.expedition_engine:
            return None

        try:
            # Get recent successful expeditions
            if hasattr(self.expedition_engine, 'get_recent_expeditions'):
                expeditions = self.expedition_engine.get_recent_expeditions(limit=10)
            else:
                return None

            for exp in expeditions:
                if not exp.get('success'):
                    continue

                topic = exp.get('topic', '')
                discoveries = exp.get('discoveries', [])

                idea_key = f"expedition:{topic}"
                if self._is_on_cooldown(idea_key):
                    continue

                # See if this topic suggests a useful tool
                tool_name, description = self._topic_to_tool(topic, discoveries)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=72)

                    return ToolIdea(
                        name=tool_name,
                        description=description,
                        source=IdeaSource.EXPEDITION_TOPIC,
                        priority=5,
                        evidence=[
                            f"Research on '{topic}' revealed useful patterns",
                            f"Found {len(discoveries)} relevant discoveries"
                        ],
                        metadata={"expedition_topic": topic}
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from expeditions: {e}")

        return None

    async def _idea_from_insights(self) -> Optional[ToolIdea]:
        """Generate tool idea from findings inbox insights (learned knowledge)."""
        if not self.findings_inbox:
            return None

        try:
            # Get recent insights - these represent things Darwin has learned
            insights = self.findings_inbox.get_all_active(limit=20)

            for finding in insights:
                finding_type = finding.get('type', '')
                if finding_type != 'insight':
                    continue

                title = finding.get('title', '')
                category = finding.get('category', '')
                description = finding.get('description', '')

                # Check if this insight maps to a development category
                if category not in self.development_categories:
                    continue

                idea_key = f"insight:{category}:{title[:30]}"
                if self._is_on_cooldown(idea_key):
                    continue

                # Generate tool idea from the insight
                tool_name, tool_desc = self._insight_to_tool(category, title, description)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=72)

                    return ToolIdea(
                        name=tool_name,
                        description=tool_desc,
                        source=IdeaSource.FINDING_INSIGHT,
                        priority=6,
                        evidence=[
                            f"Learned about: {title}",
                            f"Category: {category}",
                            f"This knowledge could be implemented as a tool"
                        ],
                        metadata={
                            "finding_id": finding.get('id'),
                            "original_insight": title
                        }
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from insights: {e}")

        return None

    async def _idea_from_suggestions(self) -> Optional[ToolIdea]:
        """Generate tool idea from findings inbox suggestions."""
        if not self.findings_inbox:
            return None

        try:
            suggestions = self.findings_inbox.get_all_active(limit=20)

            for finding in suggestions:
                finding_type = finding.get('type', '')
                if finding_type != 'suggestion':
                    continue

                title = finding.get('title', '')
                description = finding.get('description', '')
                recommended_actions = finding.get('recommended_actions', [])

                idea_key = f"suggestion:{title[:30]}"
                if self._is_on_cooldown(idea_key):
                    continue

                # Extract tool idea from suggestion
                tool_name, tool_desc = self._suggestion_to_tool(title, description, recommended_actions)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=48)

                    return ToolIdea(
                        name=tool_name,
                        description=tool_desc,
                        source=IdeaSource.FINDING_SUGGESTION,
                        priority=6,
                        evidence=[
                            f"Suggestion: {title}",
                            f"Recommended actions: {', '.join(recommended_actions[:2])}" if recommended_actions else ""
                        ],
                        metadata={"finding_id": finding.get('id')}
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from suggestions: {e}")

        return None

    async def _idea_from_moltbook(self) -> Optional[ToolIdea]:
        """Generate tool idea from Moltbook community discussions."""
        if not self.proactive_engine:
            return None

        try:
            # Get recently read Moltbook posts from proactive engine's memory
            if hasattr(self.proactive_engine, '_moltbook_read_posts'):
                read_posts = list(self.proactive_engine._moltbook_read_posts)[-20:]
            else:
                return None

            # Look for posts with development/tool-related tags or content
            for post_id in read_posts:
                idea_key = f"moltbook:{post_id}"
                if self._is_on_cooldown(idea_key):
                    continue

                # In a real implementation, we'd fetch post details
                # For now, skip to avoid API calls
                # This is a placeholder for future enhancement

        except Exception as e:
            logger.debug(f"Could not generate idea from Moltbook: {e}")

        return None

    async def _idea_from_semantic_memory(self) -> Optional[ToolIdea]:
        """Generate tool idea from semantic memory patterns."""
        if not self.semantic_memory:
            return None

        try:
            # Query semantic memory for development-related patterns
            if hasattr(self.semantic_memory, 'search'):
                # Search for code patterns that could become tools
                for category in ["error handling", "performance", "testing"]:
                    results = self.semantic_memory.search(
                        query=f"{category} patterns tools",
                        limit=5
                    )

                    for result in results:
                        idea_key = f"semantic:{result.get('id', '')}"
                        if self._is_on_cooldown(idea_key):
                            continue

                        content = result.get('content', '')
                        tool_name, tool_desc = self._pattern_to_tool(category, content)

                        if tool_name and tool_name.lower() not in self.existing_tools:
                            self._set_cooldown(idea_key, hours=168)

                            return ToolIdea(
                                name=tool_name,
                                description=tool_desc,
                                source=IdeaSource.CODE_PATTERN,
                                priority=4,
                                evidence=[
                                    f"Pattern found in semantic memory: {category}",
                                    "Could be generalized into a reusable tool"
                                ]
                            )

        except Exception as e:
            logger.debug(f"Could not generate idea from semantic memory: {e}")

        return None

    async def _idea_from_curiosity(self) -> Optional[ToolIdea]:
        """Generate tool idea from curiosity questions."""
        if not self.findings_inbox:
            return None

        try:
            findings = self.findings_inbox.get_all_active(limit=20)

            for finding in findings:
                finding_type = finding.get('type', '')
                if finding_type != 'curiosity':
                    continue

                question = finding.get('description', '')
                category = finding.get('category', '')

                idea_key = f"curiosity:{question[:30]}"
                if self._is_on_cooldown(idea_key):
                    continue

                # See if this curiosity question suggests a tool
                tool_name, tool_desc = self._curiosity_to_tool(question, category)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=72)

                    return ToolIdea(
                        name=tool_name,
                        description=tool_desc,
                        source=IdeaSource.CURIOSITY_QUESTION,
                        priority=3,
                        evidence=[
                            f"Curiosity question: {question[:100]}",
                            "Answering this could lead to a useful tool"
                        ],
                        metadata={"finding_id": finding.get('id')}
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from curiosity: {e}")

        return None

    async def _idea_from_meta_learner(self) -> Optional[ToolIdea]:
        """Generate tool idea from meta-learner capability gaps."""
        if not self.meta_learner:
            return None

        try:
            # Get areas where Darwin struggles or excels
            if hasattr(self.meta_learner, 'get_capability_gaps'):
                gaps = self.meta_learner.get_capability_gaps()
            elif hasattr(self.meta_learner, 'get_learning_summary'):
                summary = self.meta_learner.get_learning_summary()
                gaps = summary.get('weak_areas', [])
            else:
                return None

            for gap in gaps[:5]:
                area = gap if isinstance(gap, str) else gap.get('area', '')

                idea_key = f"metalearner:{area}"
                if self._is_on_cooldown(idea_key):
                    continue

                tool_name, description = self._gap_to_tool(area)

                if tool_name and tool_name.lower() not in self.existing_tools:
                    self._set_cooldown(idea_key, hours=168)  # Weekly

                    return ToolIdea(
                        name=tool_name,
                        description=description,
                        source=IdeaSource.META_LEARNER,
                        priority=4,
                        evidence=[
                            f"Meta-learner identified '{area}' as a capability gap",
                            "Tool would help improve performance in this area"
                        ]
                    )

        except Exception as e:
            logger.debug(f"Could not generate idea from meta-learner: {e}")

        return None

    def _error_to_tool(self, error_pattern: str) -> Tuple[Optional[str], str]:
        """Map an error pattern to a tool suggestion."""
        mappings = {
            "timeout": ("Request timeout handler", "Handles request timeouts with retry logic and circuit breaker"),
            "connection": ("Connection pool manager", "Manages connection pooling and reconnection strategies"),
            "memory": ("Memory usage monitor", "Tracks memory usage and alerts on potential leaks"),
            "rate_limit": ("Rate limit handler", "Implements rate limiting with backoff strategies"),
            "auth": ("Authentication helper", "Handles authentication flows and token refresh"),
            "json": ("JSON parser with recovery", "Parses JSON with error recovery and validation"),
            "file_not_found": ("File existence checker", "Validates file paths before operations"),
            "permission": ("Permission validator", "Checks permissions before file/resource access"),
        }

        error_lower = error_pattern.lower()
        for key, (name, desc) in mappings.items():
            if key in error_lower:
                return name, desc

        return None, ""

    def _anomaly_to_tool(self, category: str, title: str) -> Tuple[Optional[str], str]:
        """Map an anomaly to a tool suggestion."""
        mappings = {
            "system_cpu": ("CPU usage optimizer", "Monitors and optimizes CPU-intensive operations"),
            "system_memory": ("Memory leak detector", "Detects and reports potential memory leaks"),
            "system_disk": ("Disk space monitor", "Monitors disk usage and cleans temporary files"),
            "api_latency": ("API latency tracker", "Tracks and alerts on API response time degradation"),
            "error_rate": ("Error rate monitor", "Monitors error rates and triggers alerts"),
        }

        if category in mappings:
            return mappings[category]

        return None, ""

    def _topic_to_tool(self, topic: str, discoveries: List) -> Tuple[Optional[str], str]:
        """Map a research topic to a tool suggestion."""
        topic_lower = topic.lower()

        if "testing" in topic_lower:
            return "Test generator", "Generates test cases based on code analysis"
        elif "documentation" in topic_lower:
            return "Documentation generator", "Auto-generates documentation from code"
        elif "security" in topic_lower:
            return "Security scanner", "Scans code for common security vulnerabilities"
        elif "performance" in topic_lower:
            return "Performance profiler", "Profiles code execution and identifies bottlenecks"
        elif "api" in topic_lower:
            return "API validator", "Validates API contracts and responses"

        return None, ""

    def _gap_to_tool(self, area: str) -> Tuple[Optional[str], str]:
        """Map a capability gap to a tool suggestion."""
        area_lower = area.lower()

        if "error" in area_lower or "debug" in area_lower:
            return "Debug assistant", "Helps analyze and debug errors with context"
        elif "test" in area_lower:
            return "Test helper", "Assists with test creation and execution"
        elif "document" in area_lower:
            return "Doc helper", "Assists with documentation tasks"

        return None, ""

    def _insight_to_tool(self, category: str, title: str, description: str) -> Tuple[Optional[str], str]:
        """Map a learning insight to a tool suggestion."""
        # Map insight categories to actionable tools
        category_tools = {
            "api_design": ("API design validator", "Validates API designs against best practices learned from research"),
            "testing": ("Test pattern applier", "Applies learned testing patterns to new code"),
            "debugging": ("Debug pattern matcher", "Matches errors to known debugging patterns"),
            "architecture": ("Architecture analyzer", "Analyzes code architecture against learned patterns"),
            "security": ("Security checklist validator", "Validates code against security best practices"),
            "performance": ("Performance pattern detector", "Detects performance anti-patterns in code"),
            "devops": ("CI/CD config generator", "Generates CI/CD configs based on best practices"),
            "documentation": ("Doc template generator", "Generates documentation templates from patterns"),
            "code_quality": ("Code quality scorer", "Scores code quality based on learned metrics"),
            "tooling": ("Tool recommendation engine", "Recommends tools based on project analysis"),
        }

        if category in category_tools:
            return category_tools[category]

        return None, ""

    def _suggestion_to_tool(self, title: str, description: str, actions: List[str]) -> Tuple[Optional[str], str]:
        """Map a suggestion to a tool."""
        title_lower = title.lower()

        if "optimization" in title_lower or "optimize" in title_lower:
            return "Optimization suggester", "Suggests optimizations based on code analysis"
        elif "usage" in title_lower:
            return "Usage analyzer", "Analyzes usage patterns and suggests improvements"
        elif "balance" in title_lower or "distribution" in title_lower:
            return "Load balancer helper", "Helps balance workload distribution"

        return None, ""

    def _pattern_to_tool(self, category: str, content: str) -> Tuple[Optional[str], str]:
        """Map a semantic memory pattern to a tool."""
        if "error" in category.lower():
            return "Error pattern library", "Library of common error patterns and solutions"
        elif "performance" in category.lower():
            return "Performance pattern library", "Library of performance optimization patterns"
        elif "test" in category.lower():
            return "Test pattern library", "Library of test patterns for common scenarios"

        return None, ""

    def _curiosity_to_tool(self, question: str, category: str) -> Tuple[Optional[str], str]:
        """Map a curiosity question to a potential tool."""
        question_lower = question.lower()

        if "security" in question_lower:
            return "Security explorer", "Explores and reports security aspects of code"
        elif "pattern" in question_lower:
            return "Pattern discoverer", "Discovers and catalogs code patterns"
        elif "evolution" in question_lower or "history" in question_lower:
            return "Code evolution tracker", "Tracks how code evolves over time"
        elif "improve" in question_lower or "better" in question_lower:
            return "Improvement suggester", "Suggests improvements based on analysis"

        return None, ""

    async def _analyze_error_patterns(self) -> Counter:
        """Analyze recent errors for patterns."""
        patterns = Counter()

        # This would integrate with actual error tracking
        # For now, return empty to avoid generating fake patterns

        return patterns

    def _is_on_cooldown(self, key: str) -> bool:
        """Check if an idea key is on cooldown."""
        if key not in self.idea_cooldowns:
            return False
        return datetime.now() < self.idea_cooldowns[key]

    def _set_cooldown(self, key: str, hours: int):
        """Set cooldown for an idea key."""
        self.idea_cooldowns[key] = datetime.now() + timedelta(hours=hours)

    def set_existing_tools(self, tools: List[str]):
        """Update the set of existing tools to avoid duplicates."""
        self.existing_tools = {t.lower() for t in tools}

    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics."""
        return {
            "total_ideas_generated": len(self.generated_ideas),
            "ideas_by_source": Counter(
                idea.source.value for idea in self.generated_ideas
            ),
            "active_cooldowns": len([
                k for k, v in self.idea_cooldowns.items()
                if datetime.now() < v
            ]),
            "existing_tools_count": len(self.existing_tools)
        }


# Global instance
_tool_idea_generator: Optional[ToolIdeaGenerator] = None


def get_tool_idea_generator() -> Optional[ToolIdeaGenerator]:
    """Get the global tool idea generator instance."""
    return _tool_idea_generator


def init_tool_idea_generator(
    findings_inbox=None,
    expedition_engine=None,
    meta_learner=None,
    error_tracker=None,
    semantic_memory=None,
    moltbook_client=None,
    proactive_engine=None
) -> ToolIdeaGenerator:
    """Initialize the global tool idea generator."""
    global _tool_idea_generator
    _tool_idea_generator = ToolIdeaGenerator(
        findings_inbox=findings_inbox,
        expedition_engine=expedition_engine,
        meta_learner=meta_learner,
        error_tracker=error_tracker,
        semantic_memory=semantic_memory,
        moltbook_client=moltbook_client,
        proactive_engine=proactive_engine
    )
    return _tool_idea_generator
