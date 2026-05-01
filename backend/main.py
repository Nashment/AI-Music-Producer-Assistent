"""
FastAPI Application Factory
"""

import logging
import logging.config
import sys
from pathlib import Path

# Ensure `app` package is importable when running from project root
# (e.g. `uvicorn backend.main:app --reload`).
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.error_handlers import configure_error_handlers
from app.api.router import router
from app.data.database import db

# ---------------------------------------------------------------------------
# Logging
# Formato estruturado com nível, logger, trace_id e mensagem.
# Em produção podes trocar o handler por um JSON formatter (python-json-logger).
# ---------------------------------------------------------------------------
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG" if settings.DEBUG else "INFO",
        "handlers": ["console"],
    },
    # Reduz ruído de libs externas em produção
    "loggers": {
        "uvicorn":        {"level": "INFO",    "propagate": True},
        "uvicorn.access": {"level": "WARNING", "propagate": True},
        "sqlalchemy":     {"level": "WARNING", "propagate": True},
        "celery":         {"level": "INFO",    "propagate": True},
        "music_ai":       {"level": "DEBUG",   "propagate": True},
    },
})


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application
    
    Returns:
        Configured FastAPI instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered music production assistant API",
        debug=settings.DEBUG
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers — RFC 7807 Problem Details (antes das rotas)
    configure_error_handlers(app)

    # Include API routes
    app.include_router(router)

    # Lifespan events
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup"""
        await db.init_db()
        health = await db.health_check()
        if health:
            print("Database connection established")
        else:
            print("Database connection failed")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        await db.close_db()

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint"""
        db_health = await db.health_check()
        return {
            "status": "healthy" if db_health else "unhealthy",
            "version": settings.APP_VERSION,
            "database": "connected" if db_health else "disconnected"
        }

    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
