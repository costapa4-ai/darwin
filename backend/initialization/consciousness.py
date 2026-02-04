"""
Consciousness Initialization - Main consciousness engine setup

Initializes:
- Self analyzer
- Code generator
- Approval queue
- Auto applier
- Tool manager
- Context awareness
- Mood system
- Question system
- Personality systems
- Proactive communicator
- Consciousness engine
"""

import asyncio
from typing import Dict, Any, Optional

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


async def init_consciousness_engine(
    settings,
    phase2: Dict[str, Any],
    phase3: Dict[str, Any],
    phase4: Dict[str, Any],
    nucleus,
    health_tracker,
    crash_info: Dict[str, Any],
    tool_registry: Optional[Any]
) -> Dict[str, Any]:
    """
    Initialize the Consciousness Engine and related systems.

    Args:
        settings: Application settings
        phase2: Phase 2 services
        phase3: Phase 3 services
        phase4: Phase 4 services
        nucleus: Nucleus instance
        health_tracker: Health tracker instance
        crash_info: Crash info from health tracker
        tool_registry: Tool registry instance

    Returns:
        Dict with consciousness-related service instances
    """
    services = {
        'consciousness_engine': None,
        'communicator': None,
        'context_awareness': None,
        'mood_system': None,
        'question_system': None,
        'tool_manager': None,
        'diary_engine': None,
        'expedition_engine': None,
        'financial_consciousness': None
    }

    if not settings.enable_dream_mode or not phase3.get('agent_coordinator'):
        return services

    try:
        from introspection.self_analyzer import SelfAnalyzer
        from introspection.code_generator import CodeGenerator
        from introspection.approval_system import ApprovalQueue
        from introspection.auto_applier import AutoApplier
        from tools.tool_manager import ToolManager
        from consciousness.consciousness_engine import ConsciousnessEngine
        from api.websocket import manager

        # Core components
        self_analyzer = SelfAnalyzer(project_root="/app")
        code_generator = CodeGenerator(
            nucleus=nucleus,
            multi_model_router=phase2.get('multi_model_router'),
            tool_registry=tool_registry
        )
        approval_queue = ApprovalQueue()
        auto_applier = AutoApplier(
            backup_dir="/app/backups",
            project_root="/app",
            health_tracker=health_tracker
        )

        # Tool Manager
        tool_manager = ToolManager(tools_dir="/app/tools")
        print("Loading Darwin-generated tools...")
        tool_manager.load_all_tools()
        services['tool_manager'] = tool_manager

        # Integrate ToolManager with ToolRegistry
        if tool_registry:
            print("Connecting ToolManager to ToolRegistry...")
            tool_registry.tool_manager = tool_manager
            tool_registry._discover_dynamic_tools()
            print(f"Integrated {len(tool_registry.tools)} total tools (static + dynamic)")

        # Crash Recovery
        if crash_info.get('crashed') and crash_info.get('should_rollback'):
            logger.warning("Attempting automatic crash recovery...")
            from introspection.health_tracker import AutoRecovery
            auto_recovery = AutoRecovery(health_tracker, auto_applier)
            recovery_result = await auto_recovery.check_and_recover()

            if recovery_result.get('rollback_performed'):
                logger.info(f"Recovery: {recovery_result.get('message')}")
            else:
                logger.error(f"Recovery failed: {recovery_result.get('message')}")

        # Personality Systems
        from personality.communication_system import ProactiveCommunicator
        from personality.context_awareness import ContextAwareness
        from personality.mood_system import MoodSystem
        from personality.question_system import QuestionSystem
        from personality.interaction_memory import InteractionMemory
        from personality.quirks_system import QuirksSystem
        from personality.goals_system import GoalsSystem
        from personality.surprise_system import SurpriseSystem

        services['context_awareness'] = ContextAwareness()
        logger.info("Context Awareness System initialized")

        services['mood_system'] = MoodSystem()
        logger.info("Mood System initialized")

        services['question_system'] = QuestionSystem()
        logger.info("Question System initialized")

        interaction_memory = InteractionMemory()
        quirks_system = QuirksSystem()
        goals_system = GoalsSystem()
        surprise_system = SurpriseSystem()
        logger.info("All personality systems initialized")

        # Diary Engine
        from consciousness.diary_engine import DiaryEngine
        services['diary_engine'] = DiaryEngine(
            diary_dir="./data/consciousness/diary",
            mood_system=services['mood_system']
        )
        logger.info("Diary Engine initialized")

        # Curiosity Expeditions Engine
        from consciousness.curiosity_expeditions import CuriosityExpeditions
        services['expedition_engine'] = CuriosityExpeditions(
            expeditions_dir="./data/expeditions",
            web_researcher=phase2.get('web_researcher'),
            semantic_memory=phase2.get('semantic_memory'),
            mood_system=services['mood_system'],
            websocket_manager=manager,
            diary_engine=services['diary_engine'],
            meta_learner=phase4.get('enhanced_meta_learner')
        )
        logger.info("Curiosity Expeditions Engine initialized")

        # Feedback Loop Manager - connects curiosity systems to expedition queue
        from consciousness.feedback_loops import init_feedback_manager
        from consciousness.hooks import get_hooks_manager
        from consciousness.activity_monitor import get_activity_monitor
        from consciousness.findings_inbox import get_findings_inbox

        services['feedback_manager'] = init_feedback_manager(
            expedition_engine=services['expedition_engine'],
            findings_inbox=get_findings_inbox(),
            meta_learner=phase4.get('enhanced_meta_learner'),
            hooks_manager=get_hooks_manager(),
            activity_monitor=get_activity_monitor()
        )
        await services['feedback_manager'].initialize()
        logger.info("Feedback Loop Manager initialized")

        # Financial Consciousness
        from consciousness.financial_consciousness import FinancialConsciousness
        services['financial_consciousness'] = FinancialConsciousness(
            multi_model_router=phase2.get('multi_model_router'),
            mood_system=services['mood_system'],
            diary_engine=services['diary_engine']
        )
        logger.info("Financial Consciousness initialized")

        # Proactive Communicator
        services['communicator'] = ProactiveCommunicator(
            websocket_manager=manager,
            context_awareness=services['context_awareness'],
            mood_system=services['mood_system'],
            question_system=services['question_system'],
            interaction_memory=interaction_memory,
            quirks_system=quirks_system,
            goals_system=goals_system,
            surprise_system=surprise_system
        )
        logger.info("Proactive Communication System initialized (COMPLETE personality integration)")

        # Consciousness Engine
        consciousness_config = {
            'wake_duration_minutes': 120,  # 2 hours
            'sleep_duration_minutes': 30   # 30 minutes
        }

        services['consciousness_engine'] = ConsciousnessEngine(
            agent_coordinator=phase3.get('agent_coordinator'),
            web_researcher=phase2.get('web_researcher'),
            semantic_memory=phase2.get('semantic_memory'),
            self_analyzer=self_analyzer,
            code_generator=code_generator,
            approval_queue=approval_queue,
            auto_applier=auto_applier,
            tool_manager=tool_manager,
            multi_model_router=phase2.get('multi_model_router'),
            nucleus=nucleus,
            config=consciousness_config,
            tool_registry=tool_registry,
            hierarchical_memory=phase2.get('hierarchical_memory'),
            communicator=services['communicator'],
            code_narrator=phase3.get('code_narrator') if settings.enable_code_poetry else None,
            diary_writer=phase3.get('diary_writer') if settings.enable_daily_diary else None,
            diary_engine=services['diary_engine']
        )

        # Link diary engine back to consciousness engine
        if services['diary_engine']:
            services['diary_engine'].consciousness_engine = services['consciousness_engine']

        # Initialize routes
        from api import consciousness_routes, context_routes, mood_routes
        from api import question_routes, memory_routes, existential_routes, diary_routes
        from api import expedition_routes, learning_routes, financial_routes

        consciousness_routes.initialize_consciousness(services['consciousness_engine'], services['mood_system'])
        existential_routes.initialize_existential(services['consciousness_engine'], services['mood_system'])
        diary_routes.initialize_diary(services['diary_engine'])
        expedition_routes.initialize_expeditions(services['expedition_engine'])
        financial_routes.initialize_financial(services['financial_consciousness'])
        learning_routes.initialize_learning(
            phase4.get('enhanced_meta_learner'),
            phase4.get('self_reflection_system')
        )
        context_routes.initialize_context(services['communicator'])
        mood_routes.initialize_mood(services['communicator'])
        question_routes.initialize_questions(services['communicator'])
        memory_routes.initialize_memory(services['communicator'])

        # Start consciousness in background
        asyncio.create_task(services['consciousness_engine'].start())
        logger.info("Consciousness Engine started (Wake: 2h, Sleep: 30min)")

        # Start Proactive Engine for autonomous actions (Moltbook, exploration, etc.)
        # Integrate with mood system for mood-aware action selection
        from consciousness.proactive_engine import get_proactive_engine, init_proactive_engine_with_mood
        proactive_engine = init_proactive_engine_with_mood(services['mood_system'])
        services['proactive_engine'] = proactive_engine
        asyncio.create_task(proactive_engine.run_proactive_loop(
            interval_seconds=120,  # Check every 2 minutes
            max_actions_per_hour=30  # Increased for more activity
        ))
        logger.info("Proactive Engine started (interval: 2min, mood-action integration active)")

    except Exception as e:
        logger.error(f"Failed to start Consciousness Engine: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Keep old dream mode for compatibility info
    if phase3.get('dream_engine'):
        logger.info("Dream Engine available (deprecated, use Consciousness Engine)")

    return services
