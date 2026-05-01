"""
Audio endpoints - Audio upload, analysis and processing

Responsabilidades desta camada:
  - Receber pedidos HTTP e validar os parametros de entrada.
  - Chamar o servico e obter um Resultado[AudioErro, T].
  - Mapear AudioErro -> HTTP Problem Details (_handle_audio_error).
  - Construir a resposta HTTP de sucesso.

O que NAO esta aqui:
  - Logica de negocio (esta no servico).
  - Excecoes genericas do Python (o servico nunca as lanca para ca).
"""

import os
import shutil
import uuid
from typing import Callable
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, status, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import AudioService
from app.api.dependencies import get_db, get_current_user_id
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
    AudioErro,
)
from app.domain.dtos.endpoints.audio import AudioAnalysisResponse, AudioListResponse

router = APIRouter()

_DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[3] / "worker" / "uploads" / "audio"
UPLOAD_DIR = Path(os.getenv("AUDIO_UPLOAD_DIR", str(_DEFAULT_UPLOAD_DIR)))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# Tratamento de erros HTTP
# ===========================================================================

def _problem_json(status_code: int, type_slug: str, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type":     f"/errors/{type_slug}",
            "title":    title,
            "status":   status_code,
            "detail":   detail,
            "instance": instance,
        },
        media_type="application/problem+json",
    )


def _handle_audio_error(erro: AudioErro, instance: str) -> JSONResponse:
    match erro:
        case AudioNaoEncontrado():
            return _problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O audio referenciado nao foi encontrado.", instance)
        case ProjetoNaoEncontrado():
            return _problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O projeto referenciado nao foi encontrado.", instance)
        case FormatoAudioInvalido(extensao=ext):
            return _problem_json(400, "formato-invalido", "Formato de Audio Invalido",
                f"Formato '{ext}' nao suportado. Use .mp3 ou .wav.", instance)
        case FicheiroAudioGrande(tamanho_mb=mb):
            return _problem_json(400, "ficheiro-demasiado-grande", "Ficheiro Demasiado Grande",
                f"O ficheiro ({mb:.1f}MB) excede o limite de 50MB.", instance)
        case FicheiroFisicoNaoEncontrado():
            return _problem_json(404, "ficheiro-nao-encontrado", "Ficheiro Nao Encontrado",
                "O ficheiro fisico nao existe no servidor.", instance)
        case ModuloAudioIndisponivel():
            return _problem_json(501, "funcionalidade-indisponivel", "Funcionalidade Nao Disponivel",
                "Este processamento de audio nao esta disponivel neste ambiente.", instance)
        case FalhaProcessamento():
            return _problem_json(422, "erro-processamento", "Erro de Processamento",
                "Nao foi possivel processar o audio.", instance)
        case IntervaloInvalido(detalhe=d):
            return _problem_json(400, "intervalo-invalido", "Intervalo Invalido", d, instance)
        case _:
            return _problem_json(500, "erro-interno", "Erro Interno",
                "Ocorreu um erro inesperado no servico de audio.", instance)


def _handle_result(
    resultado: Sucesso | Falha,
    instance: str,
    success_factory: Callable,
) -> Response:
    match resultado:
        case Falha(erro=erro):
            return _handle_audio_error(erro, instance)
        case Sucesso(valor=valor):
            return success_factory(valor)


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get("/project/{project_id}", response_model=AudioListResponse)
async def list_project_audios(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """List all audio files belonging to a project."""
    resultado = await AudioService(db).get_project_audios(project_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/project/{project_id}",
        success_factory=lambda audios: AudioListResponse(audios=audios, total=len(audios)),
    )


@router.post("/project/{project_id}/upload", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Upload and analyze audio file."""
    safe_filename = f"{uuid.uuid4()}_{file.filename or 'upload'}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        return _problem_json(500, "erro-interno", "Erro Interno",
                             "Erro ao guardar o ficheiro no disco.",
                             f"/api/v1/audio/project/{project_id}/upload")
    finally:
        file.file.close()

    resultado = await AudioService(db).upload_and_analyze_audio(
        file_path=str(file_path),
        user_id=str(user_id),
        project_id=project_id,
    )

    # Limpa o ficheiro do disco se o servico falhou
    if isinstance(resultado, Falha) and file_path.exists():
        file_path.unlink()

    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/project/{project_id}/upload",
        success_factory=lambda record: record,
    )


@router.get("/analysis/{audio_id}", response_model=AudioAnalysisResponse)
async def get_audio_analysis(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get previously computed audio analysis metadata."""
    resultado = await AudioService(db).get_audio(audio_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/analysis/{audio_id}",
        success_factory=lambda record: record,
    )


@router.get("/{audio_id}")
async def get_audio_file(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Download the actual audio file."""
    resultado = await AudioService(db).get_audio_for_download(audio_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/{audio_id}",
        success_factory=lambda record: FileResponse(
            path=record.file_path,
            media_type="audio/mpeg",
            filename=Path(record.file_path).name,
        ),
    )


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete audio file from DB and disk."""
    resultado = await AudioService(db).delete_audio(audio_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/{audio_id}",
        success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )


@router.post("/{audio_id}/adjust-bpm", response_model=AudioAnalysisResponse)
async def adjust_audio_bpm(
    audio_id: uuid.UUID,
    target_bpm: float = 120.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Adjust BPM of audio file (overwrites original)."""
    resultado = await AudioService(db).adjust_bpm(audio_id, str(user_id), target_bpm, str(UPLOAD_DIR))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/{audio_id}/adjust-bpm",
        success_factory=lambda record: record,
    )


@router.post("/{audio_id}/cut", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def cut_audio(
    audio_id: uuid.UUID,
    inicio_segundos: float = 0.0,
    fim_segundos: float = 30.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Cut audio between inicio_segundos and fim_segundos."""
    resultado = await AudioService(db).cut_audio_file(
        audio_id, str(user_id), inicio_segundos, fim_segundos, str(UPLOAD_DIR)
    )
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/{audio_id}/cut",
        success_factory=lambda record: record,
    )


@router.post("/{audio_id}/separate-tracks")
async def separate_audio_tracks(
    audio_id: uuid.UUID,
    instrument: str = "guitarra",
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Separate instrument tracks from audio."""
    resultado = await AudioService(db).separate_tracks(audio_id, str(user_id), instrument, str(UPLOAD_DIR))
    return _handle_result(
        resultado,
        instance=f"/api/v1/audio/{audio_id}/separate-tracks",
        success_factory=lambda output_path: FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=Path(output_path).name,
        ),
    )
