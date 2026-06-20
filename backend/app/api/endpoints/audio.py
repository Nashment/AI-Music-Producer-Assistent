"""
Audio endpoints - Audio upload, analysis and processing
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, status, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import AudioService
from app.api.dependencies import get_db, get_current_user_id
from app.api.responses import problem_json, handle_result
from app.domain.result import Falha
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
from app.domain.dtos.endpoints.audio import AudioAnalysisResponse, AudioListResponse, AudioRename

router = APIRouter()

UPLOAD_DIR = Path(settings.AUDIO_UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



def _handle_audio_error(erro: AudioErro, instance: str) -> JSONResponse:
    match erro:
        case AudioNaoEncontrado():
            return problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O audio referenciado nao foi encontrado.", instance)
        case ProjetoNaoEncontrado():
            return problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O projeto referenciado nao foi encontrado.", instance)
        case FormatoAudioInvalido(extensao=ext):
            return problem_json(400, "formato-invalido", "Formato de Audio Invalido",
                f"Formato '{ext}' nao suportado. Use .mp3 ou .wav.", instance)
        case FicheiroAudioGrande(tamanho_mb=mb):
            return problem_json(400, "ficheiro-demasiado-grande", "Ficheiro Demasiado Grande",
                f"O ficheiro ({mb:.1f}MB) excede o limite de 50MB.", instance)
        case FicheiroFisicoNaoEncontrado():
            return problem_json(404, "ficheiro-nao-encontrado", "Ficheiro Nao Encontrado",
                "O ficheiro nao existe no armazenamento.", instance)
        case ModuloAudioIndisponivel():
            return problem_json(501, "funcionalidade-indisponivel", "Funcionalidade Nao Disponivel",
                "Este processamento de audio nao esta disponivel neste ambiente.", instance)
        case FalhaProcessamento():
            return problem_json(422, "erro-processamento", "Erro de Processamento",
                "Nao foi possivel processar o audio.", instance)
        case IntervaloInvalido(detalhe=d):
            return problem_json(400, "intervalo-invalido", "Intervalo Invalido", d, instance)
        case _:
            return problem_json(500, "erro-interno", "Erro Interno",
                "Ocorreu um erro inesperado no servico de audio.", instance)



@router.get("/project/{project_id}", response_model=AudioListResponse)
async def list_project_audios(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await AudioService(db).get_project_audios(project_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/audio/project/{project_id}", on_error=_handle_audio_error, success_factory=lambda audios: AudioListResponse(audios=audios, total=len(audios)),
    )


@router.post("/project/{project_id}/upload", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    project_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Upload, analise e guarda o audio no R2."""
    safe_filename = f"{uuid.uuid4()}_{file.filename or 'upload'}"
    file_path = UPLOAD_DIR / safe_filename

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception:
        return problem_json(500, "erro-interno", "Erro Interno",
                             "Erro ao guardar o ficheiro temporariamente.",
                             f"/api/v1/audio/project/{project_id}/upload")
    finally:
        file.file.close()

    resultado = await AudioService(db).upload_and_analyze_audio(
        file_path=str(file_path),
        user_id=str(user_id),
        project_id=project_id,
    )

    # Se o servico falhou e o ficheiro temporario ainda existe, apaga-o
    if isinstance(resultado, Falha) and file_path.exists():
        file_path.unlink()

    return handle_result(resultado, instance=f"/api/v1/audio/project/{project_id}/upload", on_error=_handle_audio_error, success_factory=lambda record: record,
    )


@router.get("/analysis/{audio_id}", response_model=AudioAnalysisResponse)
async def get_audio_analysis(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await AudioService(db).get_audio(audio_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/audio/analysis/{audio_id}", on_error=_handle_audio_error, success_factory=lambda record: record,
    )


@router.get("/{audio_id}")
async def get_audio_file(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve a presigned URL do R2 como JSON.
    O cliente faz o segundo pedido directamente ao R2 sem o header Authorization,
    evitando o conflito de autenticacao dupla que o R2 rejeita.
    """
    resultado = await AudioService(db).get_audio_download_url(audio_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}", on_error=_handle_audio_error, success_factory=lambda url: JSONResponse(content={"url": url}),
    )


@router.patch("/{audio_id}", response_model=AudioAnalysisResponse)
async def rename_audio(
    audio_id: uuid.UUID,
    body: AudioRename,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Renomeia um audio (nome amigavel). display_name vazio limpa o nome."""
    resultado = await AudioService(db).rename_audio(audio_id, str(user_id), body.display_name)
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}", on_error=_handle_audio_error, success_factory=lambda record: record,
    )


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await AudioService(db).delete_audio(audio_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}", on_error=_handle_audio_error, success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )


@router.post("/{audio_id}/adjust-bpm", response_model=AudioAnalysisResponse)
async def adjust_audio_bpm(
    audio_id: uuid.UUID,
    target_bpm: float = 120.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await AudioService(db).adjust_bpm(audio_id, str(user_id), target_bpm, str(UPLOAD_DIR))
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}/adjust-bpm", on_error=_handle_audio_error, success_factory=lambda record: record,
    )


@router.post("/{audio_id}/cut", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def cut_audio(
    audio_id: uuid.UUID,
    inicio_segundos: float = 0.0,
    fim_segundos: float = 30.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await AudioService(db).cut_audio_file(
        audio_id, str(user_id), inicio_segundos, fim_segundos, str(UPLOAD_DIR)
    )
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}/cut", on_error=_handle_audio_error, success_factory=lambda record: record,
    )


@router.post("/{audio_id}/separate-tracks")
async def separate_audio_tracks(
    audio_id: uuid.UUID,
    instrument: str = "guitarra",
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Separa a faixa do instrumento. O ficheiro temporario e apagado apos envio."""
    resultado = await AudioService(db).separate_tracks(audio_id, str(user_id), instrument, str(UPLOAD_DIR))
    return handle_result(resultado, instance=f"/api/v1/audio/{audio_id}/separate-tracks", on_error=_handle_audio_error, success_factory=lambda output_path: FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=Path(output_path).name,
            background=BackgroundTask(lambda p=output_path: Path(p).unlink(missing_ok=True)),
        ),
    )
