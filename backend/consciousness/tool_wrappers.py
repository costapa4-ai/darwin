"""
Tool Wrappers - Auto-register all available tools

Wraps existing modules to make them discoverable by the Tool Registry.
"""

from typing import Dict, Any
from consciousness.tool_registry import ToolRegistry, ToolCategory, ToolMode

from utils.logger import get_logger

logger = get_logger(__name__)


def register_all_tools(
    registry: ToolRegistry,
    **components
) -> int:
    """
    Auto-register all available tools

    Args:
        registry: Tool registry
        components: Dict of available components

    Returns:
        Number of tools registered
    """
    count = 0

    # Extract components
    web_explorer = components.get('web_explorer')
    documentation_reader = components.get('documentation_reader')
    code_repo_analyzer = components.get('code_repo_analyzer')
    enhanced_meta_learner = components.get('enhanced_meta_learner')
    self_reflection_system = components.get('self_reflection_system')
    trial_error_engine = components.get('trial_error_engine')
    experiment_designer = components.get('experiment_designer')
    curiosity_engine = components.get('curiosity_engine')
    dream_engine = components.get('dream_engine')

    # ============================================================
    # LEARNING TOOLS (SLEEP)
    # ============================================================

    if web_explorer:
        async def explore_web(**kwargs) -> Dict[str, Any]:
            """Explore the web autonomously"""
            try:
                result = await web_explorer.explore_trending_topics()

                # Extract URLs visited for display
                urls_visited = [d['url'] for d in result.get('discoveries', []) if 'url' in d]

                return {
                    'success': True,
                    'urls_explored': result.get('urls_explored', 0),
                    'knowledge_extracted': result.get('knowledge_extracted', 0),
                    'knowledge_items': result.get('knowledge_extracted', 0),  # Alias for compatibility
                    'discoveries': result.get('discoveries', []),
                    'urls_visited': urls_visited,  # NEW: List of URLs visited
                    'url': urls_visited[0] if urls_visited else None,  # NEW: First URL for display
                    'topic': result.get('topic', 'trending technology and AI')
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="web_explorer",
            description="Autonomously search the web for new knowledge, algorithms, patterns, and innovations to learn and implement",
            category=ToolCategory.LEARNING,
            mode=ToolMode.SLEEP,
            execute_fn=explore_web,
            cost=1,  # LOW COST - prioritize web research!
            cooldown_minutes=5,  # Research frequently!
            metadata={'source_type': 'web', 'learning_rate': 'very_high', 'priority': 'high'}
        )
        count += 1

    if documentation_reader:
        async def read_docs(**kwargs) -> Dict[str, Any]:
            """Read random official documentation"""
            try:
                result = await documentation_reader.read_random_documentation()

                tech = result.get('technology', 'Unknown')
                source = result.get('source', 'Official Documentation')

                return {
                    'success': result.get('success', False),
                    'technology': tech,
                    'insights_extracted': result.get('insights_extracted', 0),
                    'file': f"{tech} Documentation",  # NEW: File name for display
                    'source': source,  # NEW: Source
                    'sections': result.get('sections_read', 0)  # NEW: Sections count
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="documentation_reader",
            description="Read and learn from official technology documentation",
            category=ToolCategory.LEARNING,
            mode=ToolMode.SLEEP,
            execute_fn=read_docs,
            cost=2,
            cooldown_minutes=10,
            metadata={'source_type': 'docs', 'technologies': 10}
        )
        count += 1

    if code_repo_analyzer:
        async def analyze_repo(**kwargs) -> Dict[str, Any]:
            """Analyze popular GitHub repository"""
            try:
                result = await code_repo_analyzer.analyze_random_repository()

                repo_name = result.get('repository', '')

                return {
                    'success': result.get('success', False),
                    'repository': repo_name,
                    'patterns_discovered': result.get('patterns_discovered', 0),
                    'patterns': result.get('patterns', []),  # NEW: List of patterns found
                    'insights': result.get('insights', []),
                    'insights_found': len(result.get('insights', [])),  # NEW: Count
                    'url': f"https://github.com/{repo_name}" if repo_name else None  # NEW: GitHub URL
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="repository_analyzer",
            description="Analyze popular GitHub repositories for patterns and best practices",
            category=ToolCategory.LEARNING,
            mode=ToolMode.SLEEP,
            execute_fn=analyze_repo,
            cost=3,
            cooldown_minutes=20,
            metadata={'source_type': 'code', 'platforms': ['github']}
        )
        count += 1

    # ============================================================
    # EXPERIMENTATION TOOLS (SLEEP)
    # ============================================================

    if trial_error_engine and experiment_designer:
        async def run_experiment(**kwargs) -> Dict[str, Any]:
            """Design and run trial & error experiment"""
            try:
                # Design experiment
                experiment = await experiment_designer.design_experiment()

                # Run with trial & error
                result = await trial_error_engine.run_experiment(experiment, iterations=2)

                # Format result with fields expected by consciousness engine
                success_rate = result.get('success_rate', 0)
                category = result.get('category', 'unknown')
                insights_list = result.get('insights', [])
                learnings = result.get('learnings', [])

                return {
                    'success': result.get('final_success', False),
                    'experiment_id': result.get('experiment_id'),
                    'experiment': f"{category} experiment",  # For exploration_details
                    'category': category,
                    'outcome': f"{success_rate:.0%} success rate" if success_rate else "completed",
                    'success_rate': success_rate,
                    'insights': insights_list,
                    'learnings_count': len(learnings),
                    'iterations': result.get('iterations', 0)
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="experimental_sandbox",
            description="Run safe experiments with trial & error learning",
            category=ToolCategory.EXPERIMENTATION,
            mode=ToolMode.SLEEP,
            execute_fn=run_experiment,
            cost=4,
            cooldown_minutes=30,
            metadata={'categories': 9, 'isolation': 'docker'}
        )
        count += 1

    # ============================================================
    # REFLECTION TOOLS (WAKE)
    # ============================================================

    if self_reflection_system:
        async def daily_reflection(**kwargs) -> Dict[str, Any]:
            """Perform daily self-reflection"""
            try:
                if not self_reflection_system.should_perform_daily_reflection():
                    return {
                        'success': True,
                        'skipped': True,
                        'reason': 'Already reflected today'
                    }

                result = await self_reflection_system.daily_reflection()
                return {
                    'success': True,
                    'sections': len(result.get('sections', {})),
                    'achievements': result.get('sections', {}).get('achievements', []),
                    'challenges': result.get('sections', {}).get('challenges', [])
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="daily_reflection",
            description="Perform daily self-reflection on progress and learnings",
            category=ToolCategory.REFLECTION,
            mode=ToolMode.WAKE,
            execute_fn=daily_reflection,
            cost=2,
            cooldown_minutes=60,  # Every hour (was 1440)
            metadata={'frequency': 'hourly', 'sections': 6}
        )
        count += 1

        async def weekly_reflection(**kwargs) -> Dict[str, Any]:
            """Perform weekly self-reflection"""
            try:
                if not self_reflection_system.should_perform_weekly_reflection():
                    return {
                        'success': True,
                        'skipped': True,
                        'reason': 'Not time for weekly reflection yet'
                    }

                result = await self_reflection_system.weekly_reflection()
                return {
                    'success': True,
                    'sections': len(result.get('sections', {})),
                    'week_summary': result.get('sections', {}).get('week_summary', {}),
                    'patterns': result.get('sections', {}).get('patterns', [])
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="weekly_reflection",
            description="Perform deep weekly self-reflection and planning",
            category=ToolCategory.REFLECTION,
            mode=ToolMode.WAKE,
            execute_fn=weekly_reflection,
            cost=3,
            cooldown_minutes=10080,  # Once per week
            metadata={'frequency': 'weekly', 'sections': 7}
        )
        count += 1

    # ============================================================
    # ANALYSIS TOOLS (WAKE)
    # ============================================================

    if enhanced_meta_learner:
        async def optimize_learning(**kwargs) -> Dict[str, Any]:
            """Analyze and optimize learning strategies"""
            try:
                result = await enhanced_meta_learner.optimize_learning_strategy()
                return {
                    'success': True,
                    'optimizations_applied': len(result.get('optimizations_applied', [])),
                    'recommendations': result.get('analysis', {}).get('recommendations', [])
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="meta_learning_optimizer",
            description="Analyze learning effectiveness and optimize strategies",
            category=ToolCategory.ANALYSIS,
            mode=ToolMode.WAKE,
            execute_fn=optimize_learning,
            cost=2,
            cooldown_minutes=30,  # Every 30 min (was 120)
            metadata={'type': 'self_optimization'}
        )
        count += 1

        async def learning_report(**kwargs) -> Dict[str, Any]:
            """Generate learning effectiveness report"""
            try:
                result = await enhanced_meta_learner.analyze_learning_effectiveness()
                return {
                    'success': True,
                    'sources_analyzed': len(result.get('learning_sources_analysis', {})),
                    'recommendations': result.get('recommendations', [])
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="learning_analyzer",
            description="Analyze learning effectiveness across different sources",
            category=ToolCategory.ANALYSIS,
            mode=ToolMode.WAKE,
            execute_fn=learning_report,
            cost=1,
            cooldown_minutes=20,  # Every 20 min (was 60)
            metadata={'type': 'analysis'}
        )
        count += 1

    # ============================================================
    # CREATIVITY TOOLS (BOTH)
    # ============================================================

    if curiosity_engine:
        async def share_curiosity(**kwargs) -> Dict[str, Any]:
            """Share interesting questions and anomalies - generates on-demand if none exist"""
            try:
                # Get recent questions and anomalies
                questions = curiosity_engine.get_recent_questions(limit=3)
                anomalies = curiosity_engine.get_anomalies(limit=2)
                stats = curiosity_engine.get_stats()

                # If no curiosities, generate some on-demand
                if not questions and not anomalies:
                    # Generate a curiosity about current work
                    await curiosity_engine.ask_question(
                        question="What patterns emerge when comparing different AI architectures?",
                        context="Exploring architectural patterns"
                    )
                    questions = curiosity_engine.get_recent_questions(limit=1)

                if questions or anomalies:
                    return {
                        'success': True,
                        'questions_generated': questions,
                        'anomalies_detected': len(anomalies),
                        'total_questions': stats.get('total_questions', 0),
                        'total_anomalies': stats.get('total_anomalies', 0)
                    }

                # If still no curiosities, return success with empty data
                # This prevents the tool from failing and blocking wake activities
                return {
                    'success': True,
                    'questions_generated': [],
                    'anomalies_detected': 0,
                    'total_questions': 0,
                    'total_anomalies': 0
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="curiosity_engine",
            description="Share interesting facts and curiosities",
            category=ToolCategory.CREATIVITY,
            mode=ToolMode.BOTH,
            execute_fn=share_curiosity,
            cost=1,
            cooldown_minutes=5,
            metadata={'type': 'knowledge_sharing'}
        )
        count += 1

    # ============================================================
    # TRADITIONAL DREAM RESEARCH (SLEEP) - Disabled (legacy, not compatible with new architecture)
    # ============================================================
    #
    # Note: Dream engine is now deprecated in favor of consciousness_engine's
    # direct control over SLEEP cycles. The new architecture uses specific
    # learning tools (web_explorer, documentation_reader, repository_analyzer)
    # instead of the monolithic dream engine.

    # ============================================================
    # SECURITY & QUALITY TOOLS (WAKE)
    # ============================================================

    # Darwin Auditor - OWASP security and code quality assessment
    try:
        from tools.darwin_auditor import DarwinAuditor

        async def run_security_audit(**kwargs) -> Dict[str, Any]:
            """Run OWASP-focused security and quality audit on Darwin's codebase."""
            try:
                from tools.darwin_auditor.auditor import run_darwin_audit
                result = await run_darwin_audit(
                    project_root="/app",
                    save_report=True
                )

                # Format for consciousness engine display
                return {
                    'success': True,
                    'security_score': result['security_score'],
                    'quality_score': result['quality_score'],
                    'overall_score': result['overall_score'],
                    'critical_issues': result['critical_issues'],
                    'high_issues': result['high_issues'],
                    'total_findings': result['total_findings'],
                    'recommendations': result['recommendations'][:3],  # Top 3
                    'report_path': result.get('report_path'),
                    'summary': f"Security: {result['security_score']}/100, Quality: {result['quality_score']}/100"
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}

        registry.register_tool(
            name="darwin_auditor",
            description="Run OWASP security audit and code quality analysis on Darwin's own codebase",
            category=ToolCategory.ANALYSIS,
            mode=ToolMode.WAKE,
            execute_fn=run_security_audit,
            cost=3,
            cooldown_minutes=60,  # Once per hour
            metadata={
                'type': 'security_audit',
                'owasp_coverage': 'A01-A10',
                'checks': ['security', 'quality', 'complexity']
            }
        )
        count += 1
        logger.info("✅ Darwin Auditor tool registered (OWASP security + quality)")
    except ImportError as e:
        logger.warning(f"Could not register Darwin Auditor: {e}")

    logger.info(f"✅ Registered {count} tools in Tool Registry")

    return count
