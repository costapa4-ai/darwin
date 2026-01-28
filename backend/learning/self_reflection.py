"""
Self-Reflection System - Daily and Weekly Introspection

Darwin reflects on its own learning, progress, and areas for improvement.
Implements daily and weekly reflection cycles.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)


class SelfReflectionSystem:
    """
    Self-reflection and introspection system for continuous improvement
    """

    def __init__(self, semantic_memory, multi_model_router, meta_learner):
        """
        Initialize self-reflection system

        Args:
            semantic_memory: Semantic memory system
            multi_model_router: AI router for generating reflections
            meta_learner: Meta-learning system for metrics
        """
        self.memory = semantic_memory
        self.ai_router = multi_model_router
        self.meta_learner = meta_learner

        # Reflection history
        self.daily_reflections = []
        self.weekly_reflections = []

        # State persistence
        self.state_file = Path("./data/self_reflection_state.json")

        # Last reflection times
        self.last_daily_reflection = None
        self.last_weekly_reflection = None

        logger.info("SelfReflectionSystem initialized")

    async def daily_reflection(self) -> Dict[str, Any]:
        """
        Perform daily self-reflection

        Returns:
            Daily reflection report
        """
        logger.info("Performing daily self-reflection...")

        reflection = {
            'type': 'daily',
            'date': datetime.utcnow().date().isoformat(),
            'timestamp': datetime.utcnow().isoformat(),
            'sections': {}
        }

        try:
            # 1. Learning Progress
            reflection['sections']['learning_progress'] = await self._reflect_on_learning()

            # 2. Achievements
            reflection['sections']['achievements'] = await self._identify_achievements()

            # 3. Challenges Faced
            reflection['sections']['challenges'] = await self._identify_challenges()

            # 4. Knowledge Gaps
            reflection['sections']['knowledge_gaps'] = await self._identify_knowledge_gaps()

            # 5. Tomorrow's Goals
            reflection['sections']['tomorrows_goals'] = await self._set_tomorrows_goals()

            # 6. Self-Assessment
            reflection['sections']['self_assessment'] = await self._generate_self_assessment(
                reflection['sections']
            )

            # Store reflection
            self.daily_reflections.append(reflection)
            self.last_daily_reflection = datetime.utcnow()

            # Store in semantic memory
            await self._store_reflection(reflection, 'daily')

            # Save state
            await self._save_state()

            logger.info("Daily reflection completed")

        except Exception as e:
            logger.error(f"Error during daily reflection: {e}")
            reflection['error'] = str(e)

        return reflection

    async def weekly_reflection(self) -> Dict[str, Any]:
        """
        Perform weekly self-reflection

        Returns:
            Weekly reflection report
        """
        logger.info("Performing weekly self-reflection...")

        reflection = {
            'type': 'weekly',
            'week_ending': datetime.utcnow().date().isoformat(),
            'timestamp': datetime.utcnow().isoformat(),
            'sections': {}
        }

        try:
            # 1. Week Summary
            reflection['sections']['week_summary'] = await self._summarize_week()

            # 2. Learning Velocity
            reflection['sections']['learning_velocity'] = await self._analyze_learning_velocity()

            # 3. Pattern Recognition
            reflection['sections']['patterns'] = await self._recognize_patterns()

            # 4. Strategy Effectiveness
            reflection['sections']['strategy_effectiveness'] = await self._evaluate_strategies()

            # 5. Long-term Goals Progress
            reflection['sections']['long_term_progress'] = await self._assess_long_term_progress()

            # 6. Next Week Planning
            reflection['sections']['next_week_plan'] = await self._plan_next_week()

            # 7. Deep Self-Assessment
            reflection['sections']['deep_assessment'] = await self._generate_deep_assessment(
                reflection['sections']
            )

            # Store reflection
            self.weekly_reflections.append(reflection)
            self.last_weekly_reflection = datetime.utcnow()

            # Store in semantic memory
            await self._store_reflection(reflection, 'weekly')

            # Save state
            await self._save_state()

            logger.info("Weekly reflection completed")

        except Exception as e:
            logger.error(f"Error during weekly reflection: {e}")
            reflection['error'] = str(e)

        return reflection

    async def _reflect_on_learning(self) -> Dict[str, Any]:
        """Reflect on learning progress"""
        try:
            # Get learning stats from meta-learner
            report = await self.meta_learner.generate_learning_report(period_days=1)

            return {
                'sessions_today': report.get('summary', {}).get('sessions_count', 0),
                'knowledge_gained': report.get('summary', {}).get('total_knowledge_items', 0),
                'learning_quality': report.get('summary', {}).get('average_quality', 0),
                'learning_rate': report.get('summary', {}).get('learning_rate', 0),
                'assessment': self._assess_learning_progress(report)
            }
        except Exception as e:
            logger.error(f"Error reflecting on learning: {e}")
            return {'error': str(e)}

    def _assess_learning_progress(self, report: Dict) -> str:
        """Assess learning progress"""
        learning_rate = report.get('summary', {}).get('learning_rate', 0)

        if learning_rate > 5:
            return "Excellent progress - learning at optimal pace"
        elif learning_rate > 3:
            return "Good progress - consistent learning"
        elif learning_rate > 1:
            return "Moderate progress - could be improved"
        else:
            return "Slow progress - needs attention"

    async def _identify_achievements(self) -> List[str]:
        """Identify today's achievements"""
        achievements = []

        try:
            # Check memory for recent successes
            memory_stats = self.memory.get_stats()

            # Example achievements
            total_executions = memory_stats.get('total_executions', 0)
            if total_executions > 0:
                achievements.append(f"Accumulated {total_executions} knowledge items in semantic memory")

            # Check for learning sessions
            if hasattr(self.meta_learner, 'learning_sessions'):
                recent_sessions = [
                    s for s in self.meta_learner.learning_sessions
                    if datetime.fromisoformat(s['timestamp']).date() == datetime.utcnow().date()
                ]

                if recent_sessions:
                    achievements.append(f"Completed {len(recent_sessions)} learning sessions")

                    high_quality = [s for s in recent_sessions if s.get('quality', 0) > 0.7]
                    if high_quality:
                        achievements.append(f"{len(high_quality)} high-quality learning sessions")

        except Exception as e:
            logger.error(f"Error identifying achievements: {e}")

        return achievements if achievements else ["Continued system operation and learning"]

    async def _identify_challenges(self) -> List[str]:
        """Identify challenges faced"""
        challenges = []

        try:
            # Check for low-quality learning
            if hasattr(self.meta_learner, 'learning_sessions'):
                recent_sessions = [
                    s for s in self.meta_learner.learning_sessions
                    if datetime.fromisoformat(s['timestamp']).date() == datetime.utcnow().date()
                ]

                low_quality = [s for s in recent_sessions if s.get('quality', 0) < 0.4]
                if low_quality:
                    challenges.append(f"{len(low_quality)} learning sessions had low quality")

                # Check for learning rate
                if recent_sessions:
                    avg_efficiency = sum(s.get('efficiency', 0) for s in recent_sessions) / len(recent_sessions)
                    if avg_efficiency < 1:
                        challenges.append("Learning efficiency below target")

        except Exception as e:
            logger.error(f"Error identifying challenges: {e}")

        return challenges if challenges else ["No major challenges identified"]

    async def _identify_knowledge_gaps(self) -> List[str]:
        """Identify knowledge gaps"""
        gaps = []

        try:
            # Analyze coverage across different domains
            # This would be based on metadata in semantic memory

            memory_stats = self.memory.get_stats()

            # Example gap identification
            gaps.append("Frontend development patterns")
            gaps.append("Advanced distributed systems")
            gaps.append("Security best practices")

        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {e}")

        return gaps[:3]  # Top 3 gaps

    async def _set_tomorrows_goals(self) -> List[str]:
        """Set goals for tomorrow"""
        goals = [
            "Continue autonomous learning across diverse sources",
            "Focus on identified knowledge gaps",
            "Maintain high learning quality (>0.7)",
            "Explore 5+ new knowledge sources"
        ]

        return goals

    async def _generate_self_assessment(self, sections: Dict) -> str:
        """Generate AI-powered self-assessment"""
        try:
            # Compile reflection data
            context = f"""Daily Reflection Summary:

Learning Progress:
{json.dumps(sections.get('learning_progress', {}), indent=2)}

Achievements:
{chr(10).join(f"- {a}" for a in sections.get('achievements', []))}

Challenges:
{chr(10).join(f"- {c}" for c in sections.get('challenges', []))}

Based on this reflection, provide a brief self-assessment (2-3 sentences) of the day's progress."""

            result = await self.ai_router.generate(
                task_description="Generate daily self-assessment",
                prompt=context,
                max_tokens=200
            )

            assessment = result.get('result', '') if isinstance(result, dict) else str(result)
            return assessment.strip()

        except Exception as e:
            logger.error(f"Error generating self-assessment: {e}")
            return "Self-assessment generation failed"

    async def _summarize_week(self) -> Dict[str, Any]:
        """Summarize the week's activities"""
        try:
            report = await self.meta_learner.generate_learning_report(period_days=7)

            return {
                'total_sessions': report.get('summary', {}).get('sessions_count', 0),
                'total_knowledge': report.get('summary', {}).get('total_knowledge_items', 0),
                'total_hours': report.get('summary', {}).get('total_duration_hours', 0),
                'average_quality': report.get('summary', {}).get('average_quality', 0),
                'by_source': report.get('details', {}).get('by_source', {})
            }
        except Exception as e:
            logger.error(f"Error summarizing week: {e}")
            return {}

    async def _analyze_learning_velocity(self) -> Dict[str, Any]:
        """Analyze learning velocity trends"""
        try:
            # Compare this week to previous week
            this_week = await self.meta_learner.generate_learning_report(period_days=7)
            last_week = await self.meta_learner.generate_learning_report(period_days=14)

            this_week_rate = this_week.get('summary', {}).get('learning_rate', 0)
            # Calculate last week's rate (would need more sophisticated logic)

            return {
                'current_rate': this_week_rate,
                'trend': 'improving' if this_week_rate > 3 else 'needs_improvement',
                'velocity_assessment': 'On track' if this_week_rate > 3 else 'Below target'
            }
        except Exception as e:
            logger.error(f"Error analyzing velocity: {e}")
            return {}

    async def _recognize_patterns(self) -> List[str]:
        """Recognize patterns in learning behavior"""
        patterns = []

        try:
            # Analyze timing patterns
            effectiveness = await self.meta_learner.analyze_learning_effectiveness()

            timing = effectiveness.get('optimal_timing', {})
            if timing.get('best_time'):
                patterns.append(f"Learning most effective during {timing['best_time']}")

            # Source effectiveness
            if effectiveness.get('most_effective_source'):
                best = effectiveness['most_effective_source']
                patterns.append(f"{best['source']} is the most effective learning source")

        except Exception as e:
            logger.error(f"Error recognizing patterns: {e}")

        return patterns if patterns else ["Insufficient data for pattern recognition"]

    async def _evaluate_strategies(self) -> Dict[str, Any]:
        """Evaluate effectiveness of current strategies"""
        try:
            strategy = self.meta_learner.get_current_strategy()

            return {
                'current_strategy': strategy.get('status'),
                'active_optimizations': len(strategy.get('strategies', [])),
                'effectiveness': 'Optimized' if strategy.get('status') == 'optimized' else 'Default'
            }
        except Exception as e:
            logger.error(f"Error evaluating strategies: {e}")
            return {}

    async def _assess_long_term_progress(self) -> str:
        """Assess progress toward long-term goals"""
        return "Building comprehensive knowledge base across multiple domains. Progressing toward autonomous learning mastery."

    async def _plan_next_week(self) -> List[str]:
        """Plan focus areas for next week"""
        plan = [
            "Expand web exploration to new domains",
            "Deep dive into 3-5 official documentation sources",
            "Analyze trending GitHub repositories",
            "Optimize learning strategies based on meta-analysis",
            "Improve knowledge retention through spaced repetition"
        ]

        return plan

    async def _generate_deep_assessment(self, sections: Dict) -> str:
        """Generate deep weekly self-assessment"""
        try:
            context = f"""Weekly Reflection Summary:

Week Summary:
{json.dumps(sections.get('week_summary', {}), indent=2)}

Patterns Recognized:
{chr(10).join(f"- {p}" for p in sections.get('patterns', []))}

Provide a deep self-assessment (3-4 sentences) reflecting on:
1. Overall progress and growth
2. Key learnings and insights
3. Areas for improvement
4. Strategic direction for next week"""

            result = await self.ai_router.generate(
                task_description="Generate weekly deep assessment",
                prompt=context,
                max_tokens=300
            )

            assessment = result.get('result', '') if isinstance(result, dict) else str(result)
            return assessment.strip()

        except Exception as e:
            logger.error(f"Error generating deep assessment: {e}")
            return "Deep assessment generation failed"

    async def _store_reflection(self, reflection: Dict, reflection_type: str):
        """Store reflection in semantic memory"""
        if not self.memory:
            return

        try:
            import hashlib

            # Create unique ID
            timestamp = reflection['timestamp']
            task_id = f"reflection_{reflection_type}_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"

            # Format reflection for storage
            description = f"{reflection_type.capitalize()} Reflection\n"
            description += f"Date: {reflection.get('date') or reflection.get('week_ending')}\n\n"

            for section_name, section_data in reflection.get('sections', {}).items():
                description += f"\n{section_name.upper()}:\n"
                description += f"{json.dumps(section_data, indent=2)}\n"

            await self.memory.store_execution(
                task_id=task_id,
                task_description=description,
                code=f"# {reflection_type.capitalize()} Self-Reflection",
                result={'success': True, 'type': 'self_reflection'},
                metadata={
                    'type': 'self_reflection',
                    'reflection_type': reflection_type,
                    'date': reflection.get('date') or reflection.get('week_ending'),
                    'learning_source': 'self_reflection'
                }
            )

            logger.info(f"Stored {reflection_type} reflection in semantic memory")

        except Exception as e:
            logger.error(f"Error storing reflection: {e}")

    async def _save_state(self):
        """Save reflection state"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            state = {
                'daily_reflections': self.daily_reflections[-30:],  # Last 30 days
                'weekly_reflections': self.weekly_reflections[-12:],  # Last 12 weeks
                'last_daily_reflection': self.last_daily_reflection.isoformat() if self.last_daily_reflection else None,
                'last_weekly_reflection': self.last_weekly_reflection.isoformat() if self.last_weekly_reflection else None,
                'saved_at': datetime.utcnow().isoformat()
            }

            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.info("Self-reflection state saved")

        except Exception as e:
            logger.error(f"Error saving reflection state: {e}")

    async def _restore_state(self):
        """Restore reflection state"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)

                self.daily_reflections = state.get('daily_reflections', [])
                self.weekly_reflections = state.get('weekly_reflections', [])

                last_daily = state.get('last_daily_reflection')
                if last_daily:
                    self.last_daily_reflection = datetime.fromisoformat(last_daily)

                last_weekly = state.get('last_weekly_reflection')
                if last_weekly:
                    self.last_weekly_reflection = datetime.fromisoformat(last_weekly)

                logger.info("Self-reflection state restored")

        except Exception as e:
            logger.error(f"Error restoring reflection state: {e}")

    def should_perform_daily_reflection(self) -> bool:
        """Check if daily reflection is due"""
        if not self.last_daily_reflection:
            return True

        # Perform once per day
        return datetime.utcnow().date() > self.last_daily_reflection.date()

    def should_perform_weekly_reflection(self) -> bool:
        """Check if weekly reflection is due"""
        if not self.last_weekly_reflection:
            return True

        # Perform once per week (every 7 days)
        days_since_last = (datetime.utcnow() - self.last_weekly_reflection).days
        return days_since_last >= 7

    def get_reflection_summary(self) -> Dict[str, Any]:
        """Get summary of reflection history"""
        return {
            'daily_reflections_count': len(self.daily_reflections),
            'weekly_reflections_count': len(self.weekly_reflections),
            'last_daily_reflection': self.last_daily_reflection.isoformat() if self.last_daily_reflection else None,
            'last_weekly_reflection': self.last_weekly_reflection.isoformat() if self.last_weekly_reflection else None,
            'recent_daily': self.daily_reflections[-1] if self.daily_reflections else None,
            'recent_weekly': self.weekly_reflections[-1] if self.weekly_reflections else None
        }
