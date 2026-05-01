"""
Generation Service - Music generation orchestration and AI integration

Os métodos deste serviço devolvem Resultado[GeneracaoErro, T] em vez de
lançar exceções. Desta forma a camada de serviço fala em linguagem de
negócio e a tradução para HTTP fica exclusivamente no endpoint.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from app.data import AudioQueries, GenerationQueries
from app.domain.result import Resultado, Sucesso, Falha
from app.domain.errors.generation_errors import (
    AudioNaoEncontrado,
    GeracaoNaoEncontrada,
    CoverUrlInvalido,
    PesoAudioInvalido,
    WorkerIndisponivel,
    FilaIndisponivel,
    FalhaProcessamentoAudio,
)

try:
    from worker.audio_utils.audio_to_tablature2 import (
        extrair_midi_do_audio,
        obter_ultimo_erro_extracao,
        obter_ultimo_erro_compilacao,
        extrair_lista_notas,
        otimizar_tablatura,
        converter_midi_para_ly,
        injetar_inteligencia_no_ly,
        forcar_tablatura_no_ly,
        compilar_pdf_lilypond,
    )
except ImportError as e:
    print(f"Warning: Could not import tablature modules: {e}")
    extrair_midi_do_audio = obter_ultimo_erro_extracao = obter_ultimo_erro_compilacao = None
    extrair_lista_notas = otimizar_tablatura = converter_midi_para_ly = None
    injetar_inteligencia_no_ly = forcar_tablatura_no_ly = compilar_pdf_lilypond = None

try:
    from worker.audio_utils.audio_to_partitura import exportar_pdf_automatico, obter_ultimo_erro_partitura
except ImportError as e:
    print(f"Warning: Could not import partitura modules: {e}")
    exportar_pdf_automatico = obter_ultimo_erro_partitura = None


class GenerationService:

    def __init__(self, db_session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Submissão
    # ------------------------------------------------------------------

    async def submit_generation(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
    ) -> Resultado:
        """Cria registo PENDING e enfileira processamento assíncrono no Celery."""
        try:
            from worker.tasks.generation_tasks import process_generation_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        audio_resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(audio_resultado, Falha):
            return audio_resultado

        generation_id = str(uuid.uuid4())
        generation = await self._criar_registo_geracao(
            generation_id, user_id, project_id, audio_id,
            prompt, instrument, genre, duration, tempo_override,
        )
        return await self._enfileirar_tarefa(
            generation, process_generation_task,
            {"generation_id": generation_id},
        )

    async def submit_cover_generation(
        self,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
        upload_url: Optional[str],
        audio_weight: float,
    ) -> Resultado:
        """Cria registo PENDING e enfileira cover generation assíncrona no Celery."""
        try:
            from worker.tasks.generation_tasks import process_cover_generation_task
        except ImportError as e:
            return Falha(WorkerIndisponivel(detalhe=str(e)))

        audio_resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(audio_resultado, Falha):
            return audio_resultado
        audio = audio_resultado.valor

        resolved_upload_url = upload_url or audio.file_path
        if not isinstance(resolved_upload_url, str) or not resolved_upload_url.startswith(("http://", "https://")):
            return Falha(CoverUrlInvalido(url_recebido=str(resolved_upload_url)))
        if audio_weight < 0.0 or audio_weight > 1.0:
            return Falha(PesoAudioInvalido(valor=audio_weight))

        generation_id = str(uuid.uuid4())
        generation = await self._criar_registo_geracao(
            generation_id, user_id, project_id, audio_id,
            prompt, instrument, genre, duration, tempo_override,
        )
        return await self._enfileirar_tarefa(
            generation, process_cover_generation_task,
            {"generation_id": generation_id, "upload_url": resolved_upload_url, "audio_weight": audio_weight},
        )

    # ------------------------------------------------------------------
    # Leitura / Eliminação
    # ------------------------------------------------------------------

    async def get_generation(self, generation_id: str, user_id: str) -> Resultado:
        gen = await GenerationQueries.get_generation(db=self.db, generation_id=generation_id)
        # Devolve NaoEncontrada mesmo se existir mas pertencer a outro utilizador,
        # para não confirmar a existência do recurso (prevenção de enumeração).
        if not gen or str(gen.user_id) != user_id:
            return Falha(GeracaoNaoEncontrada(generation_id=generation_id))
        return Sucesso(gen)

    async def delete_generation(self, generation_id: str, user_id: str) -> Resultado:
        resultado = await self.get_generation(generation_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        self._apagar_ficheiros_fisicos(resultado.valor)
        await GenerationQueries.delete_generation(db=self.db, generation_id=generation_id)
        return Sucesso(None)

    # ------------------------------------------------------------------
    # Geração de notação a partir de áudio existente
    # ------------------------------------------------------------------

    async def generate_tablature(self, audio_id: uuid.UUID, user_id: str, tablatura_dir: str) -> Resultado:
        """Gera uma tablatura PDF a partir de um ficheiro de áudio existente."""
        if not all([extrair_midi_do_audio, converter_midi_para_ly, injetar_inteligencia_no_ly,
                    forcar_tablatura_no_ly, compilar_pdf_lilypond, extrair_lista_notas, otimizar_tablatura]):
            return Falha(WorkerIndisponivel(detalhe="Módulos de tablatura não disponíveis."))

        input_resultado = await self._get_audio_path_or_fail(audio_id, user_id)
        if isinstance(input_resultado, Falha):
            return input_resultado
        input_path = input_resultado.valor

        out = Path(tablatura_dir)
        out.mkdir(parents=True, exist_ok=True)
        base     = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        midi_path = out / f"{base}.mid"
        ly_path   = out / f"{base}.ly"
        pdf_path  = out / f"{base}_tablatura.pdf"

        try:
            midi_resultado = await self._extrair_midi_async(input_path, midi_path)
            if isinstance(midi_resultado, Falha):
                return midi_resultado

            if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
                return Falha(FalhaProcessamentoAudio(operacao="conversao_midi_ly"))

            estilo_resultado = await self._aplicar_estilo_tablatura_async(ly_path, midi_resultado.valor)
            if isinstance(estilo_resultado, Falha):
                return estilo_resultado

            compilar_resultado = await self._compilar_pdf_com_fallback_async(midi_path, ly_path)
            if isinstance(compilar_resultado, Falha):
                return compilar_resultado

            ly_pdf_path = ly_path.with_suffix(".pdf")
            if ly_pdf_path.exists():
                ly_pdf_path.replace(pdf_path)
            if not pdf_path.exists():
                return Falha(FalhaProcessamentoAudio(operacao="geracao_pdf"))

            return Sucesso(str(pdf_path))
        finally:
            for p in [midi_path, ly_path]:
                p.unlink(missing_ok=True)

    async def generate_partitura(self, audio_id: uuid.UUID, user_id: str, partitura_dir: str) -> Resultado:
        """Gera uma partitura PDF a partir de um ficheiro de áudio existente."""
        if not all([extrair_midi_do_audio, exportar_pdf_automatico]):
            return Falha(WorkerIndisponivel(detalhe="Módulos de partitura não disponíveis."))

        input_resultado = await self._get_audio_path_or_fail(audio_id, user_id)
        if isinstance(input_resultado, Falha):
            return input_resultado
        input_path = input_resultado.valor

        out = Path(partitura_dir)
        out.mkdir(parents=True, exist_ok=True)
        base      = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        midi_path = out / f"{base}.mid"
        pdf_path  = out / f"{base}_partitura.pdf"

        try:
            midi_resultado = await self._extrair_midi_async(input_path, midi_path)
            if isinstance(midi_resultado, Falha):
                return midi_resultado

            result = await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_path))
            if not result or not pdf_path.exists():
                return Falha(FalhaProcessamentoAudio(operacao="geracao_partitura_pdf"))

            return Sucesso(str(pdf_path))
        finally:
            midi_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    async def _get_audio_or_fail(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        """Busca o áudio e verifica o dono. Não distingue "não existe" de "não é teu"
        para prevenir enumeração de recursos."""
        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            return Falha(AudioNaoEncontrado(audio_id=audio_id))
        return Sucesso(audio)

    async def _get_audio_path_or_fail(self, audio_id: uuid.UUID, user_id: str) -> Resultado:
        """Busca o áudio, verifica o dono e confirma que o ficheiro existe em disco."""
        resultado = await self._get_audio_or_fail(audio_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        input_path = Path(resultado.valor.file_path)
        if not input_path.exists():
            return Falha(AudioNaoEncontrado(audio_id=audio_id))
        return Sucesso(input_path)

    async def _criar_registo_geracao(
        self,
        generation_id: str,
        user_id: str,
        project_id: uuid.UUID,
        audio_id: uuid.UUID,
        prompt: str,
        instrument: str,
        genre: Optional[str],
        duration: Optional[int],
        tempo_override: Optional[int],
    ):
        """Persiste o registo de geração com estado PENDING."""
        return await GenerationQueries.create_generation(
            db=self.db,
            generation_id=generation_id,
            user_id=user_id,
            project_id=project_id,
            audio_file_id=audio_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
        )

    async def _enfileirar_tarefa(self, generation, task, kwargs: dict) -> Resultado:
        """Enfileira uma tarefa Celery e devolve Sucesso((generation, task_id)) ou Falha."""
        try:
            async_result = task.apply_async(kwargs=kwargs, retry=False)
        except Exception as e:
            return Falha(FilaIndisponivel(detalhe=str(e)))
        return Sucesso((generation, async_result.id))

    @staticmethod
    def _apagar_ficheiros_fisicos(gen) -> None:
        """Apaga os ficheiros físicos associados a uma geração, ignorando falhas individuais."""
        for attr in ["audio_file_path", "midi_file_path", "partitura_file_path", "tablatura_file_path"]:
            path_str = getattr(gen, attr, None)
            if path_str:
                try:
                    Path(path_str).unlink(missing_ok=True)
                except Exception as e:
                    print(f"Aviso: não foi possível apagar {path_str}: {e}")

    async def _extrair_midi_async(self, input_path: Path, midi_path: Path) -> Resultado:
        """Extrai MIDI a partir do áudio. Devolve Sucesso(midi_data) ou Falha."""
        midi_result = await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path))
        ok, midi_data, _ = self._normalize_midi_extract_result(midi_result)
        if not ok:
            return Falha(FalhaProcessamentoAudio(operacao="extracao_midi"))
        return Sucesso(midi_data)

    async def _aplicar_estilo_tablatura_async(self, ly_path: Path, midi_data) -> Resultado:
        """Aplica dedilhado inteligente se disponível, caso contrário tablatura padrão."""
        notas_midi = extrair_lista_notas(midi_data) if midi_data else []
        dedilhado  = otimizar_tablatura(notas_midi) if notas_midi else None
        if dedilhado:
            if not await asyncio.to_thread(injetar_inteligencia_no_ly, str(ly_path), dedilhado):
                return Falha(FalhaProcessamentoAudio(operacao="injecao_dedilhado"))
        else:
            if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
                return Falha(FalhaProcessamentoAudio(operacao="tablatura_padrao"))
        return Sucesso(None)

    async def _compilar_pdf_com_fallback_async(self, midi_path: Path, ly_path: Path) -> Resultado:
        """Compila o PDF com LilyPond. Se falhar, tenta fallback com tablatura simples."""
        if await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path)):
            return Sucesso(None)

        # Fallback: regera o .ly com tablatura simples e tenta compilar de novo
        ly_path.unlink(missing_ok=True)
        if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
            return Falha(FalhaProcessamentoAudio(operacao="conversao_midi_ly_fallback"))
        if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
            return Falha(FalhaProcessamentoAudio(operacao="tablatura_padrao_fallback"))
        if not await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path)):
            return Falha(FalhaProcessamentoAudio(operacao="compilacao_pdf"))

        return Sucesso(None)

    @staticmethod
    def _normalize_midi_extract_result(result):
        if isinstance(result, tuple):
            ok       = bool(result[0])
            midi_data = result[1] if len(result) > 1 else None
            error    = result[2] if len(result) > 2 else None
            return ok, midi_data, error
        return bool(result), None, None
