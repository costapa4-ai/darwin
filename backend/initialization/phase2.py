"""
Phase 2 Initialization - Advanced capabilities

Initializes:
- Semantic memory (ChromaDB)
- Multi-model router
- Web researcher
- Meta-learner
- Hierarchical memory
"""

from typing import Dict, Any, Optional

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)
settings = get_settings()


async def init_phase2_services(core: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize Phase 2 services.

    Args:
        core: Core services dict from Phase 1

    Returns:
        Dict with phase 2 service instances
    """
    services = {
        'semantic_memory': None,
        'multi_model_router': None,
        'web_researcher': None,
        'meta_learner': None,
        'hierarchical_memory': None
    }

    # Semantic Memory
    if settings.enable_semantic_memory:
        try:
            from core.semantic_memory import SemanticMemory
            services['semantic_memory'] = SemanticMemory(
                persist_directory=settings.chroma_persist_directory
            )
            logger.info("Semantic Memory initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Semantic Memory: {e}")

    # Hierarchical Memory (3-layer system)
    try:
        from core.hierarchical_memory import HierarchicalMemory
        services['hierarchical_memory'] = HierarchicalMemory(
            storage_path="./data/memory"
        )
        logger.info("Hierarchical Memory initialized (Working, Episodic, Semantic)")
    except Exception as e:
        logger.error(f"Failed to initialize Hierarchical Memory: {e}")
        import traceback
        logger.error(traceback.format_exc())

    # Multi-Model Router
    if settings.enable_multi_model:
        try:
            from ai.multi_model_router import MultiModelRouter

            router_config = {"routing_strategy": settings.routing_strategy}

            if settings.claude_api_key:
                router_config["claude_api_key"] = settings.claude_api_key
                if settings.claude_model:
                    router_config["claude_model"] = settings.claude_model

            if settings.gemini_api_key:
                router_config["gemini_api_key"] = settings.gemini_api_key
                if settings.gemini_model:
                    router_config["gemini_model"] = settings.gemini_model

            if settings.openai_api_key:
                router_config["openai_api_key"] = settings.openai_api_key
                if settings.openai_model:
                    router_config["openai_model"] = settings.openai_model

            # Ollama (Local LLM - FREE!)
            router_config["ollama_enabled"] = settings.ollama_enabled
            router_config["ollama_url"] = settings.ollama_url
            router_config["ollama_model"] = settings.ollama_model
            router_config["ollama_code_model"] = settings.ollama_code_model
            router_config["ollama_reasoning_model"] = settings.ollama_reasoning_model

            services['multi_model_router'] = MultiModelRouter(router_config)
            logger.info(f"Multi-Model Router initialized ({settings.routing_strategy} strategy)")
        except Exception as e:
            logger.error(f"Failed to initialize Multi-Model Router: {e}")

    # Web Researcher
    if settings.enable_web_research:
        try:
            from research.web_researcher import WebResearcher

            researcher_config = {
                "serpapi_api_key": settings.serpapi_api_key,
                "github_token": settings.github_token
            }
            services['web_researcher'] = WebResearcher(researcher_config)
            logger.info("Web Researcher initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Web Researcher: {e}")

    # Meta-Learner
    if (settings.enable_meta_learning and
        services['semantic_memory'] and
        services['multi_model_router']):
        try:
            from meta.meta_learner import MetaLearner
            services['meta_learner'] = MetaLearner(
                services['semantic_memory'],
                services['multi_model_router']
            )
            logger.info("Meta-Learner initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Meta-Learner: {e}")

    return services
