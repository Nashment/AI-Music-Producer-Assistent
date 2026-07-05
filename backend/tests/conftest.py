"""
Pytest configuration and fixtures.

Fornece a sessão de DB usada pelos testes:
  - async_db_session     : AsyncSession SQLite+aiosqlite (para testar serviços reais)

Mocks reutilizáveis:
  - mock_storage         : StorageService totalmente simulado
  - mock_celery_task     : AsyncResult simulado para tarefas Celery
"""

import os

# Tem de ser definido ANTES de qualquer `from app...` (mesmo indiretamente,
# via outro ficheiro de teste importado primeiro pelo pytest) importar
# `app.core.config`, porque `settings` ali e um singleton com `@lru_cache`:
# uma vez construido, fica com o valor que a env var tinha nesse instante
# para o resto da sessao de testes. Se isto estivesse so em
# test_user_service.py, a ordem de recolha do pytest (alfabetica --
# test_audio_service.py vem primeiro) importava `app.core.config` antes
# desta linha correr, e `UserService()` rebentava com "JWT_SECRET_KEY nao
# esta definida" mesmo esta linha existindo algures. Por estar aqui, o
# conftest.py e sempre carregado antes de qualquer modulo de teste do
# directorio, garantindo a ordem certa.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")

import uuid
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

from app.data import UserQueries, ProjectQueries, AudioQueries, GenerationQueries
from app.data.models import Base, GenerationStatusEnum, User, Project, AudioFile, Generation


# ---------------------------------------------------------------------------
# AsyncSession (SQLite + aiosqlite) — para serviços e queries reais
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def async_db_session() -> AsyncSession:
    """
    AsyncSession respaldada por SQLite em memória.
    Cria o schema antes de cada teste e descarta após.
    Requer: pip install aiosqlite
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Factories de entidades de domínio
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_user(async_db_session: AsyncSession) -> User:
    """Utilizador de teste persistido na DB."""

    return await UserQueries.create_user(
        db=async_db_session,
        username="testuser",
        oauth_provider="google",
        oauth_id="google_test_001",
    )


@pytest_asyncio.fixture
async def db_project(async_db_session: AsyncSession, db_user: User) -> Project:
    """Projeto de teste persistido na DB."""
    return await ProjectQueries.create_project(
        db=async_db_session,
        user_id=db_user.id,
        title="Projecto de Teste",
        description="Desc",
        tempo=120,
    )


@pytest_asyncio.fixture
async def db_audio(async_db_session: AsyncSession, db_user: User, db_project: Project) -> AudioFile:
    """AudioFile de teste persistido na DB."""
    return await AudioQueries.create_audio_file(
        db=async_db_session,
        user_id=db_user.id,
        project_id=db_project.id,
        storage_key="audio/test-audio.wav",
        file_size=1024 * 512,
        duration=30.0,
        sample_rate=44100,
        bpm=120,
        key="C major",
    )


@pytest_asyncio.fixture
async def db_generation(
    async_db_session: AsyncSession,
    db_user: User,
    db_project: Project,
    db_audio: AudioFile,
) -> Generation:
    """Generation de teste (completed, com audio_storage_key) persistida na DB."""
    return await GenerationQueries.create_generation(
        db=async_db_session,
        user_id=db_user.id,
        project_id=db_project.id,
        audio_file_id=db_audio.id,
        prompt="Guitarra clássica",
        instrument="guitarra",
        genre="classical",
        duration=30,
        status=GenerationStatusEnum.COMPLETED,
        audio_storage_key="generations/test-gen.mp3",
    )


# ---------------------------------------------------------------------------
# Mock de StorageService
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_storage():
    """
    Substitui o singleton `storage` em app.services.storage_service.
    Todos os métodos devolvem valores de sucesso por defeito.
    """
    with patch("app.services.generation_service.storage") as mock:
        mock.delete_file.return_value = True
        mock.upload_file.return_value = True
        mock.download_file.return_value = True
        mock.get_presigned_url.return_value = "https://r2.example.com/presigned/test.pdf?token=abc"
        yield mock


# ---------------------------------------------------------------------------
# Mock de Celery task dispatch
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tablature_task():
    """Mock para generate_tablature_task.apply_async (fire-and-forget)."""
    with patch("app.services.generation_service.GenerationService.request_tablature.__wrapped__",
               create=True):
        task_mock = MagicMock()
        task_mock.apply_async.return_value = MagicMock(id="celery-task-id-tab-001")
        with patch(
            "worker.tasks.generation_tasks.generate_tablature_task",
            task_mock,
        ):
            yield task_mock


@pytest.fixture
def mock_partitura_task():
    """Mock para generate_partitura_task.apply_async (fire-and-forget)."""
    task_mock = MagicMock()
    task_mock.apply_async.return_value = MagicMock(id="celery-task-id-part-001")
    with patch(
        "worker.tasks.generation_tasks.generate_partitura_task",
        task_mock,
    ):
        yield task_mock


# ---------------------------------------------------------------------------
# Dados de teste estáticos
# ---------------------------------------------------------------------------

@pytest.fixture
def test_generation_params():
    return {
        "prompt": "Guitarra clássica suave",
        "instrument": "guitarra",
        "genre": "classical",
        "duration": 30,
    }
