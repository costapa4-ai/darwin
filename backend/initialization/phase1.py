"""
Phase 1 Initialization - Core services

Initializes:
- Health tracking
- Memory store
- Safe executor
- AI service
- Nucleus
- Evolution engine
- Metrics service
"""

from typing import Dict, Any, Tuple, Optional

from config import get_settings
from core.nucleus import Nucleus
from core.executor import SafeExecutor
from core.evolution import EvolutionEngine
from core.memory import MemoryStore
from services.ai_service import AIService
from services.metrics import MetricsService
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


def init_health_tracking() -> Tuple[Any, Dict[str, Any]]:
    """
    Initialize health tracking and check for crash recovery.

    Returns:
        Tuple of (health_tracker, crash_info)
    """
    from introspection.health_tracker import HealthTracker

    health_tracker = HealthTracker(health_file="/app/data/health.json")
    health_tracker.record_startup()

    crash_info = health_tracker.check_previous_crash()

    return health_tracker, crash_info


def init_core_services() -> Dict[str, Any]:
    """
    Initialize core services.

    Returns:
        Dict with memory_store, executor, and settings
    """
    logger.info("Initializing core services...")

    memory_store = MemoryStore(settings.database_url.replace('sqlite:///', ''))

    executor = SafeExecutor(
        timeout=settings.execution_timeout,
        max_memory_mb=settings.max_memory_mb,
        allowed_modules=settings.allowed_modules
    )

    logger.info("Core services initialized")

    return {
        'memory_store': memory_store,
        'executor': executor,
        'settings': settings
    }


def init_nucleus(
    core: Dict[str, Any],
    semantic_memory: Optional[Any] = None,
    multi_model_router: Optional[Any] = None,
    web_researcher: Optional[Any] = None
) -> Nucleus:
    """
    Initialize the Nucleus with Phase 2 components.

    Args:
        core: Core services dict
        semantic_memory: Optional semantic memory instance
        multi_model_router: Optional multi-model router instance
        web_researcher: Optional web researcher instance

    Returns:
        Configured Nucleus instance
    """
    api_key = (
        settings.claude_api_key
        if settings.ai_provider == "claude"
        else settings.gemini_api_key
    )

    if not api_key:
        logger.warning(f"No API key configured for {settings.ai_provider}")

    # Get custom model if specified
    custom_model = None
    if settings.ai_provider == "claude" and settings.claude_model:
        custom_model = settings.claude_model
    elif settings.ai_provider == "gemini" and settings.gemini_model:
        custom_model = settings.gemini_model

    nucleus = Nucleus(
        settings.ai_provider,
        api_key,
        model=custom_model,
        semantic_memory=semantic_memory,
        multi_model_router=multi_model_router,
        web_researcher=web_researcher
    )

    logger.info("Nucleus initialized")

    return nucleus


def init_evolution_and_metrics(
    nucleus: Nucleus,
    executor: SafeExecutor,
    memory_store: MemoryStore,
    meta_learner: Optional[Any] = None
) -> Tuple[EvolutionEngine, MetricsService]:
    """
    Initialize Evolution Engine and Metrics Service.

    Args:
        nucleus: Nucleus instance
        executor: SafeExecutor instance
        memory_store: MemoryStore instance
        meta_learner: Optional meta learner instance

    Returns:
        Tuple of (evolution_engine, metrics_service)
    """
    evolution_engine = EvolutionEngine(
        nucleus,
        executor,
        memory_store,
        meta_learner=meta_learner
    )

    metrics_service = MetricsService(memory_store)

    logger.info("Evolution Engine and Metrics Service initialized")

    return evolution_engine, metrics_service
