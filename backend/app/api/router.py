"""
Main API router - Aggregates all endpoint routes
"""

from fastapi import APIRouter

from .endpoints import projects, audio, generation, user, suno_webhook

router = APIRouter(prefix="/api/v1")

router.include_router(user.router,          prefix="/users",      tags=["users"])
router.include_router(projects.router,      prefix="/projects",   tags=["projects"])
router.include_router(audio.router,         prefix="/audio",      tags=["audio"])
router.include_router(generation.router,    prefix="/generation", tags=["generation"])
router.include_router(suno_webhook.router,  prefix="/suno",       tags=["suno"])

__all__ = ["router"]
