"""
Introspection API Routes - Darwin's self-analysis endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from introspection.self_analyzer import SelfAnalyzer, CodeInsight

router = APIRouter(prefix="/api/v1/introspection", tags=["introspection"])

# Global instance
self_analyzer: Optional[SelfAnalyzer] = None


class AnalysisRequest(BaseModel):
    """Request for self-analysis"""
    deep_analysis: bool = True
    include_metrics: bool = True


class InsightFilter(BaseModel):
    """Filter for insights"""
    priority: Optional[str] = None
    component: Optional[str] = None
    type: Optional[str] = None


def initialize_introspection():
    """Initialize the self-analyzer"""
    global self_analyzer
    self_analyzer = SelfAnalyzer(project_root="/app")


@router.post("/analyze")
async def analyze_self(request: AnalysisRequest = AnalysisRequest()):
    """
    🔍 Trigger Darwin's self-analysis

    Darwin will analyze its own codebase, Docker environment,
    and suggest improvements and new features.
    """
    if not self_analyzer:
        raise HTTPException(status_code=503, detail="Self-analyzer not initialized")

    try:
        analysis = self_analyzer.analyze_self()

        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'message': 'Darwin has completed self-analysis',
            'analysis': analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/insights")
async def get_insights(
    priority: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 50
):
    """
    Get insights from Darwin's self-analysis

    Filter by priority (high/medium/low) or component (backend/frontend/docker)
    """
    if not self_analyzer:
        raise HTTPException(status_code=503, detail="Self-analyzer not initialized")

    try:
        insights = self_analyzer.insights

        # Apply filters
        if priority:
            insights = [i for i in insights if i.priority == priority]

        if component:
            insights = [i for i in insights if i.component == component]

        # Convert to dict
        insights_dict = [
            {
                'type': i.type,
                'component': i.component,
                'priority': i.priority,
                'title': i.title,
                'description': i.description,
                'current_state': i.current_state,
                'proposed_change': i.proposed_change,
                'benefits': i.benefits,
                'estimated_impact': i.estimated_impact,
                'code_location': i.code_location
            }
            for i in insights[:limit]
        ]

        return {
            'success': True,
            'total': len(insights),
            'insights': insights_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/high-priority")
async def get_high_priority_insights():
    """
    Get high-priority insights - the most important improvements Darwin identified
    """
    if not self_analyzer:
        raise HTTPException(status_code=503, detail="Self-analyzer not initialized")

    try:
        high_priority = self_analyzer.get_insights_by_priority('high')

        insights_dict = [
            {
                'title': i.title,
                'component': i.component,
                'description': i.description,
                'benefits': i.benefits,
                'estimated_impact': i.estimated_impact
            }
            for i in high_priority
        ]

        return {
            'success': True,
            'count': len(high_priority),
            'insights': insights_dict,
            'recommendation': 'These are the most impactful improvements Darwin recommends'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_system_metrics():
    """
    Get metrics about Darwin's own system

    Returns statistics about codebase, Docker environment, complexity, etc.
    """
    if not self_analyzer or not self_analyzer.metrics:
        raise HTTPException(
            status_code=503,
            detail="Metrics not available. Run /analyze first"
        )

    try:
        metrics = self_analyzer.metrics

        return {
            'success': True,
            'metrics': {
                'codebase': {
                    'total_files': metrics.total_files,
                    'total_lines_of_code': metrics.total_lines_of_code,
                    'languages': metrics.languages,
                    'components': metrics.components
                },
                'docker': metrics.docker_stats,
                'complexity': metrics.code_complexity
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_analysis_summary():
    """
    Get summary of Darwin's self-analysis

    Overview of insights by type, priority, and recommended next steps
    """
    if not self_analyzer:
        raise HTTPException(status_code=503, detail="Self-analyzer not initialized")

    try:
        if not self_analyzer.insights:
            # Run analysis if not done yet
            self_analyzer.analyze_self()

        analysis = self_analyzer.analyze_self()
        summary = analysis['summary']

        return {
            'success': True,
            'summary': summary,
            'message': f"Darwin found {summary['total_insights']} insights for self-improvement"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/{component}")
async def get_component_suggestions(component: str):
    """
    Get improvement suggestions for a specific component

    Components: backend, frontend, docker, sandbox
    """
    if not self_analyzer:
        raise HTTPException(status_code=503, detail="Self-analyzer not initialized")

    try:
        insights = self_analyzer.get_insights_by_component(component)

        if not insights:
            return {
                'success': True,
                'component': component,
                'count': 0,
                'message': f'No suggestions found for {component}',
                'suggestions': []
            }

        # Sort by priority and impact
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        insights.sort(
            key=lambda x: (priority_order.get(x.priority, 0), x.estimated_impact),
            reverse=True
        )

        suggestions = [
            {
                'title': i.title,
                'type': i.type,
                'priority': i.priority,
                'description': i.description,
                'benefits': i.benefits,
                'estimated_impact': i.estimated_impact
            }
            for i in insights
        ]

        return {
            'success': True,
            'component': component,
            'count': len(suggestions),
            'suggestions': suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def introspection_status():
    """Check if introspection system is ready"""
    return {
        'enabled': self_analyzer is not None,
        'ready': self_analyzer is not None,
        'has_analysis': self_analyzer is not None and len(self_analyzer.insights) > 0,
        'insights_count': len(self_analyzer.insights) if self_analyzer else 0
    }
