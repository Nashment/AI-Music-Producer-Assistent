"""Celery tasks for async Suno generation workflow."""

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

from celery.utils.log import get_task_logger

from app.data import AudioQueries, GenerationQueries
from app.data.database import db as db_manager
from app.data.models import GenerationStatusEnum

from worker.celery_app import celery_app

try:
    from worker.ai_models.suno_audio_generator import (
        iniciar_geracao,
        iniciar_cover,
        verificar_estado,
        guardar_ficheiro,
    )
except ImportError as e:
    print(f"Warning: Could not import suno worker modules: {e}")
    iniciar_geracao = None
    iniciar_cover = None
    verificar_estado = None
    guardar_ficheiro = None

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
except ImportError as e:
    print(f"Warning: Could not import partitura modules: {e}")
    exportar_pdf_automatico = None

logger = get_task_logger(__name__)

DEFAULT_GENERATIONS_ROOT = Path(__file__).resolve().parents[1] / "generations"
AUDIO_OUTPUT_DIR = Path(os.getenv("GENERATIONS_AUDIO_DIR", str(DEFAULT_GENERATIONS_ROOT / "audio")))
PARTITURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_PARTITURA_DIR", str(DEFAULT_GENERATIONS_ROOT / "partitura")))
TABLATURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_TABLATURA_DIR", str(DEFAULT_GENERATIONS_ROOT / "tablatura")))


@celery_app.task(bind=True)
def process_generation_task(self, generation_id: str):
    """Execute Suno generation and notation pipeline for a generation_id."""
    # FIX: asyncio.get_event_loop() está deprecated no Python 3.10+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    return loop.run_until_complete(_process_generation_async(generation_id))


@celery_app.task(bind=True)
def process_cover_generation_task(self, generation_id: str, upload_url: str, audio_weight: float = 0.7):
    """Execute Suno cover generation pipeline for a generation_id."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        _process_cover_generation_async(
            generation_id=generation_id,
            upload_url=upload_url,
            audio_weight=audio_weight,
        )
    )


async def _process_generation_async(generation_id: str):
    # FIX: proteger o caso em que get_session() falha antes de db ser atribuído
    db = None
    try:
        if not all([iniciar_geracao, verificar_estado, guardar_ficheiro]):
            raise RuntimeError("Suno integration not available in worker runtime.")

        db = db_manager.get_session()

        generation = await GenerationQueries.get_generation(db=db, generation_id=generation_id)
        if not generation:
            logger.warning("Generation %s not found; skipping task", generation_id)
            return {"generation_id": generation_id, "status": "not_found"}

        audio = await AudioQueries.get_audio_file(db=db, audio_id=generation.audio_file_id)
        if not audio:
            raise RuntimeError("Audio reference not found for generation.")

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.PROCESSING,
        )

        style_prompt = _build_suno_prompt(
            prompt=generation.prompt,
            instrument=generation.instrument,
            genre=generation.genre,
            audio=audio,
            tempo_override=generation.tempo_override,
        )
        title = f"{generation.instrument} {generation.genre} - {generation.prompt[:40]}"

        suno_task_id = await asyncio.to_thread(iniciar_geracao, style_prompt, title)
        if not suno_task_id:
            raise RuntimeError("Falha ao iniciar geração no Suno.")

        logger.info(
            "Suno generation started: generation_id=%s suno_task_id=%s",
            generation_id,
            suno_task_id,
        )

        result = await _poll_and_finalize(
            db=db,
            generation_id=generation_id,
            suno_task_id=suno_task_id,
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            **result,
        }
    except Exception as e:
        logger.exception("Failed to process generation %s", generation_id)
        try:
            if db:
                await GenerationQueries.update_generation_status(
                    db=db,
                    generation_id=generation_id,
                    status=GenerationStatusEnum.FAILED,
                    error_message=str(e),
                )
        except Exception:
            logger.exception("Failed to persist FAILED status for %s", generation_id)
        raise
    finally:
        # FIX: só fecha a sessão se ela foi efectivamente criada
        if db:
            await db.close()


async def _process_cover_generation_async(generation_id: str, upload_url: str, audio_weight: float = 0.7):
    db = None
    try:
        if not all([iniciar_cover, verificar_estado, guardar_ficheiro]):
            raise RuntimeError("Suno integration not available in worker runtime.")

        db = db_manager.get_session()

        generation = await GenerationQueries.get_generation(db=db, generation_id=generation_id)
        if not generation:
            logger.warning("Generation %s not found; skipping cover task", generation_id)
            return {"generation_id": generation_id, "status": "not_found"}

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.PROCESSING,
        )

        style_prompt = _build_suno_prompt(
            prompt=generation.prompt,
            instrument=generation.instrument,
            genre=generation.genre,
            audio=None,
            tempo_override=generation.tempo_override,
        )
        title = f"Cover {generation.instrument} {generation.genre} - {generation.prompt[:40]}"

        suno_task_id = await asyncio.to_thread(
            iniciar_cover,
            upload_url,
            style_prompt,
            title,
            True,
            "V5_5",
            audio_weight,
        )
        if not suno_task_id:
            raise RuntimeError("Falha ao iniciar cover no Suno.")

        logger.info(
            "Suno cover started: generation_id=%s suno_task_id=%s upload_url=%s audio_weight=%s",
            generation_id,
            suno_task_id,
            upload_url,
            audio_weight,
        )

        result = await _poll_and_finalize(
            db=db,
            generation_id=generation_id,
            suno_task_id=suno_task_id,
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            **result,
        }
    except Exception as e:
        logger.exception("Failed to process cover generation %s", generation_id)
        try:
            if db:
                await GenerationQueries.update_generation_status(
                    db=db,
                    generation_id=generation_id,
                    status=GenerationStatusEnum.FAILED,
                    error_message=str(e),
                )
        except Exception:
            logger.exception("Failed to persist FAILED status for cover generation %s", generation_id)
        raise
    finally:
        if db:
            await db.close()


async def _poll_and_finalize(db, generation_id: str, suno_task_id: str):
    max_attempts = 20  # ~10 minutes with 30 sec interval

    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(30)

        dados = await asyncio.to_thread(verificar_estado, suno_task_id)
        if not dados:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s returned empty response",
                attempt,
                max_attempts,
                generation_id,
                suno_task_id,
            )
            continue

        if dados.get("code") != 200:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s returned code=%s",
                attempt,
                max_attempts,
                generation_id,
                suno_task_id,
                dados.get("code"),
            )
            continue

        status_value = _extract_suno_task_status(dados)
        if status_value in {"failed", "error", "cancelled", "canceled",
                            "create_task_failed", "generate_audio_failed"}:
            raise RuntimeError(f"Suno task terminou com estado: {status_value}")

        audio_url = _extract_suno_audio_url(dados)
        if not audio_url:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s still processing (status=%s)",
                attempt,
                max_attempts,
                generation_id,
                suno_task_id,
                status_value or "unknown",
            )
            continue

        AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        audio_path = AUDIO_OUTPUT_DIR / f"{generation_id}.mp3"

        ok = await asyncio.to_thread(guardar_ficheiro, audio_url, str(audio_path))
        if not ok:
            raise RuntimeError("Falha ao descarregar o áudio gerado.")

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.COMPLETED,
            audio_path=str(audio_path),
        )

        logger.info(
            "Generation %s completed with audio only; notation generation is deferred to post-cut step",
            generation_id,
        )

        return {
            "audio_file_path": str(audio_path),
            "partitura_file_path": None,
            "tablatura_file_path": None,
        }

    raise RuntimeError("Tempo limite de geração excedido (10 minutos).")


def _walk_json_values(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_json_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_json_values(item)


def _extract_suno_audio_url(payload: dict) -> Optional[str]:
    keys = {
        "audio_url",
        "audioUrl",
        "stream_audio_url",
        "streamAudioUrl",
        "source_audio_url",
        "sourceAudioUrl",
        "audio",
    }
    for node in _walk_json_values(payload):
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
                return value.strip()
    return None


def _extract_suno_task_status(payload: dict) -> Optional[str]:
    # FIX: ler directamente de data.status em vez de percorrer todo o JSON,
    # evitando apanhar um campo "status" de um subnível que não é o da tarefa.
    try:
        return payload["data"]["status"].strip().lower()
    except (KeyError, AttributeError):
        return None


async def _generate_notation_files(generation_id: str, audio_path: Path):
    midi_path: Optional[Path] = None
    partitura_path: Optional[str] = None
    tablatura_path: Optional[str] = None
    ly_path: Optional[Path] = None

    if not extrair_midi_do_audio:
        return None, None

    PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    midi_path = PARTITURA_OUTPUT_DIR / f"{generation_id}.mid"

    try:
        midi_result = await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))
        midi_ok, midi_data, midi_error = _normalize_midi_extract_result(midi_result)
        if not midi_ok:
            if midi_error:
                raise RuntimeError(f"Falha na extração MIDI: {midi_error}")
            if obter_ultimo_erro_extracao:
                last_error = obter_ultimo_erro_extracao()
                if last_error:
                    raise RuntimeError(f"Falha na extração MIDI: {last_error}")
            raise RuntimeError("Falha na extração MIDI.")

        if exportar_pdf_automatico:
            p_pdf = PARTITURA_OUTPUT_DIR / f"{generation_id}_partitura.pdf"
            result = await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(p_pdf))
            if result and p_pdf.exists():
                partitura_path = str(p_pdf)

        if all([
            converter_midi_para_ly,
            injetar_inteligencia_no_ly,
            forcar_tablatura_no_ly,
            compilar_pdf_lilypond,
            extrair_lista_notas,
            otimizar_tablatura,
        ]):
            ly_path = TABLATURA_OUTPUT_DIR / f"{generation_id}.ly"
            ok_ly = await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path))
            if ok_ly:
                if midi_data:
                    notas_midi = extrair_lista_notas(midi_data)
                    dedilhado = otimizar_tablatura(notas_midi)
                    if dedilhado:
                        await asyncio.to_thread(injetar_inteligencia_no_ly, str(ly_path), dedilhado)
                    else:
                        await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path))
                else:
                    await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path))

                ok_pdf = await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
                t_pdf = ly_path.with_suffix(".pdf")

                if not ok_pdf:
                    if ly_path.exists():
                        ly_path.unlink(missing_ok=True)
                    ok_ly_fallback = await asyncio.to_thread(converter_midi_para_ly, str(midi_path), str(ly_path))
                    if ok_ly_fallback:
                        await asyncio.to_thread(forcar_tablatura_no_ly, str(ly_path))
                        ok_pdf = await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
                        t_pdf = ly_path.with_suffix(".pdf")

                if ok_pdf and t_pdf.exists():
                    final_t_pdf = TABLATURA_OUTPUT_DIR / f"{generation_id}_tablatura.pdf"
                    t_pdf.replace(final_t_pdf)
                    tablatura_path = str(final_t_pdf)

    except Exception as e:
        logger.warning("Non-critical notation generation error for %s: %s", generation_id, e)
    finally:
        if midi_path and midi_path.exists():
            midi_path.unlink(missing_ok=True)
        if ly_path and ly_path.exists():
            ly_path.unlink(missing_ok=True)

    return partitura_path, tablatura_path


def _build_suno_prompt(prompt: str, instrument: str, genre: Optional[str], audio, tempo_override: Optional[int]) -> str:
    bpm = tempo_override or getattr(audio, "bpm", None)
    key = getattr(audio, "key", None)
    time_sig = getattr(audio, "time_signature", None)

    parts = [prompt, f"{instrument} solo"]
    if genre:
        parts.append(genre)
    if bpm:
        parts.append(f"{bpm} BPM")
    if key:
        parts.append(f"Key of {key}")
    if time_sig:
        parts.append(f"{time_sig} time signature")
    parts.append("professional quality")

    return ", ".join(parts)


def _normalize_midi_extract_result(result):
    if isinstance(result, tuple):
        ok = bool(result[0])
        midi_data = result[1] if len(result) > 1 else None
        error = result[2] if len(result) > 2 else None
        return ok, midi_data, error
    return bool(result), None, None