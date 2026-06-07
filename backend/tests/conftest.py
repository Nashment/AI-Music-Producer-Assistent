"""
Pytest configuration and fixtures.

Fornece dois níveis de DB para os testes:
  - test_db_session      : sessão síncrona SQLite (legada, para testes simples)
  - async_db_session     : AsyncSession SQLite+aiosqlite (para testar serviços reais)

Mocks reutilizáveis:
  - mock_storage         : StorageService totalmente simulado
  - mock_celery_task     : AsyncResult simulado para tarefas Celery
"""

import uuid
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

from app.data import UserQueries, ProjectQueries, AudioQueries, GenerationQueries
from app.data.models import Base, GenerationStatusEnum, User, Project, AudioFile, Generation


# ---------------------------------------------------------------------------
# Sessão síncrona (retrocompatibilidade com testes legados)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Session:
    TestingSessionLocal = sessionmaker(bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.rollback()
    session.close()


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
