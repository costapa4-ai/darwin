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

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates"""
        await manager.connect(websocket)

        try:
            while True:
                data = await websocket.receive_text()
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
