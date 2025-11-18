"""
FastAPI Application Entry Point

This module initializes the FastAPI application with all routes,
middleware, and startup/shutdown events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import metadata, generate, search, health, agents
from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Multi-Agentic Solution for DDL & Synthetic Data Generation",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(metadata.router, prefix="/api/v1/metadata", tags=["Metadata"])
    app.include_router(generate.router, prefix="/api/v1/generate", tags=["Generate"])
    app.include_router(search.router, prefix="/api/v1/search", tags=["Search"])
    app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])

    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger.info(f"Starting {settings.APP_NAME}")
        # TODO: Initialize database connections, OpenSearch, Redis

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info(f"Shutting down {settings.APP_NAME}")
        # TODO: Close database connections, OpenSearch, Redis

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
