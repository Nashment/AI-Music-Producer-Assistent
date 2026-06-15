"""
Configuration module for the application
"""

import os
from functools import lru_cache
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Carregar .env da pasta backend
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

# Raiz do backend (backend/) — usada nos defaults de paths
_BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    """
    Application settings and configuration.
    Ponto único de verdade para todas as variáveis de ambiente.
    """

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "Musical AI Production Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/music_ai_db"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() == "true"

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # ------------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------------
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI")

    # ------------------------------------------------------------------
    # Cloudflare R2 Storage
    # ------------------------------------------------------------------
    R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
    R2_BUCKET_NAME: str = os.getenv("R2_BUCKET_NAME", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_ENDPOINT_URL: str = os.getenv(
        "R2_ENDPOINT_URL",
        "https://" + os.getenv("R2_ACCOUNT_ID", "") + ".r2.cloudflarestorage.com"
    )
    R2_PRESIGNED_URL_EXPIRY: int = 3600  # segundos (1 hora)

    # ------------------------------------------------------------------
    # Suno AI
    # ------------------------------------------------------------------
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY")
    SUNO_API_KEY: Optional[str] = os.getenv("SUNO_API_KEY")
    # URL publica do backend para o Suno notificar quando a task termina.
    # Se vazio, o worker usa polling em vez de callbacks.
    SUNO_CALLBACK_URL: str = os.getenv("SUNO_CALLBACK_URL", "")

    # ------------------------------------------------------------------
    # Worker (Celery + Redis)
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # ------------------------------------------------------------------
    # Directorias de ficheiros
    # ------------------------------------------------------------------
    AUDIO_UPLOAD_DIR: str = os.getenv(
        "AUDIO_UPLOAD_DIR",
        str(_BACKEND_ROOT / "worker" / "uploads" / "audio")
    )

    _DEFAULT_GENERATIONS_ROOT = str(_BACKEND_ROOT / "worker" / "generations")
    GENERATIONS_AUDIO_DIR: str = os.getenv(
        "GENERATIONS_AUDIO_DIR",
        str(_BACKEND_ROOT / "worker" / "generations" / "audio")
    )
    GENERATIONS_PARTITURA_DIR: str = os.getenv(
        "GENERATIONS_PARTITURA_DIR",
        str(_BACKEND_ROOT / "worker" / "generations" / "partitura")
    )
    GENERATIONS_TABLATURA_DIR: str = os.getenv(
        "GENERATIONS_TABLATURA_DIR",
        str(_BACKEND_ROOT / "worker" / "generations" / "tablatura")
    )

    # ------------------------------------------------------------------
    # Paths de executáveis externos (com defaults por OS)
    # ------------------------------------------------------------------
    LILYPOND_PATH: str = os.getenv(
        "LILYPOND_PATH",
        r"C:\Program Files\LilyPond\lilypond-2.24.4\bin\lilypond.exe" if os.name == "nt"
        else "/usr/bin/lilypond"
    )
    MUSESCORE_PATH: str = os.getenv(
        "MUSESCORE_PATH",
        r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe" if os.name == "nt"
        else "/usr/bin/mscore3"
    )

    # ------------------------------------------------------------------
    # Audio Processing Parameters
    # ------------------------------------------------------------------
    SAMPLE_RATE: int = 44100
    MAX_AUDIO_DURATION: int = 300  # segundos
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()


settings = get_settings()
