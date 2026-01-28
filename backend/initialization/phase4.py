"""
Phase 4 Initialization - Advanced learning and tools

Initializes:
- Web explorer
- Documentation reader
- Code repository analyzer
- Enhanced meta-learner
- Self-reflection system
- Sandbox manager
- Experiment designer
- Trial & error engine
- Experiment tracker
- Safety validator
- Tool registry
"""

from typing import Dict, Any, Optional

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def init_phase4_services(phase2: Dict[str, Any], settings) -> Dict[str, Any]:
    """
    Initialize Phase 4 services (Advanced Learning & Experimentation).

    Args:
        phase2: Phase 2 services dict
        settings: Application settings

    Returns:
        Dict with phase 4 service instances
    """
    services = {
        'web_explorer': None,
        'documentation_reader': None,
        'code_repo_analyzer': None,
        'enhanced_meta_learner': None,
        'self_reflection_system': None,
        'sandbox_manager': None,
        'experiment_designer': None,
        'trial_error_engine': None,
        'experiment_tracker': None,
        'safety_validator': None
    }

    semantic_memory = phase2.get('semantic_memory')
    multi_model_router = phase2.get('multi_model_router')

    if not semantic_memory or not multi_model_router:
        logger.warning("Semantic memory or multi-model router not available, skipping Phase 4")
        return services

    # Advanced Learning Systems (v4.1)
    try:
        from learning.web_explorer import WebExplorer
        from learning.documentation_reader import DocumentationReader
        from learning.code_repository_analyzer import CodeRepositoryAnalyzer
        from learning.meta_learning_enhanced import EnhancedMetaLearner
        from learning.self_reflection import SelfReflectionSystem

        # Web Explorer
        explorer_config = {
            'max_depth': 2,
            'max_urls_per_session': 10,
            'request_timeout': 10
        }
        services['web_explorer'] = WebExplorer(
            semantic_memory, multi_model_router, explorer_config
        )
        logger.info("Web Explorer initialized (autonomous web navigation)")

        # Documentation Reader
        services['documentation_reader'] = DocumentationReader(
            semantic_memory, multi_model_router
        )
        logger.info("Documentation Reader initialized (10 tech sources)")

        # Code Repository Analyzer
        repo_config = {
            'github_token': getattr(settings, 'github_token', '')
        }
        services['code_repo_analyzer'] = CodeRepositoryAnalyzer(
            semantic_memory, multi_model_router, repo_config
        )
        logger.info("Code Repository Analyzer initialized (GitHub analysis)")

        # Enhanced Meta-Learner
        services['enhanced_meta_learner'] = EnhancedMetaLearner(
            semantic_memory, multi_model_router
        )
        await services['enhanced_meta_learner']._restore_state()
        logger.info("Enhanced Meta-Learner initialized (self-optimization)")

        # Self-Reflection System
        services['self_reflection_system'] = SelfReflectionSystem(
            semantic_memory,
            multi_model_router,
            services['enhanced_meta_learner']
        )
        await services['self_reflection_system']._restore_state()
        logger.info("Self-Reflection System initialized (daily/weekly)")

    except Exception as e:
        logger.error(f"Failed to initialize Advanced Learning Systems: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Experimental Sandbox (v4.2)
    try:
        from experimentation.sandbox_manager import SandboxManager
        from experimentation.experiment_designer import ExperimentDesigner
        from experimentation.trial_error_engine import TrialErrorLearningEngine
        from experimentation.experiment_tracker import ExperimentTracker
        from experimentation.safety_validator import SafetyValidator

        # Sandbox Manager
        sandbox_config = {
            'max_sandboxes': 3,
            'sandbox_lifetime_minutes': 30,
            'max_memory_mb': 512,
            'execution_timeout': 30,
            'workspace_root': './data/sandboxes'
        }
        services['sandbox_manager'] = SandboxManager(sandbox_config)
        logger.info("Sandbox Manager initialized (isolated execution)")

        # Experiment Designer
        services['experiment_designer'] = ExperimentDesigner(
            semantic_memory, multi_model_router
        )
        logger.info("Experiment Designer initialized (9 categories)")

        # Safety Validator
        services['safety_validator'] = SafetyValidator()
        logger.info("Safety Validator initialized (safety checks)")

        # Experiment Tracker
        services['experiment_tracker'] = ExperimentTracker()
        logger.info("Experiment Tracker initialized (analytics)")

        # Trial & Error Engine
        services['trial_error_engine'] = TrialErrorLearningEngine(
            services['sandbox_manager'],
            services['experiment_designer'],
            semantic_memory,
            multi_model_router
        )
        logger.info("Trial & Error Engine initialized (autonomous experimentation)")

    except Exception as e:
        logger.error(f"Failed to initialize Experimental Sandbox: {e}")
        import traceback
        logger.error(traceback.format_exc())

    return services


def init_tool_registry(
    phase2: Dict[str, Any],
    phase4: Dict[str, Any],
    phase3: Dict[str, Any]
) -> Optional[Any]:
    """
    Initialize Dynamic Tool Registry.

    Args:
        phase2: Phase 2 services
        phase4: Phase 4 services
        phase3: Phase 3 services

    Returns:
        ToolRegistry instance or None
    """
    multi_model_router = phase2.get('multi_model_router')

    if not multi_model_router:
        return None

    try:
        from consciousness.tool_registry import ToolRegistry
        from consciousness.tool_wrappers import register_all_tools

        tool_registry = ToolRegistry(multi_model_router=multi_model_router)
        logger.info("Tool Registry initialized (dynamic tool selection)")

        # Register all available tools
        tools_registered = register_all_tools(
            registry=tool_registry,
            web_explorer=phase4.get('web_explorer'),
            documentation_reader=phase4.get('documentation_reader'),
            code_repo_analyzer=phase4.get('code_repo_analyzer'),
            trial_error_engine=phase4.get('trial_error_engine'),
            experiment_designer=phase4.get('experiment_designer'),
            self_reflection_system=phase4.get('self_reflection_system'),
            enhanced_meta_learner=phase4.get('enhanced_meta_learner'),
            curiosity_engine=phase3.get('curiosity_engine'),
            dream_engine=phase3.get('dream_engine')
        )
        logger.info(f"Registered {tools_registered} tools for conscious selection")

        return tool_registry

    except Exception as e:
        logger.error(f"Failed to initialize Tool Registry: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None
