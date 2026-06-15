"""Celery tasks for async Suno generation workflow."""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional

from celery.utils.log import get_task_logger

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.data import AudioQueries, GenerationQueries
from app.data.models import GenerationStatusEnum
from app.services.storage_service import storage

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
    from worker.audio_utils.audio_extractor import extrair_midi_do_audio
    from worker.audio_utils.audio_to_tablature2 import (
        extrair_eventos,
        otimizar_tablatura,
        gerar_ly_tablatura,
        compilar_pdf_lilypond,
    )
except ImportError as e:
    print(f"Warning: Could not import tablature modules: {e}")
    extrair_midi_do_audio = None
    extrair_eventos = None
    otimizar_tablatura = None
    gerar_ly_tablatura = None
    compilar_pdf_lilypond = None

try:
    from worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
except ImportError as e:
    print(f"Warning: Could not import partitura modules: {e}")
    exportar_pdf_automatico = None

try:
    from worker.audio_utils.audio_analyzer import analisar_audio_completo
except ImportError as e:
    print(f"Warning: Could not import audio_analyzer: {e}")
    analisar_audio_completo = None

try:
    from worker.audio_utils.ajuste_bpm import ajustar_bpm_automatico
except ImportError as e:
    print(f"Warning: Could not import ajuste_bpm: {e}")
    ajustar_bpm_automatico = None

try:
    from worker.audio_utils.transposicao import transpor_musica, calcular_semitons_entre_tons
except ImportError as e:
    print(f"Warning: Could not import transposicao: {e}")
    transpor_musica = None
    calcular_semitons_entre_tons = None

try:
    from worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import separador_faixas: {e}")
    extrair_instrumento = None

from worker.ai_models.suno_helpers import (
    build_suno_prompt,
    extract_suno_audio_url,
    extract_suno_task_status,
)

logger = get_task_logger(__name__)

LIMIAR_BPM = 5

AUDIO_OUTPUT_DIR     = Path(settings.GENERATIONS_AUDIO_DIR)
PARTITURA_OUTPUT_DIR = Path(settings.GENERATIONS_PARTITURA_DIR)
TABLATURA_OUTPUT_DIR = Path(settings.GENERATIONS_TABLATURA_DIR)


def _new_task_session() -> tuple:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return Session(), engine


@celery_app.task(bind=True)
def process_generation_task(self, generation_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_process_generation_async(generation_id))


@celery_app.task(bind=True)
def process_cover_generation_task(self, generation_id: str, upload_url: str, audio_weight: float = 0.7):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        _process_cover_generation_async(
            generation_id=generation_id,
            upload_url=upload_url,
            audio_weight=audio_weight,
        )
    )


# ------------------------------------------------------------------
# Notacao (tablatura / partitura) — correm no worker com basic_pitch
# ------------------------------------------------------------------

@celery_app.task(bind=True, time_limit=600)
def generate_tablature_task(self, generation_id: str) -> dict:
    """Gera tablatura PDF no worker (basic_pitch + lilypond). Devolve {"r2_key": "..."}."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_tablature_for_generation_async(generation_id))


@celery_app.task(bind=True, time_limit=600)
def generate_partitura_task(self, generation_id: str) -> dict:
    """Gera partitura PDF no worker (basic_pitch). Devolve {"r2_key": "..."}."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_partitura_for_generation_async(generation_id))


async def _generate_tablature_for_generation_async(generation_id: str) -> dict:
    db, engine = _new_task_session()
    try:
        # Marcar como a processar antes de qualquer trabalho pesado
        await GenerationQueries.update_notation_status(
            db=db, generation_id=generation_id,
            notation_type="tablatura", status="processing",
        )

        generation = await GenerationQueries.get_generation(db=db, generation_id=generation_id)
        if not generation or not generation.audio_storage_key:
            err = f"Generation {generation_id} sem audio disponivel."
            await GenerationQueries.update_notation_status(
                db=db, generation_id=generation_id,
                notation_type="tablatura", status="failed", error_message=err,
            )
            raise ValueError(err)

        TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with storage.temp_download(generation.audio_storage_key) as audio_path:
            base      = f"{audio_path.stem}_{uuid.uuid4().hex[:8]}"
            midi_path = TABLATURA_OUTPUT_DIR / f"{base}.mid"
            ly_path   = TABLATURA_OUTPUT_DIR / f"{base}.ly"
            pdf_final = TABLATURA_OUTPUT_DIR / f"{base}_tablatura.pdf"

            try:
                if not extrair_midi_do_audio:
                    raise RuntimeError("basic_pitch nao disponivel no worker.")

                midi_data = await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))

                eventos = extrair_eventos(midi_data) if midi_data else []
                ded     = otimizar_tablatura([p for _, _, p in eventos]) if eventos else None

                await asyncio.to_thread(gerar_ly_tablatura, midi_data, ded, str(ly_path))
                try:
                    await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
                except RuntimeError:
                    # fallback: sem dedilhado otimizado (LilyPond escolhe as cordas)
                    ly_path.unlink(missing_ok=True)
                    await asyncio.to_thread(gerar_ly_tablatura, midi_data, None, str(ly_path))
                    await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
                ly_pdf = ly_path.with_suffix(".pdf")

                if ly_pdf.exists():
                    ly_pdf.replace(pdf_final)
                if not pdf_final.exists():
                    raise RuntimeError("PDF de tablatura nao foi criado.")

                # Chave R2 estavel e determinista — permite regerar no mesmo path
                r2_key = f"tablature/{generation_id}.pdf"
                storage.delete_file(r2_key)  # apaga versao anterior se existir
                if not storage.upload_file(str(pdf_final), r2_key):
                    raise RuntimeError("Falha ao fazer upload da tablatura para R2.")

                # Persistir chave e marcar completed na DB
                await GenerationQueries.update_notation_status(
                    db=db, generation_id=generation_id,
                    notation_type="tablatura", status="completed",
                    storage_key=r2_key,
                )
                return {"r2_key": r2_key}

            except Exception as exc:
                await GenerationQueries.update_notation_status(
                    db=db, generation_id=generation_id,
                    notation_type="tablatura", status="failed",
                    error_message=str(exc),
                )
                raise
            finally:
                for p in [midi_path, ly_path, pdf_final]:
                    if isinstance(p, Path):
                        p.unlink(missing_ok=True)
    finally:
        await db.close()
        await engine.dispose()


async def _generate_partitura_for_generation_async(generation_id: str) -> dict:
    db, engine = _new_task_session()
    try:
        # Marcar como a processar antes de qualquer trabalho pesado
        await GenerationQueries.update_notation_status(
            db=db, generation_id=generation_id,
            notation_type="partitura", status="processing",
        )

        generation = await GenerationQueries.get_generation(db=db, generation_id=generation_id)
        if not generation or not generation.audio_storage_key:
            err = f"Generation {generation_id} sem audio disponivel."
            await GenerationQueries.update_notation_status(
                db=db, generation_id=generation_id,
                notation_type="partitura", status="failed", error_message=err,
            )
            raise ValueError(err)

        PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        with storage.temp_download(generation.audio_storage_key) as audio_path:
            base      = f"{audio_path.stem}_{uuid.uuid4().hex[:8]}"
            midi_path = PARTITURA_OUTPUT_DIR / f"{base}.mid"
            pdf_final = PARTITURA_OUTPUT_DIR / f"{base}_partitura.pdf"

            try:
                if not extrair_midi_do_audio:
                    raise RuntimeError("basic_pitch nao disponivel no worker.")
                if not exportar_pdf_automatico:
                    raise RuntimeError("exportar_pdf_automatico nao disponivel no worker.")

                midi_data = await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))

                await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_final))
                if not pdf_final.exists():
                    raise RuntimeError("PDF de partitura nao foi criado.")

                # Chave R2 estavel e determinista — permite regerar no mesmo path
                r2_key = f"partitura/{generation_id}.pdf"
                storage.delete_file(r2_key)  # apaga versao anterior se existir
                if not storage.upload_file(str(pdf_final), r2_key):
                    raise RuntimeError("Falha ao fazer upload da partitura para R2.")

                # Persistir chave e marcar completed na DB
                await GenerationQueries.update_notation_status(
                    db=db, generation_id=generation_id,
                    notation_type="partitura", status="completed",
                    storage_key=r2_key,
                )
                return {"r2_key": r2_key}

            except Exception as exc:
                await GenerationQueries.update_notation_status(
                    db=db, generation_id=generation_id,
                    notation_type="partitura", status="failed",
                    error_message=str(exc),
                )
                raise
            finally:
                for p in [midi_path, pdf_final]:
                    if isinstance(p, Path):
                        p.unlink(missing_ok=True)
    finally:
        await db.close()
        await engine.dispose()


@celery_app.task(bind=True, time_limit=600)
def generate_tablature_from_audio_key_task(self, audio_storage_key: str, prefix: str = "audio") -> dict:
    """Gera tablatura a partir de uma R2 key de audio. Devolve {"r2_key": "..."}."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_tablature_from_key_async(audio_storage_key, prefix))


@celery_app.task(bind=True, time_limit=600)
def generate_partitura_from_audio_key_task(self, audio_storage_key: str, prefix: str = "audio") -> dict:
    """Gera partitura a partir de uma R2 key de audio. Devolve {"r2_key": "..."}."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_generate_partitura_from_key_async(audio_storage_key, prefix))


async def _generate_tablature_from_key_async(audio_storage_key: str, prefix: str) -> dict:
    TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with storage.temp_download(audio_storage_key) as audio_path:
        base      = f"{prefix}_{uuid.uuid4().hex[:8]}"
        midi_path = TABLATURA_OUTPUT_DIR / f"{base}.mid"
        ly_path   = TABLATURA_OUTPUT_DIR / f"{base}.ly"
        pdf_final = TABLATURA_OUTPUT_DIR / f"{base}_tablatura.pdf"
        try:
            if not extrair_midi_do_audio:
                raise RuntimeError("basic_pitch nao disponivel no worker.")
            midi_data = await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))
            eventos = extrair_eventos(midi_data) if midi_data else []
            ded     = otimizar_tablatura([p for _, _, p in eventos]) if eventos else None
            await asyncio.to_thread(gerar_ly_tablatura, midi_data, ded, str(ly_path))
            try:
                await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
            except RuntimeError:
                ly_path.unlink(missing_ok=True)
                await asyncio.to_thread(gerar_ly_tablatura, midi_data, None, str(ly_path))
                await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
            ly_pdf = ly_path.with_suffix(".pdf")
            if ly_pdf.exists():
                ly_pdf.replace(pdf_final)
            if not pdf_final.exists():
                raise RuntimeError("PDF de tablatura nao foi criado.")
            r2_key = f"tablature/{prefix}_{uuid.uuid4().hex[:8]}.pdf"
            if not storage.upload_file(str(pdf_final), r2_key):
                raise RuntimeError("Falha ao fazer upload da tablatura para R2.")
            return {"r2_key": r2_key}
        finally:
            for p in [midi_path, ly_path, pdf_final]:
                if isinstance(p, Path):
                    p.unlink(missing_ok=True)


async def _generate_partitura_from_key_async(audio_storage_key: str, prefix: str) -> dict:
    PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with storage.temp_download(audio_storage_key) as audio_path:
        base      = f"{prefix}_{uuid.uuid4().hex[:8]}"
        midi_path = PARTITURA_OUTPUT_DIR / f"{base}.mid"
        pdf_final = PARTITURA_OUTPUT_DIR / f"{base}_partitura.pdf"
        try:
            if not extrair_midi_do_audio:
                raise RuntimeError("basic_pitch nao disponivel no worker.")
            if not exportar_pdf_automatico:
                raise RuntimeError("exportar_pdf_automatico nao disponivel no worker.")
            await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))
            await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(pdf_final))
            if not pdf_final.exists():
                raise RuntimeError("PDF de partitura nao foi criado.")
            r2_key = f"partitura/{prefix}_{uuid.uuid4().hex[:8]}.pdf"
            if not storage.upload_file(str(pdf_final), r2_key):
                raise RuntimeError("Falha ao fazer upload da partitura para R2.")
            return {"r2_key": r2_key}
        finally:
            for p in [midi_path, pdf_final]:
                if isinstance(p, Path):
                    p.unlink(missing_ok=True)


async def _process_generation_async(generation_id: str):
    db = None
    engine = None
    try:
        if not all([iniciar_geracao, verificar_estado, guardar_ficheiro]):
            raise RuntimeError("Suno integration not available in worker runtime.")

        db, engine = _new_task_session()

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

        style_prompt = build_suno_prompt(
            prompt=generation.prompt,
            instrument=generation.instrument,
            genre=generation.genre,
            audio=audio,
            tempo_override=generation.tempo_override,
        )
        title = f"{generation.instrument} {generation.genre} - {generation.prompt[:40]}"

        suno_task_id = await asyncio.to_thread(iniciar_geracao, style_prompt, title)
        if not suno_task_id:
            raise RuntimeError("Falha ao iniciar geracao no Suno.")

        logger.info("Suno generation started: generation_id=%s suno_task_id=%s", generation_id, suno_task_id)

        result = await _poll_and_finalize(db=db, generation_id=generation_id, suno_task_id=suno_task_id)

        audio_path_gerado = Path(result["audio_storage_key"])
        audio_path_final, resumo_ajustes = await _ajustar_audio_gerado_async(
            audio_path_gerado=audio_path_gerado,
            bpm_original=getattr(audio, "bpm", None),
            tom_original=getattr(audio, "key", None),
            generation_id=generation_id,
            instrumento_alvo=generation.instrument,
        )
        logger.info("Pos-processamento concluido para generation %s: %s", generation_id, resumo_ajustes)

        r2_key = f"generations/{generation_id}{audio_path_final.suffix}"
        uploaded = storage.upload_file(str(audio_path_final), r2_key)
        if not uploaded:
            raise RuntimeError(f"Falha ao fazer upload do audio gerado para R2: {r2_key}")
        try:
            audio_path_final.unlink(missing_ok=True)
        except Exception:
            pass

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.COMPLETED,
            audio_key=r2_key,
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            "audio_storage_key": r2_key,
            "partitura_storage_key": result.get("partitura_storage_key"),
            "tablatura_storage_key": result.get("tablatura_storage_key"),
            "pos_processamento": resumo_ajustes,
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
        if db:
            await db.close()
        if engine:
            await engine.dispose()


async def _process_cover_generation_async(generation_id: str, upload_url: str, audio_weight: float = 0.7):
    db = None
    engine = None
    try:
        if not all([iniciar_cover, verificar_estado, guardar_ficheiro]):
            raise RuntimeError("Suno integration not available in worker runtime.")

        db, engine = _new_task_session()

        generation = await GenerationQueries.get_generation(db=db, generation_id=generation_id)
        if not generation:
            logger.warning("Generation %s not found; skipping cover task", generation_id)
            return {"generation_id": generation_id, "status": "not_found"}

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.PROCESSING,
        )

        style_prompt = build_suno_prompt(
            prompt=generation.prompt,
            instrument=generation.instrument,
            genre=generation.genre,
            audio=None,
            tempo_override=generation.tempo_override,
        )
        title = f"Cover {generation.instrument} {generation.genre} - {generation.prompt[:40]}"

        suno_task_id = await asyncio.to_thread(
            iniciar_cover, upload_url, style_prompt, title, True, "V5_5", audio_weight,
        )
        if not suno_task_id:
            raise RuntimeError("Falha ao iniciar cover no Suno.")

        logger.info(
            "Suno cover started: generation_id=%s suno_task_id=%s upload_url=%s audio_weight=%s",
            generation_id, suno_task_id, upload_url, audio_weight,
        )

        result = await _poll_and_finalize(db=db, generation_id=generation_id, suno_task_id=suno_task_id)

        audio = await AudioQueries.get_audio_file(db=db, audio_id=generation.audio_file_id)
        audio_path_gerado = Path(result["audio_storage_key"])
        audio_path_final, resumo_ajustes = await _ajustar_audio_gerado_async(
            audio_path_gerado=audio_path_gerado,
            bpm_original=getattr(audio, "bpm", None) if audio else None,
            tom_original=getattr(audio, "key", None) if audio else None,
            generation_id=generation_id,
            instrumento_alvo=generation.instrument,
        )
        logger.info("Pos-processamento concluido para cover generation %s: %s", generation_id, resumo_ajustes)

        r2_key = f"generations/{generation_id}{audio_path_final.suffix}"
        uploaded = storage.upload_file(str(audio_path_final), r2_key)
        if not uploaded:
            raise RuntimeError(f"Falha ao fazer upload do audio de cover para R2: {r2_key}")
        try:
            audio_path_final.unlink(missing_ok=True)
        except Exception:
            pass

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.COMPLETED,
            audio_key=r2_key,
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            "audio_storage_key": r2_key,
            "partitura_storage_key": result.get("partitura_storage_key"),
            "tablatura_storage_key": result.get("tablatura_storage_key"),
            "pos_processamento": resumo_ajustes,
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
        if engine:
            await engine.dispose()


async def _poll_and_finalize(db, generation_id: str, suno_task_id: str):
    max_attempts = 20

    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(30)

        dados = await asyncio.to_thread(verificar_estado, suno_task_id)
        if not dados:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s returned empty response",
                attempt, max_attempts, generation_id, suno_task_id,
            )
            continue

        if dados.get("code") != 200:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s returned code=%s",
                attempt, max_attempts, generation_id, suno_task_id, dados.get("code"),
            )
            continue

        status_value = extract_suno_task_status(dados)
        if status_value in {"failed", "error", "cancelled", "canceled",
                            "create_task_failed", "generate_audio_failed"}:
            raise RuntimeError(f"Suno task terminou com estado: {status_value}")

        audio_url = extract_suno_audio_url(dados)
        if not audio_url:
            logger.info(
                "Suno poll %s/%s for generation_id=%s suno_task_id=%s still processing (status=%s)",
                attempt, max_attempts, generation_id, suno_task_id, status_value or "unknown",
            )
            continue

        AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        audio_path = AUDIO_OUTPUT_DIR / f"{generation_id}.mp3"

        ok = await asyncio.to_thread(guardar_ficheiro, audio_url, str(audio_path))
        if not ok:
            raise RuntimeError("Falha ao descarregar o audio gerado.")

        logger.info("Audio Suno descarregado para generation %s -- a iniciar pos-processamento.", generation_id)

        return {
            "audio_storage_key": str(audio_path),
            "partitura_storage_key": None,
            "tablatura_storage_key": None,
        }

    raise RuntimeError("Tempo limite de geracao excedido (10 minutos).")


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
        midi_data = await asyncio.to_thread(extrair_midi_do_audio, str(audio_path), str(midi_path))

        if exportar_pdf_automatico:
            p_pdf = PARTITURA_OUTPUT_DIR / f"{generation_id}_partitura.pdf"
            try:
                await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(p_pdf))
                if p_pdf.exists():
                    partitura_path = str(p_pdf)
            except RuntimeError:
                pass  # partitura opcional — continua para tablatura

        if all([gerar_ly_tablatura, compilar_pdf_lilypond, extrair_eventos,
                otimizar_tablatura]) and midi_data:
            ly_path = TABLATURA_OUTPUT_DIR / f"{generation_id}.ly"
            eventos = extrair_eventos(midi_data)
            dedilhado = otimizar_tablatura([p for _, _, p in eventos]) if eventos else None

            await asyncio.to_thread(gerar_ly_tablatura, midi_data, dedilhado, str(ly_path))
            try:
                await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))
            except RuntimeError:
                # fallback: sem dedilhado otimizado (LilyPond escolhe as cordas)
                ly_path.unlink(missing_ok=True)
                await asyncio.to_thread(gerar_ly_tablatura, midi_data, None, str(ly_path))
                await asyncio.to_thread(compilar_pdf_lilypond, str(ly_path))

            t_pdf = ly_path.with_suffix(".pdf")
            if t_pdf.exists():
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


async def _ajustar_audio_gerado_async(
    audio_path_gerado: Path,
    bpm_original: Optional[float],
    tom_original: Optional[str],
    generation_id: str,
    instrumento_alvo: Optional[str] = None,
) -> tuple:
    resumo: dict = {
        "bpm_original": bpm_original,
        "tom_original": tom_original,
        "bpm_gerado": None,
        "tom_gerado": None,
        "ajuste_bpm_aplicado": False,
        "semitons_transpostos": 0,
        "separacao_aplicada": False,
        "erros": [],
    }

    if not all([analisar_audio_completo, ajustar_bpm_automatico, transpor_musica, calcular_semitons_entre_tons]):
        logger.warning("[pos-proc] Modulos de analise/ajuste indisponiveis para generation %s.", generation_id)
        return audio_path_gerado, resumo

    logger.info("[pos-proc] A analisar o audio gerado para generation %s...", generation_id)
    try:
        analise = await asyncio.to_thread(analisar_audio_completo, str(audio_path_gerado))
        bpm_gerado = analise.get("bpm")
        tom_gerado = analise.get("key")
        resumo["bpm_gerado"] = bpm_gerado
        resumo["tom_gerado"] = tom_gerado
        logger.info("[pos-proc] Analise generation %s -> BPM=%s, Tom=%s", generation_id, bpm_gerado, tom_gerado)
    except Exception as exc:
        logger.warning("[pos-proc] Falha na analise do audio gerado (%s): %s", generation_id, exc)
        resumo["erros"].append(f"analise: {exc}")
        return audio_path_gerado, resumo

    caminho_atual = audio_path_gerado

    if bpm_original and bpm_gerado:
        diferenca_bpm = abs(float(bpm_gerado) - float(bpm_original))
        if diferenca_bpm > LIMIAR_BPM:
            logger.info("[pos-proc] BPM incompativel para generation %s -- a ajustar...", generation_id)
            caminho_bpm = audio_path_gerado.parent / f"{generation_id}_bpm.wav"
            try:
                await asyncio.to_thread(ajustar_bpm_automatico, str(caminho_atual), str(caminho_bpm), float(bpm_original))
                if caminho_bpm.exists():
                    if caminho_atual != audio_path_gerado:
                        caminho_atual.unlink(missing_ok=True)
                    caminho_atual = caminho_bpm
                    resumo["ajuste_bpm_aplicado"] = True
            except Exception as exc:
                logger.warning("[pos-proc] Falha no ajuste de BPM para generation %s: %s", generation_id, exc)
                resumo["erros"].append(f"ajuste_bpm: {exc}")

    if tom_original and tom_gerado:
        semitons = calcular_semitons_entre_tons(tom_original, tom_gerado)
        if semitons != 0:
            caminho_trans = audio_path_gerado.parent / f"{generation_id}_trans.wav"
            try:
                await asyncio.to_thread(transpor_musica, str(caminho_atual), str(caminho_trans), semitons, tom_gerado)
                if caminho_trans.exists():
                    if caminho_atual != audio_path_gerado:
                        caminho_atual.unlink(missing_ok=True)
                    caminho_atual = caminho_trans
                    resumo["semitons_transpostos"] = semitons
            except Exception as exc:
                logger.warning("[pos-proc] Falha na transposicao para generation %s: %s", generation_id, exc)
                resumo["erros"].append(f"transposicao: {exc}")

    if extrair_instrumento and instrumento_alvo:
        try:
            await asyncio.to_thread(extrair_instrumento, str(caminho_atual), instrumento_alvo, str(audio_path_gerado.parent))
            nome_base = os.path.splitext(os.path.basename(caminho_atual))[0]
            caminho_separado = audio_path_gerado.parent / f"{nome_base}_{instrumento_alvo.lower().strip()}.wav"
            if caminho_separado.exists():
                resumo["separacao_aplicada"] = True
                if caminho_atual != audio_path_gerado:
                    caminho_atual.unlink(missing_ok=True)
                caminho_atual = caminho_separado
        except Exception as exc:
            logger.warning("[pos-proc] Falha na separacao de faixas para generation %s: %s", generation_id, exc)
            resumo["erros"].append(f"separador_faixas: {exc}")

    if caminho_atual != audio_path_gerado:
        caminho_final = audio_path_gerado.parent / f"{generation_id}.wav"
        try:
            caminho_atual.rename(caminho_final)
            caminho_atual = caminho_final
        except Exception as exc:
            logger.warning("[pos-proc] Nao foi possivel renomear ficheiro final para generation %s: %s", generation_id, exc)
            resumo["erros"].append(f"rename: {exc}")
        try:
            if audio_path_gerado.suffix.lower() != ".wav" and audio_path_gerado.exists():
                audio_path_gerado.unlink()
        except Exception:
            pass

    return caminho_atual, resumo
