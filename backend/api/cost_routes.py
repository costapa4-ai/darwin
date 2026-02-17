"""
Cost Tracking API Routes

Provides endpoints for monitoring Darwin's AI usage costs.
"""

from fastapi import APIRouter
from typing import Dict, Any, Optional
from datetime import datetime

router = APIRouter(prefix="/api/v1/costs", tags=["costs"])

# Global reference to multi-model router (set during initialization)
_multi_model_router = None


def initialize_costs(multi_model_router):
    """Initialize with multi-model router reference"""
    global _multi_model_router
    _multi_model_router = multi_model_router


# Model pricing (per 1M tokens, separate input/output)
MODEL_PRICING = {
    "haiku": {
        "name": "Claude Haiku 4.5",
        "input_per_1m": 0.80,
        "output_per_1m": 4.0,
        "tier": "simple",
        "color": "#22c55e"  # green
    },
    "gemini": {
        "name": "Gemini 2.0 Flash",
        "input_per_1m": 0.0,
        "output_per_1m": 0.0,
        "tier": "moderate",
        "color": "#eab308"  # yellow
    },
    "claude": {
        "name": "Claude Sonnet 4.5",
        "input_per_1m": 3.0,
        "output_per_1m": 15.0,
        "tier": "complex",
        "color": "#ef4444"  # red
    },
    "ollama_code": {
        "name": "Ollama qwen3:14b",
        "input_per_1m": 0.0,
        "output_per_1m": 0.0,
        "tier": "free",
        "color": "#06b6d4"  # cyan
    },
    "ollama": {
        "name": "Ollama qwen3:14b",
        "input_per_1m": 0.0,
        "output_per_1m": 0.0,
        "tier": "free",
        "color": "#8b5cf6"  # purple
    }
}


@router.get("/summary")
async def get_cost_summary() -> Dict[str, Any]:
    """
    Get a summary of Darwin's AI usage costs.

    Returns estimated daily/monthly costs based on current usage patterns.
    """
    if not _multi_model_router:
        return {"error": "Router not initialized"}

    stats = _multi_model_router.get_router_stats()
    perf_stats = stats.get("performance_stats", {})

    # Calculate totals from session
    total_requests = 0
    total_cost = 0.0
    model_breakdown = []

    for model_name, model_stats in perf_stats.items():
        requests = model_stats.get("total_requests", 0)
        cost = model_stats.get("total_cost_estimate", 0.0)
        input_tokens = model_stats.get("total_input_tokens", 0)
        output_tokens = model_stats.get("total_output_tokens", 0)
        total_requests += requests
        total_cost += cost

        pricing = MODEL_PRICING.get(model_name, {})
        model_breakdown.append({
            "model": model_name,
            "display_name": pricing.get("name", model_name),
            "requests": requests,
            "cost": round(cost, 6),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tier": pricing.get("tier", "unknown"),
            "color": pricing.get("color", "#94a3b8")
        })

    # Estimate daily cost based on session activity
    # Assuming average session is 2 hours, extrapolate to 24 hours
    hours_factor = 12  # 24 hours / 2 hour average session

    estimated_daily = total_cost * hours_factor
    estimated_monthly = estimated_daily * 30

    return {
        "session": {
            "total_requests": total_requests,
            "total_cost": round(total_cost, 5),
            "breakdown": model_breakdown
        },
        "estimates": {
            "daily": round(estimated_daily, 2),
            "monthly": round(estimated_monthly, 2),
            "yearly": round(estimated_daily * 365, 2)
        },
        "routing_strategy": stats.get("routing_strategy", "balanced"),
        "available_models": stats.get("available_models", []),
        "pricing_info": MODEL_PRICING,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/detailed")
async def get_detailed_costs() -> Dict[str, Any]:
    """
    Get detailed cost breakdown with tier information.
    """
    if not _multi_model_router:
        return {"error": "Router not initialized"}

    stats = _multi_model_router.get_router_stats()
    perf_stats = stats.get("performance_stats", {})
    model_info = stats.get("model_info", {})

    tiers = {
        "simple": {"models": [], "total_requests": 0, "total_cost": 0.0},
        "moderate": {"models": [], "total_requests": 0, "total_cost": 0.0},
        "complex": {"models": [], "total_requests": 0, "total_cost": 0.0}
    }

    for model_name, model_stats in perf_stats.items():
        requests = model_stats.get("total_requests", 0)
        cost = model_stats.get("total_cost_estimate", 0.0)

        pricing = MODEL_PRICING.get(model_name, {})
        tier = pricing.get("tier", "moderate")

        if tier in tiers:
            tiers[tier]["models"].append(model_name)
            tiers[tier]["total_requests"] += requests
            tiers[tier]["total_cost"] += cost

    return {
        "tiers": tiers,
        "model_info": {
            name: {
                **info,
                "session_stats": perf_stats.get(name, {})
            }
            for name, info in model_info.items()
        },
        "optimization_tips": [
            "Use TIERED routing for optimal cost/quality balance",
            "Haiku handles 70% of simple tasks at 1/15th the cost of Sonnet",
            "Gemini is best for research and moderate complexity tasks"
        ]
    }


@router.post("/set-strategy/{strategy}")
async def set_routing_strategy(strategy: str) -> Dict[str, Any]:
    """
    Change the routing strategy.

    Options: performance, cost, speed, balanced, tiered
    """
    if not _multi_model_router:
        return {"error": "Router not initialized"}

    valid_strategies = ["performance", "cost", "speed", "balanced", "tiered"]
    if strategy not in valid_strategies:
        return {"error": f"Invalid strategy. Options: {valid_strategies}"}

    from ai.multi_model_router import RoutingStrategy
    _multi_model_router.routing_strategy = RoutingStrategy(strategy)

    return {
        "success": True,
        "new_strategy": strategy,
        "message": f"Routing strategy changed to {strategy}"
    }
