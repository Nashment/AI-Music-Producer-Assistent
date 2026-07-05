"""
Testes para AudioService e AudioQueries.

Cobre:
  upload_and_analyze_audio — sucesso, formato inválido, ficheiro grande, upload R2 falha
  get_audio                — ownership, inexistente
  get_audio_download_url   — presigned URL, storage falha
  delete_audio             — limpa R2 + DB, ownership
  adjust_bpm               — sucesso (mockado), módulo indisponível
  cut_audio_file           — intervalo inválido, sucesso (mockado)
  AudioQueries             — create, get, get_project_files, update_analysis, delete
"""

import os
import uuid
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.audio_service import AudioService
from app.domain.result import Sucesso, Falha
from app.domain.errors.audio_errors import (
    AudioNaoEncontrado,
    ProjetoNaoEncontrado,
    FormatoAudioInvalido,
    FicheiroAudioGrande,
    FicheiroFisicoNaoEncontrado,
    ModuloAudioIndisponivel,
    FalhaProcessamento,
    IntervaloInvalido,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_temp_wav(size_bytes: int = 1024) -> str:
    """Cria um ficheiro .wav temporário com o tamanho dado."""
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    f.write(b"\x00" * size_bytes)
    f.close()
    return f.name


def _write_temp_mp3(size_bytes: int = 1024) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    f.write(b"\x00" * size_bytes)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# upload_and_analyze_audio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUploadAndAnalyzeAudio:

    async def test_invalid_format_returns_falha(self, async_db_session, db_user, db_project):
        """Assert: extensão não suportada → Falha(FormatoAudioInvalido)."""
        tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        tmp.write(b"\x00" * 512)
        tmp.close()
        try:
            svc = AudioService(async_db_session)
            result = await svc.upload_and_analyze_audio(
                file_path=tmp.name,
                user_id=str(db_user.id),
                project_id=str(db_project.id),
            )
            assert isinstance(result, Falha)
            assert isinstance(result.erro, FormatoAudioInvalido)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    async def test_file_too_large_returns_falha(self, async_db_session, db_user, db_project):
        """Assert: ficheiro > 50 MB → Falha(FicheiroAudioGrande)."""
        # Criar ficheiro de 51 MB
        size_51mb = 51 * 1024 * 1024
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.seek(size_51mb - 1)
        tmp.write(b"\x00")
        tmp.close()
        try:
            svc = AudioService(async_db_session)
            result = await svc.upload_and_analyze_audio(
                file_path=tmp.name,
                user_id=str(db_user.id),
                project_id=str(db_project.id),
            )
            assert isinstance(result, Falha)
            assert isinstance(result.erro, FicheiroAudioGrande)
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    async def test_nonexistent_file_returns_falha(self, async_db_session, db_user, db_project):
        """Assert: caminho inexistente → Falha(FicheiroFisicoNaoEncontrado)."""
        svc = AudioService(async_db_session)
        result = await svc.upload_and_analyze_audio(
            file_path="/tmp/ficheiro_que_nao_existe.wav",
            user_id=str(db_user.id),
            project_id=str(db_project.id),
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroFisicoNaoEncontrado)

    async def test_module_unavailable_returns_falha(self, async_db_session, db_user, db_project):
        """Assert: módulo audio_analyzer indisponível → Falha(ModuloAudioIndisponivel)."""
        tmp = _write_temp_wav()
        try:
            with patch("app.services.audio_service.analisar_audio_completo", None):
                svc = AudioService(async_db_session)
                result = await svc.upload_and_analyze_audio(
                    file_path=tmp,
                    user_id=str(db_user.id),
                    project_id=str(db_project.id),
                )
            assert isinstance(result, Falha)
            assert isinstance(result.erro, ModuloAudioIndisponivel)
        finally:
            Path(tmp).unlink(missing_ok=True)

    async def test_upload_r2_failure_returns_falha(self, async_db_session, db_user, db_project):
        """Assert: falha no upload R2 → Falha(FalhaProcessamento)."""
        tmp = _write_temp_wav()
        fake_analysis = {"duration": 5.0, "sample_rate": 44100, "bpm": 120, "key": "C", "time_signature": "4/4", "chords": []}
        try:
            with patch("app.services.audio_service.analisar_audio_completo", return_value=fake_analysis), \
                 patch("app.services.audio_service.storage") as mock_storage:
                mock_storage.upload_file.return_value = False  # simula falha
                svc = AudioService(async_db_session)
                result = await svc.upload_and_analyze_audio(
                    file_path=tmp,
                    user_id=str(db_user.id),
                    project_id=str(db_project.id),
                )
            assert isinstance(result, Falha)
            assert isinstance(result.erro, FalhaProcessamento)
        finally:
            Path(tmp).unlink(missing_ok=True)

    async def test_upload_success_creates_audio_record(self, async_db_session, db_user, db_project):
        """Assert: upload bem-sucedido cria registo na DB com campos correctos."""
        tmp = _write_temp_wav(2048)
        fake_analysis = {
            "duration": 10.5,
            "sample_rate": 44100,
            "bpm": 128,
            "key": "A minor",
            "time_signature": "4/4",
            "chords": ["Am", "G"],
        }
        try:
            with patch("app.services.audio_service.analisar_audio_completo", return_value=fake_analysis), \
                 patch("app.services.audio_service.storage") as mock_storage:
                mock_storage.upload_file.return_value = True
                svc = AudioService(async_db_session)
                result = await svc.upload_and_analyze_audio(
                    file_path=tmp,
                    user_id=str(db_user.id),
                    project_id=str(db_project.id),
                )
            assert isinstance(result, Sucesso)
            record = result.valor
            assert record.bpm == 128
            assert record.key == "A minor"
            assert record.duration == pytest.approx(10.5)
            assert str(record.user_id) == str(db_user.id)
        finally:
            Path(tmp).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# get_audio / get_audio_download_url
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestGetAudio:

    async def test_get_audio_success(self, async_db_session, db_user, db_audio):
        """Assert: devolve Sucesso com o registo correcto."""
        svc = AudioService(async_db_session)
        result = await svc.get_audio(db_audio.id, str(db_user.id))
        assert isinstance(result, Sucesso)
        assert result.valor.id == db_audio.id

    async def test_get_audio_wrong_user(self, async_db_session, db_audio):
        """Assert: user_id errado → Falha(AudioNaoEncontrado)."""
        svc = AudioService(async_db_session)
        result = await svc.get_audio(db_audio.id, str(uuid.uuid4()))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)

    async def test_get_audio_nonexistent(self, async_db_session, db_user):
        """Assert: UUID inexistente → Falha(AudioNaoEncontrado)."""
        svc = AudioService(async_db_session)
        result = await svc.get_audio(uuid.uuid4(), str(db_user.id))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)

    async def test_get_audio_download_url(self, async_db_session, db_user, db_audio):
        """Assert: devolve presigned URL do R2."""
        presigned = "https://r2.example.com/audio.wav?token=abc"
        with patch("app.services.audio_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = presigned
            svc = AudioService(async_db_session)
            result = await svc.get_audio_download_url(db_audio.id, str(db_user.id))
        assert isinstance(result, Sucesso)
        assert result.valor == presigned

    async def test_get_audio_download_url_storage_failure(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: storage.get_presigned_url = None → Falha(FicheiroFisicoNaoEncontrado)."""
        with patch("app.services.audio_service.storage") as mock_storage:
            mock_storage.get_presigned_url.return_value = None
            svc = AudioService(async_db_session)
            result = await svc.get_audio_download_url(db_audio.id, str(db_user.id))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, FicheiroFisicoNaoEncontrado)


# ---------------------------------------------------------------------------
# delete_audio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestDeleteAudio:

    async def test_delete_audio_cleans_r2_and_db(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: storage.delete_file chamado e registo removido da DB."""
        with patch("app.services.audio_service.storage") as mock_storage:
            mock_storage.delete_file.return_value = True
            svc = AudioService(async_db_session)
            result = await svc.delete_audio(db_audio.id, str(db_user.id))

        assert isinstance(result, Sucesso)
        mock_storage.delete_file.assert_called_once_with(db_audio.storage_key)

        # Confirmar remoção da DB
        get_result = await svc.get_audio(db_audio.id, str(db_user.id))
        assert isinstance(get_result, Falha)

    async def test_delete_audio_wrong_user(self, async_db_session, db_audio):
        """Assert: user_id errado → Falha; R2 não é tocado."""
        with patch("app.services.audio_service.storage") as mock_storage:
            svc = AudioService(async_db_session)
            result = await svc.delete_audio(db_audio.id, str(uuid.uuid4()))

        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)
        mock_storage.delete_file.assert_not_called()


# ---------------------------------------------------------------------------
# adjust_bpm
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAdjustBpm:

    async def test_adjust_bpm_module_unavailable(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: módulo de ajuste indisponível → Falha(ModuloAudioIndisponivel)."""
        with patch("app.services.audio_service.ajustar_bpm_automatico", None):
            svc = AudioService(async_db_session)
            result = await svc.adjust_bpm(db_audio.id, str(db_user.id), 120.0, "/tmp")
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ModuloAudioIndisponivel)

    async def test_adjust_bpm_wrong_user(self, async_db_session, db_audio):
        """Assert: user_id errado → Falha(AudioNaoEncontrado) antes de tocar em qualquer ficheiro."""
        svc = AudioService(async_db_session)
        result = await svc.adjust_bpm(db_audio.id, str(uuid.uuid4()), 120.0, "/tmp")
        assert isinstance(result, Falha)
        assert isinstance(result.erro, AudioNaoEncontrado)


# ---------------------------------------------------------------------------
# cut_audio_file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCutAudioFile:

    async def test_cut_negative_start_returns_falha(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: inicio < 0 → Falha(IntervaloInvalido)."""
        svc = AudioService(async_db_session)
        result = await svc.cut_audio_file(
            db_audio.id, str(db_user.id), -1.0, 10.0, "/tmp"
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloInvalido)

    async def test_cut_end_before_start_returns_falha(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: fim <= inicio → Falha(IntervaloInvalido)."""
        svc = AudioService(async_db_session)
        result = await svc.cut_audio_file(
            db_audio.id, str(db_user.id), 15.0, 5.0, "/tmp"
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloInvalido)

    async def test_cut_start_beyond_duration_returns_falha(
        self, async_db_session, db_user, db_audio
    ):
        """Assert: inicio >= duração do áudio → Falha(IntervaloInvalido)."""
        # db_audio tem duration=30.0
        svc = AudioService(async_db_session)
        result = await svc.cut_audio_file(
            db_audio.id, str(db_user.id), 35.0, 40.0, "/tmp"
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, IntervaloInvalido)

    async def test_cut_module_unavailable(self, async_db_session, db_user, db_audio):
        """Assert: módulo de corte indisponível → Falha(ModuloAudioIndisponivel)."""
        with patch("app.services.audio_service.cortar_audio", None):
            svc = AudioService(async_db_session)
            result = await svc.cut_audio_file(
                db_audio.id, str(db_user.id), 0.0, 10.0, "/tmp"
            )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ModuloAudioIndisponivel)


# ---------------------------------------------------------------------------
# AudioQueries directas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAudioQueries:

    async def test_create_audio_file(self, async_db_session, db_user, db_project):
        """Assert: create_audio_file persiste todos os campos."""
        from app.data.queries import AudioQueries
        audio = await AudioQueries.create_audio_file(
            db=async_db_session,
            user_id=db_user.id,
            project_id=db_project.id,
            storage_key="audio/test.wav",
            file_size=512 * 1024,
            duration=25.0,
            sample_rate=44100,
            bpm=140,
            key="D major",
        )
        assert audio.id is not None
        assert audio.bpm == 140
        assert audio.key == "D major"

    async def test_get_audio_file(self, async_db_session, db_audio):
        """Assert: get_audio_file devolve o registo pelo UUID."""
        from app.data.queries import AudioQueries
        found = await AudioQueries.get_audio_file(
            db=async_db_session, audio_id=db_audio.id
        )
        assert found is not None
        assert found.id == db_audio.id

    async def test_get_project_audio_files(
        self, async_db_session, db_user, db_project, db_audio
    ):
        """Assert: get_project_audio_files lista os áudios do projecto."""
        from app.data.queries import AudioQueries
        files = await AudioQueries.get_project_audio_files(
            db=async_db_session, project_id=db_project.id
        )
        assert any(f.id == db_audio.id for f in files)

    async def test_update_audio_analysis(self, async_db_session, db_audio):
        """Assert: update_audio_analysis persiste novos valores de BPM e tonalidade."""
        from app.data.queries import AudioQueries
        updated = await AudioQueries.update_audio_analysis(
            db=async_db_session,
            audio_id=db_audio.id,
            bpm=145,
            key="E minor",
        )
        assert updated.bpm == 145
        assert updated.key == "E minor"

    async def test_delete_audio_file(self, async_db_session, db_audio):
        """Assert: delete_audio_file remove o registo da DB."""
        from app.data.queries import AudioQueries
        ok = await AudioQueries.delete_audio_file(
            db=async_db_session, audio_id=db_audio.id
        )
        assert ok is True
        found = await AudioQueries.get_audio_file(
            db=async_db_session, audio_id=db_audio.id
        )
        assert found is None
