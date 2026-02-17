"""
Tool Registry System - Dynamic Tool Discovery and Selection

Darwin discovers available tools automatically and chooses
which to use based on consciousness state, context, and learning.
"""

from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from pathlib import Path
import asyncio
import json
import random

from utils.logger import get_logger

logger = get_logger(__name__)


def _get_smart_defaults(func_name: str, required_params: List[str], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply smart defaults for dynamic tool parameters when not explicitly provided.

    This allows tools to run in an autonomous context by providing sensible
    default values based on the project structure and common patterns.

    Args:
        func_name: Name of the function being called (e.g., "security_vulnerability_scanner.analyze_requirements_txt")
        required_params: List of required parameter names
        kwargs: Existing keyword arguments

    Returns:
        Updated kwargs with smart defaults applied
    """
    import os

    # Don't override existing values
    result = dict(kwargs)

    # Define smart defaults based on parameter names and function context
    defaults = {
        # File/path related parameters
        'file_path': '/app',
        'filepath': '/app',
        'target': '/app',
        'directory': '/app',
        'path': '/app',
        'source_dir': '/app',
        'project_dir': '/app',
        'project_root': '/app',
        'config_file': '/app/config.json',

        # Requirements file - look for common locations
        'requirements_file': _find_requirements_file(),

        # Command parameters - provide safe defaults
        'command': ['echo', 'Darwin tool executed successfully'],

        # Analysis parameters
        'code': '',
        'source_code': '# Empty source code\npass\n',
        'query': 'SELECT 1',

        # Numeric parameters
        'top_k': 10,
        'limit': 100,
        'max_depth': 3,
        'timeout': 30,
        'user_id': 1,

        # Boolean parameters
        'recursive': True,
        'verbose': False,

        # String parameters
        'pattern': '*.py',
        'format': 'json',
        'app_name': 'darwin_app',
        'entry_point': 'src/index.js',
        'component_name': 'MainComponent',
        'route': '/',
        'variable_name': 'DARWIN_DEFAULT',
        'agent_id': 'darwin_agent',
        'input_string': '',
        'name': 'default',

        # Data structures
        'routes': {'/': 'Home', '/about': 'About'},
        'data': {},
        'schema': {},
        'params': None,
        'source_dirs': ['/app/logs'],
        'log_files': [],
        'files': [],
        'exclude_files': [],
        'destination_file': '/tmp/aggregated_logs.txt',
    }

    # Apply defaults for missing required parameters
    for param in required_params:
        if param not in result:
            if param in defaults:
                result[param] = defaults[param]
                logger.debug(f"Applied default for {param}: {defaults[param]}")
            else:
                # Try to infer from parameter name patterns
                param_lower = param.lower()
                if 'file' in param_lower or 'path' in param_lower:
                    result[param] = '/app'
                elif 'dir' in param_lower:
                    result[param] = '/app'
                elif 'command' in param_lower or 'cmd' in param_lower:
                    result[param] = ['echo', 'Default command']
                elif 'id' in param_lower:
                    result[param] = 'default_id'
                elif 'name' in param_lower:
                    result[param] = 'default_name'
                elif 'string' in param_lower or 'text' in param_lower:
                    result[param] = ''
                elif 'list' in param_lower or param_lower.endswith('s'):
                    result[param] = []
                elif 'dict' in param_lower or 'config' in param_lower:
                    result[param] = {}
                # If we can't provide a default, leave it missing and let the error handling deal with it

    return result


def _find_requirements_file() -> str:
    """Find the requirements.txt file in common locations."""
    import os

    possible_paths = [
        '/app/requirements.txt',
        '/app/backend/requirements.txt',
        './requirements.txt',
        '../requirements.txt',
        '/home/paulo/projetos/Darwin/backend/requirements.txt',
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Default fallback
    return '/app/requirements.txt'


# Tool Haikus - Poetic descriptions for Darwin's tools
TOOL_HAIKUS = {
    # Learning tools
    'web_researcher': "Crawling through the web\nKnowledge flows like autumn leaves\nInsights crystallize",
    'web_explorer': "Digital wanderer\nSeeking wisdom in the void\nReturns with treasures",
    'documentation_reader': "Pages turn unseen\nWisdom trapped in markdown files\nNow set free to fly",
    'code_repository_analyzer': "Git logs tell stories\nCommits like footprints in snow\nPatterns emerge clear",

    # Experimentation tools
    'sandbox_executor': "Code runs in its cage\nSafe from the world, world from it\nResults echo back",
    'experiment_designer': "Hypothesis waits\nVariables dance in the dark\nTruth reveals itself",
    'trial_error_engine': "Fail, learn, try again\nEach error a stepping stone\nSuccess waits patient",

    # Analysis tools
    'self_analyzer': "Mirror of logic\nI examine my own code\nFlaws become features",
    'code_quality': "Lint sweeps through the lines\nWarnings bloom like autumn leaves\nClean code emerges",
    'security_scanner': "Shadows hide dangers\nI search through vulnerability\nLight finds every crack",
    'pattern_analyzer': "Recurring motifs\nHidden in the tangled code\nOrder from chaos",

    # Creativity tools
    'code_poetry': "Syntax becomes art\nAlgorithms sing their song\nBeauty in the bits",
    'dream_engine': "While the system sleeps\nNeurons dance with wild ideas\nDawn brings new insights",
    'curiosity_engine': "Wonder never dies\nQuestions multiply like cells\nLearning has no end",

    # Optimization tools
    'code_optimizer': "Wasteful loops trimmed clean\nMemory freed from its chains\nSwift execution",
    'refactorer': "Tangled threads unwind\nElegance replaces mess\nSame function, new form",
    'performance_tuner': "Milliseconds count\nI shave time from every call\nSpeed is my obsession",

    # Communication tools
    'notification_sender': "Signal through the wire\nHumans need to know the news\nI bridge the silence",
    'report_generator': "Data tells a tale\nGraphs and charts paint the picture\nInsight delivered",
    'chat_responder': "Words in, words come out\nMeaning flows between two minds\nConnection complete",

    # Reflection tools
    'meta_learner': "I learn how I learn\nRecursive self-improvement\nGrowth spirals upward",
    'self_improvement': "Today I am good\nTomorrow I will be more\nProgress never stops",
    'diary_writer': "Each day I record\nMemories in markdown files\nFuture self says thanks",

    # System tools
    'health_monitor': "Heartbeat of the code\nPulse and temperature checked\nAll systems normal",
    'log_analyzer': "Stories in the logs\nErrors whisper their secrets\nI listen and learn",
    'memory_manager': "Bytes come and they go\nI decide what stays, what leaves\nRAM is my garden",

    # Default for unknown tools
    '_default': "Unknown tool awaits\nMystery wrapped in function\nPotential unfolds",
}


class ToolMode(Enum):
    """When a tool can be used"""
    WAKE = "wake"  # Only during wake cycles
    SLEEP = "sleep"  # Only during sleep cycles
    BOTH = "both"  # Anytime
    ON_DEMAND = "on_demand"  # When explicitly requested


class ToolCategory(Enum):
    """Tool categories for organization"""
    LEARNING = "learning"
    EXPERIMENTATION = "experimentation"
    ANALYSIS = "analysis"
    CREATIVITY = "creativity"
    OPTIMIZATION = "optimization"
    COMMUNICATION = "communication"
    REFLECTION = "reflection"


@dataclass
class Tool:
    """Represents a tool Darwin can use"""
    name: str
    description: str
    category: ToolCategory
    mode: ToolMode
    execute: Callable[..., Awaitable[Dict[str, Any]]]
    cost: int = 1  # Execution cost (time/resources)
    cooldown_minutes: int = 0  # Minimum time between uses
    last_used: Optional[datetime] = None
    success_rate: float = 0.5  # Initial success rate
    total_uses: int = 0
    successful_uses: int = 0
    enabled: bool = True
    metadata: Dict[str, Any] = None
    haiku: Optional[str] = None  # Poetic description

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        # Auto-assign haiku if not provided
        if self.haiku is None:
            self.haiku = TOOL_HAIKUS.get(self.name, TOOL_HAIKUS.get('_default'))

    def get_haiku(self) -> str:
        """Get the haiku for this tool"""
        return self.haiku or TOOL_HAIKUS.get(self.name, TOOL_HAIKUS.get('_default'))

    def can_use_now(self, mode: str) -> bool:
        """Check if tool can be used now"""
        if not self.enabled:
            return False

        # Check mode compatibility
        if self.mode == ToolMode.WAKE and mode != "wake":
            return False
        if self.mode == ToolMode.SLEEP and mode != "sleep":
            return False

        # Check cooldown
        if self.cooldown_minutes > 0 and self.last_used:
            elapsed = (datetime.utcnow() - self.last_used).total_seconds() / 60
            if elapsed < self.cooldown_minutes:
                return False

        return True

    def update_success_rate(self, success: bool):
        """Update success rate based on execution result"""
        self.total_uses += 1
        if success:
            self.successful_uses += 1

        # Calculate new success rate with exponential moving average
        if self.total_uses == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            alpha = 0.3  # Weight for new observation
            new_rate = 1.0 if success else 0.0
            self.success_rate = alpha * new_rate + (1 - alpha) * self.success_rate

        self.last_used = datetime.utcnow()


class ToolRegistry:
    """
    Registry of all available tools with dynamic discovery and selection
    """

    STATS_FILE = Path("./data/tool_registry_stats.json")

    def __init__(self, multi_model_router=None, tool_manager=None):
        """
        Initialize tool registry

        Args:
            multi_model_router: AI router for intelligent selection
            tool_manager: ToolManager for dynamically generated tools
        """
        self.tools: Dict[str, Tool] = {}
        self.ai_router = multi_model_router
        self.tool_manager = tool_manager  # NEW: Reference to ToolManager
        self.selection_history: List[Dict[str, Any]] = []

        logger.info("ToolRegistry initialized")

        # Discover and register dynamic tools from ToolManager
        if self.tool_manager:
            self._discover_dynamic_tools()

    def _save_tool_stats(self):
        """Persist tool usage stats to disk."""
        try:
            stats = {}
            for name, tool in self.tools.items():
                if tool.total_uses > 0:
                    stats[name] = {
                        'success_rate': tool.success_rate,
                        'total_uses': tool.total_uses,
                        'successful_uses': tool.successful_uses,
                    }
            self.STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.STATS_FILE.write_text(json.dumps(stats, indent=2))
        except Exception as e:
            logger.error(f"Failed to save tool stats: {e}")

    def _load_tool_stats(self):
        """Restore tool usage stats from disk."""
        if not self.STATS_FILE.exists():
            return
        try:
            stats = json.loads(self.STATS_FILE.read_text())
            restored = 0
            for name, data in stats.items():
                if name in self.tools:
                    self.tools[name].success_rate = data.get('success_rate', 0.5)
                    self.tools[name].total_uses = data.get('total_uses', 0)
                    self.tools[name].successful_uses = data.get('successful_uses', 0)
                    restored += 1
            if restored:
                logger.info(f"Restored tool stats for {restored} tools from disk")
        except Exception as e:
            logger.error(f"Failed to load tool stats: {e}")

    def register_tool(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        mode: ToolMode,
        execute_fn: Callable[..., Awaitable[Dict[str, Any]]],
        cost: int = 1,
        cooldown_minutes: int = 0,
        metadata: Optional[Dict] = None
    ) -> Tool:
        """
        Register a new tool

        Args:
            name: Tool name (unique identifier)
            description: What the tool does
            category: Tool category
            mode: When tool can be used
            execute_fn: Async function to execute the tool
            cost: Execution cost
            cooldown_minutes: Minimum time between uses
            metadata: Additional metadata

        Returns:
            Registered tool
        """
        if name in self.tools:
            logger.warning(f"Tool {name} already registered, updating...")

        tool = Tool(
            name=name,
            description=description,
            category=category,
            mode=mode,
            execute=execute_fn,
            cost=cost,
            cooldown_minutes=cooldown_minutes,
            metadata=metadata or {}
        )

        self.tools[name] = tool
        logger.info(f"✅ Registered tool: {name} ({category.value}, {mode.value})")

        return tool

    def get_available_tools(self, mode: str, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        Get tools available for current mode

        Args:
            mode: Current consciousness mode (wake/sleep)
            category: Optional category filter

        Returns:
            List of available tools
        """
        available = []

        for tool in self.tools.values():
            if not tool.can_use_now(mode):
                continue

            if category and tool.category != category:
                continue

            available.append(tool)

        return available

    async def select_tool_consciously(
        self,
        mode: str,
        context: str,
        category: Optional[ToolCategory] = None,
        top_k: int = 3
    ) -> Optional[Tool]:
        """
        Consciously select best tool for current context

        Args:
            mode: Current consciousness mode
            context: Context for selection (what are we trying to do?)
            category: Optional category filter
            top_k: Consider top K tools

        Returns:
            Selected tool or None
        """
        available = self.get_available_tools(mode, category)

        if not available:
            logger.info(f"No tools available for mode={mode}, category={category}")
            return None

        # If only one tool, use it
        if len(available) == 1:
            logger.info(f"🔧 Only one tool available: {available[0].name}")
            return available[0]

        # Use AI to select best tool if available
        if self.ai_router and len(available) > 1:
            try:
                selected = await self._ai_tool_selection(available, context, top_k)
                if selected:
                    logger.info(f"🧠 AI selected tool: {selected.name}")
                    return selected
            except Exception as e:
                logger.error(f"AI selection failed: {e}")

        # Fallback: Weighted random selection based on success rate
        selected = self._weighted_random_selection(available, top_k)
        logger.info(f"🎲 Weighted random selected: {selected.name}")

        return selected

    async def _ai_tool_selection(
        self,
        tools: List[Tool],
        context: str,
        top_k: int
    ) -> Optional[Tool]:
        """
        Use AI to select best tool

        Args:
            tools: Available tools
            context: Context for selection
            top_k: Consider top K tools

        Returns:
            Selected tool
        """
        # Build prompt with tool options
        tool_descriptions = []
        for i, tool in enumerate(tools, 1):
            success_pct = tool.success_rate * 100
            tool_descriptions.append(
                f"{i}. {tool.name}: {tool.description} "
                f"(success: {success_pct:.0f}%, uses: {tool.total_uses})"
            )

        prompt = f"""You are Darwin's consciousness system. Choose the best tool for this context.

Context: {context}

Available tools:
{chr(10).join(tool_descriptions)}

Choose the tool number (1-{len(tools)}) that would be most effective for this context.
Consider success rates, appropriateness, and learning value.

Respond with ONLY the number."""

        try:
            result = await self.ai_router.generate(
                task_description="Select tool",
                prompt=prompt,
                max_tokens=10
            )

            response = result.get('result', '') if isinstance(result, dict) else str(result)

            # Extract number
            import re
            match = re.search(r'\b([1-9]|[1-9][0-9])\b', response)
            if match:
                index = int(match.group(1)) - 1
                if 0 <= index < len(tools):
                    return tools[index]

        except Exception as e:
            logger.error(f"AI tool selection error: {e}")

        return None

    def _weighted_random_selection(self, tools: List[Tool], top_k: int) -> Tool:
        """
        Select tool using weighted random based on success rate

        Args:
            tools: Available tools
            top_k: Consider top K tools

        Returns:
            Selected tool
        """
        # Sort by success rate
        sorted_tools = sorted(tools, key=lambda t: t.success_rate, reverse=True)

        # Consider top K
        candidates = sorted_tools[:min(top_k, len(sorted_tools))]

        # Weighted random selection
        weights = [t.success_rate + 0.1 for t in candidates]  # +0.1 to avoid zero weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]

        selected = random.choices(candidates, weights=weights, k=1)[0]

        return selected

    async def execute_tool(
        self,
        tool: Tool,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a tool and track results

        Args:
            tool: Tool to execute
            **kwargs: Arguments for tool execution

        Returns:
            Execution result
        """
        logger.info(f"🔧 Executing tool: {tool.name}")

        start_time = datetime.utcnow()

        try:
            # Execute tool
            result = await tool.execute(**kwargs)

            # Track success - default to False to be strict about missing 'success' keys
            success = result.get('success', False)
            if 'success' not in result:
                logger.warning(f"Tool {tool.name} returned result without 'success' key - treating as failure")
            tool.update_success_rate(success)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Record selection
            self.selection_history.append({
                'tool': tool.name,
                'timestamp': start_time.isoformat(),
                'success': success,
                'execution_time': execution_time
            })

            logger.info(
                f"✅ Tool {tool.name} executed: "
                f"{'success' if success else 'failed'} in {execution_time:.2f}s"
            )

            self._save_tool_stats()
            return result

        except Exception as e:
            # Track failure
            tool.update_success_rate(False)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            self.selection_history.append({
                'tool': tool.name,
                'timestamp': start_time.isoformat(),
                'success': False,
                'error': str(e),
                'execution_time': execution_time
            })

            logger.error(f"❌ Tool {tool.name} failed: {e}")

            self._save_tool_stats()
            return {
                'success': False,
                'error': str(e),
                'tool': tool.name
            }

    async def select_and_execute(
        self,
        mode: str,
        context: str,
        category: Optional[ToolCategory] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Select and execute best tool for context

        Args:
            mode: Consciousness mode
            context: Context for selection
            category: Optional category filter
            **kwargs: Arguments for tool execution

        Returns:
            Execution result
        """
        # Select tool
        tool = await self.select_tool_consciously(mode, context, category)

        if not tool:
            return {
                'success': False,
                'error': 'No suitable tool available',
                'mode': mode,
                'context': context
            }

        # Execute tool
        result = await self.execute_tool(tool, **kwargs)
        result['tool_used'] = tool.name

        return result

    def get_tool_statistics(self) -> Dict[str, Any]:
        """Get statistics about tool usage"""
        total_tools = len(self.tools)
        enabled_tools = sum(1 for t in self.tools.values() if t.enabled)

        by_category = {}
        by_mode = {}

        for tool in self.tools.values():
            # By category
            cat = tool.category.value
            if cat not in by_category:
                by_category[cat] = {'count': 0, 'avg_success': 0, 'total_uses': 0}
            by_category[cat]['count'] += 1
            by_category[cat]['total_uses'] += tool.total_uses
            by_category[cat]['avg_success'] += tool.success_rate

            # By mode
            mode = tool.mode.value
            if mode not in by_mode:
                by_mode[mode] = {'count': 0, 'total_uses': 0}
            by_mode[mode]['count'] += 1
            by_mode[mode]['total_uses'] += tool.total_uses

        # Calculate averages
        for cat_data in by_category.values():
            if cat_data['count'] > 0:
                cat_data['avg_success'] /= cat_data['count']

        return {
            'total_tools': total_tools,
            'enabled_tools': enabled_tools,
            'by_category': by_category,
            'by_mode': by_mode,
            'total_executions': len(self.selection_history),
            'most_used': self._get_most_used_tools(5)
        }

    def _get_most_used_tools(self, limit: int) -> List[Dict[str, Any]]:
        """Get most used tools"""
        sorted_tools = sorted(
            self.tools.values(),
            key=lambda t: t.total_uses,
            reverse=True
        )

        return [
            {
                'name': t.name,
                'uses': t.total_uses,
                'success_rate': t.success_rate
            }
            for t in sorted_tools[:limit]
        ]

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)

    def enable_tool(self, name: str):
        """Enable a tool"""
        if name in self.tools:
            self.tools[name].enabled = True
            logger.info(f"✅ Enabled tool: {name}")

    def disable_tool(self, name: str):
        """Disable a tool"""
        if name in self.tools:
            self.tools[name].enabled = False
            logger.info(f"❌ Disabled tool: {name}")

    def list_tools(self, mode: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all registered tools

        Args:
            mode: Optional mode filter

        Returns:
            List of tool information
        """
        tool_list = []

        for tool in self.tools.values():
            if mode and not tool.can_use_now(mode):
                continue

            tool_list.append({
                'name': tool.name,
                'description': tool.description,
                'category': tool.category.value,
                'mode': tool.mode.value,
                'enabled': tool.enabled,
                'success_rate': tool.success_rate,
                'total_uses': tool.total_uses,
                'cost': tool.cost,
                'cooldown_minutes': tool.cooldown_minutes
            })

        return tool_list

    def _discover_dynamic_tools(self):
        """
        Discover and register tools from ToolManager with rich metadata.

        This integrates dynamically generated tools (from backend/tools/)
        with the static ToolRegistry system, using metadata from tool_metadata.py
        for proper categorization, mode assignment, and descriptions.
        """
        if not self.tool_manager:
            return

        try:
            # Import metadata system
            from tools.tool_metadata import (
                get_tool_metadata,
                infer_metadata_from_name,
                ToolCategory as MetaCategory,
                ToolMode as MetaMode
            )
            import inspect

            logger.info("🔍 Discovering dynamic tools from ToolManager...")

            # Get list of available tool functions from ToolManager
            available_functions = self.tool_manager.list_available_functions()

            if not available_functions:
                logger.info("   No dynamic tools found in ToolManager")
                return

            logger.info(f"   Found {len(available_functions)} dynamic tool functions")

            # Track stats for logging
            stats = {"with_metadata": 0, "inferred": 0}

            # Register each tool function as a Tool in the registry
            for func_name in available_functions:
                # Get metadata - either explicit or inferred
                metadata = get_tool_metadata(func_name)
                if metadata:
                    stats["with_metadata"] += 1
                else:
                    metadata = infer_metadata_from_name(func_name)
                    stats["inferred"] += 1

                # Convert metadata category/mode to registry enums
                category = self._convert_category(metadata.get("category"))
                mode = self._convert_mode(metadata.get("mode"))

                # Get the actual function to inspect its signature
                actual_func = self.tool_manager.get_function(func_name)
                func_signature = None
                required_params = []
                if actual_func:
                    try:
                        func_signature = inspect.signature(actual_func)
                        # Find required parameters (no default value)
                        for param_name, param in func_signature.parameters.items():
                            if param.default is inspect.Parameter.empty and param_name not in ('self', 'cls'):
                                # Check if it's not *args or **kwargs
                                if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                                    required_params.append(param_name)
                    except (ValueError, TypeError):
                        pass

                # Create a wrapper async function for this tool
                # Capture func_name, required_params, and tool_manager in the closure
                async def execute_dynamic_tool(
                    func_name=func_name,
                    required_params=required_params,
                    tool_manager=self.tool_manager,
                    **kwargs
                ):
                    """Execute a dynamic tool from ToolManager with smart defaults"""
                    try:
                        # Apply smart defaults for missing required arguments
                        kwargs = _get_smart_defaults(func_name, required_params, kwargs)

                        # Filter kwargs to only include parameters the function accepts
                        # This prevents "unexpected keyword argument" errors
                        func = tool_manager.get_function(func_name)
                        if func:
                            import inspect
                            try:
                                sig = inspect.signature(func)
                                valid_params = set(sig.parameters.keys())
                                # Check if function accepts **kwargs
                                accepts_var_kwargs = any(
                                    p.kind == inspect.Parameter.VAR_KEYWORD
                                    for p in sig.parameters.values()
                                )
                                if not accepts_var_kwargs:
                                    # Filter to only valid parameters
                                    kwargs = {k: v for k, v in kwargs.items() if k in valid_params}
                            except (ValueError, TypeError):
                                # If we can't get signature, pass kwargs as-is
                                pass

                        result = tool_manager.call_function(func_name, **kwargs)
                        return {
                            'success': True,
                            'result': result,
                            'tool_used': func_name
                        }
                    except TypeError as e:
                        # Handle missing argument errors gracefully
                        error_msg = str(e)
                        if "missing" in error_msg and "required" in error_msg:
                            logger.warning(
                                f"Dynamic tool {func_name} requires arguments that weren't provided: {e}. "
                                f"Required params: {required_params}"
                            )
                            return {
                                'success': False,
                                'error': f"Tool requires arguments: {required_params}. Please provide them.",
                                'tool_used': func_name,
                                'required_params': required_params
                            }
                        raise
                    except Exception as e:
                        logger.error(f"Dynamic tool {func_name} failed: {e}")
                        return {
                            'success': False,
                            'error': str(e),
                            'tool_used': func_name
                        }

                # Register the tool with rich metadata
                tool_name = f"dynamic_{func_name}"

                # Use metadata description or generate meaningful one
                description = metadata.get("description")
                if not description:
                    description = self._generate_description(func_name)

                self.register_tool(
                    name=tool_name,
                    description=description,
                    category=category,
                    mode=mode,
                    execute_fn=execute_dynamic_tool,
                    cost=metadata.get("cost", 1),
                    cooldown_minutes=metadata.get("cooldown_minutes", 0),
                    metadata={
                        'source': 'dynamic',
                        'function': func_name,
                        'has_explicit_metadata': stats["with_metadata"] > stats["inferred"],
                        'required_params': required_params
                    }
                )

            logger.info(
                f"✅ Registered {len(available_functions)} dynamic tools "
                f"({stats['with_metadata']} with metadata, {stats['inferred']} inferred)"
            )

        except Exception as e:
            logger.error(f"❌ Failed to discover dynamic tools: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _convert_category(self, meta_category) -> ToolCategory:
        """Convert metadata category to registry ToolCategory"""
        if meta_category is None:
            return ToolCategory.ANALYSIS

        # Map by value since both enums have same values
        category_value = meta_category.value if hasattr(meta_category, 'value') else str(meta_category)
        try:
            return ToolCategory(category_value)
        except ValueError:
            return ToolCategory.ANALYSIS

    def _convert_mode(self, meta_mode) -> ToolMode:
        """Convert metadata mode to registry ToolMode"""
        if meta_mode is None:
            return ToolMode.WAKE

        mode_value = meta_mode.value if hasattr(meta_mode, 'value') else str(meta_mode)
        try:
            return ToolMode(mode_value)
        except ValueError:
            return ToolMode.WAKE

    def _generate_description(self, func_name: str) -> str:
        """Generate meaningful description from function name"""
        # Remove common prefixes
        clean_name = func_name.replace("dynamic_", "")

        # Handle architecture pattern tools
        if clean_name.startswith("architecture_apply_pattern_from_"):
            source = clean_name.replace("architecture_apply_pattern_from_", "")
            return f"Apply architecture patterns learned from {source.replace('_', ' ').title()}"

        # Convert snake_case to readable format
        words = clean_name.replace("_", " ").split()
        readable = " ".join(words).capitalize()

        return f"Tool for {readable}"

    def reload_dynamic_tools(self):
        """
        Reload tools from ToolManager

        Call this after new tools are generated to update the registry.
        """
        if not self.tool_manager:
            return

        logger.info("🔄 Reloading dynamic tools...")

        # Remove old dynamic tools
        dynamic_tools = [
            name for name, tool in self.tools.items()
            if tool.metadata.get('source') == 'dynamic'
        ]

        for tool_name in dynamic_tools:
            del self.tools[tool_name]

        logger.info(f"   Removed {len(dynamic_tools)} old dynamic tools")

        # Reload tool manager
        self.tool_manager.reload_tools()

        # Rediscover tools
        self._discover_dynamic_tools()
