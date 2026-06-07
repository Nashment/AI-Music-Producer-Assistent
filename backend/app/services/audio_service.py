"""
Audio Service - Audio processing and analysis business logic
"""

import os
import shutil
import uuid
import tempfile
from pathlib import Path

from app.data import ProjectQueries
from app.data import AudioQueries
from app.domain.result import Resultado, Sucesso, Falha
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
from app.services.storage_service import storage

try:
    from worker.audio_utils.audio_analyzer import analisar_audio_completo
except ImportError as e:
    print(f"Warning: Could not import audio_analyzer: {e}")
    analisar_audio_completo = None

try:
    from worker.audio_utils.ajuste_bpm import ajustar_bpm_automatico
    from worker.audio_utils.corte_audio import cortar_audio
    from worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import audio processing modules: {e}")
    ajustar_bpm_automatico = None
    cortar_audio = None
    extrair_instrumento = None


def _make_audio_key(filename: str) -> str:
    """Gera uma chave R2 unica para um ficheiro de audio de utilizador."""
    return f"audio/{uuid.uuid4()}_{Path(filename).name}"


class AudioService:
    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Upload & analise
    # ------------------------------------------------------------------

    async def get_project_audios(self, project_id: uuid.UUID, user_id: str) -> Resultado:
        project = await ProjectQueries.get_project(db=self.db, project_id=project_id)
        if not project or str(project.user_id) != user_id:
            return Falha(ProjetoNaoEncontrado(project_id=project_id))
        audios = await AudioQueries.get_project_audio_files(db=self.db, project_id=project_id)
        return Sucesso(audios)

    async def upload_and_analyze_audio(
        self,
        file_path: str,
        user_id: str,
        project_id: str,
    ) -> Resultado:
        if analisar_audio_completo is None:
            return Falha(ModuloAudioIndisponivel(modulo="audio_analyzer"))

        valid_extensions = {'.mp3', '.wav'}
        _, ext = os.path.splitext(file_path.lower())

        if ext not in valid_extensions:
            return Falha(FormatoAudioInvalido(extensao=ext))

        if not os.path.exists(file_path):
            return Falha(FicheiroFisicoNaoEncontrado())

        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            return Falha(FicheiroAudioGrande(tamanho_mb=round(file_size / 1024 / 1024, 2)))

        try:
            analysis_result = analisar_audio_completo(file_path)

            s3_key = _make_audio_key(Path(file_path).name)
            uploaded = storage.upload_file(file_path, s3_key)
            if not uploaded:
                return Falha(FalhaProcessamento(operacao="upload_r2"))

            audio_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_id,
                project_id=uuid.UUID(project_id),
                storage_key=s3_key,
                file_size=file_size,
                duration=analysis_result.get("duration", 0.0),
                sample_rate=analysis_result.get("sample_rate", 44100),
                bpm=int(analysis_result["bpm"]) if analysis_result.get("bpm") is not None else None,
                key=analysis_result.get("key"),
                time_signature=analysis_result.get("time_signature"),
            )
            audio_record.chords = analysis_result.get("chords", [])

            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                print(f"Aviso: nao foi possivel apagar ficheiro local apos upload: {e}")

            return Sucesso(audio_record)

        except Exception as e:
            print(f"Erro ao processar audio: {e}")
            return Falha(FalhaProcessamento(operacao="analise_audio"))

    # ------------------------------------------------------------------
    # Leitura / Download
    # ------------------------------------------------------------------

    async def get_audio(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        record = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not record or str(record.user_id) != user_id:
            return Falha(AudioNaoEncontrado(audio_id=audio_id))
        return Sucesso(record)

    async def get_audio_download_url(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor
        url = storage.get_presigned_url(record.storage_key)
        if not url:
            return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))
        return Sucesso(url)

    # ------------------------------------------------------------------
    # Eliminacao
    # ------------------------------------------------------------------

    async def delete_audio(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor
        storage.delete_file(record.storage_key)
        await AudioQueries.delete_audio_file(db=self.db, audio_id=audio_id)
        return Sucesso(None)

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    async def adjust_bpm(
        self, audio_id: uuid.UUID, user_id: str, target_bpm: float, upload_dir: str
    ) -> Resultado:
        if not ajustar_bpm_automatico:
            return Falha(ModuloAudioIndisponivel(modulo="ajuste_bpm"))

        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        try:
            with storage.temp_download(record.storage_key) as input_path:
                temp_out = Path(tempfile.mktemp(suffix=".wav"))
                try:
                    ajustar_bpm_automatico(str(input_path), str(temp_out), target_bpm)
                    if not temp_out.exists():
                        return Falha(FalhaProcessamento(operacao="ajuste_bpm"))

                    uploaded = storage.upload_file(str(temp_out), record.storage_key)
                    if not uploaded:
                        return Falha(FalhaProcessamento(operacao="upload_r2_bpm"))

                    updated = await AudioQueries.update_audio_analysis(
                        db=self.db, audio_id=audio_id, bpm=int(target_bpm)
                    )
                    return Sucesso(updated)
                finally:
                    temp_out.unlink(missing_ok=True)
        except Exception:
            return Falha(FalhaProcessamento(operacao="ajuste_bpm"))

    async def cut_audio_file(
        self,
        audio_id: uuid.UUID,
        user_id: str,
        inicio_segundos: float,
        fim_segundos: float,
        upload_dir: str,
    ) -> Resultado:
        if not cortar_audio:
            return Falha(ModuloAudioIndisponivel(modulo="corte_audio"))

        if inicio_segundos < 0:
            return Falha(IntervaloInvalido(detalhe="O tempo de inicio nao pode ser negativo."))
        if fim_segundos <= inicio_segundos:
            return Falha(IntervaloInvalido(detalhe="O tempo de fim deve ser maior que o tempo de inicio."))

        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        original_duration = record.duration or 0.0
        if inicio_segundos >= original_duration:
            return Falha(IntervaloInvalido(
                detalhe=f"Tempo de inicio ({inicio_segundos}s) maior ou igual a duracao ({original_duration:.2f}s)."
            ))

        actual_end = min(fim_segundos, original_duration)
        actual_duration = actual_end - inicio_segundos

        output_tmp = Path(tempfile.mktemp(suffix=".wav"))
        try:
            with storage.temp_download(record.storage_key) as input_path:
                try:
                    cortar_audio(str(input_path), str(output_tmp), inicio_segundos, actual_end)
                except RuntimeError:
                    return Falha(FalhaProcessamento(operacao="corte_audio"))

            if not output_tmp.exists():
                return Falha(FalhaProcessamento(operacao="corte_audio"))

            cut_key = f"audio/{uuid.uuid4()}_cut_{inicio_segundos}s_{actual_end}s.wav"
            uploaded = storage.upload_file(str(output_tmp), cut_key)
            if not uploaded:
                return Falha(FalhaProcessamento(operacao="upload_r2_cut"))

            new_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_id,
                project_id=record.project_id,
                storage_key=cut_key,
                file_size=output_tmp.stat().st_size,
                duration=round(actual_duration, 3),
                sample_rate=record.sample_rate,
                bpm=record.bpm,
                key=record.key,
                time_signature=record.time_signature,
                parent_audio_id=audio_id,
            )
            return Sucesso(new_record)
        except Exception:
            return Falha(FalhaProcessamento(operacao="corte_audio"))
        finally:
            output_tmp.unlink(missing_ok=True)

    async def separate_tracks(
        self, audio_id: uuid.UUID, user_id: str, instrument: str, upload_dir: str
    ) -> Resultado:
        if not extrair_instrumento:
            return Falha(ModuloAudioIndisponivel(modulo="separador_faixas"))

        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        instrument_normalized = instrument.lower().strip()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            local_input = tmp_dir_path / Path(record.storage_key).name

            ok = storage.download_file(record.storage_key, str(local_input))
            if not ok:
                return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))

            output_path = tmp_dir_path / f"{local_input.stem}_{instrument_normalized}.wav"

            try:
                extrair_instrumento(str(local_input), instrument, str(tmp_dir_path))
                if not output_path.exists():
                    return Falha(FalhaProcessamento(operacao="separacao_faixas"))

                final_output = Path(tempfile.mktemp(suffix=f"_{instrument_normalized}.wav"))
                shutil.copy2(str(output_path), str(final_output))
                return Sucesso(str(final_output))
            except Exception:
                return Falha(FalhaProcessamento(operacao="separacao_faixas"))
