"""
Testes unitários para GenerationQueries.update_notation_status.

Cobre:
  - Atualização de partitura_status e partitura_storage_key
  - Atualização de tablatura_status e tablatura_storage_key
  - Estado 'failed' persiste error_message
  - storage_key None não sobrescreve chave existente
  - generation_id inválido (UUID malformado) devolve None sem crash
  - generation_id inexistente devolve None sem crash
"""

import uuid
import pytest
import pytest_asyncio

from app.data.queries import GenerationQueries
from app.data.models import Generation


@pytest.mark.asyncio
class TestUpdateNotationStatus:
    """Testes para GenerationQueries.update_notation_status."""

    # ------------------------------------------------------------------
    # Partitura
    # ------------------------------------------------------------------

    async def test_partitura_pending_sets_status(
        self, async_db_session, db_generation: Generation
    ):
        """Arrange: geração existente sem partitura.
        Act: marcar partitura como pending.
        Assert: partitura_status='pending', chave permanece None."""
        # Act
        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="pending",
        )

        # Assert
        assert updated is not None
        assert updated.partitura_status == "pending"
        assert updated.partitura_storage_key is None  # sem chave ainda

    async def test_partitura_completed_persists_key(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: partitura_status='completed' e chave R2 persistida."""
        r2_key = f"partitura/{db_generation.id}.pdf"

        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="completed",
            storage_key=r2_key,
        )

        assert updated.partitura_status == "completed"
        assert updated.partitura_storage_key == r2_key

    async def test_partitura_failed_persists_error_message(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: status='failed' persiste error_message."""
        error_msg = "basic_pitch indisponível no worker."

        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="failed",
            error_message=error_msg,
        )

        assert updated.partitura_status == "failed"
        assert updated.error_message == error_msg

    async def test_partitura_completed_without_key_does_not_overwrite(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: passar storage_key=None não apaga chave já existente."""
        original_key = f"partitura/{db_generation.id}.pdf"

        # Primeiro: definir a chave
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="completed",
            storage_key=original_key,
        )

        # Act: atualizar status sem passar key
        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="completed",
            storage_key=None,
        )

        # Assert: chave original preservada
        assert updated.partitura_storage_key == original_key

    # ------------------------------------------------------------------
    # Tablatura
    # ------------------------------------------------------------------

    async def test_tablatura_processing_sets_status(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: tablatura_status='processing' é persistido."""
        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="processing",
        )

        assert updated.tablatura_status == "processing"

    async def test_tablatura_completed_persists_key(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: tablatura_storage_key é persistida ao marcar 'completed'."""
        r2_key = f"tablature/{db_generation.id}.pdf"

        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="completed",
            storage_key=r2_key,
        )

        assert updated.tablatura_status == "completed"
        assert updated.tablatura_storage_key == r2_key

    async def test_tablatura_failed_sets_error(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: status='failed' persiste error_message na tablatura."""
        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="failed",
            error_message="Falha no lilypond.",
        )

        assert updated.tablatura_status == "failed"
        assert "lilypond" in updated.error_message

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    async def test_invalid_uuid_returns_none(self, async_db_session):
        """Assert: UUID malformado devolve None sem levantar exceção."""
        result = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id="not-a-valid-uuid",
            notation_type="partitura",
            status="pending",
        )
        assert result is None

    async def test_nonexistent_generation_returns_none(self, async_db_session):
        """Assert: UUID válido mas inexistente devolve None."""
        result = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(uuid.uuid4()),
            notation_type="tablatura",
            status="completed",
            storage_key="tablature/ghost.pdf",
        )
        assert result is None

    async def test_partitura_and_tablatura_are_independent(
        self, async_db_session, db_generation: Generation
    ):
        """Assert: atualizar tablatura não afeta campos de partitura e vice-versa."""
        partitura_key = f"partitura/{db_generation.id}.pdf"

        # Definir partitura completed
        await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="partitura",
            status="completed",
            storage_key=partitura_key,
        )

        # Atualizar tablatura para pending
        updated = await GenerationQueries.update_notation_status(
            db=async_db_session,
            generation_id=str(db_generation.id),
            notation_type="tablatura",
            status="pending",
        )

        # Partitura não foi tocada
        assert updated.partitura_status == "completed"
        assert updated.partitura_storage_key == partitura_key
        # Tablatura foi atualizada
        assert updated.tablatura_status == "pending"
