import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import AudioService
from app.api.dependencies import get_db, get_current_user_id
from app.domain.dtos.endpoints.audio import AudioAnalysisResponse, AudioListResponse

router = APIRouter()

_DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[3] / "worker" / "uploads" / "audio"
UPLOAD_DIR = Path(os.getenv("AUDIO_UPLOAD_DIR", str(_DEFAULT_UPLOAD_DIR)))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/project/{project_id}", response_model=AudioListResponse)
async def list_project_audios(
        project_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user_id: uuid.UUID = Depends(get_current_user_id)
):
    """List all audio files belonging to a project"""
    try:
        audios = await AudioService(db).get_project_audios(project_id, user_id)
        return AudioListResponse(audios=audios, total=len(audios))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/project/{project_id}/upload", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
        project_id: str,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Upload and analyze audio file"""

    # 1. Gerar um nome único e seguro para o ficheiro
    original_name = file.filename or "upload"
    safe_filename = f"{uuid.uuid4()}_{original_name}"

    # 2. O Pathlib junta caminhos de forma inteligente (funciona em Windows, Mac e Linux/Docker)
    file_path = UPLOAD_DIR / safe_filename

    # 3. Guardar o ficheiro físico no servidor
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao guardar o ficheiro no disco: {str(e)}"
        )
    finally:
        file.file.close()  # Libertar memória RAM

    # 4. Chamar o serviço de áudio para processar (librosa) e guardar na base de dados
    audio_service = AudioService(db)

    try:
        audio_record = await audio_service.upload_and_analyze_audio(
            file_path=str(file_path),
            user_id=user_id,
            project_id=project_id
        )
        return audio_record

    except ValueError as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        # Apanha qualquer outro erro inesperado
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno durante a análise de áudio."
        )


@router.get("/analysis/{audio_id}", response_model=AudioAnalysisResponse)
async def get_audio_analysis(
        audio_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Get previously computed audio analysis metadata"""
    try:
        return await AudioService(db).get_audio(audio_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{audio_id}")
async def get_audio_file(
        audio_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Download the actual audio file"""
    try:
        record = await AudioService(db).get_audio(audio_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not Path(record.file_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficheiro físico não encontrado no servidor.")

    original_filename = Path(record.file_path).name
    return FileResponse(path=record.file_path, media_type="audio/mpeg", filename=original_filename)


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
        audio_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Delete audio file from DB and disk"""
    try:
        await AudioService(db).delete_audio(audio_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==========================================
# Audio Processing Endpoints
# ==========================================

@router.post("/{audio_id}/adjust-bpm", response_model=AudioAnalysisResponse)
async def adjust_audio_bpm(
    audio_id: uuid.UUID,
    target_bpm: float = 120.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Adjust BPM of audio file (overwrites original)"""
    try:
        return await AudioService(db).adjust_bpm(audio_id, user_id, target_bpm, str(UPLOAD_DIR))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"BPM adjustment failed: {str(e)}")


@router.post("/{audio_id}/cut", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def cut_audio(
    audio_id: uuid.UUID,
    inicio_segundos: float = 0.0,
    fim_segundos: float = 30.0,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Cut audio between inicio_segundos and fim_segundos and save as new record linked to original"""
    try:
        return await AudioService(db).cut_audio_file(audio_id, user_id, inicio_segundos, fim_segundos, str(UPLOAD_DIR))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Audio cutting failed: {str(e)}")


@router.post("/{audio_id}/separate-tracks")
async def separate_audio_tracks(
    audio_id: uuid.UUID,
    instrument: str = "guitarra",
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Separate instrument tracks from audio"""
    try:
        output_path = await AudioService(db).separate_tracks(audio_id, user_id, instrument, str(UPLOAD_DIR))
        return FileResponse(path=output_path, media_type="audio/wav", filename=Path(output_path).name)
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Track separation failed: {str(e)}")