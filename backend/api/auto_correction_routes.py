"""
Auto-Correction API Routes
Endpoints for the auto-correction workflow with human approval
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from introspection.self_analyzer import SelfAnalyzer, CodeInsight
from introspection.code_generator import CodeGenerator, GeneratedCode
from introspection.code_validator import CodeValidator, ValidationResult
from introspection.approval_system import ApprovalQueue, ChangeRequest
from introspection.auto_applier import AutoApplier


router = APIRouter(prefix="/api/v1/auto-correction", tags=["auto-correction"])

# Global instances
code_generator: Optional[CodeGenerator] = None
code_validator: Optional[CodeValidator] = None
approval_queue: Optional[ApprovalQueue] = None
auto_applier: Optional[AutoApplier] = None
self_analyzer: Optional[SelfAnalyzer] = None


class ApprovalRequest(BaseModel):
    """Request to approve a change"""
    comment: Optional[str] = None


class RejectionRequest(BaseModel):
    """Request to reject a change"""
    reason: str


def initialize_auto_correction(nucleus=None):
    """Initialize auto-correction system"""
    global code_generator, code_validator, approval_queue, auto_applier, self_analyzer

    code_generator = CodeGenerator(nucleus=nucleus)
    code_validator = CodeValidator()
    approval_queue = ApprovalQueue()
    auto_applier = AutoApplier()
    self_analyzer = SelfAnalyzer()

    print("✅ Auto-Correction System initialized")


@router.get("/status")
async def get_system_status():
    """
    📊 Get auto-correction system status

    Returns current state and statistics
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    stats = approval_queue.get_statistics()

    return {
        'enabled': True,
        'components': {
            'code_generator': code_generator is not None,
            'code_validator': code_validator is not None,
            'approval_queue': approval_queue is not None,
            'auto_applier': auto_applier is not None
        },
        'statistics': stats
    }


@router.post("/generate/{insight_index}")
async def generate_code_for_insight(insight_index: int):
    """
    🔧 Generate code for a specific insight

    Steps:
    1. Get insight from self-analysis
    2. Generate code using AI
    3. Validate generated code
    4. Add to approval queue

    Args:
        insight_index: Index of insight in self-analysis results (0-based)

    Returns:
        Generated code, validation results, and change request info
    """
    if not code_generator or not code_validator or not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    try:
        # 1. Run analysis to get insights
        analysis = self_analyzer.analyze_self()
        insights = analysis['insights']

        if insight_index >= len(insights):
            raise HTTPException(
                status_code=404,
                detail=f"Insight {insight_index} not found. Available: 0-{len(insights)-1}"
            )

        insight_dict = insights[insight_index]
        insight = CodeInsight(**insight_dict)

        print(f"🔧 Generating code for insight {insight_index}: {insight.title}")

        # 2. Generate code
        generated = await code_generator.generate_code_for_insight(insight)

        # 3. Validate
        validation = await code_validator.validate(generated)

        # 4. Add to approval queue
        queue_result = approval_queue.add(generated, validation)

        return {
            'success': True,
            'insight': insight_dict,
            'generated_code': {
                'file_path': generated.file_path,
                'risk_level': generated.risk_level,
                'estimated_time_minutes': generated.estimated_time_minutes,
                'explanation': generated.explanation,
                'diff_unified': generated.diff_unified[:500] + '...' if len(generated.diff_unified) > 500 else generated.diff_unified
            },
            'validation': {
                'valid': validation.valid,
                'score': validation.score,
                'checks_passed': validation.checks_passed,
                'checks_failed': validation.checks_failed,
                'warnings': validation.warnings,
                'security_issues': validation.security_issues
            },
            'queue_result': queue_result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.get("/pending")
async def get_pending_changes():
    """
    ⏳ Get all changes pending approval

    Returns list of changes awaiting manual approval
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    pending = approval_queue.get_pending()

    return {
        'success': True,
        'count': len(pending),
        'changes': pending
    }


@router.get("/change/{change_id}")
async def get_change_details(change_id: str):
    """
    🔍 Get detailed information about a specific change

    Returns complete details including diff, validation, etc.
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    change = approval_queue.get_change(change_id)

    if not change:
        raise HTTPException(status_code=404, detail=f"Change {change_id} not found")

    return {
        'success': True,
        'change': change
    }


@router.post("/approve/{change_id}")
async def approve_change(change_id: str, request: ApprovalRequest):
    """
    ✅ Approve a change and apply it to the codebase

    Steps:
    1. Approve in queue
    2. Apply change with backup
    3. Mark as applied
    4. Return rollback ID

    Args:
        change_id: ID of the change to approve
        request: Optional comment

    Returns:
        Application result with rollback ID
    """
    if not approval_queue or not auto_applier:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    try:
        # 1. Approve in queue
        approval_result = approval_queue.approve(change_id, request.comment)

        if not approval_result['success']:
            raise HTTPException(status_code=404, detail=approval_result['message'])

        # 2. Get approved change
        change = approval_queue.get_change(change_id)

        # 3. Apply change
        apply_result = auto_applier.apply_change(change)

        if apply_result['success']:
            # 4. Mark as applied
            approval_queue.mark_as_applied(change_id, apply_result['rollback_id'])

            return {
                'success': True,
                'message': '✅ Change approved and applied successfully',
                'change_id': change_id,
                'rollback_id': apply_result['rollback_id'],
                'file_path': change['generated_code']['file_path'],
                'backup_path': apply_result['backup_path']
            }
        else:
            # Mark as failed
            approval_queue.mark_as_failed(change_id, apply_result['error'])

            return {
                'success': False,
                'message': f"❌ Change approved but failed to apply: {apply_result['error']}",
                'change_id': change_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post("/reject/{change_id}")
async def reject_change(change_id: str, request: RejectionRequest):
    """
    ❌ Reject a pending change

    Args:
        change_id: ID of the change to reject
        request: Reason for rejection

    Returns:
        Rejection confirmation
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    result = approval_queue.reject(change_id, request.reason)

    if not result['success']:
        raise HTTPException(status_code=404, detail=result['message'])

    return {
        'success': True,
        'message': result['message'],
        'change_id': change_id
    }


@router.post("/rollback/{rollback_id}")
async def rollback_change(rollback_id: str):
    """
    ⏪ Rollback a previously applied change

    Restores file from backup

    Args:
        rollback_id: ID returned when change was applied

    Returns:
        Rollback result
    """
    if not auto_applier or not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    try:
        # Perform rollback
        result = auto_applier.rollback(rollback_id)

        if result['success']:
            # Find and mark change as rolled back
            for change in approval_queue.history:
                if change.rollback_id == rollback_id:
                    approval_queue.mark_as_rolled_back(change.id)
                    break

            return {
                'success': True,
                'message': result['message'],
                'rollback_id': rollback_id,
                'file_restored': result['file_restored']
            }
        else:
            return {
                'success': False,
                'message': result['message']
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


@router.get("/history")
async def get_change_history(
    limit: int = Query(default=50, le=100),
    status: Optional[str] = None
):
    """
    📜 Get history of all changes

    Args:
        limit: Maximum number of changes to return
        status: Filter by status (pending, approved, rejected, applied, failed)

    Returns:
        List of historical changes
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    history = approval_queue.get_history(limit=limit, status=status)

    return {
        'success': True,
        'count': len(history),
        'history': history
    }


@router.get("/statistics")
async def get_statistics():
    """
    📊 Get detailed statistics about auto-correction

    Returns:
    - Total changes
    - Approval rates
    - Success rates
    - Status breakdown
    """
    if not approval_queue:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    stats = approval_queue.get_statistics()

    return {
        'success': True,
        'statistics': stats
    }


@router.get("/rollbacks")
async def list_rollbacks(limit: int = Query(default=20, le=50)):
    """
    🔄 List all applied changes with rollback capability

    Returns list of changes that can be rolled back
    """
    if not auto_applier:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    applied = auto_applier.list_applied_changes(limit=limit)

    return {
        'success': True,
        'count': len(applied),
        'rollbacks': applied
    }


@router.post("/cleanup-backups")
async def cleanup_old_backups(days: int = Query(default=7, ge=1, le=30)):
    """
    🗑️ Cleanup old backup files

    Args:
        days: Delete backups older than this many days (default: 7)

    Returns:
        Number of backups deleted
    """
    if not auto_applier:
        raise HTTPException(status_code=503, detail="Auto-correction not initialized")

    deleted = auto_applier.cleanup_old_backups(days=days)

    return {
        'success': True,
        'deleted': deleted,
        'message': f'🗑️ Cleaned up {deleted} backups older than {days} days'
    }
