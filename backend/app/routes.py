"""
Route Registration - Centralized route configuration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from api.routes import router
from api import phase2_routes
from api import phase3_routes
from api import introspection_routes
from api import error_routes
from api import auto_correction_routes
from api import consciousness_routes
from api import context_routes
from api import mood_routes
from api import question_routes
from api import memory_routes
from api import inquiry_routes
from api import cost_routes
from api import findings_routes
from api import command_routes
from api import existential_routes
from api import diary_routes
from api import expedition_routes
from api import learning_routes
from api import channel_routes
from api import financial_routes
from api import hooks_routes
from api import ui_automation_routes
from api import voice_routes
from api import distributed_routes
from api import moltbook_routes
from api import monitor_routes
from api import language_evolution_routes
from api import observatory_routes
from api import genome_routes
from api import export_routes
from api.websocket import manager
from utils.logger import setup_logger

logger = setup_logger(__name__)


def register_all_routes(app: FastAPI):
    """
    Register all API routes on the application.

    Args:
        app: FastAPI application instance
    """
    # Core routes
    app.include_router(router)

    # Phase 2 routes
    app.include_router(phase2_routes.router)

    # Phase 3 routes
    app.include_router(phase3_routes.router)

    # Introspection & Error routes
    app.include_router(introspection_routes.router)
    app.include_router(error_routes.router)
    app.include_router(auto_correction_routes.router)

    # Consciousness & Personality routes
    app.include_router(consciousness_routes.router)
    app.include_router(inquiry_routes.router)
    app.include_router(context_routes.router)
    app.include_router(mood_routes.router)
    app.include_router(question_routes.router)
    app.include_router(memory_routes.router)

    # Cost tracking routes
    app.include_router(cost_routes.router)

    # Findings Inbox routes
    app.include_router(findings_routes.router)

    # Safe Command Execution routes
    app.include_router(command_routes.router)

    # Existential/Philosophical routes
    app.include_router(existential_routes.router)

    # Diary routes
    app.include_router(diary_routes.router)

    # Curiosity Expedition routes
    app.include_router(expedition_routes.router)

    # Learning System routes
    app.include_router(learning_routes.router)

    # Channel Gateway routes
    app.include_router(channel_routes.router)

    # Financial Consciousness routes
    app.include_router(financial_routes.router)

    # Hooks System routes
    app.include_router(hooks_routes.router)

    # UI Automation routes
    app.include_router(ui_automation_routes.router)

    # Voice Synthesis routes
    app.include_router(voice_routes.router)

    # Distributed Consciousness routes
    app.include_router(distributed_routes.router)

    # Moltbook Integration routes
    app.include_router(moltbook_routes.router)

    # Activity Monitor routes
    app.include_router(monitor_routes.router)

    # Language Evolution routes
    app.include_router(language_evolution_routes.router)

    # Observatory Dashboard routes
    app.include_router(observatory_routes.router)

    # Genome & Identity routes
    app.include_router(genome_routes.router)

    # Data Export routes
    app.include_router(export_routes.router)

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        import json
        await manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    # Handle pong response from client
                    if message.get('type') == 'pong':
                        manager.handle_pong(websocket)
                    else:
                        logger.info(f"WebSocket message received: {data}")
                except json.JSONDecodeError:
                    logger.info(f"WebSocket message received: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            manager.disconnect(websocket)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with system status"""
        from app.lifespan import get_system_status
        return get_system_status()
