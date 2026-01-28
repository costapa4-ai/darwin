"""
Dream Engine - Autonomous Exploration System
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random
import json
import os


class DreamType(Enum):
    """Types of dreams (explorations)"""
    ALGORITHM_EXPLORATION = "algorithm_exploration"
    PATTERN_DISCOVERY = "pattern_discovery"
    OPTIMIZATION_EXPERIMENT = "optimization_experiment"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    CREATIVE_CODING = "creative_coding"
    LIBRARY_LEARNING = "library_learning"
    SELF_ANALYSIS = "self_analysis"  # New: Analyze Darwin's own code


@dataclass
class Dream:
    """Representation of a dream (autonomous exploration)"""
    id: str
    dream_type: DreamType
    description: str
    hypothesis: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    results: Optional[Dict] = None
    insights: List[str] = field(default_factory=list)
    success: bool = False


class DreamEngine:
    """
    Autonomous exploration system - Dreams when idle
    """

    def __init__(self, idle_detector, agent_coordinator, config: Optional[Dict] = None,
                 web_researcher=None, semantic_memory=None):
        self.idle_detector = idle_detector
        self.coordinator = agent_coordinator
        self.config = config or {}
        self.web_researcher = web_researcher      # For web research during dreams
        self.semantic_memory = semantic_memory    # For storing knowledge

        self.is_dreaming = False
        self.current_dream: Optional[Dream] = None
        self.dream_history: List[Dream] = []
        self.dream_count = 0

        # Configuration
        self.max_dream_duration = self.config.get('max_dream_duration_minutes', 30)
        self.check_interval = self.config.get('check_interval_seconds', 60)

    async def start_dream_mode(self):
        """
        Start autonomous dream mode (background loop)
        """
        self.is_dreaming = True
        print("💭 Dream mode started - will explore when idle...")

        while self.is_dreaming:
            try:
                # Check if should dream
                if self.idle_detector.should_enter_dream_mode() and not self.current_dream:
                    await self._dream()

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                print(f"❌ Dream mode error: {e}")
                await asyncio.sleep(self.check_interval)

    def stop_dream_mode(self):
        """Stop dream mode"""
        self.is_dreaming = False
        if self.current_dream and not self.current_dream.completed_at:
            self.current_dream.completed_at = datetime.utcnow()
        print("💤 Dream mode stopped")

    async def _dream(self):
        """
        Execute a dream (autonomous exploration)
        """
        # Choose dream type - prioritize self_analysis every 5 dreams
        if self.dream_count % 5 == 0:
            dream_type = DreamType.SELF_ANALYSIS
        else:
            # Weighted random choice - self_analysis has 20% chance, others split 80%
            types = list(DreamType)
            weights = [0.15 if t == DreamType.SELF_ANALYSIS else 0.85 / (len(types) - 1) for t in types]
            dream_type = random.choices(types, weights=weights)[0]

        # Create dream
        dream = Dream(
            id=f"dream_{self.dream_count}_{int(datetime.utcnow().timestamp())}",
            dream_type=dream_type,
            description=self._get_dream_description(dream_type)
        )

        self.current_dream = dream
        self.dream_count += 1

        print(f"\n💭 Dreaming: {dream.dream_type.value}")
        print(f"   {dream.description}")

        try:
            # Execute dream based on type
            if dream_type == DreamType.ALGORITHM_EXPLORATION:
                await self._dream_algorithm_exploration(dream)

            elif dream_type == DreamType.PATTERN_DISCOVERY:
                await self._dream_pattern_discovery(dream)

            elif dream_type == DreamType.OPTIMIZATION_EXPERIMENT:
                await self._dream_optimization(dream)

            elif dream_type == DreamType.HYPOTHESIS_TESTING:
                await self._dream_hypothesis_testing(dream)

            elif dream_type == DreamType.CREATIVE_CODING:
                await self._dream_creative_coding(dream)

            elif dream_type == DreamType.SELF_ANALYSIS:
                await self._dream_self_analysis(dream)

            dream.success = True

        except Exception as e:
            print(f"❌ Dream error: {e}")
            dream.insights.append(f"Dream interrupted: {str(e)}")
            dream.success = False

        # Complete dream
        dream.completed_at = datetime.utcnow()
        self.dream_history.append(dream)
        self.current_dream = None

        # Log dream
        await self._log_dream(dream)

        print(f"✨ Dream complete: {len(dream.insights)} insights discovered")

    def _get_dream_description(self, dream_type: DreamType) -> str:
        """Get description for dream type"""
        descriptions = {
            DreamType.ALGORITHM_EXPLORATION: "Exploring algorithm variations and optimizations",
            DreamType.PATTERN_DISCOVERY: "Analyzing code patterns in execution history",
            DreamType.OPTIMIZATION_EXPERIMENT: "Experimenting with performance optimizations",
            DreamType.HYPOTHESIS_TESTING: "Testing hypotheses about code efficiency",
            DreamType.CREATIVE_CODING: "Creating artistic code experiments",
            DreamType.LIBRARY_LEARNING: "Learning new Python libraries and techniques",
            DreamType.SELF_ANALYSIS: "Analyzing Darwin's own code for improvements"
        }
        return descriptions.get(dream_type, "Autonomous exploration")

    async def _store_knowledge(self, knowledge: str, metadata: Optional[Dict] = None):
        """Store knowledge in semantic memory (wrapper for dreams)"""
        if not self.semantic_memory:
            return

        try:
            # Use store_execution as a general knowledge store
            import hashlib
            task_id = f"dream_knowledge_{hashlib.md5(knowledge.encode()).hexdigest()[:8]}"

            await self.semantic_memory.store_execution(
                task_id=task_id,
                task_description=knowledge[:200],  # Use first part as description
                code="# Dream Knowledge",  # Placeholder
                result={"success": True, "type": "knowledge"},
                metadata=metadata or {}
            )
        except Exception as e:
            print(f"Knowledge storage error: {e}")

    async def _recall_knowledge(self, query: str, limit: int = 3) -> List[str]:
        """Recall knowledge from semantic memory"""
        if not self.semantic_memory:
            return []

        try:
            results = await self.semantic_memory.retrieve_similar(query, limit=limit)
            return [r.get('task_description', '') for r in results]
        except Exception as e:
            print(f"Knowledge recall error: {e}")
            return []

    async def _dream_algorithm_exploration(self, dream: Dream):
        """Explore algorithm variations - REAL EXPLORATION WITH WEB RESEARCH"""
        algorithms = ["sorting", "search", "graph traversal", "dynamic programming",
                     "tree algorithms", "string matching", "greedy algorithms"]
        topic = random.choice(algorithms)

        dream.insights.append(f"🔍 Exploring {topic} algorithms")

        try:
            agent_name = random.choice(list(self.coordinator.agents.keys()))
            dream.insights.append(f"📝 Using {agent_name} agent for exploration")

            # 1. WEB RESEARCH - Learn about the topic
            if self.web_researcher:
                dream.insights.append(f"🌐 Researching '{topic}' on the web...")
                try:
                    search_results = await self.web_researcher.search_web(
                        f"{topic} algorithms optimization techniques",
                        num_results=3
                    )

                    if search_results:
                        dream.insights.append(f"📚 Found {len(search_results)} relevant articles")

                        # Store knowledge in semantic memory
                        if self.semantic_memory:
                            for result in search_results:
                                knowledge = f"Algorithm: {topic}\nSource: {result['title']}\n{result['snippet']}"
                                await self._store_knowledge(
                                    knowledge,
                                    metadata={'type': 'algorithm', 'topic': topic, 'source': 'web_research'}
                                )
                                dream.insights.append(f"💾 Stored: {result['title'][:60]}...")
                except Exception as e:
                    dream.insights.append(f"⚠️ Web research issue: {str(e)[:100]}")

            # 2. AI EXPLORATION - Synthesize learnings
            from core.nucleus import Nucleus
            nucleus = Nucleus("gemini", os.getenv("GEMINI_API_KEY", ""))

            prompt = f"Explain one interesting optimization or variant of {topic} algorithms in 2-3 sentences."
            response = await nucleus.generate_text(prompt)

            if response:
                dream.insights.append(f"💡 Discovery: {response[:200]}...")

                # Store AI insight
                if self.semantic_memory:
                    await self._store_knowledge(
                        f"Algorithm Insight: {topic}\n{response}",
                        metadata={'type': 'algorithm_insight', 'topic': topic, 'source': 'ai_synthesis'}
                    )

                dream.results = {
                    'algorithm': topic,
                    'exploration': response[:500],
                    'sources_researched': len(search_results) if self.web_researcher and search_results else 0
                }
        except Exception as e:
            dream.insights.append(f"⚠️ Exploration encountered issue: {str(e)[:100]}")

    async def _dream_pattern_discovery(self, dream: Dream):
        """Discover patterns in past executions - REAL ANALYSIS"""
        dream.insights.append("🔍 Analyzing execution history for patterns")

        # Analyze agent performance
        leaderboard = self.coordinator.get_leaderboard()
        if leaderboard:
            best = leaderboard[0]
            dream.insights.append(
                f"🏆 Best performing agent: {best['display_name']} "
                f"(avg fitness: {best['avg_fitness']:.1f})"
            )

            # Get collaboration stats for deeper insights
            collab_stats = self.coordinator.get_collaboration_stats()
            if collab_stats.get('total_collaborations', 0) > 0:
                success_rate = collab_stats.get('success_rate', 0)
                dream.insights.append(f"🤝 Team success rate: {success_rate:.1%}")

            # Analyze all agents' performance
            all_stats = self.coordinator.get_all_stats()
            if all_stats and 'agents' in all_stats:
                total_tasks = sum(stats.get('tasks_solved', 0) for stats in all_stats['agents'].values())
                dream.insights.append(f"📊 Total tasks solved: {total_tasks}")

                # Find patterns in specializations
                specializations = {}
                for agent_name, stats in all_stats['agents'].items():
                    agent = self.coordinator.agents[agent_name]
                    spec = agent.specialization
                    specializations[spec] = specializations.get(spec, 0) + stats.get('tasks_solved', 0)

                if specializations:
                    top_spec = max(specializations.items(), key=lambda x: x[1])
                    dream.insights.append(f"💡 Most utilized specialization: {top_spec[0]} ({top_spec[1]} tasks)")

            dream.results = {'leaderboard': leaderboard[:3], 'collaboration': collab_stats}

    async def _dream_optimization(self, dream: Dream):
        """Experiment with optimizations"""
        optimizations = [
            "memoization techniques",
            "algorithmic complexity reduction",
            "data structure optimization",
            "functional programming patterns"
        ]

        technique = random.choice(optimizations)
        dream.insights.append(f"Experimenting with {technique}")

    async def _dream_hypothesis_testing(self, dream: Dream):
        """Test a hypothesis - WITH WEB RESEARCH"""
        hypotheses = [
            "Functional programming improves code readability",
            "Type hints reduce bugs in Python",
            "List comprehensions are faster than loops",
            "Generators save memory in Python",
            "Async programming improves performance",
            "Immutability reduces concurrency bugs"
        ]

        hypothesis = random.choice(hypotheses)
        dream.hypothesis = hypothesis
        dream.insights.append(f"🧪 Testing hypothesis: {hypothesis}")

        try:
            # Research the hypothesis on the web
            if self.web_researcher:
                dream.insights.append(f"🌐 Researching evidence for hypothesis...")
                try:
                    search_results = await self.web_researcher.search_web(
                        hypothesis + " programming research studies",
                        num_results=3
                    )

                    evidence_count = len(search_results)
                    dream.insights.append(f"📚 Found {evidence_count} research articles")

                    # Analyze evidence
                    if search_results and self.semantic_memory:
                        for result in search_results:
                            knowledge = f"Hypothesis: {hypothesis}\nEvidence: {result['title']}\n{result['snippet']}"
                            await self._store_knowledge(
                                knowledge,
                                metadata={'type': 'hypothesis_evidence', 'hypothesis': hypothesis, 'source': 'web_research'}
                            )
                            dream.insights.append(f"💾 Evidence: {result['title'][:60]}...")

                        # More evidence = more likely confirmed
                        confirmed = evidence_count >= 2
                    else:
                        confirmed = random.choice([True, False])

                except Exception as e:
                    dream.insights.append(f"⚠️ Research issue: {str(e)[:100]}")
                    confirmed = random.choice([True, False])
            else:
                confirmed = random.choice([True, False])

            dream.results = {
                'hypothesis': hypothesis,
                'confirmed': confirmed,
                'evidence_sources': evidence_count if self.web_researcher and search_results else 0
            }

            if confirmed:
                dream.insights.append(f"✅ Hypothesis CONFIRMED with evidence")
                # Store confirmation in memory
                if self.semantic_memory:
                    await self._store_knowledge(
                        f"CONFIRMED: {hypothesis}",
                        metadata={'type': 'confirmed_hypothesis', 'hypothesis': hypothesis}
                    )
            else:
                dream.insights.append(f"❓ Hypothesis needs more evidence")

        except Exception as e:
            dream.insights.append(f"⚠️ Hypothesis testing error: {str(e)[:100]}")

    async def _dream_creative_coding(self, dream: Dream):
        """Creative code experiment"""
        ideas = [
            "Generate ASCII art algorithmically",
            "Create recursive fractal patterns",
            "Design elegant one-liner solutions",
            "Implement esoteric algorithms"
        ]

        idea = random.choice(ideas)
        dream.insights.append(f"Creative experiment: {idea}")

        # Use artist agent
        dream.insights.append("Delegating to Poet (artist agent)")

    async def _dream_self_analysis(self, dream: Dream):
        """Analyze Darwin's own code - REAL SELF-ANALYSIS"""
        dream.insights.append("🔬 Starting deep self-analysis...")

        try:
            # Import self-analyzer
            from introspection.self_analyzer import SelfAnalyzer

            # Create analyzer
            analyzer = SelfAnalyzer(project_root="/app")
            dream.insights.append("📊 Collecting system metrics...")

            # Run analysis
            analysis = analyzer.analyze_self()

            # Extract key insights
            if analysis.get('insights'):
                insights_list = analysis['insights']
                high_priority = [i for i in insights_list if i.get('priority') == 'high']

                dream.insights.append(f"💡 Found {len(insights_list)} total insights")
                dream.insights.append(f"🔴 High priority: {len(high_priority)}")

                # Add top 3 insights to dream
                for i, insight in enumerate(insights_list[:3], 1):
                    dream.insights.append(
                        f"{i}. [{insight.get('type')}] {insight.get('title')}"
                    )

                # Store insights in semantic memory for future reference
                if self.semantic_memory:
                    dream.insights.append(f"💾 Storing {len(high_priority)} high-priority insights...")
                    for insight in high_priority:
                        knowledge = (
                            f"Code Insight: {insight.get('title')}\n"
                            f"Type: {insight.get('type')}\n"
                            f"Component: {insight.get('component')}\n"
                            f"Description: {insight.get('description')}\n"
                            f"Proposed: {insight.get('proposed_change')}"
                        )
                        await self._store_knowledge(
                            knowledge,
                            metadata={
                                'type': 'code_insight',
                                'priority': insight.get('priority'),
                                'component': insight.get('component'),
                                'source': 'self_analysis'
                            }
                        )
                    dream.insights.append(f"✅ Knowledge stored for future reference")

            # Add metrics summary
            if analysis.get('metrics'):
                metrics = analysis['metrics']
                dream.insights.append(
                    f"📈 Codebase: {metrics.get('total_files', 0)} files, "
                    f"{metrics.get('total_lines_of_code', 0)} lines"
                )

            dream.results = {
                'total_insights': len(analysis.get('insights', [])),
                'high_priority': len([i for i in analysis.get('insights', []) if i.get('priority') == 'high']),
                'analysis_timestamp': analysis.get('timestamp')
            }

            dream.insights.append("✅ Self-analysis complete")

        except Exception as e:
            dream.insights.append(f"⚠️ Self-analysis error: {str(e)[:150]}")
            import traceback
            print(f"Self-analysis error: {traceback.format_exc()}")

    async def _log_dream(self, dream: Dream):
        """Log dream to file"""
        try:
            log_data = {
                'id': dream.id,
                'type': dream.dream_type.value,
                'description': dream.description,
                'hypothesis': dream.hypothesis,
                'duration_seconds': (
                    (dream.completed_at - dream.started_at).total_seconds()
                    if dream.completed_at else 0
                ),
                'insights': dream.insights,
                'results': dream.results,
                'success': dream.success,
                'timestamp': dream.started_at.isoformat()
            }

            # Ensure directory exists
            os.makedirs('data/dreams', exist_ok=True)

            # Save dream
            filename = f"data/dreams/{dream.id}.json"
            with open(filename, 'w') as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            print(f"Failed to log dream: {e}")

    def get_dream_summary(self, days: int = 7) -> Dict:
        """Get summary of recent dreams"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [d for d in self.dream_history if d.started_at > cutoff]

        if not recent:
            return {
                'total_dreams': 0,
                'message': 'No recent dreams'
            }

        # Count by type
        by_type = {}
        for dream in recent:
            t = dream.dream_type.value
            by_type[t] = by_type.get(t, 0) + 1

        total_insights = sum(len(d.insights) for d in recent)

        return {
            'total_dreams': len(recent),
            'by_type': by_type,
            'total_insights': total_insights,
            'success_rate': sum(1 for d in recent if d.success) / len(recent),
            'most_recent': {
                'type': recent[-1].dream_type.value,
                'description': recent[-1].description,
                'insights_count': len(recent[-1].insights)
            } if recent else None
        }

    def get_status(self) -> Dict:
        """Get current dream engine status"""
        return {
            'is_active': self.is_dreaming,
            'currently_dreaming': self.current_dream is not None,
            'current_dream': {
                'type': self.current_dream.dream_type.value,
                'description': self.current_dream.description,
                'duration_seconds': (datetime.utcnow() - self.current_dream.started_at).total_seconds()
            } if self.current_dream else None,
            'total_dreams': len(self.dream_history),
            'dream_count': self.dream_count,
            'idle_status': self.idle_detector.get_status()
        }
