"""
Generation endpoints - Music generation from AI
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user_id
from app.services.generation_service import GenerationService
from app.domain.dtos.endpoints.generation import (
    GenerationRequest,
    CoverGenerationRequest,
    GenerationResponse,
    GenerationResult,
)

router = APIRouter()

_DEFAULT_GENERATIONS_ROOT = Path(__file__).resolve().parents[3] / "worker" / "generations"
AUDIO_OUTPUT_DIR = Path(os.getenv("GENERATIONS_AUDIO_DIR", str(_DEFAULT_GENERATIONS_ROOT / "audio")))
PARTITURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_PARTITURA_DIR", str(_DEFAULT_GENERATIONS_ROOT / "partitura")))
TABLATURA_OUTPUT_DIR = Path(os.getenv("GENERATIONS_TABLATURA_DIR", str(_DEFAULT_GENERATIONS_ROOT / "tablatura")))

AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PARTITURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TABLATURA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# Rotas de notação (específicas primeiro para evitar conflitos de routing)
# ==========================================

@router.post("/tablature/{audio_id}")
async def generate_tablature_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate tablature PDF from an existing audio file"""
    try:
        pdf_path = await GenerationService(db).generate_tablature(
            audio_id=audio_id, user_id=user_id, tablatura_dir=str(TABLATURA_OUTPUT_DIR)
        )
        return FileResponse(path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Tablature generation failed: {str(e)}")


@router.post("/partitura/{audio_id}")
async def generate_partitura_from_audio(
    audio_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate musical score PDF from an existing audio file"""
    try:
        pdf_path = await GenerationService(db).generate_partitura(
            audio_id=audio_id, user_id=user_id, partitura_dir=str(PARTITURA_OUTPUT_DIR)
        )
        return FileResponse(path=pdf_path, media_type="application/pdf", filename=Path(pdf_path).name)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Partitura generation failed: {str(e)}")


# ==========================================
# Rotas de geração AI
# ==========================================

@router.post("", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_music(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Submit an AI music generation request.
    Returns 202 immediately; poll GET /{generation_id}/status to track progress.
    """
    try:
        service = GenerationService(db)
        generation, _celery_task_id = await service.submit_generation(
            user_id=user_id,
            project_id=request.project_id,
            audio_id=request.audio_id,
            prompt=request.prompt,
            instrument=request.instrument.value,
            genre=request.genre.value if request.genre else None,
            duration=request.duration,
            tempo_override=request.tempo_override,
        )

        return generation

    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falha ao submeter geração: {str(e)}")


@router.post("/cover", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_cover(
    request: CoverGenerationRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Submit an AI cover generation request using a source audio URL + style prompt."""
    try:
        service = GenerationService(db)
        generation, _celery_task_id = await service.submit_cover_generation(
            user_id=user_id,
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

        return generation

    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Falha ao submeter cover: {str(e)}")


@router.get("/{generation_id}/status", response_model=GenerationResult)
async def get_generation_status(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get the current status of a generation task."""
    try:
        return await GenerationService(db).get_generation(generation_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{generation_id}", response_model=GenerationResult)
async def get_generation_result(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get the full result of a completed generation task."""
    try:
        return await GenerationService(db).get_generation(generation_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete a generation and its associated files."""
    try:
        await GenerationService(db).delete_generation(generation_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

