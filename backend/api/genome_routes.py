"""
Genome API Routes — Monitor and manage Darwin's evolvable genome.

Endpoints:
- GET /api/v1/genome/status         — Summary, stats, cooldown
- GET /api/v1/genome/domain/{name}  — Full domain data
- GET /api/v1/genome/history        — Evolution changelog
- POST /api/v1/genome/rollback      — Manual rollback (Paulo only)
- GET /api/v1/identity/core-values  — Current core values
- PUT /api/v1/identity/core-values  — Update core values (Paulo only)
- GET /api/v1/identity/self-model   — Darwin's self-model
"""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["genome"])

IDENTITY_DIR = Path("/app/data/identity")


def _get_genome():
    from consciousness.genome_manager import get_genome
    return get_genome()


# ==================== Genome Endpoints ====================

@router.get("/genome/status")
async def genome_status():
    """Get genome summary, per-domain stats, cooldown status."""
    try:
        genome = _get_genome()
        stats = genome.get_stats()
        stats["summary"] = genome.get_summary()
        stats["domains"] = list(genome._data.keys())
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genome/domain/{name}")
async def genome_domain(name: str):
    """Get full domain data."""
    try:
        genome = _get_genome()
        from consciousness.genome_manager import DOMAINS
        if name not in DOMAINS:
            raise HTTPException(status_code=404, detail=f"Unknown domain: {name}. Available: {DOMAINS}")
        data = genome.get_domain(name)
        return {"domain": name, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genome/history")
async def genome_history(limit: int = 50):
    """Get evolution changelog."""
    try:
        genome = _get_genome()
        changelog = genome.get_changelog(limit=limit)
        return {"changelog": changelog, "count": len(changelog)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RollbackRequest(BaseModel):
    snapshot_id: Optional[str] = None


@router.post("/genome/rollback")
async def genome_rollback(req: RollbackRequest):
    """Manual rollback (Paulo only). Re-enables Darwin's self-rollback."""
    try:
        genome = _get_genome()
        ok, msg = genome.manual_rollback(snapshot_id=req.snapshot_id)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Identity / Core Values Endpoints ====================

@router.get("/identity/core-values")
async def get_core_values():
    """Get Darwin's core values (defined by Paulo)."""
    try:
        identity_file = IDENTITY_DIR / "darwin_self.json"
        if not identity_file.exists():
            return {"core_values": [], "note": "Identity file not found"}
        data = json.loads(identity_file.read_text())
        return {
            "core_values": data.get("core_values", []),
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoreValuesUpdate(BaseModel):
    core_values: List[str]


@router.put("/identity/core-values")
async def update_core_values(req: CoreValuesUpdate):
    """Update Darwin's core values (Paulo only)."""
    try:
        identity_file = IDENTITY_DIR / "darwin_self.json"
        if not identity_file.exists():
            raise HTTPException(status_code=404, detail="Identity file not found")

        data = json.loads(identity_file.read_text())
        old_values = data.get("core_values", [])
        data["core_values"] = req.core_values

        from datetime import datetime
        data["updated_at"] = datetime.utcnow().isoformat()

        identity_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

        logger.info(f"Core values updated by Paulo: {old_values} → {req.core_values}")

        return {
            "success": True,
            "old_values": old_values,
            "new_values": req.core_values,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/identity/self-model")
async def get_self_model():
    """Get Darwin's full self-model (read-only view)."""
    try:
        identity_file = IDENTITY_DIR / "darwin_self.json"
        if not identity_file.exists():
            return {"note": "Identity file not found"}
        data = json.loads(identity_file.read_text())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
