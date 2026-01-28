"""
Application Lifespan - Startup and shutdown event handlers
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()

# Global service instances - accessible from other modules
_services = {}


def get_service(name: str):
    """Get a service instance by name"""
    return _services.get(name)


def set_service(name: str, instance):
    """Set a service instance"""
    _services[name] = instance


def get_system_status():
    """Get system status for root endpoint"""
    phase2_status = {
        "semantic_memory": _services.get('semantic_memory') is not None,
        "multi_model_router": _services.get('multi_model_router') is not None,
        "web_researcher": _services.get('web_researcher') is not None,
        "meta_learner": _services.get('meta_learner') is not None
    }

    phase3_status = {
        "agent_coordinator": _services.get('agent_coordinator') is not None,
        "dream_engine": _services.get('dream_engine') is not None,
        "code_poetry": _services.get('code_narrator') is not None or _services.get('diary_writer') is not None,
        "curiosity_engine": _services.get('curiosity_engine') is not None,
        "benchmarking": _services.get('benchmark_generator') is not None
    }

    return {
        "service": "Darwin System",
        "version": "3.0.0",
        "status": "running",
        "docs": "/docs",
        "phase2_enabled": any(phase2_status.values()),
        "phase2_features": phase2_status,
        "phase3_enabled": any(phase3_status.values()),
        "phase3_features": phase3_status
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with phased initialization"""

    logger.info("Darwin System starting up...")

    # Phase 0: Health tracking and crash recovery
    from initialization.phase1 import init_health_tracking
    health_tracker, crash_info = init_health_tracking()
    set_service('health_tracker', health_tracker)

    if crash_info.get('crashed'):
        logger.error(f"PREVIOUS CRASH DETECTED: {crash_info.get('message')}")
        logger.warning("Auto-recovery will be attempted after initialization...")
    else:
        logger.info("No crash detected. Previous session ended cleanly.")

    # Phase 1: Core services
    from initialization.phase1 import init_core_services
    core = init_core_services()
    for name, service in core.items():
        set_service(name, service)

    # Phase 2: Semantic memory, multi-model, web research
    from initialization.phase2 import init_phase2_services
    phase2 = await init_phase2_services(core)
    for name, service in phase2.items():
        set_service(name, service)

    # Initialize Nucleus with Phase 2 components
    from initialization.phase1 import init_nucleus
    nucleus = init_nucleus(
        core,
        phase2.get('semantic_memory'),
        phase2.get('multi_model_router'),
        phase2.get('web_researcher')
    )
    set_service('nucleus', nucleus)

    # Initialize Evolution Engine and Metrics
    from initialization.phase1 import init_evolution_and_metrics
    evolution, metrics = init_evolution_and_metrics(
        nucleus, core['executor'], core['memory_store'], phase2.get('meta_learner')
    )
    set_service('evolution_engine', evolution)
    set_service('metrics_service', metrics)

    # Inject services into routes
    from api.routes import set_services
    set_services(evolution, metrics)

    # Initialize Phase 2 routes
    from api import phase2_routes
    phase2_routes.initialize_phase2(
        phase2.get('semantic_memory'),
        phase2.get('multi_model_router'),
        phase2.get('web_researcher'),
        phase2.get('meta_learner')
    )

    # Initialize Cost tracking routes
    from api import cost_routes
    cost_routes.initialize_costs(phase2.get('multi_model_router'))

    # Phase 3: Agents, dreams, poetry
    from initialization.phase3 import init_phase3_services
    phase3 = init_phase3_services(phase2, settings)
    for name, service in phase3.items():
        set_service(name, service)

    # Initialize Phase 3 routes
    from api import phase3_routes
    phase3_routes.initialize_phase3(
        phase3.get('agent_coordinator'),
        phase3.get('dream_engine'),
        phase3.get('idle_detector'),
        phase3.get('code_narrator'),
        phase3.get('diary_writer'),
        phase3.get('curiosity_engine'),
        phase3.get('benchmark_generator')
    )

    # Initialize introspection and auto-correction
    from api import introspection_routes, auto_correction_routes
    introspection_routes.initialize_introspection()
    auto_correction_routes.initialize_auto_correction(nucleus=nucleus)
    logger.info("Self-Analysis and Auto-Correction Systems initialized")

    # Initialize Findings Inbox
    from consciousness.findings_inbox import FindingsInbox, set_findings_inbox
    findings_inbox = FindingsInbox(storage_path="./data/findings")
    set_findings_inbox(findings_inbox)
    set_service('findings_inbox', findings_inbox)
    logger.info(f"Findings Inbox initialized with {findings_inbox.get_unread_count()} unread findings")

    # Initialize Safe Command Executor
    from tools.safe_command_executor import SafeCommandExecutor, set_safe_executor
    safe_executor = SafeCommandExecutor()
    set_safe_executor(safe_executor)
    set_service('safe_executor', safe_executor)
    logger.info("Safe Command Executor initialized")

    # Initialize Question Engine
    from initialization.phase3 import init_question_engine
    question_engine_services = init_question_engine(phase2)
    for name, service in question_engine_services.items():
        set_service(name, service)

    # Phase 4: Advanced learning systems
    from initialization.phase4 import init_phase4_services
    phase4 = await init_phase4_services(phase2, settings)
    for name, service in phase4.items():
        set_service(name, service)

    # Initialize tool registry
    from initialization.phase4 import init_tool_registry
    tool_registry = init_tool_registry(phase2, phase4, phase3)
    set_service('tool_registry', tool_registry)

    # Initialize Consciousness Engine
    from initialization.consciousness import init_consciousness_engine
    consciousness_result = await init_consciousness_engine(
        settings=settings,
        phase2=phase2,
        phase3=phase3,
        phase4=phase4,
        nucleus=nucleus,
        health_tracker=health_tracker,
        crash_info=crash_info,
        tool_registry=tool_registry
    )

    for name, service in consciousness_result.items():
        set_service(name, service)

    # Log startup summary
    phase2_features = {k: v is not None for k, v in phase2.items()}
    phase3_features = {k: v is not None for k, v in phase3.items()}

    logger.info("Darwin System ready", extra={
        "ai_provider": settings.ai_provider,
        "phase2_enabled": any(phase2_features.values()),
        "phase3_enabled": any(phase3_features.values())
    })

    # Mark system as fully running
    health_tracker.record_running()

    yield

    # Shutdown
    logger.info("Darwin System shutting down...")
    health_tracker.record_shutdown()

    consciousness_engine = _services.get('consciousness_engine')
    if consciousness_engine and consciousness_engine.is_running:
        consciousness_engine.stop()

    dream_engine = _services.get('dream_engine')
    if dream_engine and dream_engine.is_dreaming:
        dream_engine.stop_dream_mode()

    logger.info("Darwin System shutdown complete")
