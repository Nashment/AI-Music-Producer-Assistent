"""
FastAPI Application Factory
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.api.router import router
from backend.app.data.database import db


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

    # Include API routes
    app.include_router(router)

    # Lifespan events
    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup"""
        await db.init_db()
        health = await db.health_check()
        if health:
            print("✓ Database connection established")
        else:
            print("✗ Database connection failed")

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
