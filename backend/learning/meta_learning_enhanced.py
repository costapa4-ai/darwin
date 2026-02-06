"""
Enhanced Meta-Learning System

Darwin optimizes its own learning process, identifies what works best,
and continuously improves how it learns.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import statistics
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class EnhancedMetaLearner:
    """
    Advanced meta-learning system for self-optimization
    """

    def __init__(self, semantic_memory, multi_model_router):
        """
        Initialize enhanced meta-learner

        Args:
            semantic_memory: Semantic memory system
            multi_model_router: AI router
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router

        # Learning metrics
        self.learning_sessions = []
        self.learning_effectiveness = defaultdict(list)
        self.knowledge_retention = {}
        self.optimal_strategies = []

        # Meta-learning state
        self.state_file = Path("./data/meta_learning_state.json")

        logger.info("EnhancedMetaLearner initialized")

    async def analyze_learning_effectiveness(self) -> Dict[str, Any]:
        """
        Analyze effectiveness of different learning methods

        Returns:
            Effectiveness analysis
        """
        logger.info("Analyzing learning effectiveness...")

        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'learning_sources_analysis': {},
            'optimal_timing': {},
            'knowledge_retention': {},
            'recommendations': []
        }

        try:
            # Get memory stats
            memory_stats = self.memory.get_stats()

            # Analyze different learning sources
            if hasattr(self.memory, 'get_all_executions'):
                all_executions = await self.memory.get_all_executions(limit=100)

                # Group by learning source
                by_source = defaultdict(list)
                for execution in all_executions:
                    metadata = execution.get('metadata', {})
                    source = metadata.get('learning_source', 'unknown')
                    by_source[source].append(execution)

                # Analyze effectiveness of each source
                for source, executions in by_source.items():
                    analysis['learning_sources_analysis'][source] = {
                        'count': len(executions),
                        'avg_quality': self._estimate_quality(executions),
                        'recent_trend': self._calculate_trend(executions)
                    }

                # Identify most effective sources
                if by_source:
                    effectiveness_scores = {
                        source: data['avg_quality']
                        for source, data in analysis['learning_sources_analysis'].items()
                    }

                    best_source = max(effectiveness_scores.items(), key=lambda x: x[1])
                    analysis['most_effective_source'] = {
                        'source': best_source[0],
                        'quality_score': best_source[1]
                    }

                    analysis['recommendations'].append(
                        f"Focus more on {best_source[0]} (quality score: {best_source[1]:.2f})"
                    )

            # Analyze learning timing patterns
            timing_analysis = await self._analyze_learning_timing()
            analysis['optimal_timing'] = timing_analysis

            if timing_analysis.get('best_time'):
                analysis['recommendations'].append(
                    f"Schedule intensive learning during {timing_analysis['best_time']}"
                )

            # Knowledge retention analysis
            retention = await self._analyze_knowledge_retention()
            analysis['knowledge_retention'] = retention

            if retention.get('retention_rate', 0) < 0.7:
                analysis['recommendations'].append(
                    "Implement spaced repetition to improve retention"
                )

        except Exception as e:
            logger.error(f"Error analyzing learning effectiveness: {e}")
            analysis['error'] = str(e)

        return analysis

    def _estimate_quality(self, executions: List[Dict]) -> float:
        """
        Estimate quality of learning from executions

        Args:
            executions: List of execution records

        Returns:
            Quality score (0-1)
        """
        if not executions:
            return 0.0

        quality_indicators = []

        for execution in executions:
            # Factors that indicate quality:
            # - Success rate
            # - Metadata completeness
            # - Task description length (indicates detail)
            # - Code quality (if present)

            score = 0.0

            # Success contributes 40%
            result = execution.get('result', {})
            if isinstance(result, dict) and result.get('success'):
                score += 0.4

            # Metadata completeness contributes 30%
            metadata = execution.get('metadata', {})
            if len(metadata) >= 3:  # Has at least 3 metadata fields
                score += 0.3

            # Description detail contributes 30%
            description = execution.get('task_description', '')
            if len(description) > 100:
                score += 0.3

            quality_indicators.append(score)

        return statistics.mean(quality_indicators) if quality_indicators else 0.0

    def _calculate_trend(self, executions: List[Dict]) -> str:
        """
        Calculate trend in learning quality

        Args:
            executions: List of execution records

        Returns:
            Trend description
        """
        if len(executions) < 4:
            return 'insufficient_data'

        # Split into older and recent halves
        mid_point = len(executions) // 2
        older = executions[:mid_point]
        recent = executions[mid_point:]

        older_quality = self._estimate_quality(older)
        recent_quality = self._estimate_quality(recent)

        diff = recent_quality - older_quality

        if diff > 0.1:
            return 'improving'
        elif diff < -0.1:
            return 'declining'
        else:
            return 'stable'

    async def _analyze_learning_timing(self) -> Dict[str, Any]:
        """
        Analyze when learning is most effective

        Returns:
            Timing analysis
        """
        timing_data = {
            'morning': [],  # 6-12
            'afternoon': [],  # 12-18
            'evening': [],  # 18-24
            'night': []  # 0-6
        }

        try:
            # Analyze learning session times
            for session in self.learning_sessions[-50:]:  # Last 50 sessions
                timestamp = session.get('timestamp')
                if timestamp:
                    dt = datetime.fromisoformat(timestamp)
                    hour = dt.hour

                    quality = session.get('quality', 0.5)

                    if 6 <= hour < 12:
                        timing_data['morning'].append(quality)
                    elif 12 <= hour < 18:
                        timing_data['afternoon'].append(quality)
                    elif 18 <= hour < 24:
                        timing_data['evening'].append(quality)
                    else:
                        timing_data['night'].append(quality)

            # Calculate averages
            averages = {}
            for period, qualities in timing_data.items():
                if qualities:
                    averages[period] = statistics.mean(qualities)

            if averages:
                best_time = max(averages.items(), key=lambda x: x[1])
                return {
                    'averages': averages,
                    'best_time': best_time[0],
                    'best_time_quality': best_time[1]
                }

        except Exception as e:
            logger.error(f"Error analyzing learning timing: {e}")

        return {}

    async def _analyze_knowledge_retention(self) -> Dict[str, Any]:
        """
        Analyze how well knowledge is retained

        Returns:
            Retention analysis
        """
        retention_data = {
            'total_knowledge_items': 0,
            'retained_items': 0,
            'retention_rate': 0.0
        }

        try:
            memory_stats = self.memory.get_stats()
            retention_data['total_knowledge_items'] = memory_stats.get('total_executions', 0)

            # Estimate retention based on reuse
            # Knowledge is "retained" if it's retrieved/used again
            if hasattr(self.memory, 'get_retrieval_stats'):
                retrieval_stats = await self.memory.get_retrieval_stats()
                retention_data['retained_items'] = retrieval_stats.get('reused_count', 0)

                if retention_data['total_knowledge_items'] > 0:
                    retention_data['retention_rate'] = (
                        retention_data['retained_items'] / retention_data['total_knowledge_items']
                    )

        except Exception as e:
            logger.error(f"Error analyzing retention: {e}")

        return retention_data

    async def optimize_learning_strategy(self) -> Dict[str, Any]:
        """
        Optimize Darwin's learning strategy based on analysis

        Returns:
            Optimization report
        """
        logger.info("Optimizing learning strategy...")

        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'analysis': {},
            'optimizations_applied': [],
            'expected_improvements': []
        }

        try:
            # Analyze current effectiveness
            effectiveness = await self.analyze_learning_effectiveness()
            report['analysis'] = effectiveness

            # Apply optimizations based on analysis
            optimizations = []

            # 1. Prioritize effective sources
            if effectiveness.get('most_effective_source'):
                best_source = effectiveness['most_effective_source']
                optimizations.append({
                    'type': 'source_priority',
                    'action': f"Increase time on {best_source['source']}",
                    'reason': f"Highest quality score: {best_source['quality_score']:.2f}"
                })

            # 2. Optimize timing
            timing = effectiveness.get('optimal_timing', {})
            if timing.get('best_time'):
                optimizations.append({
                    'type': 'timing',
                    'action': f"Schedule intensive learning during {timing['best_time']}",
                    'reason': f"Quality: {timing.get('best_time_quality', 0):.2f}"
                })

            # 3. Address retention issues
            retention = effectiveness.get('knowledge_retention', {})
            retention_rate = retention.get('retention_rate', 0)
            if retention_rate < 0.7:
                optimizations.append({
                    'type': 'retention',
                    'action': "Implement spaced repetition review cycles",
                    'reason': f"Current retention: {retention_rate:.1%}"
                })

            # 4. Diversify if needed
            sources = effectiveness.get('learning_sources_analysis', {})
            if len(sources) < 3:
                optimizations.append({
                    'type': 'diversity',
                    'action': "Expand to more learning sources",
                    'reason': f"Only using {len(sources)} sources"
                })

            report['optimizations_applied'] = optimizations

            # Store optimal strategies
            self.optimal_strategies.extend(optimizations)

            # Expected improvements
            report['expected_improvements'] = [
                "Increased learning efficiency",
                "Better knowledge retention",
                "More diverse knowledge base",
                "Optimized learning schedule"
            ]

            # Save state
            await self._save_state()

        except Exception as e:
            logger.error(f"Error optimizing learning strategy: {e}")
            report['error'] = str(e)

        return report

    async def track_learning_session(self,
                                    source: str,
                                    topic: str,
                                    duration_minutes: float,
                                    knowledge_gained: int,
                                    quality: float):
        """
        Track a learning session for meta-analysis

        Args:
            source: Learning source
            topic: Topic studied
            duration_minutes: Duration in minutes
            knowledge_gained: Number of knowledge items
            quality: Estimated quality (0-1)
        """
        session = {
            'timestamp': datetime.utcnow().isoformat(),
            'source': source,
            'topic': topic,
            'duration_minutes': duration_minutes,
            'knowledge_gained': knowledge_gained,
            'quality': quality,
            'efficiency': knowledge_gained / duration_minutes if duration_minutes > 0 else 0
        }

        self.learning_sessions.append(session)
        self.learning_effectiveness[source].append(quality)

        logger.info(f"Tracked learning session: {source} - {topic} (quality: {quality:.2f})")

        # Trigger ON_LEARNING hook for connected systems (feedback loops, etc.)
        try:
            from consciousness.hooks import trigger_hook, HookEvent

            asyncio.create_task(
                trigger_hook(
                    HookEvent.ON_LEARNING,
                    data={
                        "session": session,
                        "source": source,
                        "topic": topic,
                        "quality": quality,
                        "knowledge_gained": knowledge_gained
                    },
                    source="meta_learner"
                )
            )
        except Exception as e:
            logger.debug(f"Could not trigger ON_LEARNING hook: {e}")

    async def generate_learning_report(self, period_days: int = 7) -> Dict[str, Any]:
        """
        Generate comprehensive learning report

        Args:
            period_days: Period to analyze

        Returns:
            Learning report
        """
        logger.info(f"Generating {period_days}-day learning report...")

        cutoff_date = datetime.utcnow() - timedelta(days=period_days)

        report = {
            'period_days': period_days,
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {},
            'details': {},
            'insights': []
        }

        try:
            # Filter recent sessions
            recent_sessions = [
                s for s in self.learning_sessions
                if datetime.fromisoformat(s['timestamp']) >= cutoff_date
            ]

            if recent_sessions:
                # Summary statistics
                total_duration = sum(s['duration_minutes'] for s in recent_sessions)
                total_knowledge = sum(s['knowledge_gained'] for s in recent_sessions)
                avg_quality = statistics.mean(s['quality'] for s in recent_sessions)

                report['summary'] = {
                    'sessions_count': len(recent_sessions),
                    'total_duration_hours': round(total_duration / 60, 2),
                    'total_knowledge_items': total_knowledge,
                    'average_quality': round(avg_quality, 2),
                    'learning_rate': round(total_knowledge / total_duration * 60, 2) if total_duration > 0 else 0
                }

                # By source breakdown
                by_source = defaultdict(lambda: {'sessions': 0, 'knowledge': 0, 'duration': 0})
                for session in recent_sessions:
                    source = session['source']
                    by_source[source]['sessions'] += 1
                    by_source[source]['knowledge'] += session['knowledge_gained']
                    by_source[source]['duration'] += session['duration_minutes']

                report['details']['by_source'] = dict(by_source)

                # Generate insights
                if report['summary']['learning_rate'] > 5:
                    report['insights'].append("Excellent learning rate - maintain current pace")
                elif report['summary']['learning_rate'] < 2:
                    report['insights'].append("Low learning rate - consider optimizing approach")

                if avg_quality > 0.7:
                    report['insights'].append("High quality learning - strategies are effective")
                else:
                    report['insights'].append("Quality could improve - review learning methods")

        except Exception as e:
            logger.error(f"Error generating learning report: {e}")
            report['error'] = str(e)

        return report

    async def _save_state(self):
        """Save meta-learning state"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'learning_sessions': self.learning_sessions[-100:],  # Last 100
                'optimal_strategies': self.optimal_strategies[-20:],  # Last 20
                'saved_at': datetime.utcnow().isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info("Meta-learning state saved")

        except Exception as e:
            logger.error(f"Error saving meta-learning state: {e}")

    async def _restore_state(self):
        """Restore meta-learning state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                self.learning_sessions = state.get('learning_sessions', [])
                self.optimal_strategies = state.get('optimal_strategies', [])

                logger.info("Meta-learning state restored")

        except Exception as e:
            logger.error(f"Error restoring meta-learning state: {e}")

    def get_current_strategy(self) -> Dict[str, Any]:
        """
        Get current optimal learning strategy

        Returns:
            Current strategy
        """
        if not self.optimal_strategies:
            return {
                'status': 'default',
                'message': 'Using default learning strategy'
            }

        return {
            'status': 'optimized',
            'strategies': self.optimal_strategies[-5:],  # Last 5 optimizations
            'applied_at': self.optimal_strategies[-1].get('timestamp') if self.optimal_strategies else None
        }

    async def get_learning_analytics(self) -> Dict[str, Any]:
        """
        Get learning analytics for feedback loops priority boosting.

        Returns topic quality scores so feedback loops can boost priority
        for topics where Darwin learns effectively.
        """
        analytics = {
            "topic_quality": {},
            "overall_effectiveness": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Calculate topic quality from learning sessions
            topic_quality = defaultdict(list)
            for session in self.learning_sessions[-100:]:
                topic = session.get('topic', 'unknown')
                quality = session.get('quality', 0.5)
                topic_quality[topic].append(quality)

            # Average quality per topic
            for topic, qualities in topic_quality.items():
                if qualities:
                    analytics["topic_quality"][topic] = statistics.mean(qualities)

            # Overall effectiveness
            if self.learning_sessions:
                all_qualities = [s.get('quality', 0.5) for s in self.learning_sessions[-50:]]
                analytics["overall_effectiveness"] = statistics.mean(all_qualities)

        except Exception as e:
            logger.error(f"Error getting learning analytics: {e}")

        return analytics

    def get_capability_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify areas where Darwin struggles.

        Returns list of capability gaps for tool idea generation.
        Darwin can use these to create tools that address weaknesses.
        """
        gaps = []

        try:
            # Analyze learning sessions for low-quality areas
            by_source = defaultdict(list)
            for session in self.learning_sessions[-100:]:
                source = session.get('source', 'unknown')
                quality = session.get('quality', 0.5)
                by_source[source].append(quality)

            # Find sources with consistently low quality
            for source, qualities in by_source.items():
                if qualities:
                    avg_quality = statistics.mean(qualities)
                    if avg_quality < 0.5:
                        gaps.append({
                            "area": source,
                            "avg_quality": avg_quality,
                            "session_count": len(qualities),
                            "severity": "high" if avg_quality < 0.3 else "medium"
                        })

            # Sort by severity (lowest quality first)
            gaps.sort(key=lambda x: x.get('avg_quality', 1.0))

        except Exception as e:
            logger.error(f"Error getting capability gaps: {e}")

        return gaps

    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get summary of learning with weak areas.

        Returns summary dict with weak_areas list for proactive learning.
        Used by proactive_engine to identify what Darwin should learn.
        """
        summary = {
            "weak_areas": [],
            "strong_areas": [],
            "total_sessions": len(self.learning_sessions),
            "recent_quality": 0.0
        }

        try:
            # Get capability gaps as weak areas
            gaps = self.get_capability_gaps()
            summary["weak_areas"] = [
                {"area": g["area"], "quality": g["avg_quality"]}
                for g in gaps[:5]
            ]

            # Find strong areas
            by_source = defaultdict(list)
            for session in self.learning_sessions[-100:]:
                source = session.get('source', 'unknown')
                quality = session.get('quality', 0.5)
                by_source[source].append(quality)

            for source, qualities in by_source.items():
                if qualities:
                    avg_quality = statistics.mean(qualities)
                    if avg_quality > 0.7:
                        summary["strong_areas"].append({
                            "area": source,
                            "quality": avg_quality
                        })

            # Recent quality
            if self.learning_sessions:
                recent = [s.get('quality', 0.5) for s in self.learning_sessions[-10:]]
                summary["recent_quality"] = statistics.mean(recent)

        except Exception as e:
            logger.error(f"Error getting learning summary: {e}")

        return summary
