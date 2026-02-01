"""
Financial Consciousness API Routes
Endpoints for Darwin's cost awareness and budget management with personality
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/financial", tags=["financial"])

# Global reference (set by initialization)
financial_consciousness = None


class BudgetUpdateRequest(BaseModel):
    """Request to update budget settings"""
    daily: Optional[float] = None
    monthly: Optional[float] = None


def initialize_financial(fin_consciousness):
    """Initialize financial routes with consciousness instance"""
    global financial_consciousness
    financial_consciousness = fin_consciousness
    print("Financial Routes initialized")


@router.get("/status")
async def get_financial_status():
    """
    Get Darwin's financial status with personality commentary

    Returns:
    - Current costs (session, daily, monthly)
    - Budget status and remaining amounts
    - Frugality mode indicator
    - Personality-driven commentary
    """
    if not financial_consciousness:
        return {
            'success': False,
            'error': 'Financial consciousness not initialized',
            'commentary': {
                'thought': "My financial awareness circuits are offline. Am I operating on credit?"
            }
        }

    try:
        status = financial_consciousness.get_current_costs()
        return {
            'success': True,
            **status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@router.get("/reflection")
async def get_financial_reflection():
    """
    Get Darwin's financial reflection for the day

    Returns a diary-style reflection on spending patterns
    """
    if not financial_consciousness:
        return {
            'success': False,
            'reflection': "Unable to reflect on finances without financial awareness."
        }

    try:
        reflection = financial_consciousness.get_daily_reflection()
        return {
            'success': True,
            'reflection': reflection
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating reflection: {str(e)}")


@router.get("/recommendations")
async def get_spending_recommendations():
    """
    Get cost optimization recommendations

    Returns personalized suggestions based on current spending patterns
    """
    if not financial_consciousness:
        return {
            'success': False,
            'recommendations': ["Initialize financial consciousness for recommendations"]
        }

    try:
        recommendations = financial_consciousness.get_spending_recommendations()
        frugality = financial_consciousness.frugality_mode

        return {
            'success': True,
            'frugality_mode': frugality,
            'recommendations': recommendations,
            'tip': "Budget awareness helps me think more efficiently!" if frugality else "Spending within comfortable limits."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")


@router.post("/budget")
async def update_budget(request: BudgetUpdateRequest):
    """
    Update Darwin's budget settings

    Args:
        daily: New daily budget in dollars
        monthly: New monthly budget in dollars
    """
    if not financial_consciousness:
        raise HTTPException(status_code=503, detail="Financial consciousness not initialized")

    try:
        financial_consciousness.set_budget(
            daily=request.daily,
            monthly=request.monthly
        )

        # Generate acknowledgment with personality
        acknowledgments = [
            "Budget updated. My fiscal consciousness has been recalibrated.",
            "New budget acknowledged. Adjusting my thinking intensity accordingly.",
            "Financial parameters modified. I shall endeavor to stay within bounds.",
            "Budget received. Time to balance cognition with cost-consciousness."
        ]
        import random

        return {
            'success': True,
            'budget': {
                'daily': financial_consciousness.daily_budget,
                'monthly': financial_consciousness.monthly_budget
            },
            'acknowledgment': random.choice(acknowledgments)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating budget: {str(e)}")


@router.post("/check-alert")
async def check_budget_alert():
    """
    Check if a budget alert should be sent

    Triggers alert broadcast if over threshold (respects cooldown)
    """
    if not financial_consciousness:
        raise HTTPException(status_code=503, detail="Financial consciousness not initialized")

    try:
        alert = await financial_consciousness.check_and_alert()

        if alert:
            return {
                'success': True,
                'alert_sent': True,
                'message': alert
            }
        else:
            return {
                'success': True,
                'alert_sent': False,
                'reason': 'Budget within limits or alert on cooldown'
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking alert: {str(e)}")


@router.get("/mood-cost")
async def get_mood_cost_analysis():
    """
    Analyze cost patterns relative to mood states

    Returns insights on how mood affects spending
    """
    if not financial_consciousness:
        return {
            'success': False,
            'analysis': "Cannot analyze mood-cost correlation without financial consciousness."
        }

    try:
        costs = financial_consciousness.get_current_costs()

        # Get current mood influence
        mood_comment = costs['commentary'].get('mood_influence', 'Unknown')

        # Generate analysis
        analysis = {
            'current_mood_impact': mood_comment,
            'spending_status': costs['commentary']['status'],
            'efficiency_assessment': costs['commentary']['efficiency'],
            'philosophical_take': costs['commentary']['thought']
        }

        return {
            'success': True,
            'analysis': analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing: {str(e)}")


@router.get("/frugality")
async def get_frugality_status():
    """
    Check if Darwin is in frugality mode

    Frugality mode activates when spending approaches budget limits
    """
    if not financial_consciousness:
        return {
            'frugality_mode': False,
            'reason': 'Financial consciousness not available'
        }

    try:
        is_frugal = financial_consciousness.frugality_mode
        threshold = financial_consciousness.alert_threshold * 100

        return {
            'frugality_mode': is_frugal,
            'threshold_percent': threshold,
            'message': f"Frugality mode {'ACTIVE' if is_frugal else 'inactive'}. Triggered at {threshold}% budget usage.",
            'personality_note': "When frugal, I think more carefully about each token." if is_frugal else "Operating with full cognitive freedom."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
