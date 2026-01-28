"""
Darwin System - Main application entry point

This is a slim entrypoint that delegates to the modular app structure:
- app/factory.py: Application creation
- app/lifespan.py: Startup/shutdown lifecycle
- app/routes.py: Route registration
- initialization/: Phased service initialization
"""

import os


def main():
    """Run the Darwin application"""
    import uvicorn
    from app import create_app

    # Create the application
    app = create_app()

    # Get port from environment or use default
    port = int(os.getenv("PORT", "8000"))

    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


# For uvicorn direct import (uvicorn main:app)
def get_app():
    """Get the application instance for uvicorn"""
    from app import create_app
    return create_app()


# Create app instance for direct uvicorn usage
app = get_app()


if __name__ == "__main__":
    main()
