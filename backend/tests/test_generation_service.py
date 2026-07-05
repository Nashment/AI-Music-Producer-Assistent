"""
Testes para GenerationService e GenerationQueries.

Cobre:
  submit_generation     — enfileira Celery, cria registo, ownership
  get_generation        — ownership, inexistente
  list_generations_for_audio / list_cuts_for_generation
  get_generation_audio_url — presigned URL, sem chave
  cut_generation        — cria corte, intervalo inválido, sem áudio
  delete_generation     — limpa R2 + DB (coberto também em test_notation_service)
  GenerationQueries     — create, get, list_by_audio, list_cuts, update_status
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.data.models import GenerationStatusEnum, Generation
from app.domain.result import Sucesso, Falha
from app.domain.errors.generation_errors import (
    AudioNaoEncontrado,
    GeracaoNaoEncontrada,
    FicheiroGeracaoIndisponivel,
    IntervaloCorteInvalido,
    FilaIndisponivel,
    WorkerIndisponivel,
)
from app.services.generation_service import GenerationService


# ---------------------------------------------------------------------------
# submit_generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSubmitGeneration:

    async def test_submit_creates_pending_record(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: registo criado com status PENDING e task Celery enfileirada."""
        task_mock = MagicMock()
        task_mock.apply_async.return_value = MagicMock(id="celery-fake-001")

        with patch(
            "worker.tasks.generation_tasks.process_generation_task",
            task_mock,
            create=True,
        ):
            svc = GenerationService(async_db_session)
            result = await svc.submit_generation(
                user_id=str(db_user.id),
                project_id=db_project.id,
                audio_id=db_audio.id,
                prompt="Guitarra rock",
                instrument="guitarra",
                genre="rock",
                duration=30,
                tempo_override=None,
            )

        assert isinstance(result, Sucesso)
        gen, celery_id = result.valor
        assert gen.status == GenerationStatusEnum.PENDING
        assert gen.prompt == "Guitarra rock"
        task_mock.apply_async.assert_called_once()

    async def test_submit_fails_if_audio_not_found(
        self, async_db_session, db_user, db_project
    ):
        """Assert: audio_id inexistente → Falha(AudioNaoEncontrado)."""
        svc = GenerationService(async_db_session)
        result = await svc.submit_generation(
            user_id=str(db_user.id),
            project_id=db_project.id,
            audio_id=uuid.uuid4(),
            prompt="Teste",
            instrument="piano",
            genre=None,
            duration=None,
            tempo_override=None,
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)

    async def test_submit_fails_if_audio_wrong_user(
        self, async_db_session, db_project, db_audio
    ):
        """Assert: audio de outro utilizador → Falha(AudioNaoEncontrado)."""
        svc = GenerationService(async_db_session)
        result = await svc.submit_generation(
            user_id=str(uuid.uuid4()),
            project_id=db_project.id,
            audio_id=db_audio.id,
            prompt="Teste",
            instrument="piano",
            genre=None,
            duration=None,
            tempo_override=None,
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)

    async def test_submit_fails_if_celery_unavailable(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: Celery indisponível → Falha(FilaIndisponivel)."""
        task_mock = MagicMock()
        task_mock.apply_async.side_effect = Exception("Redis down")

        with patch(
            "worker.tasks.generation_tasks.process_generation_task",
            task_mock,
            create=True,
        ):
            svc = GenerationService(async_db_session)
            result = await svc.submit_generation(
                user_id=str(db_user.id),
                project_id=db_project.id,
                audio_id=db_audio.id,
                prompt="Teste",
                instrument="piano",
                genre=None,
                duration=None,
                tempo_override=None,
            )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, FilaIndisponivel)


# ---------------------------------------------------------------------------
# get_generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetGeneration:

    async def test_get_generation_success(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: devolve Sucesso com a geração correcta."""
        svc = GenerationService(async_db_session)
        result = await svc.get_generation(str(db_generation.id), str(db_user.id))
        assert isinstance(result, Sucesso)
        assert result.valor.id == db_generation.id

    async def test_get_generation_wrong_user(
        self, async_db_session, db_generation
    ):
        """Assert: user_id errado → Falha(GeracaoNaoEncontrada)."""
        svc = GenerationService(async_db_session)
        result = await svc.get_generation(str(db_generation.id), str(uuid.uuid4()))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)

    async def test_get_generation_nonexistent(self, async_db_session, db_user):
        """Assert: UUID inexistente → Falha(GeracaoNaoEncontrada)."""
        svc = GenerationService(async_db_session)
        result = await svc.get_generation(str(uuid.uuid4()), str(db_user.id))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)


# ---------------------------------------------------------------------------
# list_generations_for_audio / list_cuts_for_generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestListGenerations:

    async def test_list_generations_for_audio(
        self, async_db_session, db_user, db_project, db_audio, db_generation
    ):
        """Assert: lista contém a geração root do áudio."""
        svc = GenerationService(async_db_session)
        result = await svc.list_generations_for_audio(db_audio.id, str(db_user.id))
        assert isinstance(result, Sucesso)
        ids = [g.id for g in result.valor]
        assert db_generation.id in ids

    async def test_list_generations_wrong_user(
        self, async_db_session, db_audio
    ):
        """Assert: áudio de outro utilizador → Falha(AudioNaoEncontrado)."""
        svc = GenerationService(async_db_session)
        result = await svc.list_generations_for_audio(db_audio.id, str(uuid.uuid4()))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)

    async def test_list_cuts_for_generation(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: lista de cortes de uma geração sem cortes está vazia."""
        svc = GenerationService(async_db_session)
        result = await svc.list_cuts_for_generation(str(db_generation.id), str(db_user.id))
        assert isinstance(result, Sucesso)
        assert result.valor == []

    async def test_list_cuts_shows_child_generations(
        self, async_db_session, db_user, db_project, db_audio, db_generation
    ):
        """Assert: corte criado aparece na lista de cortes da geração pai."""
        from app.data.queries import GenerationQueries
        cut = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Corte 0-15s",
            instrument="guitarra",
            parent_generation_id=db_generation.id,
            status=GenerationStatusEnum.COMPLETED,
            audio_storage_key="generations/cut.wav",
        )
        svc = GenerationService(async_db_session)
        result = await svc.list_cuts_for_generation(str(db_generation.id), str(db_user.id))
        assert isinstance(result, Sucesso)
        assert any(c.id == cut.id for c in result.valor)


# ---------------------------------------------------------------------------
# get_generation_audio_url
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetGenerationAudioUrl:

    async def test_returns_presigned_url(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: devolve URL presigned do R2."""
        presigned = "https://r2.example.com/gen.mp3?token=x"
        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = presigned
            svc = GenerationService(async_db_session)
            result = await svc.get_generation_audio_url(
                str(db_generation.id), str(db_user.id)
            )
        assert isinstance(result, Sucesso)
        assert result.valor == presigned

    async def test_fails_when_no_audio_key(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: geração sem audio_storage_key → Falha(FicheiroGeracaoIndisponivel)."""
        from app.data.queries import GenerationQueries
        gen_sem_audio = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Sem áudio",
            instrument="guitarra",
            status=GenerationStatusEnum.PENDING,
        )
        svc = GenerationService(async_db_session)
        result = await svc.get_generation_audio_url(
            str(gen_sem_audio.id), str(db_user.id)
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroGeracaoIndisponivel)


# ---------------------------------------------------------------------------
# cut_generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCutGeneration:

    async def test_cut_invalid_interval_start_negative(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: inicio < 0 → Falha(IntervaloCorteInvalido)."""
        svc = GenerationService(async_db_session)
        result = await svc.cut_generation(
            parent_generation_id=str(db_generation.id),
            user_id=str(db_user.id),
            inicio_segundos=-1.0,
            fim_segundos=10.0,
            output_dir="/tmp",
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloCorteInvalido)

    async def test_cut_invalid_interval_end_before_start(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: fim <= inicio → Falha(IntervaloCorteInvalido)."""
        svc = GenerationService(async_db_session)
        result = await svc.cut_generation(
            parent_generation_id=str(db_generation.id),
            user_id=str(db_user.id),
            inicio_segundos=20.0,
            fim_segundos=10.0,
            output_dir="/tmp",
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloCorteInvalido)

    async def test_cut_exceeds_max_window(
        self, async_db_session, db_user, db_generation
    ):
        """Assert: janela > 45s → Falha(IntervaloCorteInvalido)."""
        svc = GenerationService(async_db_session)
        result = await svc.cut_generation(
            parent_generation_id=str(db_generation.id),
            user_id=str(db_user.id),
            inicio_segundos=0.0,
            fim_segundos=60.0,
            output_dir="/tmp",
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloCorteInvalido)

    async def test_cut_fails_without_audio_key(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: geração pai sem audio_storage_key → Falha(FicheiroGeracaoIndisponivel)."""
        from app.data.queries import GenerationQueries
        gen_sem_audio = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Sem áudio",
            instrument="guitarra",
            status=GenerationStatusEnum.COMPLETED,
        )
        svc = GenerationService(async_db_session)
        result = await svc.cut_generation(
            parent_generation_id=str(gen_sem_audio.id),
            user_id=str(db_user.id),
            inicio_segundos=0.0,
            fim_segundos=10.0,
            output_dir="/tmp",
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroGeracaoIndisponivel)


# ---------------------------------------------------------------------------
# GenerationQueries directas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGenerationQueries:

    async def test_create_generation(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: registo criado com campos correctos."""
        from app.data.queries import GenerationQueries
        gen = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Piano jazz",
            instrument="piano",
            genre="jazz",
            duration=60,
        )
        assert gen.id is not None
        assert gen.prompt == "Piano jazz"
        assert gen.status == GenerationStatusEnum.PENDING

    async def test_get_generation_by_id(
        self, async_db_session, db_generation
    ):
        """Assert: get_generation devolve o registo pelo UUID."""
        from app.data.queries import GenerationQueries
        found = await GenerationQueries.get_generation(
            db=async_db_session, generation_id=str(db_generation.id)
        )
        assert found is not None
        assert found.id == db_generation.id

    async def test_update_generation_status_completed(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: update_generation_status persiste status e audio_key."""
        from app.data.queries import GenerationQueries
        gen = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Teste status",
            instrument="guitarra",
        )
        updated = await GenerationQueries.update_generation_status(
            db=async_db_session,
            generation_id=str(gen.id),
            status=GenerationStatusEnum.COMPLETED,
            audio_key="generations/test-audio.mp3",
        )
        assert updated.status == GenerationStatusEnum.COMPLETED
        assert updated.audio_storage_key == "generations/test-audio.mp3"
        assert updated.completed_at is not None

    async def test_update_generation_status_failed(
        self, async_db_session, db_generation
    ):
        """Assert: update_generation_status persiste FAILED e error_message."""
        from app.data.queries import GenerationQueries
        updated = await GenerationQueries.update_generation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            status=GenerationStatusEnum.FAILED,
            error_message="Suno timeout",
        )
        assert updated.status == GenerationStatusEnum.FAILED
        assert "timeout" in updated.error_message

    async def test_list_generations_by_audio_only_roots(
        self, async_db_session, db_user, db_project, db_audio, db_generation
    ):
        """Assert: only_roots=True exclui cortes."""
        from app.data.queries import GenerationQueries
        # Criar corte (filho)
        await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Corte",
            instrument="guitarra",
            parent_generation_id=db_generation.id,
            status=GenerationStatusEnum.COMPLETED,
        )
        roots = await GenerationQueries.list_generations_by_audio(
            db=async_db_session, audio_file_id=db_audio.id, only_roots=True
        )
        # Apenas a geração root — o corte é excluído
        assert all(g.parent_generation_id is None for g in roots)

    async def test_delete_generation(self, async_db_session, db_generation):
        """Assert: delete_generation remove o registo."""
        from app.data.queries import GenerationQueries
        ok = await GenerationQueries.delete_generation(
            db=async_db_session, generation_id=str(db_generation.id)
        )
        assert ok is True
        found = await GenerationQueries.get_generation(
            db=async_db_session, generation_id=str(db_generation.id)
        )
        assert found is None
