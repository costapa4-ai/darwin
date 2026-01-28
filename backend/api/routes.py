"""API routes for Darwin System"""
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from core.evolution import EvolutionEngine
from services.metrics import MetricsService
from api.websocket import manager
from utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


# Request/Response models
class TaskCreate(BaseModel):
    description: str
    type: str = "algorithm"
    parameters: dict = {}


class TaskResponse(BaseModel):
    id: str
    description: str
    type: str
    status: str
    created_at: str


class ConfigUpdate(BaseModel):
    ai_provider: Optional[str] = None
    max_generations: Optional[int] = None
    population_size: Optional[int] = None


# Global instances (will be injected in main.py)
evolution_engine: Optional[EvolutionEngine] = None
metrics_service: Optional[MetricsService] = None
active_tasks = {}


def set_services(evolution: EvolutionEngine, metrics: MetricsService):
    """Set service instances"""
    global evolution_engine, metrics_service
    evolution_engine = evolution
    metrics_service = metrics


@router.post("/api/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Create new task for the system to solve"""
    task_id = str(uuid.uuid4())

    task_data = {
        'id': task_id,
        'description': task.description,
        'type': task.type,
        'parameters': task.parameters,
        'status': 'pending',
        'created_at': None
    }

    active_tasks[task_id] = task_data

    logger.info("Task created", extra={
        "task_id": task_id,
        "description": task.description,
        "type": task.type
    })

    # Broadcast task creation
    await manager.broadcast({
        'type': 'task_created',
        'data': {
            'task_id': task_id,
            'description': task.description,
            'type': task.type
        }
    })

    # Start evolution in background
    background_tasks.add_task(run_evolution, task_data)

    from datetime import datetime
    task_data['created_at'] = datetime.now().isoformat()

    return TaskResponse(**task_data)


async def run_evolution(task: dict):
    """Run evolution process for a task"""
    task_id = task['id']

    try:
        active_tasks[task_id]['status'] = 'running'

        # Evolution callback for progress updates
        async def evolution_callback(event: dict):
            await manager.broadcast(event)

        # Run evolution
        result = await evolution_engine.evolve_task(
            task,
            max_generations=5,
            population_size=3,
            callback=evolution_callback
        )

        active_tasks[task_id]['status'] = 'completed'
        active_tasks[task_id]['result'] = result

        await manager.broadcast({
            'type': 'task_completed',
            'data': {
                'task_id': task_id,
                'best_fitness': result['best_fitness']
            }
        })

    except Exception as e:
        logger.error(f"Evolution error: {e}", extra={"task_id": task_id})
        active_tasks[task_id]['status'] = 'failed'
        active_tasks[task_id]['error'] = str(e)

        await manager.broadcast({
            'type': 'task_failed',
            'data': {
                'task_id': task_id,
                'error': str(e)
            }
        })


@router.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and results"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    return active_tasks[task_id]


@router.get("/api/tasks")
async def list_tasks():
    """List all tasks"""
    return {
        'tasks': list(active_tasks.values()),
        'total': len(active_tasks)
    }


@router.get("/api/generations/{task_id}")
async def get_generations(task_id: str):
    """Get all generations for a task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = active_tasks[task_id]

    if 'result' not in task:
        return {'generations': [], 'status': task['status']}

    return {
        'generations': task['result'].get('generations', []),
        'best_solution': task['result'].get('best_solution'),
        'best_fitness': task['result'].get('best_fitness')
    }


@router.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    if not metrics_service:
        return {'error': 'Metrics service not available'}

    return metrics_service.get_system_metrics()


@router.post("/api/config")
async def update_config(config: ConfigUpdate):
    """Update system configuration"""
    # For MVP, just return success
    # In production, this would update settings
    logger.info("Configuration update requested", extra=config.dict(exclude_unset=True))

    return {
        'status': 'success',
        'message': 'Configuration updated (MVP: changes not persisted)'
    }


@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'service': 'darwin-backend',
        'version': '1.0.0'
    }
