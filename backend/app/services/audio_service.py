"""
Audio Service - Audio processing and analysis business logic

Os metodos deste servico devolvem Resultado[AudioErro, T] em vez de
lancar excecoes. A traducao para HTTP fica exclusivamente no endpoint.
"""

import os
import shutil
import uuid
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
from worker.audio_utils.audio_analyzer import analisar_audio_completo

try:
    from worker.audio_utils.ajuste_bpm import ajustar_bpm_automatico
    from worker.audio_utils.corte_audio import cortar_audio
    from worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import audio processing modules: {e}")
    ajustar_bpm_automatico = None
    cortar_audio = None
    extrair_instrumento = None


class AudioService:
    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Upload & analise
    # ------------------------------------------------------------------

    async def get_project_audios(self, project_id: uuid.UUID, user_id: str) -> Resultado:
        """Lista todos os audios de um projeto, verificando autorizacao."""
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
        """Valida, analisa e persiste um ficheiro de audio enviado pelo utilizador."""
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

            audio_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_id,
                project_id=uuid.UUID(project_id),
                file_path=file_path,
                file_size=file_size,
                duration=analysis_result.get("duration", 0.0),
                sample_rate=analysis_result.get("sample_rate", 44100),
                bpm=int(analysis_result["bpm"]) if analysis_result.get("bpm") is not None else None,
                key=analysis_result.get("key"),
                time_signature=analysis_result.get("time_signature"),
            )
            audio_record.chords = analysis_result.get("chords", [])
            return Sucesso(audio_record)

        except Exception as e:
            print(f"Erro ao processar audio: {e}")
            return Falha(FalhaProcessamento(operacao="analise_audio"))

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    async def get_audio(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        """Obtem o registo e verifica o dono. Nao distingue nao-existe de nao-e-teu."""
        record = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not record or str(record.user_id) != user_id:
            return Falha(AudioNaoEncontrado(audio_id=audio_id))
        return Sucesso(record)

    async def get_audio_for_download(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        """Obtem o registo e confirma que o ficheiro fisico existe em disco."""
        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor
        if not Path(record.file_path).exists():
            return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))
        return Sucesso(record)

    # ------------------------------------------------------------------
    # Eliminacao
    # ------------------------------------------------------------------

    async def delete_audio(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        """Apaga o ficheiro do disco e o registo da base de dados."""
        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        file_path = Path(record.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Aviso: nao foi possivel apagar o ficheiro fisico: {e}")

        await AudioQueries.delete_audio_file(db=self.db, audio_id=audio_id)
        return Sucesso(None)

    # ------------------------------------------------------------------
    # Processamento
    # ------------------------------------------------------------------

    async def adjust_bpm(
        self, audio_id: uuid.UUID, user_id: str, target_bpm: float, upload_dir: str
    ) -> Resultado:
        """Ajusta o BPM e substitui o ficheiro original."""
        if not ajustar_bpm_automatico:
            return Falha(ModuloAudioIndisponivel(modulo="ajuste_bpm"))

        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        input_path = Path(record.file_path)
        if not input_path.exists():
            return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))

        temp_path = Path(upload_dir) / f"{uuid.uuid4()}_bpm_temp.wav"
        try:
            ajustar_bpm_automatico(str(input_path), str(temp_path), target_bpm)
            shutil.move(str(temp_path), str(input_path))
            updated = await AudioQueries.update_audio_analysis(
                db=self.db, audio_id=audio_id, bpm=int(target_bpm)
            )
            return Sucesso(updated)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            return Falha(FalhaProcessamento(operacao="ajuste_bpm"))

    async def cut_audio_file(
        self,
        audio_id: uuid.UUID,
        user_id: str,
        inicio_segundos: float,
        fim_segundos: float,
        upload_dir: str,
    ) -> Resultado:
        """Corta o audio e guarda como novo registo ligado ao original."""
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

        input_path = Path(record.file_path)
        if not input_path.exists():
            return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))

        original_duration = record.duration or 0.0
        if inicio_segundos >= original_duration:
            return Falha(IntervaloInvalido(
                detalhe=f"Tempo de inicio ({inicio_segundos}s) maior ou igual a duracao ({original_duration:.2f}s)."
            ))

        actual_end      = min(fim_segundos, original_duration)
        actual_duration = actual_end - inicio_segundos
        output_path     = Path(upload_dir) / f"{uuid.uuid4()}_cut_{inicio_segundos}s_{actual_end}s.wav"

        try:
            cortar_audio(str(input_path), str(output_path), inicio_segundos, actual_end)
            new_record = await AudioQueries.create_audio_file(
                db=self.db,
                user_id=user_id,
                project_id=record.project_id,
                file_path=str(output_path),
                file_size=output_path.stat().st_size,
                duration=round(actual_duration, 3),
                sample_rate=record.sample_rate,
                bpm=record.bpm,
                key=record.key,
                time_signature=record.time_signature,
                parent_audio_id=audio_id,
            )
            return Sucesso(new_record)
        except Exception:
            if output_path.exists():
                output_path.unlink()
            return Falha(FalhaProcessamento(operacao="corte_audio"))

    async def separate_tracks(
        self, audio_id: uuid.UUID, user_id: str, instrument: str, upload_dir: str
    ) -> Resultado:
        """Separa a faixa do instrumento e devolve o caminho do ficheiro gerado."""
        if not extrair_instrumento:
            return Falha(ModuloAudioIndisponivel(modulo="separador_faixas"))

        resultado = await self.get_audio(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        record = resultado.valor

        input_path = Path(record.file_path)
        if not input_path.exists():
            return Falha(FicheiroFisicoNaoEncontrado(audio_id=audio_id))

        instrument_normalized = instrument.lower().strip()
        output_path = Path(upload_dir) / f"{input_path.stem}_{instrument_normalized}.wav"

        try:
            extrair_instrumento(str(input_path), instrument, upload_dir)
            if not output_path.exists():
                return Falha(FalhaProcessamento(operacao="separacao_faixas"))
            return Sucesso(str(output_path))
        except Exception:
            return Falha(FalhaProcessamento(operacao="separacao_faixas"))
