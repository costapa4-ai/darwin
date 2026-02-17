"""
Phase 3 API Routes - Autonomy & Personalities
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/v1/phase3", tags=["phase3"])

# Global instances (set by main.py)
agent_coordinator = None
dream_engine = None
idle_detector = None
code_narrator = None
diary_writer = None
curiosity_engine = None
benchmark_generator = None


def initialize_phase3(
    coordinator,
    dream,
    idle,
    narrator,
    diary,
    curiosity,
    benchmark
):
    """Initialize Phase 3 components"""
    global agent_coordinator, dream_engine, idle_detector
    global code_narrator, diary_writer, curiosity_engine, benchmark_generator

    agent_coordinator = coordinator
    dream_engine = dream
    idle_detector = idle
    code_narrator = narrator
    diary_writer = diary
    curiosity_engine = curiosity
    benchmark_generator = benchmark


# Request Models
class SolveRequest(BaseModel):
    task: Dict[str, Any]
    agent: Optional[str] = None
    mode: str = 'auto'


class CollaborateRequest(BaseModel):
    task: Dict[str, Any]
    num_agents: int = 3


# =========================
# AGENT ENDPOINTS
# =========================

@router.get("/status")
async def get_phase3_status():
    """Get Phase 3 feature status"""
    return {
        "phase3_enabled": True,
        "features": {
            "multi_agent": agent_coordinator is not None,
            "dream_mode": dream_engine is not None,
            "code_poetry": code_narrator is not None,
            "curiosity": curiosity_engine is not None,
            "benchmarking": benchmark_generator is not None
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/agents/list")
async def list_agents():
    """List all available agents"""
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    agents_info = []
    for name, agent in agent_coordinator.agents.items():
        agents_info.append({
            'name': name,
            'display_name': agent.name,
            'personality': agent.personality,
            'specialization': agent.specialization,
            'traits': [t.value for t in agent.traits],
            'tasks_solved': agent.memory.tasks_solved,
            'avg_fitness': agent.get_stats().avg_fitness
        })

    return {
        'agents': agents_info,
        'total': len(agents_info)
    }


@router.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed information about specific agent"""
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    agent = agent_coordinator.agents.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        'agent': agent.to_dict(),
        'description': agent.describe_self(),
        'stats': agent.get_stats().__dict__
    }


@router.post("/agents/solve")
async def solve_with_agent(request: SolveRequest):
    """
    Solve task with specific agent or using selection mode
    """
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    try:
        from core.nucleus import Nucleus
        from config import get_settings
        from app.lifespan import get_service

        settings = get_settings()
        api_key = settings.claude_api_key or settings.gemini_api_key
        provider = "claude" if settings.claude_api_key else "gemini"
        router = get_service('multi_model_router')
        nucleus = Nucleus(provider, api_key, multi_model_router=router)

        # Solve with agent
        result = await agent_coordinator.solve_with_agent(
            task=request.task,
            nucleus=nucleus,
            agent_name=request.agent,
            mode=request.mode
        )

        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/collaborate")
async def collaborate_on_task(request: CollaborateRequest):
    """
    Multiple agents collaborate on task
    """
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    try:
        from core.nucleus import Nucleus
        from config import get_settings
        from app.lifespan import get_service

        settings = get_settings()
        api_key = settings.claude_api_key or settings.gemini_api_key
        provider = "claude" if settings.claude_api_key else "gemini"
        router = get_service('multi_model_router')
        nucleus = Nucleus(provider, api_key, multi_model_router=router)

        result = await agent_coordinator.solve_collaborative(
            task=request.task,
            nucleus=nucleus,
            num_agents=request.num_agents
        )

        return {
            'success': True,
            'result': result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/stats")
async def get_all_agent_stats():
    """Get statistics for all agents"""
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    return agent_coordinator.get_all_stats()


@router.get("/agents/leaderboard")
async def get_agent_leaderboard():
    """Get agent performance leaderboard"""
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    return {
        'leaderboard': agent_coordinator.get_leaderboard()
    }


@router.get("/agents/collaboration/stats")
async def get_collaboration_stats():
    """Get collaboration statistics"""
    if not agent_coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")

    return agent_coordinator.get_collaboration_stats()


# =========================
# DREAM MODE ENDPOINTS
# =========================

@router.get("/dreams/status")
async def get_dream_status():
    """Get current dream mode status with detailed information"""
    if not dream_engine:
        raise HTTPException(status_code=503, detail="Dream engine not available")

    status = dream_engine.get_status()

    # If currently dreaming, add more detailed information
    if dream_engine.current_dream:
        dream = dream_engine.current_dream
        duration = (datetime.utcnow() - dream.started_at).total_seconds()

        status['current_dream'] = {
            'id': dream.id,
            'type': dream.dream_type.value,
            'description': dream.description,
            'hypothesis': dream.hypothesis,
            'duration_seconds': duration,
            'duration_minutes': duration / 60,
            'progress': min(100, int((duration / (dream_engine.max_dream_duration * 60)) * 100)),
            'insights': dream.insights,
            'insights_count': len(dream.insights),
            'started_at': dream.started_at.isoformat(),
            'results': dream.results
        }

    return status


@router.get("/dreams/summary")
async def get_dream_summary(days: int = 7):
    """Get summary of recent dreams"""
    if not dream_engine:
        raise HTTPException(status_code=503, detail="Dream engine not available")

    return dream_engine.get_dream_summary(days=days)


@router.get("/dreams/history")
async def get_dream_history(limit: int = 10):
    """Get dream history"""
    if not dream_engine:
        raise HTTPException(status_code=503, detail="Dream engine not available")

    dreams = dream_engine.dream_history[-limit:]

    return {
        'dreams': [
            {
                'id': d.id,
                'type': d.dream_type.value,
                'description': d.description,
                'insights_count': len(d.insights),
                'success': d.success,
                'started_at': d.started_at.isoformat(),
                'completed_at': d.completed_at.isoformat() if d.completed_at else None,
                'duration_seconds': (d.completed_at - d.started_at).total_seconds() if d.completed_at else 0
            }
            for d in dreams
        ],
        'total': len(dreams)
    }


@router.get("/dreams/history/{dream_id}")
async def get_dream_details(dream_id: str):
    """Get detailed information about a specific dream"""
    if not dream_engine:
        raise HTTPException(status_code=503, detail="Dream engine not available")

    # Find dream in history
    dream = next((d for d in dream_engine.dream_history if d.id == dream_id), None)

    if not dream:
        raise HTTPException(status_code=404, detail="Dream not found")

    return {
        'id': dream.id,
        'type': dream.dream_type.value,
        'description': dream.description,
        'hypothesis': dream.hypothesis,
        'started_at': dream.started_at.isoformat(),
        'completed_at': dream.completed_at.isoformat() if dream.completed_at else None,
        'duration_seconds': (dream.completed_at - dream.started_at).total_seconds() if dream.completed_at else 0,
        'insights': dream.insights,
        'insights_count': len(dream.insights),
        'results': dream.results,
        'success': dream.success
    }


@router.get("/dreams/idle")
async def get_idle_status():
    """Get idle detection status"""
    if not idle_detector:
        raise HTTPException(status_code=503, detail="Idle detector not available")

    return idle_detector.get_status()


@router.post("/dreams/trigger")
async def trigger_dream_now():
    """Manually trigger a dream (for testing/debugging)"""
    if not dream_engine:
        raise HTTPException(status_code=503, detail="Dream engine not available")

    try:
        # Manually trigger a dream
        await dream_engine._dream()

        return {
            'success': True,
            'message': 'Dream triggered successfully',
            'total_dreams': dream_engine.dream_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# CODE POETRY ENDPOINTS
# =========================

@router.post("/poetry/narrate")
async def narrate_solution(task: Dict, solution: Dict):
    """Generate narrative for solution"""
    if not code_narrator:
        raise HTTPException(status_code=503, detail="Code narrator not available")

    narrative = code_narrator.narrate_solution(task, solution)

    return {
        'narrative': narrative
    }


@router.post("/poetry/haiku")
async def generate_haiku(execution: Dict):
    """Generate haiku for execution"""
    if not code_narrator:
        raise HTTPException(status_code=503, detail="Code narrator not available")

    haiku = code_narrator.generate_haiku(execution)

    return {
        'haiku': haiku
    }


@router.get("/poetry/diary/today")
async def get_daily_diary():
    """Get today's diary entry"""
    if not diary_writer:
        raise HTTPException(status_code=503, detail="Diary writer not available")

    # Real stats from system services
    stats = {}
    try:
        from app.lifespan import get_service
        from consciousness.activity_monitor import get_activity_monitor

        # Activity stats
        monitor = get_activity_monitor()
        if monitor:
            ms = monitor.get_stats()
            stats['tasks_completed'] = ms.get('total_activities', 0)

        # Tool success rate
        tool_reg = get_service('tool_registry')
        if tool_reg:
            tools = tool_reg.list_tools() or []
            used = [t for t in tools if isinstance(t, dict) and t.get('total_uses', 0) > 0]
            rates = [t.get('success_rate', 0) for t in used]
            stats['success_rate'] = round(sum(rates) / len(rates), 2) if rates else 0
            stats['patterns_learned'] = len(used)

        # Router stats
        router_svc = get_service('multi_model_router')
        if router_svc:
            rs = router_svc.get_router_stats()
            perf = rs.get('performance_stats', {})
            stats['avg_fitness'] = round(sum(
                m.get('total_requests', 0) for m in perf.values()
            ) / max(len(perf), 1), 1)
            stats['best_agent'] = max(perf.keys(), key=lambda k: perf[k].get('total_requests', 0)) if perf else 'none'
    except Exception:
        # Fallback if services unavailable
        stats.setdefault('tasks_completed', 0)
        stats.setdefault('avg_fitness', 0)
        stats.setdefault('success_rate', 0)
        stats.setdefault('patterns_learned', 0)
        stats.setdefault('best_agent', 'none')

    diary = diary_writer.write_daily_summary(stats)

    return {
        'diary': diary,
        'day_number': diary_writer._calculate_day_number()
    }


# =========================
# CURIOSITY ENDPOINTS
# =========================

@router.get("/curiosity/questions")
async def get_recent_questions(limit: int = 10):
    """Get recent questions asked by curiosity engine"""
    if not curiosity_engine:
        raise HTTPException(status_code=503, detail="Curiosity engine not available")

    return {
        'questions': curiosity_engine.get_recent_questions(limit)
    }


@router.get("/curiosity/anomalies")
async def get_anomalies(limit: int = 10):
    """Get recent anomalies detected"""
    if not curiosity_engine:
        raise HTTPException(status_code=503, detail="Curiosity engine not available")

    return {
        'anomalies': curiosity_engine.get_anomalies(limit)
    }


@router.get("/curiosity/stats")
async def get_curiosity_stats():
    """Get curiosity engine statistics"""
    if not curiosity_engine:
        raise HTTPException(status_code=503, detail="Curiosity engine not available")

    return curiosity_engine.get_stats()


# =========================
# BENCHMARKING ENDPOINTS
# =========================

@router.get("/benchmark/stats")
async def get_benchmark_stats():
    """Get benchmarking statistics"""
    if not benchmark_generator:
        raise HTTPException(status_code=503, detail="Benchmark generator not available")

    return benchmark_generator.get_stats()


# =========================
# HEALTH CHECK
# =========================

@router.get("/health")
async def phase3_health_check():
    """Comprehensive Phase 3 health check"""
    health = {
        "status": "healthy",
        "components": {},
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check each component
    health["components"]["agent_coordinator"] = {
        "status": "healthy" if agent_coordinator else "not_configured",
        "agents_count": len(agent_coordinator.agents) if agent_coordinator else 0
    }

    health["components"]["dream_engine"] = {
        "status": "healthy" if dream_engine else "not_configured",
        "is_active": dream_engine.is_dreaming if dream_engine else False
    }

    health["components"]["code_poetry"] = {
        "status": "healthy" if code_narrator else "not_configured"
    }

    health["components"]["curiosity_engine"] = {
        "status": "healthy" if curiosity_engine else "not_configured"
    }

    health["components"]["benchmarking"] = {
        "status": "healthy" if benchmark_generator else "not_configured"
    }

    # Overall status
    if not any([agent_coordinator, dream_engine, code_narrator]):
        health["status"] = "degraded"

    return health
