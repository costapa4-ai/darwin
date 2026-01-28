"""
Interaction Memory API Routes
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])
communicator = None

def initialize_memory(comm):
    global communicator
    communicator = comm
    print("✅ Memory Routes initialized")

@router.get("/preferences")
async def get_preferences(min_confidence: float = 0.7):
    if not communicator:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    prefs = communicator.memory.get_all_preferences(min_confidence)
    return {'success': True, 'preferences': prefs}

@router.get("/insights")
async def get_insights():
    if not communicator:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    insights = communicator.memory.get_communication_insights()
    return {'success': True, 'insights': insights}

@router.get("/interactions")
async def get_interactions(limit: int = 20, type: Optional[str] = None):
    if not communicator:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    interactions = communicator.memory.get_recent_interactions(limit, type)
    return {'success': True, 'interactions': interactions, 'count': len(interactions)}

@router.get("/statistics")
async def get_statistics():
    if not communicator:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    stats = communicator.memory.get_statistics()
    return {'success': True, 'statistics': stats}

@router.get("/frequency")
async def get_frequency(days: int = 7):
    if not communicator:
        raise HTTPException(status_code=503, detail="Memory not initialized")

    freq = communicator.memory.get_interaction_frequency(days)
    return {'success': True, 'frequency': freq}
