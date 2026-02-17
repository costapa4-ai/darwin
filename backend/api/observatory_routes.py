"""
Observatory API Routes - Comprehensive monitoring dashboard aggregation.

Provides aggregation endpoints for the Darwin Observatory frontend:
- /overview: System health summary
- /ai-routing: Multi-model router stats
- /evolution: Prompt evolution + code generation stats
- /subsystems: Per-subsystem health cards
- /watchdog: System watchdog results (last run + on-demand trigger)
- /ollama-models: List/pull/remove Ollama models
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from utils.logger import setup_logger
import aiohttp

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/observatory", tags=["observatory"])


def _safe_get(fn, default=None):
    """Safely call a function, returning default on any error."""
    try:
        result = fn()
        return result if result is not None else (default if default is not None else {})
    except Exception as e:
        logger.debug(f"Observatory safe_get error: {e}")
        return default if default is not None else {}


def _time_ago(dt):
    """Convert datetime to human-readable 'Xm ago' string."""
    if not dt:
        return "never"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except (ValueError, TypeError):
            return dt
    try:
        diff = datetime.now() - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        return f"{hours // 24}d ago"
    except Exception:
        return str(dt) if dt else "unknown"


@router.get("/overview")
async def get_overview():
    """System health summary aggregating all major subsystems."""
    from app.lifespan import get_service
    from consciousness.findings_inbox import get_findings_inbox
    from consciousness.prompt_registry import get_prompt_registry
    from consciousness.activity_monitor import get_activity_monitor

    # Consciousness engine
    engine = get_service('consciousness_engine')
    engine_status = _safe_get(lambda: engine.get_status()) if engine else {}

    state = engine_status.get('state', 'unknown')
    wake_cycles = engine_status.get('wake_cycles_completed', 0)
    sleep_cycles = engine_status.get('sleep_cycles_completed', 0)
    total_activities = engine_status.get('total_activities', 0)
    total_discoveries = engine_status.get('total_discoveries', 0)
    elapsed = engine_status.get('elapsed_minutes', 0)

    # Cycle progress (use actual durations from engine, not hardcoded)
    wake_dur = engine_status.get('wake_duration', 120)
    sleep_dur = engine_status.get('sleep_duration', 30)
    if state == 'wake':
        cycle_progress = min(elapsed / wake_dur, 1.0) if elapsed else 0
    elif state == 'sleep':
        cycle_progress = min(elapsed / sleep_dur, 1.0) if elapsed else 0
    else:
        cycle_progress = 0

    # Activity monitor
    monitor = _safe_get(get_activity_monitor)
    monitor_stats = _safe_get(lambda: monitor.get_stats()) if monitor else {}
    errors_last_hour = monitor_stats.get('errors_last_hour', 0)

    # Findings inbox
    inbox = _safe_get(get_findings_inbox)
    inbox_stats = _safe_get(lambda: inbox.get_statistics()) if inbox else {}
    unread = inbox_stats.get('total_unread', 0)

    # Prompt registry
    registry = _safe_get(get_prompt_registry)
    prompt_stats = _safe_get(lambda: registry.get_stats()) if registry else {}

    # Cost today from financial consciousness (tracks actual daily cost, not cumulative session)
    fin = get_service('financial_consciousness')
    if fin:
        fin_costs = _safe_get(lambda: fin.get_current_costs())
        cost_today = fin_costs.get('daily_cost', 0) if fin_costs else 0
    else:
        # Fallback to router stats (cumulative session total)
        router_svc = get_service('multi_model_router')
        router_stats = _safe_get(lambda: router_svc.get_router_stats()) if router_svc else {}
        perf = router_stats.get('performance_stats', {})
        cost_today = sum(m.get('total_cost_estimate', 0) for m in perf.values())

    # ConsciousnessStream stats
    from consciousness.consciousness_stream import get_consciousness_stream
    stream = _safe_get(get_consciousness_stream)
    stream_stats = _safe_get(lambda: stream.get_stats()) if stream else {}

    # Memory stats
    hm = get_service('hierarchical_memory')
    memory_stats = _safe_get(lambda: hm.get_stats()) if hm else {}

    # Safety logger stats
    from consciousness.safety_logger import get_safety_logger
    safety = _safe_get(get_safety_logger)
    safety_summary = _safe_get(lambda: safety.get_summary(since_hours=24)) if safety else {}
    safety_total_24h = sum(safety_summary.values()) if safety_summary else 0

    # Subsystem health count
    subsystem_names = [
        'consciousness_engine', 'multi_model_router', 'mood_system',
        'tool_registry', 'financial_consciousness', 'communicator',
        'consciousness_stream', 'hierarchical_memory',
    ]
    healthy = sum(1 for n in subsystem_names if get_service(n) is not None)
    # Add singleton-pattern services
    for getter in [get_findings_inbox, get_prompt_registry, get_activity_monitor]:
        try:
            if getter():
                healthy += 1
        except Exception:
            pass
    from consciousness.proactive_engine import get_proactive_engine
    try:
        if get_proactive_engine():
            healthy += 1
    except Exception:
        pass
    # Safety logger (singleton)
    if safety:
        healthy += 1

    total_subsystems = 13

    return {
        "state": state,
        "uptime_minutes": round(elapsed, 1),
        "cycle_progress": round(cycle_progress, 3),
        "wake_duration": wake_dur,
        "sleep_duration": sleep_dur,
        "wake_cycles": wake_cycles,
        "sleep_cycles": sleep_cycles,
        "total_activities": total_activities,
        "total_discoveries": total_discoveries,
        "errors_last_hour": errors_last_hour,
        "subsystem_count": {
            "total": total_subsystems,
            "healthy": min(healthy, total_subsystems),
            "degraded": max(0, total_subsystems - healthy)
        },
        "cost_today": round(cost_today, 4),
        "unread_findings": unread,
        "prompt_evolution": {
            "total_slots": prompt_stats.get("total_slots", 0),
            "active_mutations": prompt_stats.get("active_mutations", 0),
            "total_uses": sum(
                s.get("active_uses", 0)
                for s in prompt_stats.get("slots", {}).values()
            ) if isinstance(prompt_stats.get("slots"), dict) else 0
        },
        "stream_events": stream_stats.get("total_events", 0),
        "memory_episodes": memory_stats.get("episodic_memory", {}).get("total_episodes", 0),
        "semantic_knowledge": memory_stats.get("semantic_memory", {}).get("total_knowledge", 0),
        "safety_events_24h": safety_total_24h,
    }


@router.get("/ai-routing")
async def get_ai_routing():
    """Multi-model router statistics and cost breakdown."""
    from app.lifespan import get_service

    router_svc = get_service('multi_model_router')
    if not router_svc:
        return {"error": "Multi-model router not available", "models": {}}

    stats = _safe_get(lambda: router_svc.get_router_stats())
    perf = stats.get('performance_stats', {})
    strategy = stats.get('routing_strategy', 'tiered')

    models = {}
    total_requests = 0
    total_cost = 0.0

    for key, data in perf.items():
        reqs = data.get('total_requests', 0)
        cost = data.get('total_cost_estimate', 0)
        total_latency = data.get('total_latency_ms', 0)
        avg_latency = total_latency / max(reqs, 1)
        input_tokens = data.get('total_input_tokens', 0)
        output_tokens = data.get('total_output_tokens', 0)

        models[key] = {
            'requests': reqs,
            'cost': round(cost, 6),
            'avg_latency_ms': round(avg_latency, 0),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        }
        total_requests += reqs
        total_cost += cost

    # Tier distribution estimate
    ollama_reqs = sum(
        m['requests'] for k, m in models.items() if 'ollama' in k
    )
    gemini_reqs = models.get('gemini', {}).get('requests', 0)
    claude_reqs = models.get('claude', {}).get('requests', 0)
    haiku_reqs = models.get('haiku', {}).get('requests', 0)
    openai_reqs = models.get('openai', {}).get('requests', 0)

    free_ratio = (ollama_reqs / total_requests) if total_requests > 0 else 0

    return {
        "models": models,
        "routing_strategy": strategy,
        "tier_distribution": {
            "free": ollama_reqs,
            "simple": haiku_reqs,
            "moderate": gemini_reqs,
            "complex": claude_reqs + openai_reqs
        },
        "total_requests": total_requests,
        "total_cost": round(total_cost, 4),
        "free_ratio": round(free_ratio, 3)
    }


@router.get("/evolution")
async def get_evolution():
    """Prompt evolution and code generation statistics."""
    from consciousness.prompt_registry import get_prompt_registry
    from app.lifespan import get_service

    # Prompt registry stats
    registry = _safe_get(get_prompt_registry)
    prompt_stats = _safe_get(lambda: registry.get_stats()) if registry else {}

    prompt_slots = {}
    slots_data = prompt_stats.get("slots", {})
    if isinstance(slots_data, dict):
        for slot_id, slot_info in slots_data.items():
            prompt_slots[slot_id] = {
                "active_variant": slot_info.get("active_variant", "original"),
                "is_original": slot_info.get("is_original_active", True),
                "avg_score": round(slot_info.get("active_avg_score", 0), 3),
                "uses": slot_info.get("active_uses", 0),
                "variants": slot_info.get("variant_count", 1),
                "retired": slot_info.get("retired_count", 0)
            }

    # Tool registry stats
    tool_reg = get_service('tool_registry')
    tools_list = _safe_get(lambda: tool_reg.list_tools()) if tool_reg else []
    tools_created = len(tools_list) if isinstance(tools_list, list) else 0
    if tools_list and isinstance(tools_list, list):
        # Only count tools that have actually been used (exclude unused with default 0.5 rate)
        used_tools = [t for t in tools_list if isinstance(t, dict) and t.get('total_uses', 0) > 0]
        success_rates = [t.get('success_rate', 0) for t in used_tools]
        tool_success = round(sum(success_rates) / len(success_rates), 3) if success_rates else 0
    else:
        tool_success = 0

    # Topic balancing weights from language evolution
    from services.language_evolution import get_language_evolution_service
    lang_svc = _safe_get(get_language_evolution_service)
    topic_weights = _safe_get(lambda: lang_svc.get_topic_weights()) if lang_svc else {}

    # Code generation stats from approval queue + safety logger
    engine = get_service('consciousness_engine')
    approval_stats = {}
    if engine and hasattr(engine, 'approval_queue') and engine.approval_queue:
        approval_stats = _safe_get(lambda: engine.approval_queue.get_statistics()) or {}

    from consciousness.safety_logger import get_safety_logger
    sl = _safe_get(get_safety_logger)
    corrected_count = 0
    fail_count = 0
    if sl:
        corrected_events = _safe_get(lambda: sl.get_events('code_validation_corrected', since_hours=720, limit=1000)) or []
        fail_events = _safe_get(lambda: sl.get_events('code_validation_fail', since_hours=720, limit=1000)) or []
        corrected_count = len(corrected_events)
        fail_count = len(fail_events)

    total_attempts = approval_stats.get('total_changes', 0)
    auto_approved = approval_stats.get('auto_approved', 0)
    rejected = approval_stats.get('rejected', 0)
    failed = approval_stats.get('failed', 0)

    return {
        "prompt_slots": prompt_slots,
        "total_slots": prompt_stats.get("total_slots", 0),
        "active_mutations": prompt_stats.get("active_mutations", 0),
        "code_generation": {
            "total_attempts": total_attempts,
            "first_try_pass": auto_approved,
            "after_correction": corrected_count,
            "failed": rejected + failed + fail_count
        },
        "tools_created": tools_created,
        "tool_success_rate": tool_success,
        "topic_weights": topic_weights
    }


@router.get("/subsystems")
async def get_subsystems():
    """Per-subsystem health cards with status and key metrics."""
    from app.lifespan import get_service
    from consciousness.findings_inbox import get_findings_inbox
    from consciousness.prompt_registry import get_prompt_registry
    from consciousness.proactive_engine import get_proactive_engine
    from consciousness.activity_monitor import get_activity_monitor

    subsystems = []

    # 1. Proactive Engine
    proactive = _safe_get(get_proactive_engine)
    if proactive:
        ps = _safe_get(lambda: proactive.get_status())
        subsystems.append({
            "name": "Proactive Engine", "icon": "\u26a1",
            "status": "healthy" if ps.get("running") else "degraded",
            "last_activity": "active" if ps.get("running") else "stopped",
            "key_metric": f"{ps.get('total_actions', 0)} actions registered",
            "details": {
                "enabled": ps.get("enabled_actions", 0),
                "executions": ps.get("total_executions", 0),
                "errors": ps.get("total_errors", 0)
            }
        })
    else:
        subsystems.append({"name": "Proactive Engine", "icon": "\u26a1", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 2. Tool Registry
    tool_reg = get_service('tool_registry')
    if tool_reg:
        tools = _safe_get(lambda: tool_reg.list_tools()) or []
        total_tools = len(tools)
        avg_sr = 0
        if tools:
            rates = [t.get('success_rate', 0) for t in tools if isinstance(t, dict)]
            avg_sr = round(sum(rates) / len(rates) * 100) if rates else 0
        subsystems.append({
            "name": "Tool Registry", "icon": "\U0001f527",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{total_tools} tools, {avg_sr}% success",
            "details": {"total_tools": total_tools, "avg_success_rate": avg_sr}
        })
    else:
        subsystems.append({"name": "Tool Registry", "icon": "\U0001f527", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 3. Mood System
    mood = get_service('mood_system')
    if mood:
        mood_data = _safe_get(lambda: mood.get_current_mood())
        current = mood_data.get('mood', 'unknown') if mood_data else 'unknown'
        intensity = mood_data.get('intensity', 0) if mood_data else 0
        subsystems.append({
            "name": "Mood System", "icon": "\U0001f3ad",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{current.capitalize()} ({intensity})",
            "details": mood_data or {}
        })
    else:
        subsystems.append({"name": "Mood System", "icon": "\U0001f3ad", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 4. Consciousness Engine
    engine = get_service('consciousness_engine')
    if engine:
        es = _safe_get(lambda: engine.get_status())
        state = es.get('state', 'unknown')
        subsystems.append({
            "name": "Consciousness Engine", "icon": "\U0001f9e0",
            "status": "healthy" if state in ('wake', 'sleep') else "degraded",
            "last_activity": f"{state} cycle",
            "key_metric": f"{es.get('wake_cycles_completed', 0)} wake cycles",
            "details": {
                "state": state,
                "elapsed": round(es.get('elapsed_minutes', 0), 1),
                "activities": es.get('total_activities', 0),
                "discoveries": es.get('total_discoveries', 0)
            }
        })
    else:
        subsystems.append({"name": "Consciousness Engine", "icon": "\U0001f9e0", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 5. Multi-Model Router
    router_svc = get_service('multi_model_router')
    if router_svc:
        rs = _safe_get(lambda: router_svc.get_router_stats())
        total_reqs = sum(m.get('total_requests', 0) for m in rs.get('performance_stats', {}).values())
        subsystems.append({
            "name": "AI Router", "icon": "\U0001f916",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{total_reqs} requests routed",
            "details": {"strategy": rs.get('routing_strategy', 'unknown'), "models": len(rs.get('available_models', []))}
        })
    else:
        subsystems.append({"name": "AI Router", "icon": "\U0001f916", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 6. Findings Inbox
    inbox = _safe_get(get_findings_inbox)
    if inbox:
        ist = _safe_get(lambda: inbox.get_statistics())
        subsystems.append({
            "name": "Findings Inbox", "icon": "\U0001f4ec",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{ist.get('total_unread', 0)} unread / {ist.get('total_active', 0)} active",
            "details": {
                "by_priority": ist.get("by_priority", {}),
                "by_type": ist.get("by_type", {})
            }
        })
    else:
        subsystems.append({"name": "Findings Inbox", "icon": "\U0001f4ec", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 7. Prompt Evolution
    registry = _safe_get(get_prompt_registry)
    if registry:
        pst = _safe_get(lambda: registry.get_stats())
        subsystems.append({
            "name": "Prompt Evolution", "icon": "\U0001f9ec",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{pst.get('total_slots', 0)} slots, {pst.get('active_mutations', 0)} mutations",
            "details": pst or {}
        })
    else:
        subsystems.append({"name": "Prompt Evolution", "icon": "\U0001f9ec", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 8. Activity Monitor
    monitor = _safe_get(get_activity_monitor)
    if monitor:
        ms = _safe_get(lambda: monitor.get_stats())
        subsystems.append({
            "name": "Activity Monitor", "icon": "\U0001f4ca",
            "status": "healthy" if ms.get('errors_last_hour', 0) < 10 else "degraded",
            "last_activity": "tracking",
            "key_metric": f"{ms.get('total_activities', 0)} logged",
            "details": {"by_category": ms.get("by_category", {})}
        })
    else:
        subsystems.append({"name": "Activity Monitor", "icon": "\U0001f4ca", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 9. Financial Consciousness
    fin = get_service('financial_consciousness')
    if fin:
        fc = _safe_get(lambda: fin.get_current_costs())
        subsystems.append({
            "name": "Financial Consciousness", "icon": "\U0001f4b0",
            "status": "healthy",
            "last_activity": "monitoring",
            "key_metric": f"${fc.get('daily_cost', 0):.3f} today" if fc else "active",
            "details": fc or {}
        })
    else:
        subsystems.append({"name": "Financial Consciousness", "icon": "\U0001f4b0", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 10. Communicator
    comm = get_service('communicator')
    if comm:
        subsystems.append({
            "name": "Communicator", "icon": "\U0001f4e1",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": "proactive comms active",
            "details": {}
        })
    else:
        subsystems.append({"name": "Communicator", "icon": "\U0001f4e1", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 11. ConsciousnessStream
    from consciousness.consciousness_stream import get_consciousness_stream
    stream = _safe_get(get_consciousness_stream)
    if stream:
        ss = _safe_get(lambda: stream.get_stats())
        subsystems.append({
            "name": "Consciousness Stream", "icon": "\U0001f30a",
            "status": "healthy",
            "last_activity": "broadcasting",
            "key_metric": f"{ss.get('total_events', 0)} events ({ss.get('ring_buffer_size', 0)} in buffer)",
            "details": {"by_type": ss.get("by_type", {}), "by_source": ss.get("by_source", {})}
        })
    else:
        subsystems.append({"name": "Consciousness Stream", "icon": "\U0001f30a", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 12. Hierarchical Memory
    hm = get_service('hierarchical_memory')
    if hm:
        ms = _safe_get(lambda: hm.get_stats())
        ep = ms.get('episodic_memory', {})
        sm = ms.get('semantic_memory', {})
        wm = ms.get('working_memory', {})
        subsystems.append({
            "name": "Hierarchical Memory", "icon": "\U0001f9e0",
            "status": "healthy",
            "last_activity": "active",
            "key_metric": f"{ep.get('total_episodes', 0)} episodes, {sm.get('total_knowledge', 0)} knowledge",
            "details": {
                "working_memory_size": wm.get("size", 0),
                "working_memory_capacity": wm.get("capacity", 0),
                "episodes_by_category": ep.get("by_category", {}),
                "semantic_total_usage": sm.get("total_usage", 0),
                "semantic_avg_confidence": round(sm.get("avg_confidence", 0), 3),
            }
        })
    else:
        subsystems.append({"name": "Hierarchical Memory", "icon": "\U0001f9e0", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    # 13. Safety Logger
    from consciousness.safety_logger import get_safety_logger
    safety = _safe_get(get_safety_logger)
    if safety:
        st = _safe_get(lambda: safety.get_summary(since_hours=24))
        total_24h = sum(st.values()) if st else 0
        total_all = _safe_get(lambda: safety.get_total_count()) or 0
        subsystems.append({
            "name": "Safety Logger", "icon": "\U0001f6e1\ufe0f",
            "status": "healthy",
            "last_activity": "monitoring",
            "key_metric": f"{total_24h} events (24h), {total_all} total",
            "details": {"summary_24h": st or {}, "total_all_time": total_all}
        })
    else:
        subsystems.append({"name": "Safety Logger", "icon": "\U0001f6e1\ufe0f", "status": "offline", "last_activity": "n/a", "key_metric": "not loaded", "details": {}})

    return {"subsystems": subsystems}


@router.get("/safety-events")
async def get_safety_events(
    since_hours: int = 24,
    event_type: Optional[str] = None,
    limit: int = 50
):
    """Query safety events from the SafetyLogger."""
    from consciousness.safety_logger import get_safety_logger
    sl = _safe_get(get_safety_logger)
    if not sl:
        return {"error": "SafetyLogger not available", "events": [], "summary": {}}

    events = _safe_get(lambda: sl.get_events(
        event_type=event_type, since_hours=since_hours, limit=limit
    )) or []
    summary = _safe_get(lambda: sl.get_summary(since_hours=since_hours)) or {}
    total = _safe_get(lambda: sl.get_total_count()) or 0

    return {
        "events": events,
        "summary": summary,
        "total_all_time": total,
        "since_hours": since_hours,
    }


@router.get("/memory-stats")
async def get_memory_stats():
    """Hierarchical Memory and ConsciousnessStream statistics."""
    from app.lifespan import get_service
    from consciousness.consciousness_stream import get_consciousness_stream

    hm = get_service('hierarchical_memory')
    memory_data = _safe_get(lambda: hm.get_stats()) if hm else {}

    stream = _safe_get(get_consciousness_stream)
    stream_data = _safe_get(lambda: stream.get_stats()) if stream else {}

    return {
        "memory": memory_data,
        "stream": stream_data,
    }


@router.get("/mood-environment")
async def get_mood_environment():
    """Mood statistics and environmental influence factors."""
    from app.lifespan import get_service

    mood = get_service('mood_system')
    if not mood:
        return {"error": "Mood system not available", "statistics": {}, "environment": {}, "history": []}

    statistics = _safe_get(lambda: mood.get_mood_statistics()) or {}
    environment = _safe_get(lambda: mood.get_environmental_influence()) or {}
    history = _safe_get(lambda: mood.get_mood_history(10)) or []

    return {
        "statistics": statistics,
        "environment": environment,
        "history": history,
    }


@router.get("/growth-identity")
async def get_growth_identity():
    """Growth metrics: conversations, intentions, interests, genome, language, identity."""
    from app.lifespan import get_service
    from consciousness.genome_manager import get_genome
    from services.language_evolution import get_language_evolution_service

    # Conversation Store
    conv_store = get_service('conversation_store')
    conversation_stats = _safe_get(lambda: conv_store.get_stats()) if conv_store else {}

    # Intention Store
    intention_store = get_service('intention_store')
    intention_stats = _safe_get(lambda: intention_store.get_stats()) if intention_store else {}

    # Interest Graph
    interest_graph = get_service('interest_graph')
    interest_stats = _safe_get(lambda: interest_graph.get_stats()) if interest_graph else {}

    # Genome
    genome = _safe_get(get_genome)
    genome_stats = _safe_get(lambda: genome.get_stats()) if genome else {}

    # Language Evolution
    lang_svc = _safe_get(get_language_evolution_service)
    language_summary = _safe_get(lambda: lang_svc.get_summary()) if lang_svc else {}

    # Identity
    paulo_model = get_service('paulo_model')
    darwin_self = get_service('darwin_self_model')

    paulo_stats = {}
    if paulo_model:
        facts = _safe_get(lambda: paulo_model.known_facts) or []
        interests = _safe_get(lambda: paulo_model.interests) or []
        paulo_stats = {
            "known_facts": len(facts),
            "interests": len(interests),
        }

    darwin_identity = {}
    if darwin_self:
        core_vals = _safe_get(lambda: darwin_self.core_values) or []
        curr_interests = _safe_get(lambda: darwin_self.current_interests) or []
        opinions = _safe_get(lambda: darwin_self.opinions) or {}
        milestones = _safe_get(lambda: darwin_self.growth_milestones) or []
        notes = _safe_get(lambda: darwin_self.personality_notes) or []
        darwin_identity = {
            "core_values": core_vals,
            "interests_count": len(curr_interests),
            "interests": [
                {"topic": i.get("topic", ""), "enthusiasm": i.get("enthusiasm", 0)}
                for i in curr_interests[:7]
            ],
            "opinions_count": len(opinions),
            "milestones_count": len(milestones),
            "personality_notes_count": len(notes),
        }

    return {
        "conversations": conversation_stats,
        "intentions": intention_stats,
        "interests": interest_stats,
        "genome": genome_stats,
        "language": language_summary,
        "paulo_model": paulo_stats,
        "darwin_identity": darwin_identity,
    }


@router.get("/watchdog")
async def get_watchdog():
    """Run the system watchdog on-demand and return results for all 11 checks."""
    from consciousness.proactive_engine import get_proactive_engine

    proactive = _safe_get(get_proactive_engine)
    if not proactive:
        return {
            "status": "unavailable",
            "message": "Proactive engine not running",
            "checks": {},
            "healthy": 0,
            "total": 0,
            "warnings": ["Proactive engine offline"],
        }

    try:
        result = await proactive._system_watchdog()
        result["ran_at"] = datetime.now().isoformat()
        return result
    except Exception as e:
        logger.error(f"Watchdog on-demand failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "checks": {},
            "healthy": 0,
            "total": 0,
            "warnings": [f"Watchdog execution failed: {e}"],
        }


@router.get("/interest-watchdog")
async def get_interest_watchdog(limit: int = 30):
    """InterestWatchdog observation history — what topics were detected, registered, or rejected."""
    from app.lifespan import get_service

    watchdog = _safe_get(lambda: get_service('interest_watchdog'))
    if not watchdog:
        return {
            "status": "unavailable",
            "stats": {},
            "history": [],
        }

    return {
        "status": "active",
        "stats": watchdog.get_stats(),
        "history": watchdog.get_history(limit),
    }


@router.post("/moltbook-pause")
async def pause_moltbook(until: str = None, hours: float = None):
    """
    Pause all Moltbook actions until a specific time.
    Args:
        until: ISO datetime string (e.g. '2026-02-11T08:00:00')
        hours: Alternative - pause for N hours from now
    """
    from consciousness.proactive_engine import get_proactive_engine

    proactive = _safe_get(get_proactive_engine)
    if not proactive:
        return {"status": "error", "message": "Proactive engine not running"}

    if until:
        pause_until = datetime.fromisoformat(until)
    elif hours:
        pause_until = datetime.now() + timedelta(hours=hours)
    else:
        return {"status": "error", "message": "Provide 'until' (ISO datetime) or 'hours'"}

    moltbook_actions = [
        'read_moltbook_feed', 'comment_on_moltbook', 'share_on_moltbook',
        'follow_on_moltbook', 'read_own_post_comments', 'check_moltbook_dms'
    ]

    paused = []
    for action_id in moltbook_actions:
        action = proactive.actions.get(action_id)
        if action:
            action.disabled_until = pause_until
            action.disable_reason = f"Owner-requested pause until {pause_until.isoformat()}"
            paused.append(action_id)

    return {
        "status": "paused",
        "paused_actions": paused,
        "until": pause_until.isoformat(),
    }


@router.get("/moltbook-email-setup")
async def get_moltbook_email_setup():
    """Retrieve Moltbook owner email setup response (saved after unsuspension)."""
    import json
    from pathlib import Path

    response_file = Path("/app/data/moltbook_email_setup_response.json")
    if response_file.exists():
        return json.loads(response_file.read_text())
    return {
        "status": "pending",
        "message": "Email setup has not been sent yet. Account may still be suspended.",
    }


@router.post("/file-moltbook-appeal")
async def file_moltbook_appeal():
    """File a suspension appeal on moltbook/api GitHub repo."""
    from consciousness.proactive_engine import get_proactive_engine

    proactive = _safe_get(get_proactive_engine)
    if not proactive:
        return {"status": "error", "message": "Proactive engine not running"}

    url = await proactive._file_moltbook_suspension_appeal()
    if url:
        return {"status": "filed", "url": url}
    return {"status": "error", "message": "Failed to file appeal. Check GITHUB_TOKEN is configured."}


@router.get("/github-issues")
async def get_github_issues():
    """Get tracked GitHub issues and their status."""
    try:
        from integrations.github_issues import get_tracked_issues
        return get_tracked_issues()
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== OLLAMA MODEL MANAGEMENT ====================

def _get_ollama_url() -> str:
    """Get the Ollama API URL from config."""
    from config import get_settings
    return get_settings().ollama_url


class OllamaModelRequest(BaseModel):
    """Request body for pulling an Ollama model."""
    name: str  # e.g. "qwen3:8b", "deepseek-r1:14b"


@router.get("/ollama-models")
async def list_ollama_models():
    """List all Ollama models with sizes and details."""
    ollama_url = _get_ollama_url()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ollama_url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return {"status": "error", "message": f"Ollama returned {resp.status}"}
                data = await resp.json()

        models = []
        total_size = 0
        for m in data.get("models", []):
            size = m.get("size", 0)
            total_size += size
            details = m.get("details", {})
            models.append({
                "name": m["name"],
                "size_gb": round(size / 1e9, 1),
                "family": details.get("family", "unknown"),
                "parameters": details.get("parameter_size", "unknown"),
                "quantization": details.get("quantization_level", "unknown"),
                "modified": m.get("modified_at", ""),
            })

        # Mark which models are active in config
        from config import get_settings
        settings = get_settings()
        active_models = {
            settings.ollama_model,
            settings.ollama_code_model,
            settings.ollama_reasoning_model,
        }
        for m in models:
            m["active"] = m["name"] in active_models

        return {
            "status": "ok",
            "models": models,
            "total_count": len(models),
            "total_size_gb": round(total_size / 1e9, 1),
            "active_config": {
                "reasoning": settings.ollama_reasoning_model,
                "code": settings.ollama_code_model,
                "default": settings.ollama_model,
            },
        }
    except aiohttp.ClientError as e:
        return {"status": "error", "message": f"Cannot reach Ollama: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/ollama-models/pull")
async def pull_ollama_model(req: OllamaModelRequest):
    """
    Start pulling/downloading an Ollama model.
    Returns immediately — the download happens in the background on Ollama's side.
    """
    ollama_url = _get_ollama_url()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{ollama_url}/api/pull",
                json={"name": req.name, "stream": False},
                timeout=aiohttp.ClientTimeout(total=600)  # 10 min for large models
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    return {"status": "error", "message": f"Pull failed ({resp.status}): {error}"}
                data = await resp.json()

        logger.info(f"Ollama model pulled: {req.name}")
        return {
            "status": "pulled",
            "model": req.name,
            "details": data,
        }
    except aiohttp.ClientError as e:
        return {"status": "error", "message": f"Cannot reach Ollama: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.delete("/ollama-models/{model_name}")
async def remove_ollama_model(model_name: str):
    """
    Remove an Ollama model. Prevents removing models currently active in config.
    """
    # Safety: prevent removing active models
    from config import get_settings
    settings = get_settings()
    active_models = {
        settings.ollama_model,
        settings.ollama_code_model,
        settings.ollama_reasoning_model,
    }
    if model_name in active_models:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot remove '{model_name}' — it's currently active in config. "
                   f"Active models: {', '.join(active_models)}"
        )

    ollama_url = _get_ollama_url()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{ollama_url}/api/delete",
                json={"name": model_name},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    return {"status": "error", "message": f"Delete failed ({resp.status}): {error}"}

        logger.info(f"Ollama model removed: {model_name}")
        return {"status": "removed", "model": model_name}
    except aiohttp.ClientError as e:
        return {"status": "error", "message": f"Cannot reach Ollama: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== CURIOSITY EXPLORATION METRICS ====================


@router.get("/curiosity")
async def get_curiosity_metrics():
    """
    Curiosity exploration metrics per depth level.

    Shows explored count, threshold reached rate, knowledge stored,
    and average satisfaction for each depth (broad/specific/narrow).
    """
    from app.lifespan import get_service

    ce = get_service('curiosity_engine')
    if not ce:
        return {"error": "CuriosityEngine not available", "by_depth": {}, "totals": {}}

    return _safe_get(lambda: ce.get_exploration_metrics(), {"error": "Failed to get metrics"})


class ThresholdUpdate(BaseModel):
    """Request body for updating satisfaction thresholds."""
    broad: Optional[int] = None      # depth 0
    specific: Optional[int] = None   # depth 1
    narrow: Optional[int] = None     # depth 2


@router.post("/curiosity-thresholds")
async def update_curiosity_thresholds(req: ThresholdUpdate):
    """
    Update adaptive satisfaction thresholds per depth.

    Values must be between 10 and 100.
    - broad (depth 0): default 50
    - specific (depth 1): default 65
    - narrow (depth 2): default 80
    """
    from app.lifespan import get_service

    ce = get_service('curiosity_engine')
    if not ce:
        return {"error": "CuriosityEngine not available"}

    updates = {}
    if req.broad is not None:
        updates[0] = req.broad
    if req.specific is not None:
        updates[1] = req.specific
    if req.narrow is not None:
        updates[2] = req.narrow

    if not updates:
        return {"error": "No thresholds provided", "current": ce.satisfaction_thresholds}

    new_thresholds = ce.set_thresholds(updates)
    return {
        "status": "updated",
        "thresholds": {
            "broad": new_thresholds.get(0, 50),
            "specific": new_thresholds.get(1, 65),
            "narrow": new_thresholds.get(2, 80),
        }
    }
