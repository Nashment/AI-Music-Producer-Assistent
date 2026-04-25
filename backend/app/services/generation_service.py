"""
Generation Service - Music generation orchestration and AI integration
"""

import asyncio
import uuid
from pathlib import Path
from typing import Optional

from app.data import AudioQueries, GenerationQueries
from app.data.models import GenerationStatusEnum

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
    extrair_midi_do_audio = None
    obter_ultimo_erro_extracao = None
    obter_ultimo_erro_compilacao = None
    extrair_lista_notas = None
    otimizar_tablatura = None
    converter_midi_para_ly = None
    injetar_inteligencia_no_ly = None
    forcar_tablatura_no_ly = None
    compilar_pdf_lilypond = None

try:
    from worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
    from worker.audio_utils.audio_to_partitura import obter_ultimo_erro_partitura
except ImportError as e:
    print(f"Warning: Could not import partitura modules: {e}")
    exportar_pdf_automatico = None
    obter_ultimo_erro_partitura = None


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
    ):
        """Cria registo PENDING e enfileira processamento assíncrono no Celery."""
        try:
            from worker.tasks.generation_tasks import process_generation_task
        except ImportError as e:
            raise NotImplementedError(f"Celery worker integration not available: {e}")

        # Validar que o áudio pertence ao utilizador
        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado ou sem permissão.")

        generation_id = str(uuid.uuid4())

        # Guardar na base de dados
        generation = await GenerationQueries.create_generation(
            db=self.db,
            generation_id=generation_id,
            user_id=uuid.UUID(user_id),
            project_id=project_id,
            audio_file_id=audio_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
        )

        try:
            # retry=False evita bloqueio prolongado quando o broker está indisponível
            async_result = process_generation_task.apply_async(
                kwargs={"generation_id": generation_id},
                retry=False,
            )
        except Exception as e:
            raise RuntimeError(f"Falha ao enfileirar geração no Celery/Redis: {e}")

        return generation, async_result.id

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
    ):
        """Cria registo PENDING e enfileira cover generation assíncrona no Celery."""
        try:
            from worker.tasks.generation_tasks import process_cover_generation_task
        except ImportError as e:
            raise NotImplementedError(f"Celery worker integration not available: {e}")

        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado ou sem permissão.")

        resolved_upload_url = upload_url or audio.file_path
        if not isinstance(resolved_upload_url, str) or not resolved_upload_url.startswith(("http://", "https://")):
            raise ValueError("Cover exige upload_url público (http/https).")

        if audio_weight < 0.0 or audio_weight > 1.0:
            raise ValueError("audio_weight deve estar entre 0.0 e 1.0.")

        generation_id = str(uuid.uuid4())

        generation = await GenerationQueries.create_generation(
            db=self.db,
            generation_id=generation_id,
            user_id=uuid.UUID(user_id),
            project_id=project_id,
            audio_file_id=audio_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
        )

        try:
            async_result = process_cover_generation_task.apply_async(
                kwargs={
                    "generation_id": generation_id,
                    "upload_url": resolved_upload_url,
                    "audio_weight": audio_weight,
                },
                retry=False,
            )
        except Exception as e:
            raise RuntimeError(f"Falha ao enfileirar cover no Celery/Redis: {e}")

        return generation, async_result.id

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    async def get_generation(self, generation_id: str, user_id: str):
        gen = await GenerationQueries.get_generation(db=self.db, generation_id=generation_id)
        if not gen:
            raise ValueError("Geração não encontrada.")
        if str(gen.user_id) != user_id:
            raise PermissionError("Acesso negado.")
        return gen

    async def delete_generation(self, generation_id: str, user_id: str):
        gen = await self.get_generation(generation_id, user_id)
        # Apagar ficheiros gerados do disco
        for attr in ["audio_file_path", "midi_file_path", "partitura_file_path", "tablatura_file_path"]:
            path_str = getattr(gen, attr, None)
            if path_str:
                p = Path(path_str)
                if p.exists():
                    try:
                        p.unlink()
                    except Exception as e:
                        print(f"Aviso: não foi possível apagar {path_str}: {e}")
        await GenerationQueries.delete_generation(db=self.db, generation_id=generation_id)

    # ------------------------------------------------------------------
    # Geração de notação a partir de áudio existente
    # ------------------------------------------------------------------

    async def generate_tablature(self, audio_id: uuid.UUID, user_id: str, tablatura_dir: str) -> str:
        """Gera uma tablatura PDF a partir de um ficheiro de áudio existente."""
        if not all([
            extrair_midi_do_audio,
            converter_midi_para_ly,
            injetar_inteligencia_no_ly,
            forcar_tablatura_no_ly,
            compilar_pdf_lilypond,
            extrair_lista_notas,
            otimizar_tablatura,
        ]):
            raise NotImplementedError("Tablature generation not available.")

        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado.")

        input_path = Path(audio.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        base = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        out = Path(tablatura_dir)
        out.mkdir(parents=True, exist_ok=True)
        midi_path = out / f"{base}.mid"
        ly_path = out / f"{base}.ly"
        pdf_path = out / f"{base}_tablatura.pdf"

        try:
            midi_result = await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path))
            midi_ok, midi_data, midi_error = self._normalize_midi_extract_result(midi_result)
            if not midi_ok:
                if midi_error:
                    raise RuntimeError(f"Falha na extração MIDI: {midi_error}")
                if obter_ultimo_erro_extracao:
                    last_error = obter_ultimo_erro_extracao()
                    if last_error:
                        raise RuntimeError(f"Falha na extração MIDI: {last_error}")
                raise RuntimeError("Falha na extração MIDI.")
            if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
                raise RuntimeError("Falha na conversão MIDI→LilyPond.")

            if not midi_data:
                raise RuntimeError("Falha ao obter dados MIDI para otimização de tablatura.")
            notas_midi = extrair_lista_notas(midi_data)
            dedilhado = otimizar_tablatura(notas_midi)
            if not dedilhado:
                print("Aviso: dedilhado otimizado indisponível, a gerar tablatura padrão.")
                dedilhado = None

            if dedilhado:
                if not await asyncio.to_thread(injetar_inteligencia_no_ly, str(ly_path), dedilhado):
                    raise RuntimeError("Falha na formatação de tablatura.")
            else:
                if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
                    raise RuntimeError("Falha na formatação de tablatura padrão.")

            compiled = await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
            if not compiled:
                print("Aviso: compilação LilyPond falhou na versão atual, a tentar fallback padrão.")
                if ly_path.exists():
                    ly_path.unlink(missing_ok=True)
                if not await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path)):
                    raise RuntimeError("Falha na conversão MIDI→LilyPond (fallback).")
                if not await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path)):
                    raise RuntimeError("Falha na formatação de tablatura padrão (fallback).")
                compiled = await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
                if not compiled:
                    compile_error = obter_ultimo_erro_compilacao() if obter_ultimo_erro_compilacao else None
                    if compile_error:
                        raise RuntimeError(f"Falha na compilação PDF: {compile_error}")
                    raise RuntimeError("Falha na compilação PDF.")

            ly_pdf_path = ly_path.with_suffix(".pdf")
            if ly_pdf_path.exists():
                ly_pdf_path.replace(pdf_path)
            if not pdf_path.exists():
                compile_error = obter_ultimo_erro_compilacao() if obter_ultimo_erro_compilacao else None
                if compile_error:
                    raise RuntimeError(f"PDF não foi gerado: {compile_error}")
                raise RuntimeError("PDF não foi gerado.")
            return str(pdf_path)
        finally:
            for p in [midi_path, ly_path]:
                if p.exists():
                    p.unlink(missing_ok=True)

    async def generate_partitura(self, audio_id: uuid.UUID, user_id: str, partitura_dir: str) -> str:
        """Gera uma partitura PDF a partir de um ficheiro de áudio existente."""
        if not all([extrair_midi_do_audio, exportar_pdf_automatico]):
            raise NotImplementedError("Partitura generation not available.")

        audio = await AudioQueries.get_audio_file(db=self.db, audio_id=audio_id)
        if not audio or str(audio.user_id) != user_id:
            raise ValueError("Áudio não encontrado.")

        input_path = Path(audio.file_path)
        if not input_path.exists():
            raise FileNotFoundError("Ficheiro de áudio não encontrado no disco.")

        base = f"{input_path.stem}_{uuid.uuid4().hex[:8]}"
        out = Path(partitura_dir)
        out.mkdir(parents=True, exist_ok=True)
        midi_path = out / f"{base}.mid"
        pdf_path = out / f"{base}_partitura.pdf"

        try:
            midi_result = await asyncio.to_thread(extrair_midi_do_audio, str(input_path), str(midi_path))
            midi_ok, _, midi_error = self._normalize_midi_extract_result(midi_result)
            if not midi_ok:
                if midi_error:
                    raise RuntimeError(f"Falha na extração MIDI: {midi_error}")
                if obter_ultimo_erro_extracao:
                    last_error = obter_ultimo_erro_extracao()
                    if last_error:
                        raise RuntimeError(f"Falha na extração MIDI: {last_error}")
                raise RuntimeError("Falha na extração MIDI.")
            result = await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_path))
            if not result or not pdf_path.exists():
                partitura_error = obter_ultimo_erro_partitura() if obter_ultimo_erro_partitura else None
                if partitura_error:
                    raise RuntimeError(f"Falha na geração da partitura PDF: {partitura_error}")
                raise RuntimeError("Falha na geração da partitura PDF.")
            return str(pdf_path)
        finally:
            if midi_path.exists():
                midi_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------


    @staticmethod
    def _normalize_midi_extract_result(result):
        if isinstance(result, tuple):
            ok = bool(result[0])
            midi_data = result[1] if len(result) > 1 else None
            error = result[2] if len(result) > 2 else None
            return ok, midi_data, error
        return bool(result), None, None
