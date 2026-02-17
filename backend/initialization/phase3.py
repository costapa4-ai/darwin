"""
Phase 3 Initialization - Autonomous capabilities

Initializes:
- Agent coordinator
- Idle detector
- Dream engine
- Code narrator (poetry)
- Diary writer
- Curiosity engine
- Benchmark generator
- Question engine system
"""

import os
from typing import Dict, Any

from config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)


def init_phase3_services(phase2: Dict[str, Any], settings) -> Dict[str, Any]:
    """
    Initialize Phase 3 services.

    Args:
        phase2: Phase 2 services dict
        settings: Application settings

    Returns:
        Dict with phase 3 service instances
    """
    services = {
        'agent_coordinator': None,
        'idle_detector': None,
        'dream_engine': None,
        'code_narrator': None,
        'diary_writer': None,
        'curiosity_engine': None,
        'benchmark_generator': None
    }

    # Agent Coordinator
    if settings.enable_multi_agent:
        try:
            from agents.agent_coordinator import AgentCoordinator
            services['agent_coordinator'] = AgentCoordinator()
            logger.info("Agent Coordinator initialized (4 personalities)")
        except Exception as e:
            logger.error(f"Failed to initialize Agent Coordinator: {e}")

    # Idle Detector
    if settings.enable_dream_mode:
        try:
            from dream.idle_detector import IdleDetector
            services['idle_detector'] = IdleDetector(
                idle_threshold_minutes=settings.dream_idle_threshold_minutes
            )
            logger.info("Idle Detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Idle Detector: {e}")

    # Dream Engine
    if (settings.enable_dream_mode and
        services['idle_detector'] and
        services['agent_coordinator']):
        try:
            from dream.dream_engine import DreamEngine

            dream_config = {
                'max_dream_duration_minutes': settings.dream_max_duration_minutes,
                'check_interval_seconds': settings.dream_check_interval_seconds
            }
            services['dream_engine'] = DreamEngine(
                services['idle_detector'],
                services['agent_coordinator'],
                dream_config,
                web_researcher=phase2.get('web_researcher'),
                semantic_memory=phase2.get('semantic_memory')
            )
            logger.info("Dream Engine initialized (with web research & semantic memory)")
        except Exception as e:
            logger.error(f"Failed to initialize Dream Engine: {e}")

    # Code Poetry
    if settings.enable_code_poetry:
        # Create poetry output directories
        poetry_dirs = [
            "/app/data/poetry",
            "/app/data/poetry/narratives",
            "/app/data/poetry/haikus",
            "/app/data/poetry/diary"
        ]
        for directory in poetry_dirs:
            os.makedirs(directory, exist_ok=True)
        logger.info("Poetry directories created")

        try:
            from poetry.code_narrator import CodeNarrator
            services['code_narrator'] = CodeNarrator()
            logger.info("Code Narrator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Code Narrator: {e}")

    # Diary Writer
    if settings.enable_daily_diary:
        try:
            from poetry.diary_writer import DiaryWriter
            services['diary_writer'] = DiaryWriter()
            logger.info("Diary Writer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Diary Writer: {e}")

    # Curiosity Engine
    if settings.enable_curiosity:
        try:
            from consciousness.curiosity_engine import CuriosityEngine
            services['curiosity_engine'] = CuriosityEngine()
            logger.info("Curiosity Engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Curiosity Engine: {e}")

    # Benchmark Generator
    if settings.enable_auto_benchmark:
        try:
            from benchmarking.benchmark_generator import BenchmarkGenerator
            services['benchmark_generator'] = BenchmarkGenerator()
            logger.info("Benchmark Generator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Benchmark Generator: {e}")

    return services


def init_question_engine(phase2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize Question Engine System.

    Args:
        phase2: Phase 2 services dict

    Returns:
        Dict with question engine service instances
    """
    services = {
        'question_engine': None,
        'answer_pursuer': None,
        'socratic_dialogue': None
    }

    try:
        from inquiry.question_engine import QuestionEngine
        from inquiry.answer_pursuer import AnswerPursuer
        from inquiry.socratic_dialogue import SocraticDialogue
        from api import inquiry_routes

        services['question_engine'] = QuestionEngine(
            multi_model_router=phase2.get('multi_model_router')
        )

        services['answer_pursuer'] = AnswerPursuer(
            semantic_memory=phase2.get('semantic_memory'),
            multi_model_router=phase2.get('multi_model_router'),
            web_researcher=phase2.get('web_researcher'),
            max_depth=3
        )

        services['socratic_dialogue'] = SocraticDialogue(
            multi_model_router=phase2.get('multi_model_router'),
            max_turns=10
        )

        inquiry_routes.initialize_inquiry(
            services['question_engine'],
            services['answer_pursuer'],
            services['socratic_dialogue']
        )

        logger.info("Question Engine System initialized (Deep Inquiry)")

    except Exception as e:
        logger.error(f"Failed to initialize Question Engine: {e}")

    return services
