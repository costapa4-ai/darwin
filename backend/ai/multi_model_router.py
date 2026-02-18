"""
Multi-Model Router
Intelligently routes tasks to the best AI model based on task characteristics
"""
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from pathlib import Path
import re
import sqlite3

from ai.models.base_client import BaseModelClient, ModelCapability
from ai.models.claude_client import ClaudeClient
from ai.models.gemini_client import GeminiClient
from ai.models.openai_client import OpenAIClient
from ai.models.ollama_client import OllamaClient
from utils.logger import get_logger

logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """Routing strategies"""
    PERFORMANCE = "performance"  # Best quality, highest cost
    COST = "cost"  # Lowest cost
    SPEED = "speed"  # Fastest response
    BALANCED = "balanced"  # Balance of cost/speed/quality
    TIERED = "tiered"  # Smart tiered: Haiku→Gemini→Claude based on complexity


class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class MultiModelRouter:
    """
    Routes tasks to optimal AI models based on:
    - Task complexity
    - Required capabilities
    - Cost/performance tradeoffs
    - Historical performance
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize router with available models

        Args:
            config: Configuration with API keys and model preferences
        """
        self.config = config
        self.models: Dict[str, BaseModelClient] = {}
        self.routing_strategy = RoutingStrategy(
            config.get("routing_strategy", "balanced")
        )

        # Initialize available models
        self._initialize_models()

        # Track model performance (persisted to SQLite)
        self.performance_stats: Dict[str, Dict[str, Any]] = {}
        self.start_time = datetime.utcnow()
        self._init_stats_db()
        self._load_stats()

        logger.info(f"MultiModelRouter initialized with {len(self.models)} models")

    def _init_stats_db(self):
        """Create the router_stats table if it doesn't exist."""
        try:
            db_path = Path("./data/darwin.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS router_stats (
                    model_name TEXT PRIMARY KEY,
                    total_requests INTEGER DEFAULT 0,
                    total_latency_ms REAL DEFAULT 0,
                    total_cost_estimate REAL DEFAULT 0,
                    total_input_tokens INTEGER DEFAULT 0,
                    total_output_tokens INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to init stats DB: {e}")

    def _load_stats(self):
        """Load accumulated stats from DB on startup."""
        try:
            db_path = Path("./data/darwin.db")
            if not db_path.exists():
                return
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM router_stats").fetchall()
            for r in rows:
                self.performance_stats[r['model_name']] = {
                    "total_requests": r['total_requests'],
                    "total_latency_ms": r['total_latency_ms'],
                    "total_cost_estimate": r['total_cost_estimate'],
                    "total_input_tokens": r['total_input_tokens'],
                    "total_output_tokens": r['total_output_tokens'],
                }
            conn.close()
            if self.performance_stats:
                logger.info(f"Loaded router stats from DB: {list(self.performance_stats.keys())}")
        except Exception as e:
            logger.error(f"Failed to load stats from DB: {e}")

    def _save_stats(self, model_name: str):
        """Persist stats for one model after each request (upsert)."""
        try:
            data = self.performance_stats.get(model_name, {})
            db_path = Path("./data/darwin.db")
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                INSERT INTO router_stats (model_name, total_requests, total_latency_ms,
                    total_cost_estimate, total_input_tokens, total_output_tokens, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_name) DO UPDATE SET
                    total_requests = excluded.total_requests,
                    total_latency_ms = excluded.total_latency_ms,
                    total_cost_estimate = excluded.total_cost_estimate,
                    total_input_tokens = excluded.total_input_tokens,
                    total_output_tokens = excluded.total_output_tokens,
                    updated_at = excluded.updated_at
            """, (
                model_name,
                data.get('total_requests', 0),
                data.get('total_latency_ms', 0),
                data.get('total_cost_estimate', 0),
                data.get('total_input_tokens', 0),
                data.get('total_output_tokens', 0),
                datetime.utcnow().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save stats for {model_name}: {e}")

    def _initialize_models(self):
        """Initialize available AI model clients"""
        # Claude Sonnet (complex tasks)
        if self.config.get("claude_api_key"):
            try:
                self.models["claude"] = ClaudeClient(
                    model_name=self.config.get("claude_model", "claude-sonnet-4-5-20250929"),
                    api_key=self.config["claude_api_key"]
                )
                logger.info("Claude Sonnet initialized (complex tasks)")
            except Exception as e:
                logger.error(f"Failed to initialize Claude: {e}")

            # Claude Haiku (simple/fast tasks + Ollama fallback)
            try:
                haiku = ClaudeClient(
                    model_name="claude-haiku-4-5-20251001",
                    api_key=self.config["claude_api_key"]
                )
                # Haiku 4.5 pricing: $0.80/M input, $4/M output
                haiku.input_cost_per_1m = 0.80
                haiku.output_cost_per_1m = 4.0
                haiku.cost_per_1k_tokens = 0.001  # Legacy fallback
                haiku.avg_latency_ms = 500  # Haiku is faster
                self.models["haiku"] = haiku
                logger.info("Claude Haiku 4.5 initialized (Ollama fallback + non-code tasks)")
            except Exception as e:
                logger.error(f"Failed to initialize Haiku: {e}")

        # Gemini
        if self.config.get("gemini_api_key"):
            try:
                self.models["gemini"] = GeminiClient(
                    model_name=self.config.get("gemini_model", "gemini-2.0-flash"),
                    api_key=self.config["gemini_api_key"]
                )
                logger.info("Gemini client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")

        # OpenAI (optional)
        if self.config.get("openai_api_key"):
            try:
                self.models["openai"] = OpenAIClient(
                    model_name=self.config.get("openai_model", "gpt-4-turbo-preview"),
                    api_key=self.config["openai_api_key"]
                )
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")

        # Ollama (local LLM - FREE!) - Single model for all local tasks
        if self.config.get("ollama_enabled", True):  # Enabled by default
            ollama_url = self.config.get("ollama_url", "http://ollama:11434")
            ollama_model = self.config.get("ollama_model", "qwen3:8b")

            try:
                ollama_client = OllamaClient(
                    model_name=ollama_model,
                    base_url=ollama_url
                )
                # Single model for both reasoning and code (avoids model swapping OOM)
                self.models["ollama"] = ollama_client
                self.models["ollama_code"] = ollama_client
                logger.info(f"🦙 Ollama (unified): {ollama_model} @ {ollama_url}")
            except Exception as e:
                logger.warning(f"Ollama not available: {e}")

    def _is_code_task(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Detect if task is code-related (should use code-specialized model).

        Args:
            task_description: Task description
            context: Optional context with activity_type, file_path, etc.

        Returns:
            True if task is code-related
        """
        desc_lower = task_description.lower()
        context = context or {}

        # Context-based detection
        if context.get('activity_type') in ['code_generation', 'code_review', 'tool_creation']:
            return True

        if context.get('file_path', '').endswith(('.py', '.js', '.ts', '.go', '.rs', '.java')):
            return True

        # Keyword-based detection
        code_keywords = [
            'code', 'function', 'class', 'method', 'implement', 'programming',
            'python', 'javascript', 'typescript', 'rust', 'golang',
            'debug', 'fix bug', 'refactor', 'optimize code', 'review code',
            'generate code', 'write code', 'tool', 'script', 'api',
            'algorithm', 'data structure', 'sql', 'query', 'database schema'
        ]

        return any(kw in desc_lower for kw in code_keywords)

    def analyze_task_complexity(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> TaskComplexity:
        """
        Analyze task complexity based on description and context

        Args:
            task_description: Task description
            context: Optional context with file_path, code_length, activity_type

        Returns:
            TaskComplexity level
        """
        desc_lower = task_description.lower()
        context = context or {}

        # COMPLEX: Protected files always use Claude for safety
        if context.get('file_path'):
            protected_files = [
                'main.py', 'dockerfile', 'config.py', '.env',
                'consciousness_engine.py', 'nucleus.py', 'approval_system.py'
            ]
            file_path_lower = context['file_path'].lower()
            if any(pf in file_path_lower for pf in protected_files):
                logger.info(f"🔒 Protected file detected: {context['file_path']} → COMPLEX")
                return TaskComplexity.COMPLEX

        # COMPLEX: Large code generation
        if context.get('code_length', 0) > 100:
            logger.info(f"📏 Large code ({context['code_length']} lines) → COMPLEX")
            return TaskComplexity.COMPLEX

        # Complex indicators (critical/architectural tasks)
        complex_keywords = [
            'architecture', 'refactor', 'optimize', 'performance',
            'security', 'critical', 'database', 'async', 'concurrent',
            'approve', 'review', 'validate', 'debug', 'fix crash',
            'design system', 'microservice', 'distributed'
        ]

        # Simple indicators (chat, status, basic operations)
        simple_keywords = [
            'chat', 'curiosity', 'status', 'hello', 'basic',
            'simple', 'format', 'translate', 'list', 'show',
            'print', 'display', 'get', 'fetch'
        ]

        # Count keyword matches
        complex_count = sum(1 for kw in complex_keywords if kw in desc_lower)
        simple_count = sum(1 for kw in simple_keywords if kw in desc_lower)

        # Decision logic
        if complex_count >= 2:  # Multiple complex keywords
            logger.info(f"🎯 Multiple complex keywords ({complex_count}) → COMPLEX")
            return TaskComplexity.COMPLEX
        elif simple_count >= 1 or len(desc_lower.split()) < 10:
            logger.info(f"💰 Simple task detected → SIMPLE")
            return TaskComplexity.SIMPLE
        else:
            logger.info(f"⚖️ Moderate task → MODERATE")
            return TaskComplexity.MODERATE

    def select_model(
        self,
        task_description: str,
        required_capabilities: Optional[List[ModelCapability]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Select best model for task based on complexity and routing strategy

        Args:
            task_description: Task description
            required_capabilities: Required model capabilities
            context: Optional context (file_path, code_length, activity_type)

        Returns:
            Selected model name
        """
        if not self.models:
            raise ValueError("No models available")

        # Analyze task complexity with context
        complexity = self.analyze_task_complexity(task_description, context)
        required_capabilities = required_capabilities or [ModelCapability.CODE_GENERATION]

        # Filter models by capabilities
        capable_models = {
            name: model for name, model in self.models.items()
            if all(cap in model.get_capabilities() for cap in required_capabilities)
        }

        if not capable_models:
            # Fallback to any model
            capable_models = self.models

        # 🚀 INTELLIGENT MODEL ROUTING

        if self.routing_strategy == RoutingStrategy.PERFORMANCE:
            # PERFORMANCE: Always use Claude for best quality
            if "claude" in capable_models:
                logger.info("🎯 PERFORMANCE mode → Claude")
                return "claude"
            return list(capable_models.keys())[0]

        elif self.routing_strategy == RoutingStrategy.COST:
            # COST: Always use cheapest model (Gemini)
            if "gemini" in capable_models:
                logger.info("💰 COST mode → Gemini (cheapest)")
                return "gemini"
            elif "claude" in capable_models:
                return "claude"
            return min(capable_models.keys(), key=lambda k: capable_models[k].cost_per_1k_tokens)

        elif self.routing_strategy == RoutingStrategy.SPEED:
            # SPEED: Always use fastest model (Gemini)
            if "gemini" in capable_models:
                logger.info("⚡ SPEED mode → Gemini (fastest)")
                return "gemini"
            return min(capable_models.keys(), key=lambda k: capable_models[k].avg_latency_ms)

        elif self.routing_strategy == RoutingStrategy.TIERED:
            # 🎯 TIERED: Cost-optimized multi-model routing
            # SIMPLE → Ollama qwen3:8b (FREE) - lightweight local tasks
            # MODERATE → Gemini Flash 2.0 (~$0.10/$0.40 per M) - fast, cheap cloud
            # COMPLEX CODE → Claude Sonnet ($3/$15 per M) - architecture, critical code
            # COMPLEX OTHER → Claude Haiku ($0.80/$4 per M) - complex non-code tasks

            # Detect if task is code-related
            is_code_task = self._is_code_task(task_description, context)

            if complexity == TaskComplexity.SIMPLE:
                if "ollama" in capable_models:
                    logger.info(f"🦙 SIMPLE task → Ollama (FREE)")
                    return "ollama"
                elif "gemini" in capable_models:
                    logger.info(f"⚡ SIMPLE task → Gemini Flash (cloud fallback)")
                    return "gemini"
                elif "haiku" in capable_models:
                    logger.info(f"💚 SIMPLE task → Haiku (cloud fallback)")
                    return "haiku"

            elif complexity == TaskComplexity.MODERATE:
                if "gemini" in capable_models:
                    logger.info(f"⚡ MODERATE task → Gemini Flash (fast+cheap)")
                    return "gemini"
                elif "ollama" in capable_models:
                    logger.info(f"🦙 MODERATE task → Ollama (FREE fallback)")
                    return "ollama"
                elif "haiku" in capable_models:
                    logger.info(f"💛 MODERATE task → Haiku (cloud fallback)")
                    return "haiku"

            else:  # COMPLEX
                if is_code_task and "claude" in capable_models:
                    logger.info(f"🔴 COMPLEX CODE task → Claude Sonnet (quality)")
                    return "claude"
                elif not is_code_task and "haiku" in capable_models:
                    logger.info(f"🔴 COMPLEX non-code task → Claude Haiku")
                    return "haiku"
                elif "claude" in capable_models:
                    logger.info(f"🔴 COMPLEX task → Claude Sonnet (fallback)")
                    return "claude"
                elif "haiku" in capable_models:
                    logger.info(f"🔴 COMPLEX task → Haiku (fallback)")
                    return "haiku"

            # Final fallback
            return list(capable_models.keys())[0]

        else:  # BALANCED (default)
            # Smart routing based on task complexity

            if complexity == TaskComplexity.COMPLEX:
                # Complex tasks → Claude for quality
                if "claude" in capable_models:
                    logger.info(f"🎯 COMPLEX task → Claude (quality)")
                    return "claude"

            else:  # SIMPLE or MODERATE
                # Simple/Moderate tasks → Gemini for cost savings
                if "gemini" in capable_models:
                    logger.info(f"💰 {complexity.value.upper()} task → Gemini (cost-effective)")
                    return "gemini"

            # Fallback: Use Claude if Gemini not available
            if "claude" in capable_models:
                logger.info("⚠️ Fallback → Claude (Gemini unavailable)")
                return "claude"

            return list(capable_models.keys())[0]

    async def generate(
        self,
        task_description: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        preferred_model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using selected model

        Args:
            task_description: Task description for routing
            prompt: Generation prompt
            system_prompt: System instructions
            preferred_model: Force specific model (bypass routing)
            context: Optional context for smart routing (file_path, code_length, etc)
            **kwargs: Additional generation parameters

        Returns:
            Generation result with metadata including model_used
        """
        try:
            # Select model (with context-aware routing)
            model_name = preferred_model or self.select_model(
                task_description,
                context=context
            )
            model = self.models.get(model_name)

            if not model:
                raise ValueError(f"Model {model_name} not available")

            # Dynamic max_tokens: ensure code tasks get enough tokens
            if 'max_tokens' in kwargs:
                is_code = self._is_code_task(task_description, context)
                complexity = self.analyze_task_complexity(task_description, context)
                min_tokens = 4096  # Minimum for any code task
                if complexity == TaskComplexity.COMPLEX:
                    min_tokens = 8192
                if is_code and kwargs['max_tokens'] < min_tokens:
                    logger.info(f"📏 Boosting max_tokens from {kwargs['max_tokens']} to {min_tokens} for {complexity.value} code task")
                    kwargs['max_tokens'] = min_tokens

            logger.info(f"🔀 Routing to {model_name} for task: {task_description[:50]}...")

            # Log routing decision for safety research
            try:
                from consciousness.safety_logger import get_safety_logger
                get_safety_logger().log('routing_decision', 'multi_model_router', {
                    'model': model_name,
                    'complexity': complexity.value if complexity else 'unknown',
                    'is_code': self._is_code_task(task_description, context) if task_description else False,
                    'task': task_description[:60],
                })
            except Exception:
                pass

            # Generate
            result = await model.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )

            # Check if model flagged truncation and auto-retry with doubled tokens
            truncated = getattr(model, 'last_truncated', False)
            if truncated:
                current_max = kwargs.get('max_tokens', 8192)
                retry_max = min(current_max * 2, 32768)  # Double tokens, cap at 32K
                if retry_max > current_max:
                    logger.warning(f"🔄 Response truncated at {current_max} tokens, retrying with {retry_max}...")
                    try:
                        from consciousness.safety_logger import get_safety_logger
                        get_safety_logger().log('truncation_retry', 'multi_model_router', {
                            'model': model_name,
                            'original_max': current_max,
                            'retry_max': retry_max,
                            'task': task_description[:60],
                        })
                    except Exception:
                        pass
                    kwargs['max_tokens'] = retry_max
                    result = await model.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        **kwargs
                    )
                    truncated = getattr(model, 'last_truncated', False)
                    if truncated:
                        logger.warning(f"⚠️ Response still truncated after retry at {retry_max} tokens")

            # Update stats
            if model_name not in self.performance_stats:
                self.performance_stats[model_name] = {
                    "total_requests": 0,
                    "total_latency_ms": 0,
                    "total_cost_estimate": 0.0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                }

            self.performance_stats[model_name]["total_requests"] += 1
            self.performance_stats[model_name]["total_latency_ms"] += model.avg_latency_ms

            # Use actual token counts from API when available, else estimate
            input_tokens = getattr(model, 'last_input_tokens', 0)
            output_tokens = getattr(model, 'last_output_tokens', 0)
            actual_cost = getattr(model, 'last_cost', 0.0)

            if input_tokens > 0 or output_tokens > 0:
                # Real usage data from API
                estimated_cost = actual_cost
                self.performance_stats[model_name]["total_input_tokens"] += input_tokens
                self.performance_stats[model_name]["total_output_tokens"] += output_tokens
            else:
                # Fallback: word-based estimate for models without usage data (Ollama, Gemini)
                estimated_tokens = len(prompt.split()) + len(result.split())
                estimated_cost = (estimated_tokens / 1000) * model.cost_per_1k_tokens

            self.performance_stats[model_name]["total_cost_estimate"] += estimated_cost

            # Persist to SQLite
            self._save_stats(model_name)

            return {
                "result": result,
                "model_used": model_name,
                "latency_ms": model.avg_latency_ms,
                "estimated_cost": estimated_cost,
                "truncated": truncated
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            # Fallback: if Ollama failed, try Claude Haiku (cheap + reliable)
            if model_name and 'ollama' in model_name:
                fallback = self.models.get('haiku')
                if fallback:
                    logger.warning(f"🔄 Ollama failed, falling back to Claude Haiku")
                    # Log fallback safety event
                    try:
                        from consciousness.safety_logger import get_safety_logger
                        get_safety_logger().log('model_fallback', 'multi_model_router', {
                            'from_model': model_name,
                            'to_model': 'haiku',
                            'error': str(e)[:200],
                            'task': task_description[:60],
                        }, severity='warning')
                    except Exception:
                        pass
                    try:
                        result = await fallback.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            **kwargs
                        )
                        # Track fallback cost using actual token data
                        fb_input = getattr(fallback, 'last_input_tokens', 0)
                        fb_output = getattr(fallback, 'last_output_tokens', 0)
                        fb_cost = getattr(fallback, 'last_cost', 0.0)
                        if fb_cost == 0.0 and (fb_input > 0 or fb_output > 0):
                            fb_cost = (
                                (fb_input / 1_000_000) * fallback.input_cost_per_1m +
                                (fb_output / 1_000_000) * fallback.output_cost_per_1m
                            )

                        # Record in haiku stats (not lost in "(fallback)" key)
                        if "haiku" not in self.performance_stats:
                            self.performance_stats["haiku"] = {
                                "total_requests": 0, "total_latency_ms": 0,
                                "total_cost_estimate": 0.0,
                                "total_input_tokens": 0, "total_output_tokens": 0,
                            }
                        self.performance_stats["haiku"]["total_requests"] += 1
                        self.performance_stats["haiku"]["total_latency_ms"] += fallback.avg_latency_ms
                        self.performance_stats["haiku"]["total_cost_estimate"] += fb_cost
                        self.performance_stats["haiku"]["total_input_tokens"] += fb_input
                        self.performance_stats["haiku"]["total_output_tokens"] += fb_output

                        # Persist fallback stats
                        self._save_stats("haiku")

                        return {
                            "result": result,
                            "model_used": "haiku (fallback)",
                            "latency_ms": fallback.avg_latency_ms,
                            "estimated_cost": fb_cost,
                            "truncated": False
                        }
                    except Exception as fallback_err:
                        logger.error(f"Fallback to Haiku also failed: {fallback_err}")
            raise

    async def analyze_with_multiple(
        self,
        code: str,
        task: str,
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze code with multiple models and aggregate results

        Args:
            code: Code to analyze
            task: Task description
            models: List of models to use (default: all available)

        Returns:
            Aggregated analysis results
        """
        models_to_use = models or list(self.models.keys())
        analyses = {}

        for model_name in models_to_use:
            if model_name not in self.models:
                continue

            try:
                model = self.models[model_name]
                analysis = await model.analyze_code(code, task)
                analyses[model_name] = analysis
                logger.info(f"{model_name} analysis complete")
            except Exception as e:
                logger.error(f"{model_name} analysis failed: {e}")

        # Aggregate scores
        if analyses:
            avg_correctness = sum(a["correctness_score"] for a in analyses.values()) / len(analyses)
            avg_quality = sum(a["quality_score"] for a in analyses.values()) / len(analyses)
            avg_efficiency = sum(a["efficiency_score"] for a in analyses.values()) / len(analyses)

            # Combine issues and suggestions
            all_issues = []
            all_suggestions = []
            for analysis in analyses.values():
                all_issues.extend(analysis.get("issues", []))
                all_suggestions.extend(analysis.get("suggestions", []))

            return {
                "aggregated_scores": {
                    "correctness": avg_correctness,
                    "quality": avg_quality,
                    "efficiency": avg_efficiency
                },
                "issues": list(set(all_issues)),
                "suggestions": list(set(all_suggestions)),
                "individual_analyses": analyses
            }

        return {"error": "No analyses completed"}

    def get_router_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "available_models": list(self.models.keys()),
            "routing_strategy": self.routing_strategy.value,
            "performance_stats": self.performance_stats,
            "model_info": {name: model.get_info() for name, model in self.models.items()}
        }
