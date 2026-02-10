"""
Observatory API Routes - Comprehensive monitoring dashboard aggregation.

Provides 5 aggregation endpoints for the Darwin Observatory frontend:
- /overview: System health summary
- /ai-routing: Multi-model router stats
- /evolution: Prompt evolution + code generation stats
- /subsystems: Per-subsystem health cards
- /watchdog: System watchdog results (last run + on-demand trigger)
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from utils.logger import setup_logger

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

    # Cycle progress
    if state == 'wake':
        cycle_progress = min(elapsed / 120.0, 1.0) if elapsed else 0
    elif state == 'sleep':
        cycle_progress = min(elapsed / 30.0, 1.0) if elapsed else 0
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

    # Multi-model router for cost
    router_svc = get_service('multi_model_router')
    router_stats = _safe_get(lambda: router_svc.get_router_stats()) if router_svc else {}
    perf = router_stats.get('performance_stats', {})
    cost_today = sum(m.get('total_cost_estimate', 0) for m in perf.values())

    # Subsystem health count
    subsystem_names = [
        'consciousness_engine', 'multi_model_router', 'mood_system',
        'tool_registry', 'financial_consciousness', 'communicator'
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

    total_subsystems = 10

    return {
        "state": state,
        "uptime_minutes": round(elapsed, 1),
        "cycle_progress": round(cycle_progress, 3),
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
        }
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

    # Map internal model keys to display names
    model_map = {
        'ollama_code': 'ollama_code',
        'ollama_reasoning': 'ollama_reasoning',
        'ollama': 'ollama_code',
        'gemini': 'gemini',
        'gemini_flash': 'gemini',
        'claude': 'claude',
        'openai': 'openai',
    }

    for key, data in perf.items():
        display_key = model_map.get(key, key)
        reqs = data.get('total_requests', 0)
        cost = data.get('total_cost_estimate', 0)
        avg_latency = data.get('avg_latency_ms', 0)

        if display_key in models:
            models[display_key]['requests'] += reqs
            models[display_key]['cost'] += cost
        else:
            models[display_key] = {
                'requests': reqs,
                'cost': round(cost, 4),
                'avg_latency_ms': round(avg_latency, 0)
            }
        total_requests += reqs
        total_cost += cost

    # Tier distribution estimate
    ollama_reqs = sum(
        m['requests'] for k, m in models.items() if 'ollama' in k
    )
    gemini_reqs = models.get('gemini', {}).get('requests', 0)
    claude_reqs = models.get('claude', {}).get('requests', 0)
    openai_reqs = models.get('openai', {}).get('requests', 0)

    free_ratio = (ollama_reqs / total_requests) if total_requests > 0 else 0

    return {
        "models": models,
        "routing_strategy": strategy,
        "tier_distribution": {
            "simple": ollama_reqs,
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
        success_rates = [t.get('success_rate', 0) for t in tools_list if isinstance(t, dict)]
        tool_success = round(sum(success_rates) / len(success_rates), 3) if success_rates else 0
    else:
        tool_success = 0

    # Topic balancing weights from language evolution
    from services.language_evolution import get_language_evolution_service
    lang_svc = _safe_get(get_language_evolution_service)
    topic_weights = _safe_get(lambda: lang_svc.get_topic_weights()) if lang_svc else {}

    return {
        "prompt_slots": prompt_slots,
        "total_slots": prompt_stats.get("total_slots", 0),
        "active_mutations": prompt_stats.get("active_mutations", 0),
        "code_generation": {
            "total_attempts": 0,
            "first_try_pass": 0,
            "after_correction": 0,
            "failed": 0
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

    return {"subsystems": subsystems}


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
