import shutil
import uuid
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session


from backend.app.services import AudioService
from backend.app.data import AudioQueries

from backend.app.api.dependencies import get_db, get_current_user_id

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]  # Chega à pasta 'backend'
UPLOAD_DIR = BASE_DIR / "worker" / "uploads" / "audio"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class AudioAnalysisResponse(BaseModel):
    """Audio analysis response schema"""
    id: uuid.UUID
    file_path: str
    duration: float
    sample_rate: int
    bpm: Optional[int] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None

    class Config:
        from_attributes = True  # Permite que o Pydantic leia diretamente do modelo SQLAlchemy


@router.post("/upload", response_model=AudioAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
        project_id: Optional[str] = None,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user_id)
):
    """Upload and analyze audio file"""

    # 1. Gerar um nome único e seguro para o ficheiro
    safe_filename = f"{uuid.uuid4()}_{file.filename}"

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
        audio_id: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user_id)
):
    """Get previously computed audio analysis metadata"""

    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))

    if not audio_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise de áudio não encontrada.")

    if str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")

    return audio_record


@router.get("/{audio_id}")
async def get_audio_file(
        audio_id: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user_id)
):
    """Download the actual audio file"""
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))

    if not audio_record or not Path(audio_record.file_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficheiro físico não encontrado no servidor.")

    if str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")

    return FileResponse(path=audio_record.file_path, media_type="audio/mpeg")


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio(
        audio_id: str,
        db: Session = Depends(get_db),
        user_id: str = Depends(get_current_user_id)
):
    """Delete audio file from DB and disk"""
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))

    if not audio_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio não encontrado.")

    if str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")

    # Apagar do disco rígido de forma segura com Pathlib
    file_path = Path(audio_record.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception as e:
            print(f"Aviso: Não foi possível apagar o ficheiro físico: {e}")

    # Apagar da base de dados
    AudioQueries.delete_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    return