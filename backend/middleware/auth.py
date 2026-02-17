"""
API Key Authentication Middleware

Validates requests against DARWIN_API_KEY environment variable.
If DARWIN_API_KEY is not set, all requests are allowed (development mode).
"""

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# Paths that never require authentication
PUBLIC_PATHS = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# Path prefixes that never require authentication
PUBLIC_PREFIXES = (
    "/api/v1/health",
)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates API key from X-API-Key header.

    Behavior:
    - If DARWIN_API_KEY env var is not set: all requests allowed (dev mode)
    - If DARWIN_API_KEY is set: requires matching X-API-Key header
    - Health/docs endpoints are always public
    - WebSocket connections check via query param ?api_key=
    """

    async def dispatch(self, request: Request, call_next):
        # Always allow public paths
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return await call_next(request)

        # Check if auth is configured
        expected_key = os.environ.get("DARWIN_API_KEY")
        if not expected_key:
            # No key configured = development mode, allow all
            return await call_next(request)

        # WebSocket: check query param
        if path.startswith("/ws"):
            api_key = request.query_params.get("api_key")
        else:
            # HTTP: check header
            api_key = request.headers.get("X-API-Key")

        if api_key != expected_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)
