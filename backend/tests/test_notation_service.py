"""
Testes de integração para os novos métodos de notação assíncrona
em GenerationService:

  request_tablature   — fire-and-forget; enfileira Celery sem bloquear
  request_partitura   — idem para partitura
  get_tablature_url   — devolve presigned URL do R2
  get_partitura_url   — idem para partitura
  delete_generation   — apaga DB + todos os ficheiros R2 (incl. notações)

Todos os testes usam mocks para Celery e StorageService —
nenhuma chamada real à cloud ou ao broker.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.data.models import Generation, GenerationStatusEnum
from app.domain.result import Sucesso, Falha
from app.domain.errors.generation_errors import (
    GeracaoNaoEncontrada,
    FicheiroGeracaoIndisponivel,
    FilaIndisponivel,
)
from app.services.generation_service import GenerationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_celery_task_mock():
    """Mock de uma Celery task com apply_async (fire-and-forget)."""
    task = MagicMock()
    task.apply_async.return_value = MagicMock(id="celery-fake-id")
    return task


# ===========================================================================
# request_tablature
# ===========================================================================

@pytest.mark.asyncio
class TestRequestTablature:

    async def test_returns_202_with_pending_status(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Arrange: geração completed com audio_storage_key.
        Act: request_tablature.
        Assert: devolve Sucesso com tablatura_status='pending'; task enfileirada."""
        task_mock = _make_celery_task_mock()

        with patch("app.services.generation_service.storage") as mock_storage, \
             patch(
                 "worker.tasks.generation_tasks.generate_tablature_task",
                 task_mock,
                 create=True,
             ):
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            result = await service.request_tablature(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        # Assert
        assert isinstance(result, Sucesso)
        assert result.valor.tablatura_status == "pending"
        # Celery foi chamado sem .get() — fire-and-forget
        task_mock.apply_async.assert_called_once()
        # Não bloqueou à espera do resultado (fire-and-forget de facto).
        #
        # Nota: a asserção original era `assert not hasattr(..., "get_called")`,
        # que nunca poderia falhar -- um MagicMock cria automaticamente
        # qualquer atributo que lhe seja acedido (inclusive um chamado
        # "get_called", que nunca existiu), por isso `hasattr` devolve sempre
        # True e o teste "passava" sem verificar nada. O que se quer
        # verificar de facto é que `.get()` nunca foi chamado no AsyncResult.
        task_mock.apply_async.return_value.get.assert_not_called()

    async def test_deletes_old_r2_key_on_regeneration(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: se tablatura_storage_key já existe, storage.delete_file é chamado."""
        # Pre-popular tablatura na geração
        from app.data.queries import GenerationQueries
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="completed",
            storage_key=f"tablature/{db_generation.id}.pdf",
        )

        task_mock = _make_celery_task_mock()

        with patch("app.services.generation_service.storage") as mock_storage, \
             patch(
                 "worker.tasks.generation_tasks.generate_tablature_task",
                 task_mock,
                 create=True,
             ):
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            await service.request_tablature(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

            # Assert: chave anterior foi apagada do R2
            mock_storage.delete_file.assert_called_once_with(
                f"tablature/{db_generation.id}.pdf"
            )

    async def test_fails_if_generation_not_found(
        self, async_db_session, db_user
    ):
        """Assert: generation_id inexistente devolve Falha(GeracaoNaoEncontrada)."""
        service = GenerationService(async_db_session)
        result = await service.request_tablature(
            generation_id=str(uuid.uuid4()),
            user_id=str(db_user.id),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)

    async def test_fails_if_wrong_user(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: user_id diferente devolve Falha(GeracaoNaoEncontrada)."""
        service = GenerationService(async_db_session)
        result = await service.request_tablature(
            generation_id=str(db_generation.id),
            user_id=str(uuid.uuid4()),  # utilizador errado
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)

    async def test_fails_if_no_audio_key(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: geração sem audio_storage_key devolve Falha(FicheiroGeracaoIndisponivel)."""
        from app.data.queries import GenerationQueries
        gen_sem_audio = await GenerationQueries.create_generation(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            audio_file_id=db_audio.id,
            prompt="Sem áudio ainda",
            instrument="guitarra",
            status=GenerationStatusEnum.PENDING,
            # audio_storage_key omitido → None
        )

        service = GenerationService(async_db_session)
        result = await service.request_tablature(
            generation_id=str(gen_sem_audio.id),
            user_id=str(db_user.id),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroGeracaoIndisponivel)

    async def test_fails_if_celery_queue_unavailable(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: se Celery lançar exceção, devolve Falha(FilaIndisponivel)."""
        task_mock = MagicMock()
        task_mock.apply_async.side_effect = Exception("Redis connection refused")

        with patch("app.services.generation_service.storage") as mock_storage, \
             patch(
                 "worker.tasks.generation_tasks.generate_tablature_task",
                 task_mock,
                 create=True,
             ):
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            result = await service.request_tablature(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, FilaIndisponivel)


# ===========================================================================
# request_partitura
# ===========================================================================

@pytest.mark.asyncio
class TestRequestPartitura:

    async def test_returns_pending_status(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: devolve Sucesso com partitura_status='pending'."""
        task_mock = _make_celery_task_mock()

        with patch("app.services.generation_service.storage") as mock_storage, \
             patch(
                 "worker.tasks.generation_tasks.generate_partitura_task",
                 task_mock,
                 create=True,
             ):
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            result = await service.request_partitura(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Sucesso)
        assert result.valor.partitura_status == "pending"
        task_mock.apply_async.assert_called_once()

    async def test_ownership_enforced(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: user_id diferente devolve Falha."""
        service = GenerationService(async_db_session)
        result = await service.request_partitura(
            generation_id=str(db_generation.id),
            user_id=str(uuid.uuid4()),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)


# ===========================================================================
# get_tablature_url / get_partitura_url
# ===========================================================================

@pytest.mark.asyncio
class TestGetNotationUrl:

    async def test_tablature_url_returns_presigned_url(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Arrange: tablatura_storage_key existente.
        Assert: devolve Sucesso com a presigned URL do R2."""
        from app.data.queries import GenerationQueries
        r2_key = f"tablature/{db_generation.id}.pdf"
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="completed",
            storage_key=r2_key,
        )

        presigned = "https://r2.example.com/presigned/tablature.pdf?token=xyz"

        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = presigned

            service = GenerationService(async_db_session)
            result = await service.get_tablature_url(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Sucesso)
        assert result.valor == presigned
        mock_storage.get_presigned_url.assert_called_once_with(r2_key)

    async def test_tablature_url_fails_when_key_missing(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: sem tablatura_storage_key → Falha(FicheiroGeracaoIndisponivel)."""
        service = GenerationService(async_db_session)
        result = await service.get_tablature_url(
            generation_id=str(db_generation.id),
            user_id=str(db_user.id),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroGeracaoIndisponivel)

    async def test_partitura_url_returns_presigned_url(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: partitura_storage_key existente → URL correcta."""
        from app.data.queries import GenerationQueries
        r2_key = f"partitura/{db_generation.id}.pdf"
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="completed",
            storage_key=r2_key,
        )

        presigned = "https://r2.example.com/presigned/partitura.pdf?token=abc"

        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = presigned

            service = GenerationService(async_db_session)
            result = await service.get_partitura_url(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Sucesso)
        assert result.valor == presigned

    async def test_storage_failure_returns_falha(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: storage.get_presigned_url retorna None → Falha."""
        from app.data.queries import GenerationQueries
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="completed",
            storage_key=f"tablature/{db_generation.id}.pdf",
        )

        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = None  # simula falha R2

            service = GenerationService(async_db_session)
            result = await service.get_tablature_url(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroGeracaoIndisponivel)


# ===========================================================================
# delete_generation — limpeza completa de R2
# ===========================================================================

@pytest.mark.asyncio
class TestDeleteGeneration:

    async def test_deletes_all_r2_keys(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: delete_generation chama storage.delete_file para todos os
        ficheiros associados (audio, midi, partitura, tablatura)."""
        from app.data.queries import GenerationQueries

        # Preencher todas as chaves
        audio_key     = db_generation.audio_storage_key
        midi_key      = f"midi/{db_generation.id}.mid"
        partitura_key = f"partitura/{db_generation.id}.pdf"
        tablatura_key = f"tablature/{db_generation.id}.pdf"

        await GenerationQueries.update_generation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            status=GenerationStatusEnum.COMPLETED,
            midi_key=midi_key,
            partitura_key=partitura_key,
            tablatura_key=tablatura_key,
        )

        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            result = await service.delete_generation(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        assert isinstance(result, Sucesso)

        # Todas as chaves R2 foram eliminadas
        deleted_keys = [c.args[0] for c in mock_storage.delete_file.call_args_list]
        assert audio_key     in deleted_keys
        assert midi_key      in deleted_keys
        assert partitura_key in deleted_keys
        assert tablatura_key in deleted_keys

    async def test_delete_enforces_ownership(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: user_id errado → Falha(GeracaoNaoEncontrada); DB não é alterada."""
        service = GenerationService(async_db_session)
        result = await service.delete_generation(
            generation_id=str(db_generation.id),
            user_id=str(uuid.uuid4()),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)

        # Confirmar que o registo ainda existe
        from app.data.queries import GenerationQueries
        gen = await GenerationQueries.get_generation(
            db=async_db_session,
            generation_id=str(db_generation.id),
        )
        assert gen is not None

    async def test_delete_removes_db_record(
        self, async_db_session, db_generation: Generation, db_user
    ):
        """Assert: após delete, o registo não existe na DB."""
        with patch("app.services.generation_service.storage") as mock_storage:
            mock_storage.delete_file.return_value = True

            service = GenerationService(async_db_session)
            await service.delete_generation(
                generation_id=str(db_generation.id),
                user_id=str(db_user.id),
            )

        from app.data.queries import GenerationQueries
        gen = await GenerationQueries.get_generation(
            db=async_db_session,
            generation_id=str(db_generation.id),
        )
        assert gen is None

    async def test_delete_nonexistent_returns_falha(
        self, async_db_session, db_user
    ):
        """Assert: generation_id inexistente → Falha(GeracaoNaoEncontrada)."""
        service = GenerationService(async_db_session)
        result = await service.delete_generation(
            generation_id=str(uuid.uuid4()),
            user_id=str(db_user.id),
        )

        assert isinstance(result, Falha)
        assert isinstance(result.erro, GeracaoNaoEncontrada)
