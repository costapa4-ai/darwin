"""
Command Routes - REST API for safe command execution

Provides endpoints for:
- Executing whitelisted safe commands
- Getting available commands
- Viewing command execution history
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from tools.safe_command_executor import get_safe_executor
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/commands", tags=["commands"])


class ExecuteCommandRequest(BaseModel):
    """Request body for executing a command."""
    command: str
    working_dir: Optional[str] = None
    timeout: Optional[int] = None


@router.get("/available")
async def list_available_commands():
    """
    Get list of available safe commands and their configurations.
    """
    executor = get_safe_executor()

    return {
        "commands": executor.get_available_commands(),
        "safe_paths": executor.safe_paths
    }


@router.post("/execute")
async def execute_command(request: ExecuteCommandRequest):
    """
    Execute a safe command.

    The command must be in the whitelist and pass security validation.
    """
    executor = get_safe_executor()

    result = await executor.execute(
        command=request.command,
        working_dir=request.working_dir,
        timeout=request.timeout
    )

    if result.error and "blocked" in result.error.lower():
        raise HTTPException(
            status_code=403,
            detail=result.error
        )

    return {
        "success": result.success,
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_seconds": result.duration_seconds,
        "truncated": result.truncated,
        "error": result.error
    }


@router.get("/history")
async def get_command_history(limit: int = 20):
    """
    Get recent command execution history.
    """
    executor = get_safe_executor()

    return {
        "history": executor.get_execution_history(limit=limit),
        "total_commands": len(executor.execution_history)
    }


@router.post("/validate")
async def validate_command(request: ExecuteCommandRequest):
    """
    Validate a command without executing it.

    Returns whether the command would be allowed.
    """
    executor = get_safe_executor()

    is_valid, error = executor.validate_command(request.command)

    return {
        "command": request.command,
        "valid": is_valid,
        "error": error if not is_valid else None
    }
