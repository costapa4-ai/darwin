"""
Meta-Learning System
Self-optimization and performance analysis
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import statistics

from utils.logger import get_logger

logger = get_logger(__name__)


class MetaLearner:
    """
    Meta-learning system for analyzing performance and optimizing strategies
    """

    def __init__(self, memory_system, router):
        """
        Initialize meta-learner

        Args:
            memory_system: SemanticMemory instance
            router: MultiModelRouter instance
        """
        self.memory = memory_system
        self.router = router

        # Performance tracking
        self.execution_history: List[Dict[str, Any]] = []
        self.pattern_success_rates: Dict[str, float] = {}
        self.model_performance: Dict[str, Dict[str, Any]] = defaultdict(dict)

        logger.info("MetaLearner initialized")

    async def record_execution(
        self,
        task_id: str,
        task_description: str,
        code: str,
        result: Dict[str, Any],
        model_used: str,
        generation_time: float
    ):
        """
        Record execution for meta-learning

        Args:
            task_id: Task identifier
            task_description: Task description
            code: Generated code
            result: Execution result
            model_used: Model that generated the code
            generation_time: Time taken to generate
        """
        execution_record = {
            "task_id": task_id,
            "task_description": task_description,
            "code": code,
            "success": result.get("success", False),
            "execution_time": result.get("execution_time", 0),
            "model_used": model_used,
            "generation_time": generation_time,
            "timestamp": datetime.now().isoformat(),
            "error": result.get("error", None)
        }

        self.execution_history.append(execution_record)

        # Update model performance stats
        if model_used not in self.model_performance:
            self.model_performance[model_used] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_generation_time": 0,
                "total_execution_time": 0
            }

        stats = self.model_performance[model_used]
        stats["total_tasks"] += 1
        if execution_record["success"]:
            stats["successful_tasks"] += 1
        stats["total_generation_time"] += generation_time
        stats["total_execution_time"] += execution_record["execution_time"]

        logger.info(f"Recorded execution {task_id} for meta-learning")

    def analyze_model_performance(self) -> Dict[str, Any]:
        """
        Analyze performance of different models

        Returns:
            Performance analysis by model
        """
        analysis = {}

        for model, stats in self.model_performance.items():
            if stats["total_tasks"] == 0:
                continue

            analysis[model] = {
                "success_rate": stats["successful_tasks"] / stats["total_tasks"],
                "avg_generation_time": stats["total_generation_time"] / stats["total_tasks"],
                "avg_execution_time": stats["total_execution_time"] / stats["total_tasks"],
                "total_tasks": stats["total_tasks"]
            }

        return analysis

    def analyze_task_patterns(self) -> Dict[str, Any]:
        """
        Analyze patterns in task success/failure

        Returns:
            Pattern analysis
        """
        if not self.execution_history:
            return {"message": "No execution history available"}

        # Group by success/failure
        successful = [e for e in self.execution_history if e["success"]]
        failed = [e for e in self.execution_history if not e["success"]]

        # Analyze timing patterns
        if successful:
            success_times = [e["execution_time"] for e in successful]
            avg_success_time = statistics.mean(success_times)
        else:
            avg_success_time = 0

        if failed:
            failure_times = [e["execution_time"] for e in failed]
            avg_failure_time = statistics.mean(failure_times)
        else:
            avg_failure_time = 0

        # Common error patterns
        error_types = defaultdict(int)
        for execution in failed:
            if execution.get("error"):
                error_type = type(execution["error"]).__name__ if isinstance(execution["error"], Exception) else "Unknown"
                error_types[error_type] += 1

        return {
            "total_executions": len(self.execution_history),
            "success_rate": len(successful) / len(self.execution_history),
            "avg_success_time": avg_success_time,
            "avg_failure_time": avg_failure_time,
            "common_errors": dict(error_types)
        }

    async def suggest_optimizations(self) -> List[Dict[str, str]]:
        """
        Suggest system optimizations based on analysis

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Analyze model performance
        model_analysis = self.analyze_model_performance()

        # Find best performing model
        if model_analysis:
            best_model = max(
                model_analysis.items(),
                key=lambda x: x[1]["success_rate"]
            )

            suggestions.append({
                "type": "model_selection",
                "suggestion": f"Consider using {best_model[0]} more often",
                "reason": f"Success rate: {best_model[1]['success_rate']:.2%}"
            })

        # Analyze task patterns
        pattern_analysis = self.analyze_task_patterns()

        if pattern_analysis.get("success_rate", 0) < 0.7:
            suggestions.append({
                "type": "code_generation",
                "suggestion": "Overall success rate is low. Consider improving prompts or adding more validation",
                "reason": f"Current success rate: {pattern_analysis['success_rate']:.2%}"
            })

        # Check for slow executions
        recent_executions = self.execution_history[-10:] if len(self.execution_history) >= 10 else self.execution_history
        if recent_executions:
            avg_time = statistics.mean([e["execution_time"] for e in recent_executions])
            if avg_time > 5.0:  # More than 5 seconds
                suggestions.append({
                    "type": "performance",
                    "suggestion": "Recent executions are slow. Consider optimizing generated code",
                    "reason": f"Average execution time: {avg_time:.2f}s"
                })

        # Memory usage suggestions
        memory_stats = self.memory.get_stats()
        if memory_stats.get("total_executions", 0) > 1000:
            suggestions.append({
                "type": "memory",
                "suggestion": "Large execution history. Consider archiving old records",
                "reason": f"Total executions: {memory_stats['total_executions']}"
            })

        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        return suggestions

    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Get comprehensive learning insights

        Returns:
            Learning insights and metrics
        """
        model_performance = self.analyze_model_performance()
        task_patterns = self.analyze_task_patterns()

        # Calculate improvement trends
        if len(self.execution_history) >= 10:
            recent_10 = self.execution_history[-10:]
            older_10 = self.execution_history[-20:-10] if len(self.execution_history) >= 20 else self.execution_history[:10]

            recent_success = sum(1 for e in recent_10 if e["success"]) / len(recent_10)
            older_success = sum(1 for e in older_10 if e["success"]) / len(older_10)

            improvement_trend = recent_success - older_success
        else:
            improvement_trend = 0

        return {
            "model_performance": model_performance,
            "task_patterns": task_patterns,
            "improvement_trend": improvement_trend,
            "total_executions": len(self.execution_history),
            "memory_stats": self.memory.get_stats(),
            "router_stats": self.router.get_router_stats()
        }

    async def self_optimize(self) -> Dict[str, Any]:
        """
        Perform self-optimization based on learned patterns

        Returns:
            Optimization report
        """
        logger.info("Starting self-optimization...")

        # Get suggestions
        suggestions = await self.suggest_optimizations()

        # Analyze patterns
        patterns = await self.memory.find_reusable_patterns()

        # Get insights
        insights = self.get_learning_insights()

        optimization_report = {
            "timestamp": datetime.now().isoformat(),
            "suggestions": suggestions,
            "discovered_patterns": len(patterns),
            "insights": insights,
            "actions_taken": []
        }

        # Auto-apply some optimizations
        model_performance = insights["model_performance"]
        if model_performance:
            # Find best model
            best_model = max(
                model_performance.items(),
                key=lambda x: x[1]["success_rate"]
            )

            # Update router preferences if significantly better
            if best_model[1]["success_rate"] > 0.8:
                optimization_report["actions_taken"].append({
                    "action": "updated_preferred_model",
                    "model": best_model[0],
                    "reason": f"High success rate: {best_model[1]['success_rate']:.2%}"
                })

        logger.info(f"Self-optimization complete: {len(suggestions)} suggestions, {len(patterns)} patterns")

        return optimization_report

    def export_learning_data(self, filepath: str):
        """
        Export learning data for analysis

        Args:
            filepath: Path to export JSON file
        """
        try:
            export_data = {
                "execution_history": self.execution_history,
                "model_performance": dict(self.model_performance),
                "pattern_success_rates": self.pattern_success_rates,
                "exported_at": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Learning data exported to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export learning data: {e}")

    def import_learning_data(self, filepath: str):
        """
        Import learning data from file

        Args:
            filepath: Path to JSON file
        """
        try:
            with open(filepath, 'r') as f:
                import_data = json.load(f)

            self.execution_history.extend(import_data.get("execution_history", []))

            for model, stats in import_data.get("model_performance", {}).items():
                if model not in self.model_performance:
                    self.model_performance[model] = stats
                else:
                    # Merge stats
                    for key, value in stats.items():
                        self.model_performance[model][key] = self.model_performance[model].get(key, 0) + value

            self.pattern_success_rates.update(import_data.get("pattern_success_rates", {}))

            logger.info(f"Learning data imported from {filepath}")

        except Exception as e:
            logger.error(f"Failed to import learning data: {e}")
