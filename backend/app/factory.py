"""
Application Factory - Creates and configures the FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.lifespan import lifespan
from app.routes import register_all_routes


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Darwin System API",
        description="Sistema de evolucao autonoma de codigo com Multi-Agent, Dream Mode e Curiosidade",
        version="3.0.0",
        lifespan=lifespan
    )

    # CORS middleware - allow all frontend access methods
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3050",
            "http://localhost:3051",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://127.0.0.1:3050",
            "http://127.0.0.1:3051",
            "http://127.0.0.1:5175",
            "http://192.168.1.117:3050",
            "http://192.168.1.117:3051",
            "http://192.168.1.117:5173",
            "http://192.168.1.117:5174",
            "http://192.168.1.117:5175",
            "http://myserver.local:3050",
            "http://myserver.local:3051",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register all routes
    register_all_routes(app)

    return app
