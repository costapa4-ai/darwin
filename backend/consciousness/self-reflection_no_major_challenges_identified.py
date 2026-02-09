"""
Self-Reflection Enhancement Module

This module provides comprehensive self-reflection capabilities for the Darwin System,
enabling the system to analyze its performance, identify patterns, and implement
continuous improvements even when no major challenges are identified.

This addresses the insight: "No major challenges identified" by implementing
proactive monitoring, optimization tracking, and incremental improvement mechanisms.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics


class ReflectionCategory(Enum):
    """Categories for reflection metrics."""
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"
    LEARNING = "learning"
    ADAPTATION = "adaptation"
    STABILITY = "stability"


class ImprovementStatus(Enum):
    """Status of improvement implementations."""
    IDENTIFIED = "identified"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VALIDATED = "validated"


@dataclass
class PerformanceMetric:
    """Represents a performance metric for tracking."""
    name: str
    value: float
    timestamp: str
    category: str
    baseline: Optional[float] = None
    target: Optional[float] = None
    
    def improvement_percentage(self) -> Optional[float]:
        """Calculate improvement percentage from baseline."""
        if self.baseline is None or self.baseline == 0:
            return None
        return ((self.value - self.baseline) / abs(self.baseline)) * 100


@dataclass
class MicroImprovement:
    """Represents a small, incremental improvement opportunity."""
    id: str
    description: str
    category: str
    impact_score: float
    effort_score: float
    status: str
    identified_at: str
    implemented_at: Optional[str] = None
    validated_at: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    
    def priority_score(self) -> float:
        """Calculate priority based on impact vs effort."""
        if self.effort_score == 0:
            return self.impact_score * 10
        return self.impact_score / self.effort_score


class SelfReflectionEngine:
    """
    Engine for continuous self-reflection and improvement tracking.
    
    This system operates on the principle that absence of major challenges
    is an opportunity to focus on micro-optimizations and preventive measures.
    """
    
    def __init__(self, data_dir: str = "data/reflections"):
        """
        Initialize the self-reflection engine.
        
        Args:
            data_dir: Directory for storing reflection data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.data_dir / "performance_metrics.json"
        self.improvements_file = self.data_dir / "micro_improvements.json"
        self.patterns_file = self.data_dir / "learned_patterns.json"
        
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        self.metrics: List[PerformanceMetric] = []
        self.improvements: List[MicroImprovement] = []
        self.patterns: Dict[str, Any] = {}
        
        self._load_state()
    
    def _setup_logging(self) -> None:
        """Configure logging for the reflection engine."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_state(self) -> None:
        """Load previous reflection state from disk."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    self.metrics = [
                        PerformanceMetric(**m) for m in data
                    ]
            
            if self.improvements_file.exists():
                with open(self.improvements_file, 'r') as f:
                    data = json.load(f)
                    self.improvements = [
                        MicroImprovement(**i) for i in data
                    ]
            
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r') as f:
                    self.patterns = json.load(f)
                    
        except Exception as e:
            self.logger.error(f"Error loading reflection state: {e}")
    
    def _save_state(self) -> None:
        """Persist reflection state to disk."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(
                    [asdict(m) for m in self.metrics],
                    f,
                    indent=2
                )
            
            with open(self.improvements_file, 'w') as f:
                json.dump(
                    [asdict(i) for i in self.improvements],
                    f,
                    indent=2
                )
            
            with open(self.patterns_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving reflection state: {e}")
    
    def record_metric(
        self,
        name: str,
        value: float,
        category: ReflectionCategory,
        baseline: Optional[float] = None,
        target: Optional[float] = None
    ) -> None:
        """
        Record a performance metric for tracking.
        
        Args:
            name: Metric name
            value: Current metric value
            category: Category of the metric
            baseline: Baseline value for comparison
            target: Target value to achieve
        """
        metric = PerformanceMetric(
            name=name,
            value=value,
            timestamp=datetime.now().isoformat(),
            category=category.value,
            baseline=baseline,
            target=target
        )
        
        self.metrics.append(metric)
        self.logger.info(f"Recorded metric: {name} = {value}")
        
        self._analyze_metric_trends()
        self._save_state()
    
    def _analyze_metric_trends(self) -> None:
        """Analyze metric trends to identify improvement opportunities."""
        if len(self.metrics) < 5:
            return
        
        recent_metrics = self.metrics[-50:]
        metrics_by_name: Dict[str, List[PerformanceMetric]] = {}
        
        for metric in recent_metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)
        
        for name, metrics_list in metrics_by_name.items():
            if len(metrics_list) >= 3:
                values = [m.value for m in metrics_list]
                trend = self._calculate_trend(values)
                
                if abs(trend) < 0.01:
                    self._identify_stagnation_improvement(name, metrics_list)
                elif trend < -0.05:
                    self._identify_degradation_improvement(name, metrics_list)
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate trend coefficient for a series of values.
        
        Args:
            values: List of metric values
            
        Returns:
            Trend coefficient (positive = improving, negative = degrading)
        """
        if len(values) < 2:
            return 0.0
        
        try:
            n = len(values)
            x = list(range(n))
            mean_x = statistics.mean(x)
            mean_y = statistics.mean(values)
            
            numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, values))
            denominator = sum((xi - mean_x) ** 2 for xi in x)
            
            if denominator == 0:
                return 0.0
            
            slope = numerator / denominator
            # Normalize by mean to get relative trend
            if mean_y != 0:
                return slope / abs(mean_y)
            return slope
            
        except Exception:
            return 0.0
    
    def _identify_stagnation_improvement(
        self,
        metric_name: str,
        metrics_list: List[PerformanceMetric]
    ) -> None:
        """
        Identify improvement opportunities when metrics are stagnating.
        
        Args:
            metric_name: Name of the stagnating metric
            metrics_list: List of recent metric values
        """
        values = [m.value for m in metrics_list]
        avg_value = statistics.mean(values)
        
        improvement = MicroImprovement(
            id=f"stagnation_{metric_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            description=f"Metric '{metric_name}' has stagnated around {avg_value:.2f}. "
                        f"Consider new optimization strategies.",
            category=metrics_list[-1].category,
            impact_score=0.5,
            effort_score=0.3,
            status=ImprovementStatus.IDENTIFIED.value,
            identified_at=datetime.now().isoformat()
        )
        
        self.improvements.append(improvement)
        self.logger.info(f"Identified stagnation in {metric_name}")
    
    def _identify_degradation_improvement(
        self,
        metric_name: str,
        metrics_list: List[PerformanceMetric]
    ) -> None:
        """
        Identify improvement opportunities when metrics are degrading.
        
        Args:
            metric_name: Name of the degrading metric
            metrics_list: List of recent metric values
        """
        values = [m.value for m in metrics_list]
        recent_avg = statistics.mean(values[-3:])
        older_avg = statistics.mean(values[:3]) if len(values) >= 6 else values[0]
        
        improvement = MicroImprovement(
            id=f"degradation_{metric_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            description=f"Metric '{metric_name}' is degrading: {older_avg:.2f} -> {recent_avg:.2f}. "
                        f"Investigate root cause and implement corrective action.",
            category=metrics_list[-1].category,
            impact_score=0.8,
            effort_score=0.5,
            status=ImprovementStatus.IDENTIFIED.value,
            identified_at=datetime.now().isoformat()
        )
        
        self.improvements.append(improvement)
        self.logger.warning(f"Identified degradation in {metric_name}")
    
    def get_reflection_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the current reflection state.
        
        Returns:
            Dictionary with reflection summary
        """
        pending = [i for i in self.improvements if i.status == ImprovementStatus.IDENTIFIED.value]
        in_progress = [i for i in self.improvements if i.status == ImprovementStatus.IN_PROGRESS.value]
        completed = [i for i in self.improvements if i.status == ImprovementStatus.COMPLETED.value]
        
        return {
            "total_metrics_recorded": len(self.metrics),
            "total_improvements_identified": len(self.improvements),
            "improvements_pending": len(pending),
            "improvements_in_progress": len(in_progress),
            "improvements_completed": len(completed),
            "top_priorities": [
                {
                    "id": i.id,
                    "description": i.description,
                    "priority": i.priority_score()
                }
                for i in sorted(pending, key=lambda x: x.priority_score(), reverse=True)[:5]
            ],
            "patterns_learned": len(self.patterns),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_statistics(self, top_k: int = None, **kwargs) -> Dict[str, Any]:
        """
        Get self-reflection statistics.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with statistics
        """
        return self.get_reflection_summary()
