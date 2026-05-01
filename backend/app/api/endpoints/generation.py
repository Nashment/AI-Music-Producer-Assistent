"""
Generation endpoints - Music generation from AI

Responsabilidades desta camada:
  - Receber pedidos HTTP e validar os parâmetros de entrada.
  - Chamar o serviço e obter um Resultado[GeneracaoErro, T].
  - Mapear GeneracaoErro -> HTTP Problem Details  (_handle_generation_error).
  - Construir a resposta HTTP de sucesso.

O que NAO esta aqui:
  - Logica de negocio (esta no servico).
  - Excecoes genericas do Python (o servico nunca as lanca para ca).
"""

import os
import uuid
from typing import Callable
from pathlib import Path

from fastapi import APIRouter, status, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_id
from app.domain.result import Sucesso, Falha
from app.domain.errors.generation_errors import (
    AudioNaoEncontrado,
    GeracaoNaoEncontrada,
    CoverUrlInvalido,
    PesoAudioInvalido,
    WorkerIndisponivel,
    FilaIndisponivel,
    FalhaProcessamentoAudio,
    GeneracaoErro,
)
from app.services.generation_service import GenerationService
from app.domain.dtos.endpoints.generation import (
    GenerationRequest,
    CoverGenerationRequest,
    GenerationResponse,
    GenerationResult,
)

router = APIRouter()

_DEFAULT_GENERATIONS_ROOT = Path(__file__).resolve().parents[3] / "worker" / "generations"
AUDIO_OUTPUT_DIR     = Path(os.getenv("GENERATIONS_AUDIO_DIR",     str(_DEFAULT_GENERATIONS_ROOT / "audio")))
PARTITURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_PARTITURA_DIR", str(_DEFAULT_GENERATIONS_ROOT / "partitura")))
TABLATURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_TABLATURA_DIR", str(_DEFAULT_GENERATIONS_ROOT / "tablatura")))

AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def _handle_generation_error(erro: GeneracaoErro, instance: str) -> JSONResponse:
    match erro:
        case AudioNaoEncontrado():
            return _problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O audio referenciado nao foi encontrado.", instance)
        case GeracaoNaoEncontrada():
            return _problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "A geracao pedida nao foi encontrada.", instance)
        case CoverUrlInvalido():
            return _problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                "O campo upload_url deve ser uma URL publica (http/https).", instance)
        case PesoAudioInvalido(valor=v):
            return _problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                f"audio_weight com valor '{v}' invalido. Deve estar entre 0.0 e 1.0.", instance)
        case WorkerIndisponivel():
            return _problem_json(501, "servico-indisponivel", "Funcionalidade Nao Disponivel",
                "O servico de geracao de musica nao esta disponivel neste ambiente.", instance)
        case FilaIndisponivel():
            return _problem_json(503, "servico-temporariamente-indisponivel", "Servico Temporariamente Indisponivel",
                "Nao foi possivel enfileirar a geracao. Tente novamente em alguns instantes.", instance)
        case FalhaProcessamentoAudio():
            return _problem_json(422, "erro-processamento-audio", "Erro de Processamento de Audio",
                "Nao foi possivel processar o audio. Verifique se o ficheiro e valido.", instance)
        case _:
            return _problem_json(500, "erro-interno", "Erro Interno do Servidor",
                "Ocorreu um erro inesperado no servico de geracao.", instance)


def _handle_result(
    resultado: Sucesso | Falha,
    instance: str,
    success_factory: Callable,
) -> Response:
    match resultado:
        case Falha(erro=erro):
            return _handle_generation_error(erro, instance)
        case Sucesso(valor=valor):
            return success_factory(valor)


@router.post("/tablature/{audio_id}")
async def generate_tablature_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate tablature PDF from an existing audio file."""
    resultado = await GenerationService(db).generate_tablature(
        audio_id=audio_id,
        user_id=str(user_id),
        tablatura_dir=str(TABLATURA_OUTPUT_DIR),
    )
    return _handle_result(
        resultado,
        instance=f"/api/v1/generation/tablature/{audio_id}",
        success_factory=lambda pdf_path: FileResponse(
            path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name
        ),
    )


@router.post("/partitura/{audio_id}")
async def generate_partitura_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate musical score PDF from an existing audio file."""
    resultado = await GenerationService(db).generate_partitura(
        audio_id=audio_id,
        user_id=str(user_id),
        partitura_dir=str(PARTITURA_OUTPUT_DIR),
    )
    return _handle_result(
        resultado,
        instance=f"/api/v1/generation/partitura/{audio_id}",
        success_factory=lambda pdf_path: FileResponse(
            path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name
        ),
    )


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_music(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Submit an AI music generation request."""
    resultado = await GenerationService(db).submit_generation(
        user_id=str(user_id),
        project_id=request.project_id,
        audio_id=request.audio_id,
        prompt=request.prompt,
        instrument=request.instrument.value,
        genre=request.genre.value if request.genre else None,
        duration=request.duration,
        tempo_override=request.tempo_override,
    )
    return _handle_result(
        resultado,
        instance="/api/v1/generation",
        success_factory=lambda v: JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=GenerationResponse.model_validate(v[0]).model_dump(mode="json"),
        ),
    )


@router.post("/cover", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_cover(
    request: CoverGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Submit an AI cover generation request using a source audio URL + style prompt."""
    resultado = await GenerationService(db).submit_cover_generation(
        user_id=str(user_id),
        project_id=request.project_id,
        audio_id=request.audio_id,
        prompt=request.prompt,
        instrument=request.instrument.value,
        genre=request.genre.value if request.genre else None,
        duration=request.duration,
        tempo_override=request.tempo_override,
        upload_url=request.upload_url,
        audio_weight=request.audio_weight,
    )
    return _handle_result(
        resultado,
        instance="/api/v1/generation/cover",
        success_factory=lambda v: JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=GenerationResponse.model_validate(v[0]).model_dump(mode="json"),
        ),
    )


@router.get("/{generation_id}/status", response_model=GenerationResult)
async def get_generation_status(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get the current status of a generation task."""
    resultado = await GenerationService(db).get_generation(generation_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/generation/{generation_id}/status",
        success_factory=lambda gen: JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenerationResult.model_validate(gen).model_dump(mode="json"),
        ),
    )


@router.get("/{generation_id}", response_model=GenerationResult)
async def get_generation_result(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get the full result of a completed generation task."""
    resultado = await GenerationService(db).get_generation(generation_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/generation/{generation_id}",
        success_factory=lambda gen: JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenerationResult.model_validate(gen).model_dump(mode="json"),
        ),
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a generation and its associated files."""
    resultado = await GenerationService(db).delete_generation(generation_id, str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/generation/{generation_id}",
        success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )
