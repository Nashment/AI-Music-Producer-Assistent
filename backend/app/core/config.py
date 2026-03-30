"""
Configuration module for the application
"""

import os
from functools import lru_cache
from typing import Optional


class Settings:
    """
    Application settings and configuration
    """

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/music_ai_db"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() == "true"

    # Application Configuration
    APP_NAME: str = "Musical AI Production Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # API Configuration
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # AI and Model Configuration
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    SUNO_API_KEY: Optional[str] = os.getenv("SUNO_API_KEY")
    
    # Audio Processing Configuration
    AUDIO_UPLOAD_DIR: str = os.path.join(
        os.path.dirname(__file__),
        "../../generations/audio/"
    )
    PARTITURA_OUTPUT_DIR: str = os.path.join(
        os.path.dirname(__file__),
        "../../generations/partitura/"
    )
    TABLATURA_OUTPUT_DIR: str = os.path.join(
        os.path.dirname(__file__),
        "../../generations/tablatura/"
    )

    # Audio Processing Parameters
    SAMPLE_RATE: int = 44100
    MAX_AUDIO_DURATION: int = 300  # seconds
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Worker Configuration
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/0"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()


settings = get_settings()
