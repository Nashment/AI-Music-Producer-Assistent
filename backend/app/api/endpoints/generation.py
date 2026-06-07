"""
Generation endpoints - Music generation from AI
"""

import uuid
from pathlib import Path
from fastapi import APIRouter, status, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.dependencies import get_db, get_current_user_id
from app.api.responses import problem_json, handle_result
from app.domain.result import Falha
from app.domain.errors.generation_errors import (
    AudioNaoEncontrado,
    GeracaoNaoEncontrada,
    CoverUrlInvalido,
    PesoAudioInvalido,
    WorkerIndisponivel,
    FilaIndisponivel,
    FalhaProcessamentoAudio,
    IntervaloCorteInvalido,
    FicheiroGeracaoIndisponivel,
    GeneracaoErro,
)
from app.services.generation_service import GenerationService
from app.domain.dtos.endpoints.generation import (
    GenerationRequest,
    CoverGenerationRequest,
    GenerationResponse,
    GenerationResult,
    GenerationListResponse,
    CutGenerationRequest,
)

router = APIRouter()

AUDIO_OUTPUT_DIR     = Path(settings.GENERATIONS_AUDIO_DIR)
PARTITURA_OUTPUT_DIR = Path(settings.GENERATIONS_PARTITURA_DIR)
TABLATURA_OUTPUT_DIR = Path(settings.GENERATIONS_TABLATURA_DIR)

AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)



def _handle_generation_error(erro: GeneracaoErro, instance: str) -> JSONResponse:
    match erro:
        case AudioNaoEncontrado():
            return problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O audio referenciado nao foi encontrado.", instance)
        case GeracaoNaoEncontrada():
            return problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "A geracao pedida nao foi encontrada.", instance)
        case CoverUrlInvalido():
            return problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                "O campo upload_url deve ser uma URL publica (http/https).", instance)
        case PesoAudioInvalido(valor=v):
            return problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                f"audio_weight com valor '{v}' invalido. Deve estar entre 0.0 e 1.0.", instance)
        case WorkerIndisponivel():
            return problem_json(501, "servico-indisponivel", "Funcionalidade Nao Disponivel",
                "O servico de geracao de musica nao esta disponivel neste ambiente.", instance)
        case FilaIndisponivel():
            return problem_json(503, "servico-temporariamente-indisponivel", "Servico Temporariamente Indisponivel",
                "Nao foi possivel enfileirar a geracao. Tente novamente em alguns instantes.", instance)
        case FalhaProcessamentoAudio():
            return problem_json(422, "erro-processamento-audio", "Erro de Processamento de Audio",
                "Nao foi possivel processar o audio. Verifique se o ficheiro e valido.", instance)
        case IntervaloCorteInvalido(detalhe=d):
            return problem_json(400, "intervalo-invalido", "Intervalo de Corte Invalido", d, instance)
        case FicheiroGeracaoIndisponivel(detalhe=d):
            return problem_json(409, "ficheiro-indisponivel", "Ficheiro Indisponivel", d, instance)
        case _:
            return problem_json(500, "erro-interno", "Erro Interno do Servidor",
                "Ocorreu um erro inesperado no servico de geracao.", instance)



@router.post("/tablature/{audio_id}")
async def generate_tablature_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).generate_tablature(
        audio_id=audio_id,
        user_id=str(user_id),
        tablatura_dir=str(TABLATURA_OUTPUT_DIR),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/tablature/{audio_id}", on_error=_handle_generation_error, success_factory=lambda pdf_path: FileResponse(
            path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name,
            background=BackgroundTask(lambda p=pdf_path: Path(p).unlink(missing_ok=True)),
        ),
    )


@router.post("/partitura/{audio_id}")
async def generate_partitura_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).generate_partitura(
        audio_id=audio_id,
        user_id=str(user_id),
        partitura_dir=str(PARTITURA_OUTPUT_DIR),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/partitura/{audio_id}", on_error=_handle_generation_error, success_factory=lambda pdf_path: FileResponse(
            path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name,
            background=BackgroundTask(lambda p=pdf_path: Path(p).unlink(missing_ok=True)),
        ),
    )


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_music(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
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
    return handle_result(resultado, instance="/api/v1/generation", on_error=_handle_generation_error, success_factory=lambda v: v[0],
    )


@router.post("/cover", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_cover(
    request: CoverGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
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
    return handle_result(resultado, instance="/api/v1/generation/cover", on_error=_handle_generation_error, success_factory=lambda v: v[0],
    )


@router.get("/{generation_id}/status", response_model=GenerationResult)
async def get_generation_status(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).get_generation(generation_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/status", on_error=_handle_generation_error, success_factory=lambda gen: gen,
    )


@router.get("/{generation_id}", response_model=GenerationResult)
async def get_generation_result(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).get_generation(generation_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}", on_error=_handle_generation_error, success_factory=lambda gen: gen,
    )


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).delete_generation(generation_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}", on_error=_handle_generation_error, success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )


@router.get("/by-audio/{audio_id}", response_model=GenerationListResponse)
async def list_generations_by_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).list_generations_for_audio(audio_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/by-audio/{audio_id}", on_error=_handle_generation_error, success_factory=lambda gens: GenerationListResponse(
            generations=[GenerationResult.model_validate(g) for g in gens],
        ),
    )


@router.get("/{generation_id}/cuts", response_model=GenerationListResponse)
async def list_cuts_of_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).list_cuts_for_generation(generation_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/cuts", on_error=_handle_generation_error, success_factory=lambda cuts: GenerationListResponse(
            generations=[GenerationResult.model_validate(c) for c in cuts],
        ),
    )


@router.get("/{generation_id}/audio")
async def get_generation_audio(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve a presigned URL do R2 como JSON.
    O cliente faz o segundo pedido directamente ao R2 sem o header Authorization,
    evitando o conflito de autenticacao dupla que o R2 rejeita.
    """
    resultado = await GenerationService(db).get_generation_audio_url(generation_id, str(user_id))
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/audio", on_error=_handle_generation_error, success_factory=lambda url: JSONResponse(content={"url": url}),
    )


@router.post("/{generation_id}/cut", response_model=GenerationResult, status_code=status.HTTP_201_CREATED)
async def cut_generation_endpoint(
    generation_id: str,
    request: CutGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    resultado = await GenerationService(db).cut_generation(
        parent_generation_id=generation_id,
        user_id=str(user_id),
        inicio_segundos=request.inicio_segundos,
        fim_segundos=request.fim_segundos,
        output_dir=str(AUDIO_OUTPUT_DIR),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/cut", on_error=_handle_generation_error, success_factory=lambda cut: cut,
    )


@router.post("/{generation_id}/partitura", response_model=GenerationResult, status_code=status.HTTP_202_ACCEPTED)
async def request_partitura_from_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Enfileira a geracao de partitura em background. Devolve 202 imediatamente.
    O cliente faz polling em GET /{id}/status e aguarda partitura_status='completed'.
    Serve tambem como endpoint de regeneracao (idempotente)."""
    resultado = await GenerationService(db).request_partitura(
        generation_id=generation_id,
        user_id=str(user_id),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/partitura", on_error=_handle_generation_error, success_factory=lambda gen: gen,
    )


@router.get("/{generation_id}/partitura")
async def get_partitura_url(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve a presigned URL do R2 para a partitura.
    Retorna 409 se partitura_status != 'completed'."""
    resultado = await GenerationService(db).get_partitura_url(
        generation_id=generation_id,
        user_id=str(user_id),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/partitura", on_error=_handle_generation_error, success_factory=lambda url: JSONResponse(content={"url": url}),
    )


@router.post("/{generation_id}/tablature", response_model=GenerationResult, status_code=status.HTTP_202_ACCEPTED)
async def request_tablature_from_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Enfileira a geracao de tablatura em background. Devolve 202 imediatamente.
    Serve tambem como endpoint de regeneracao (idempotente)."""
    resultado = await GenerationService(db).request_tablature(
        generation_id=generation_id,
        user_id=str(user_id),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/tablature", on_error=_handle_generation_error, success_factory=lambda gen: gen,
    )


@router.get("/{generation_id}/tablature")
async def get_tablature_url(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve a presigned URL do R2 para a tablatura.
    Retorna 409 se tablatura_status != 'completed'."""
    resultado = await GenerationService(db).get_tablature_url(
        generation_id=generation_id,
        user_id=str(user_id),
    )
    return handle_result(resultado, instance=f"/api/v1/generation/{generation_id}/tablature", on_error=_handle_generation_error, success_factory=lambda url: JSONResponse(content={"url": url}),
    )
