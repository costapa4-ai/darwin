"""
Multi-Model Router
Intelligently routes tasks to the best AI model based on task characteristics
"""
from typing import Dict, Any, Optional, List
from enum import Enum
import re

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

        # Track model performance
        self.performance_stats: Dict[str, Dict[str, Any]] = {}

        logger.info(f"MultiModelRouter initialized with {len(self.models)} models")

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

            # Claude Haiku (simple/fast tasks)
            try:
                haiku = ClaudeClient(
                    model_name="claude-3-5-haiku-20241022",
                    api_key=self.config["claude_api_key"]
                )
                # Override Haiku pricing ($0.25/M input, $1.25/M output ≈ $0.001 avg)
                haiku.cost_per_1k_tokens = 0.001
                haiku.avg_latency_ms = 500  # Haiku is faster
                self.models["haiku"] = haiku
                logger.info("Claude Haiku initialized (simple/fast tasks)")
            except Exception as e:
                logger.error(f"Failed to initialize Haiku: {e}")

        # Gemini
        if self.config.get("gemini_api_key"):
            try:
                self.models["gemini"] = GeminiClient(
                    model_name=self.config.get("gemini_model", "gemini-2.0-flash-exp"),
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

        # Ollama (local LLM - FREE!)
        if self.config.get("ollama_enabled", True):  # Enabled by default
            try:
                ollama_url = self.config.get("ollama_url", "http://ollama:11434")
                ollama_model = self.config.get("ollama_model", "llama3.2")
                self.models["ollama"] = OllamaClient(
                    model_name=ollama_model,
                    base_url=ollama_url
                )
                logger.info(f"🦙 Ollama initialized: {ollama_model} @ {ollama_url} (FREE local LLM)")
            except Exception as e:
                logger.warning(f"Ollama not available (optional): {e}")

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
            # 🎯 TIERED: Smart 4-tier routing for optimal cost/quality
            # SIMPLE → Ollama (FREE!) - chat, status, basic queries, curiosities
            # SIMPLE (fallback) → Haiku ($0.001/1K) - if Ollama unavailable
            # MODERATE → Gemini ($0.0005/1K) - research, analysis
            # COMPLEX → Claude Sonnet ($0.015/1K) - code gen, architecture

            if complexity == TaskComplexity.SIMPLE:
                # 🦙 Try Ollama first - it's FREE and local!
                if "ollama" in capable_models:
                    logger.info(f"🦙 SIMPLE task → Ollama (FREE local LLM)")
                    return "ollama"
                elif "haiku" in capable_models:
                    logger.info(f"💚 SIMPLE task → Haiku (cheap cloud fallback)")
                    return "haiku"
                elif "gemini" in capable_models:
                    logger.info(f"💚 SIMPLE task → Gemini (fallback)")
                    return "gemini"

            elif complexity == TaskComplexity.MODERATE:
                if "gemini" in capable_models:
                    logger.info(f"💛 MODERATE task → Gemini (balanced)")
                    return "gemini"
                elif "ollama" in capable_models:
                    logger.info(f"🦙 MODERATE task → Ollama (free fallback)")
                    return "ollama"
                elif "haiku" in capable_models:
                    logger.info(f"💛 MODERATE task → Haiku (fallback)")
                    return "haiku"

            else:  # COMPLEX
                if "claude" in capable_models:
                    logger.info(f"🔴 COMPLEX task → Claude Sonnet (quality)")
                    return "claude"
                elif "gemini" in capable_models:
                    logger.info(f"🔴 COMPLEX task → Gemini (fallback)")
                    return "gemini"

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

            logger.info(f"🔀 Routing to {model_name} for task: {task_description[:50]}...")

            # Generate
            result = await model.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                **kwargs
            )

            # Update stats
            if model_name not in self.performance_stats:
                self.performance_stats[model_name] = {
                    "total_requests": 0,
                    "total_latency_ms": 0,
                    "total_cost_estimate": 0.0
                }

            self.performance_stats[model_name]["total_requests"] += 1
            self.performance_stats[model_name]["total_latency_ms"] += model.avg_latency_ms

            # Estimate cost (rough approximation)
            estimated_tokens = len(prompt.split()) + len(result.split())
            estimated_cost = (estimated_tokens / 1000) * model.cost_per_1k_tokens
            self.performance_stats[model_name]["total_cost_estimate"] += estimated_cost

            return {
                "result": result,
                "model_used": model_name,
                "latency_ms": model.avg_latency_ms,
                "estimated_cost": estimated_cost
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
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
