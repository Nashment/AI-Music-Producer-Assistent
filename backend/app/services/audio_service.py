"""
Audio Service - Audio processing and analysis business logic
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from backend.app.data import AudioQueries
from backend.worker.audio_utils.audio_analyzer import analisar_audio_completo

try:
    from backend.worker.audio_utils.ajuste_bpm import ajustar_bpm_automatico
    from backend.worker.audio_utils.corte_audio import cortar_audio
    from backend.worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import audio processing modules: {e}")
    ajustar_bpm_automatico = None
    cortar_audio = None
    extrair_instrumento = None


class AudioService:
    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Upload & análise
    # ------------------------------------------------------------------

    async def get_project_audios(self, project_id: uuid.UUID, user_id: str):
        """Lista todos os áudios de um projeto, verificando autorização."""
        from backend.app.data import ProjectQueries
        project = await ProjectQueries.get_project(db=self.db, project_id=project_id)
        if not project:
            raise ValueError("Projeto não encontrado.")
        if str(project.user_id) != user_id:
            raise PermissionError("Acesso negado.")
        return await AudioQueries.get_project_audio_files(db=self.db, project_id=project_id)

    async def upload_and_analyze_audio(
        self,
        file_path: str,
        user_id: str,
        project_id: str
    ):
        valid_extensions = {'.mp3', '.wav'}
        _, ext = os.path.splitext(file_path.lower())

        if ext not in valid_extensions:
            raise ValueError(f"Formato não suportado. Formatos válidos: {valid_extensions}")

        if not os.path.exists(file_path):
            raise FileNotFoundError("O ficheiro de áudio não foi encontrado no servidor.")

        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            raise ValueError(f"O ficheiro é demasiado grande ({file_size / 1024 / 1024:.2f}MB). O limite é 50MB.")

        try:
            analysis_result = analisar_audio_completo(file_path)

            user_uuid = uuid.UUID(user_id)
            project_uuid = uuid.UUID(project_id)

            duration = analysis_result.get("duration", 0.0)
            sample_rate = analysis_result.get("sample_rate", 44100)
            bpm_raw = analysis_result.get("bpm")
            bpm = int(bpm_raw) if bpm_raw is not None else None
            key = analysis_result.get("key")
            time_signature = analysis_result.get("time_signature")

            audio_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_uuid,
                project_id=project_uuid,
                file_path=file_path,
                file_size=file_size,
                duration=duration,
                sample_rate=sample_rate,
                bpm=bpm,
                key=key,
                time_signature=time_signature
            )

            audio_record.chords = analysis_result.get("chords", [])
            return audio_record

        except Exception as e:
            print(f"Erro ao processar áudio: {e}")
            raise

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    async def get_audio(self, audio_id: uuid.UUID, user_id: str):
        """Obtém o registo de áudio e verifica autorização."""
        record = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not record:
            raise ValueError("Áudio não encontrado.")
        if str(record.user_id) != user_id:
            raise PermissionError("Acesso negado.")
        return record

    # ------------------------------------------------------------------
    # Eliminação
    # ------------------------------------------------------------------

    async def delete_audio(self, audio_id: uuid.UUID, user_id: str):
        """Apaga o ficheiro do disco e o registo da base de dados."""
        record = await self.get_audio(audio_id, user_id)

        file_path = Path(record.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Aviso: Não foi possível apagar o ficheiro físico: {e}")

        await AudioQueries.delete_audio_file(db=self.db, audio_id=audio_id)

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    async def adjust_bpm(self, audio_id: uuid.UUID, user_id: str, target_bpm: float, upload_dir: str):
        """Ajusta o BPM e substitui o ficheiro original."""
        if not ajustar_bpm_automatico:
            raise NotImplementedError("BPM adjustment not available")

        record = await self.get_audio(audio_id, user_id)
        input_path = Path(record.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        temp_path = Path(upload_dir) / f"{uuid.uuid4()}_bpm_temp.wav"
        try:
            ajustar_bpm_automatico(str(input_path), str(temp_path), target_bpm)
            shutil.move(str(temp_path), str(input_path))
            updated = await AudioQueries.update_audio_analysis(
                db=self.db, audio_id=audio_id, bpm=int(target_bpm)
            )
            return updated
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    async def cut_audio_file(
        self, audio_id: uuid.UUID, user_id: str, inicio_segundos: float, fim_segundos: float, upload_dir: str
    ):
        """Corta o áudio entre inicio_segundos e fim_segundos e guarda como novo registo ligado ao original."""
        if not cortar_audio:
            raise NotImplementedError("Audio cutting not available")

        if inicio_segundos < 0:
            raise ValueError("O tempo de início não pode ser negativo.")
        if fim_segundos <= inicio_segundos:
            raise ValueError("O tempo de fim deve ser maior que o tempo de início.")

        record = await self.get_audio(audio_id, user_id)
        input_path = Path(record.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        original_duration = record.duration or 0.0
        if inicio_segundos >= original_duration:
            raise ValueError(
                f"O tempo de início ({inicio_segundos}s) é maior ou igual à duração do áudio ({original_duration:.2f}s)."
            )
        actual_end = min(fim_segundos, original_duration)
        actual_duration = actual_end - inicio_segundos

        output_filename = f"{uuid.uuid4()}_cut_{inicio_segundos}s_{actual_end}s.wav"
        output_path = Path(upload_dir) / output_filename
        try:
            cortar_audio(str(input_path), str(output_path), inicio_segundos, actual_end)
            file_size = output_path.stat().st_size
            new_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=uuid.UUID(user_id),
                project_id=record.project_id,
                file_path=str(output_path),
                file_size=file_size,
                duration=round(actual_duration, 3),
                sample_rate=record.sample_rate,
                bpm=record.bpm,
                key=record.key,
                time_signature=record.time_signature,
                parent_audio_id=audio_id
            )
            return new_record
        except Exception:
            if output_path.exists():
                output_path.unlink()
            raise

    async def separate_tracks(
        self, audio_id: uuid.UUID, user_id: str, instrument: str, upload_dir: str
    ) -> str:
        """Separa a faixa do instrumento e devolve o caminho do ficheiro gerado."""
        if not extrair_instrumento:
            raise NotImplementedError("Track separation not available")

        record = await self.get_audio(audio_id, user_id)
        input_path = Path(record.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        base_name = input_path.stem
        instrument_normalized = instrument.lower().strip()
        output_filename = f"{base_name}_{instrument_normalized}.wav"
        output_path = Path(upload_dir) / output_filename

        extrair_instrumento(str(input_path), instrument, upload_dir)

        if not output_path.exists():
            raise RuntimeError("A separação de faixas não gerou o ficheiro esperado.")

        return str(output_path)

