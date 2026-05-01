"""Celery tasks for async Suno generation workflow."""

import asyncio
import os
from pathlib import Path
from typing import Any, Optional

from celery.utils.log import get_task_logger

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.data import AudioQueries, GenerationQueries
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
    from worker.audio_utils.transposicao import transpor_musica
except ImportError as e:
    print(f"Warning: Could not import transposicao: {e}")
    transpor_musica = None

try:
    from worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import separador_faixas: {e}")
    extrair_instrumento = None

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes para analise e correcao musical
# ---------------------------------------------------------------------------
_NOTAS_CROMATICAS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_BEMOIS_PARA_SUSTENIDOS = {
    'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
    'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B',
}
LIMIAR_BPM = 5

DEFAULT_GENERATIONS_ROOT = Path(__file__).resolve().parents[1] / "generations"
AUDIO_OUTPUT_DIR     = Path(os.getenv("GENERATIONS_AUDIO_DIR",     str(DEFAULT_GENERATIONS_ROOT / "audio")))
PARTITURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_PARTITURA_DIR", str(DEFAULT_GENERATIONS_ROOT / "partitura")))
TABLATURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_TABLATURA_DIR", str(DEFAULT_GENERATIONS_ROOT / "tablatura")))


def _new_task_session() -> tuple:
    """
    Cria um AsyncSession com NullPool para uso dentro de uma Celery task.

    Cada task Celery corre num event loop proprio (asyncio.new_event_loop()).
    O engine global da aplicacao tem um pool de ligacoes ligado ao loop em que
    foi primeiro usado -- reutiliza-lo noutro loop causa:
        "Future attached to a different loop"

    Com NullPool nao ha pooling: cada ligacao e aberta e fechada a pedido,
    sem dependencia do loop em que o engine foi criado.

    Returns:
        (session, engine) -- ambos devem ser fechados no bloco finally da task.
    """
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return Session(), engine


# ---------------------------------------------------------------------------
# Celery tasks (entry points)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True)
def process_generation_task(self, generation_id: str):
    """Execute Suno generation and notation pipeline for a generation_id."""
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


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------

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
            raise RuntimeError("Falha ao iniciar geracao no Suno.")

        logger.info(
            "Suno generation started: generation_id=%s suno_task_id=%s",
            generation_id, suno_task_id,
        )

        result = await _poll_and_finalize(
            db=db,
            generation_id=generation_id,
            suno_task_id=suno_task_id,
        )

        audio_path_gerado = Path(result["audio_file_path"])
        audio_path_final, resumo_ajustes = await _ajustar_audio_gerado_async(
            audio_path_gerado=audio_path_gerado,
            bpm_original=getattr(audio, "bpm", None),
            tom_original=getattr(audio, "key", None),
            generation_id=generation_id,
            instrumento_alvo=generation.instrument,
        )
        logger.info("Pos-processamento concluido para generation %s: %s", generation_id, resumo_ajustes)

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.COMPLETED,
            audio_path=str(audio_path_final),
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            "audio_file_path": str(audio_path_final),
            "partitura_file_path": result.get("partitura_file_path"),
            "tablatura_file_path": result.get("tablatura_file_path"),
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

        style_prompt = _build_suno_prompt(
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

        result = await _poll_and_finalize(
            db=db,
            generation_id=generation_id,
            suno_task_id=suno_task_id,
        )

        audio = await AudioQueries.get_audio_file(db=db, audio_id=generation.audio_file_id)
        audio_path_gerado = Path(result["audio_file_path"])
        audio_path_final, resumo_ajustes = await _ajustar_audio_gerado_async(
            audio_path_gerado=audio_path_gerado,
            bpm_original=getattr(audio, "bpm", None) if audio else None,
            tom_original=getattr(audio, "key", None) if audio else None,
            generation_id=generation_id,
            instrumento_alvo=generation.instrument,
        )
        logger.info("Pos-processamento concluido para cover generation %s: %s", generation_id, resumo_ajustes)

        await GenerationQueries.update_generation_status(
            db=db,
            generation_id=generation_id,
            status=GenerationStatusEnum.COMPLETED,
            audio_path=str(audio_path_final),
        )

        return {
            "generation_id": generation_id,
            "suno_task_id": suno_task_id,
            "status": "completed",
            "audio_file_path": str(audio_path_final),
            "partitura_file_path": result.get("partitura_file_path"),
            "tablatura_file_path": result.get("tablatura_file_path"),
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
    max_attempts = 20  # ~10 minutes with 30 sec interval

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

        status_value = _extract_suno_task_status(dados)
        if status_value in {"failed", "error", "cancelled", "canceled",
                            "create_task_failed", "generate_audio_failed"}:
            raise RuntimeError(f"Suno task terminou com estado: {status_value}")

        audio_url = _extract_suno_audio_url(dados)
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

        logger.info(
            "Audio Suno descarregado para generation %s -- a iniciar pos-processamento.",
            generation_id,
        )

        return {
            "audio_file_path": str(audio_path),
            "partitura_file_path": None,
            "tablatura_file_path": None,
        }

    raise RuntimeError("Tempo limite de geracao excedido (10 minutos).")


# ---------------------------------------------------------------------------
# Helpers JSON
# ---------------------------------------------------------------------------

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
        "audio_url", "audioUrl", "stream_audio_url", "streamAudioUrl",
        "source_audio_url", "sourceAudioUrl", "audio",
    }
    for node in _walk_json_values(payload):
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
                return value.strip()
    return None


def _extract_suno_task_status(payload: dict) -> Optional[str]:
    try:
        return payload["data"]["status"].strip().lower()
    except (KeyError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Geracao de ficheiros de notacao (nao criticos)
# ---------------------------------------------------------------------------

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
                raise RuntimeError(f"Falha na extracao MIDI: {midi_error}")
            if obter_ultimo_erro_extracao:
                last_error = obter_ultimo_erro_extracao()
                if last_error:
                    raise RuntimeError(f"Falha na extracao MIDI: {last_error}")
            raise RuntimeError("Falha na extracao MIDI.")

        if exportar_pdf_automatico:
            p_pdf = PARTITURA_OUTPUT_DIR / f"{generation_id}_partitura.pdf"
            result = await asyncio.to_thread(exportar_pdf_automatico, str(midi_path), str(p_pdf))
            if result and p_pdf.exists():
                partitura_path = str(p_pdf)

        if all([
            converter_midi_para_ly, injetar_inteligencia_no_ly, forcar_tablatura_no_ly,
            compilar_pdf_lilypond, extrair_lista_notas, otimizar_tablatura,
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


# ---------------------------------------------------------------------------
# Helpers de teoria musical
# ---------------------------------------------------------------------------

def _extrair_nota_raiz(tom: str) -> Optional[str]:
    """Extrai a nota raiz de uma string de tom (ex: 'A Menor' -> 'A', 'C# Maior' -> 'C#')."""
    if not tom:
        return None
    nota = tom.strip().split()[0]
    nota = _BEMOIS_PARA_SUSTENIDOS.get(nota, nota)
    return nota if nota in _NOTAS_CROMATICAS else None


def _calcular_semitons_entre_tons(tom_original: str, tom_gerado: str) -> int:
    """Calcula os semitons necessarios para transpor tom_gerado ate tom_original.
    Devolve um valor no intervalo [-6, +6] (caminho mais curto no circulo cromatico).
    """
    nota_orig = _extrair_nota_raiz(tom_original)
    nota_ger  = _extrair_nota_raiz(tom_gerado)
    if not nota_orig or not nota_ger:
        return 0
    diff = (_NOTAS_CROMATICAS.index(nota_orig) - _NOTAS_CROMATICAS.index(nota_ger)) % 12
    if diff > 6:
        diff -= 12
    return diff


# ---------------------------------------------------------------------------
# Pos-processamento: analise e correccao do audio gerado
# ---------------------------------------------------------------------------

async def _ajustar_audio_gerado_async(
    audio_path_gerado: Path,
    bpm_original: Optional[float],
    tom_original: Optional[str],
    generation_id: str,
    instrumento_alvo: Optional[str] = None,
) -> tuple:
    """Analisa o audio gerado pelo Suno e corrige BPM e tonalidade se necessario.
    Tambem separa a pista do instrumento pedido, tornando-a o audio final.

    Fluxo:
        1. Analisar o audio gerado (BPM + tom).
        2. Se |BPM_gerado - BPM_original| > LIMIAR_BPM -> ajustar tempo.
        3. Se nota raiz diferir -> transpor pelo caminho cromatico mais curto.
        4. Separar a faixa do instrumento se disponivel.
        5. Consolidar num ficheiro .wav final e apagar intermediarios.

    O audio final guardado em audio_file_path e sempre o instrumento isolado
    (pos-processado), nunca o mix completo do Suno.

    Processo inteiramente nao-critico: qualquer falha e registada em log e o
    audio sem correccao e preservado.
    """
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

    if not all([analisar_audio_completo, ajustar_bpm_automatico, transpor_musica]):
        logger.warning(
            "[pos-proc] Modulos de analise/ajuste indisponiveis para generation %s -- a saltar.",
            generation_id,
        )
        return audio_path_gerado, resumo

    # -- 1. Analise do audio gerado
    logger.info("[pos-proc] A analisar o audio gerado para generation %s...", generation_id)
    try:
        analise = await asyncio.to_thread(analisar_audio_completo, str(audio_path_gerado))
        bpm_gerado = analise.get("bpm")
        tom_gerado = analise.get("key")
        resumo["bpm_gerado"] = bpm_gerado
        resumo["tom_gerado"] = tom_gerado
        logger.info(
            "[pos-proc] Analise generation %s -> BPM=%s, Tom=%s",
            generation_id, bpm_gerado, tom_gerado,
        )
    except Exception as exc:
        logger.warning("[pos-proc] Falha na analise do audio gerado (%s): %s", generation_id, exc)
        resumo["erros"].append(f"analise: {exc}")
        return audio_path_gerado, resumo

    caminho_atual = audio_path_gerado

    # -- 2. Ajuste de BPM
    if bpm_original and bpm_gerado:
        diferenca_bpm = abs(float(bpm_gerado) - float(bpm_original))
        if diferenca_bpm > LIMIAR_BPM:
            logger.info(
                "[pos-proc] BPM incompativel para generation %s (gerado=%s, original=%s, D=%.1f) -- a ajustar...",
                generation_id, bpm_gerado, bpm_original, diferenca_bpm,
            )
            caminho_bpm = audio_path_gerado.parent / f"{generation_id}_bpm.wav"
            try:
                await asyncio.to_thread(ajustar_bpm_automatico, str(caminho_atual), str(caminho_bpm), float(bpm_original))
                if caminho_bpm.exists():
                    if caminho_atual != audio_path_gerado:
                        caminho_atual.unlink(missing_ok=True)
                    caminho_atual = caminho_bpm
                    resumo["ajuste_bpm_aplicado"] = True
                    logger.info("[pos-proc] Ajuste de BPM aplicado para generation %s.", generation_id)
                else:
                    logger.warning(
                        "[pos-proc] ajustar_bpm_automatico nao produziu ficheiro para generation %s.",
                        generation_id,
                    )
            except Exception as exc:
                logger.warning("[pos-proc] Falha no ajuste de BPM para generation %s: %s", generation_id, exc)
                resumo["erros"].append(f"ajuste_bpm: {exc}")
        else:
            logger.info(
                "[pos-proc] BPM dentro do limiar para generation %s (D=%.1f <= %d) -- sem ajuste.",
                generation_id, diferenca_bpm, LIMIAR_BPM,
            )

    # -- 3. Transposicao de tonalidade
    if tom_original and tom_gerado:
        semitons = _calcular_semitons_entre_tons(tom_original, tom_gerado)
        if semitons != 0:
            logger.info(
                "[pos-proc] Tom incompativel para generation %s (gerado=%s, original=%s, D=%+d st) -- a transpor...",
                generation_id, tom_gerado, tom_original, semitons,
            )
            caminho_trans = audio_path_gerado.parent / f"{generation_id}_trans.wav"
            try:
                await asyncio.to_thread(transpor_musica, str(caminho_atual), str(caminho_trans), semitons, tom_gerado)
                if caminho_trans.exists():
                    if caminho_atual != audio_path_gerado:
                        caminho_atual.unlink(missing_ok=True)
                    caminho_atual = caminho_trans
                    resumo["semitons_transpostos"] = semitons
                    logger.info(
                        "[pos-proc] Transposicao de %+d semitons aplicada para generation %s.",
                        semitons, generation_id,
                    )
                else:
                    logger.warning(
                        "[pos-proc] transpor_musica nao produziu ficheiro para generation %s.",
                        generation_id,
                    )
            except Exception as exc:
                logger.warning("[pos-proc] Falha na transposicao para generation %s: %s", generation_id, exc)
                resumo["erros"].append(f"transposicao: {exc}")
        else:
            logger.info(
                "[pos-proc] Tonalidade compativel para generation %s (%s ~= %s) -- sem transposicao.",
                generation_id, tom_gerado, tom_original,
            )

    # -- 4. Separacao de pistas
    # O audio final sera apenas a faixa do instrumento pedido; o mix Suno e descartado.
    if extrair_instrumento and instrumento_alvo:
        try:
            logger.info(
                "[pos-proc] A tentar separar a faixa de '%s' para generation %s...",
                instrumento_alvo, generation_id,
            )
            await asyncio.to_thread(
                extrair_instrumento,
                str(caminho_atual),
                instrumento_alvo,
                str(audio_path_gerado.parent),
            )
            nome_base = os.path.splitext(os.path.basename(caminho_atual))[0]
            caminho_separado = audio_path_gerado.parent / f"{nome_base}_{instrumento_alvo.lower().strip()}.wav"

            if caminho_separado.exists():
                resumo["separacao_aplicada"] = True
                logger.info(
                    "[pos-proc] Faixa de '%s' separada com sucesso para %s.",
                    instrumento_alvo, generation_id,
                )
                if caminho_atual != audio_path_gerado:
                    caminho_atual.unlink(missing_ok=True)
                caminho_atual = caminho_separado
                logger.info(
                    "[pos-proc] O audio final sera apenas a faixa de '%s' para %s.",
                    instrumento_alvo, generation_id,
                )
            else:
                logger.warning(
                    "[pos-proc] extrair_instrumento nao produziu o ficheiro esperado para %s.",
                    generation_id,
                )
        except Exception as exc:
            logger.warning(
                "[pos-proc] Falha na separacao de faixas para generation %s: %s",
                generation_id, exc,
            )
            resumo["erros"].append(f"separador_faixas: {exc}")

    # -- 5. Consolidar para caminho final
    if caminho_atual != audio_path_gerado:
        caminho_final = audio_path_gerado.parent / f"{generation_id}.wav"
        try:
            caminho_atual.rename(caminho_final)
            caminho_atual = caminho_final
            logger.info("[pos-proc] Audio final corrigido guardado em %s.", caminho_final)
        except Exception as exc:
            logger.warning(
                "[pos-proc] Nao foi possivel renomear ficheiro final para generation %s: %s",
                generation_id, exc,
            )
            resumo["erros"].append(f"rename: {exc}")
        try:
            if audio_path_gerado.suffix.lower() != ".wav" and audio_path_gerado.exists():
                audio_path_gerado.unlink()
        except Exception:
            pass

    return caminho_atual, resumo


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
        error     = result[2] if len(result) > 2 else None
        return ok, midi_data, error
    return bool(result), None, None
