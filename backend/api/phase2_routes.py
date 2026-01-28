"""
Phase 2 API Routes
Enhanced endpoints for RAG, multi-model, web research, and meta-learning
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

router = APIRouter(prefix="/api/v1/phase2", tags=["phase2"])

# Request/Response models
class ResearchRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None  # ["web", "github", "stackoverflow", "arxiv"]

class PatternSearchRequest(BaseModel):
    task_description: str
    max_results: int = 5

class MultiModelAnalysisRequest(BaseModel):
    code: str
    task_description: str
    models: Optional[List[str]] = None

class MetaLearningRequest(BaseModel):
    action: str  # "analyze", "optimize", "export", "import"
    filepath: Optional[str] = None


# Global instances (will be set by main.py)
semantic_memory = None
router_instance = None
web_researcher = None
meta_learner = None


def initialize_phase2(memory, model_router, researcher, learner):
    """Initialize Phase 2 components"""
    global semantic_memory, router_instance, web_researcher, meta_learner
    semantic_memory = memory
    router_instance = model_router
    web_researcher = researcher
    meta_learner = learner


@router.get("/status")
async def get_phase2_status():
    """Get Phase 2 feature status"""
    return {
        "phase2_enabled": True,
        "features": {
            "semantic_memory": semantic_memory is not None,
            "multi_model_router": router_instance is not None,
            "web_researcher": web_researcher is not None,
            "meta_learner": meta_learner is not None
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/memory/stats")
async def get_memory_stats():
    """Get semantic memory statistics"""
    if not semantic_memory:
        raise HTTPException(status_code=503, detail="Semantic memory not available")

    try:
        stats = semantic_memory.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/search")
async def search_similar_executions(request: PatternSearchRequest):
    """Search for similar past executions"""
    if not semantic_memory:
        raise HTTPException(status_code=503, detail="Semantic memory not available")

    try:
        results = await semantic_memory.retrieve_similar(
            query=request.task_description,
            n_results=request.max_results
        )

        return {
            "success": True,
            "query": request.task_description,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/patterns")
async def discover_patterns():
    """Discover reusable code patterns"""
    if not semantic_memory:
        raise HTTPException(status_code=503, detail="Semantic memory not available")

    try:
        patterns = await semantic_memory.find_reusable_patterns()

        return {
            "success": True,
            "patterns": patterns,
            "count": len(patterns)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/router/stats")
async def get_router_stats():
    """Get multi-model router statistics"""
    if not router_instance:
        raise HTTPException(status_code=503, detail="Multi-model router not available")

    try:
        stats = router_instance.get_router_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/router/analyze")
async def analyze_code_multi_model(request: MultiModelAnalysisRequest):
    """Analyze code with multiple models"""
    if not router_instance:
        raise HTTPException(status_code=503, detail="Multi-model router not available")

    try:
        analysis = await router_instance.analyze_with_multiple(
            code=request.code,
            task=request.task_description,
            models=request.models
        )

        return {
            "success": True,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research")
async def research_topic(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Perform web research on a topic"""
    if not web_researcher:
        raise HTTPException(status_code=503, detail="Web researcher not available")

    try:
        results = await web_researcher.comprehensive_search(
            query=request.query,
            sources=request.sources
        )

        formatted_context = web_researcher.format_research_context(results)

        return {
            "success": True,
            "query": request.query,
            "results": results,
            "formatted_context": formatted_context,
            "total_results": sum(len(r) for r in results.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/insights")
async def get_learning_insights():
    """Get meta-learning insights"""
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Meta-learner not available")

    try:
        insights = meta_learner.get_learning_insights()
        return {
            "success": True,
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meta/optimize")
async def trigger_self_optimization():
    """Trigger self-optimization process"""
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Meta-learner not available")

    try:
        report = await meta_learner.self_optimize()
        return {
            "success": True,
            "optimization_report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/meta/suggestions")
async def get_optimization_suggestions():
    """Get optimization suggestions"""
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Meta-learner not available")

    try:
        suggestions = await meta_learner.suggest_optimizations()
        return {
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meta/export")
async def export_learning_data(filepath: str):
    """Export meta-learning data"""
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Meta-learner not available")

    try:
        meta_learner.export_learning_data(filepath)
        return {
            "success": True,
            "message": f"Learning data exported to {filepath}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meta/import")
async def import_learning_data(filepath: str):
    """Import meta-learning data"""
    if not meta_learner:
        raise HTTPException(status_code=503, detail="Meta-learner not available")

    try:
        meta_learner.import_learning_data(filepath)
        return {
            "success": True,
            "message": f"Learning data imported from {filepath}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def phase2_health_check():
    """Comprehensive Phase 2 health check"""
    health = {
        "status": "healthy",
        "components": {},
        "timestamp": datetime.now().isoformat()
    }

    # Check semantic memory
    if semantic_memory:
        try:
            stats = semantic_memory.get_stats()
            health["components"]["semantic_memory"] = {
                "status": "healthy",
                "executions": stats.get("total_executions", 0),
                "patterns": stats.get("total_patterns", 0)
            }
        except Exception as e:
            health["components"]["semantic_memory"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
    else:
        health["components"]["semantic_memory"] = {"status": "not_configured"}

    # Check router
    if router_instance:
        try:
            stats = router_instance.get_router_stats()
            health["components"]["multi_model_router"] = {
                "status": "healthy",
                "available_models": len(stats.get("available_models", []))
            }
        except Exception as e:
            health["components"]["multi_model_router"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
    else:
        health["components"]["multi_model_router"] = {"status": "not_configured"}

    # Check web researcher
    health["components"]["web_researcher"] = {
        "status": "healthy" if web_researcher else "not_configured"
    }

    # Check meta-learner
    if meta_learner:
        try:
            insights = meta_learner.get_learning_insights()
            health["components"]["meta_learner"] = {
                "status": "healthy",
                "total_executions": insights.get("total_executions", 0)
            }
        except Exception as e:
            health["components"]["meta_learner"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health["status"] = "degraded"
    else:
        health["components"]["meta_learner"] = {"status": "not_configured"}

    return health
