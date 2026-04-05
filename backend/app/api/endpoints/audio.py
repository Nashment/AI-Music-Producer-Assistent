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

# Audio processing utilities
try:
    from backend.worker.audio_utils.ajuste_bpm import ajustar_bpm_automatico
    from backend.worker.audio_utils.corte_audio import cortar_audio_para_30_segundos
    from backend.worker.audio_utils.separador_faixas import extrair_instrumento
except ImportError as e:
    print(f"Warning: Could not import audio processing modules: {e}")
    ajustar_bpm_automatico = None
    cortar_audio_para_30_segundos = None
    extrair_instrumento = None

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


# ==========================================
# Audio Processing Endpoints
# ==========================================

@router.post("/{audio_id}/adjust-bpm")
async def adjust_audio_bpm(
    audio_id: str,
    target_bpm: float = 120.0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Adjust BPM of audio file"""
    if not ajustar_bpm_automatico:
        raise HTTPException(status_code=501, detail="BPM adjustment not available")
    
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    if not audio_record or str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    input_path = Path(audio_record.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    output_filename = f"{uuid.uuid4()}_adjusted_bpm.wav"
    output_path = UPLOAD_DIR / output_filename
    
    try:
        ajustar_bpm_automatico(str(input_path), str(output_path), target_bpm)
        return FileResponse(path=str(output_path), media_type="audio/wav", filename=output_filename)
    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"BPM adjustment failed: {str(e)}")


@router.post("/{audio_id}/cut")
async def cut_audio(
    audio_id: str,
    duration_seconds: int = 30,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Cut audio to specified duration"""
    if not cortar_audio_para_30_segundos:
        raise HTTPException(status_code=501, detail="Audio cutting not available")
    
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    if not audio_record or str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    input_path = Path(audio_record.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    output_filename = f"{uuid.uuid4()}_cut.wav"
    output_path = UPLOAD_DIR / output_filename
    
    try:
        cortar_audio_para_30_segundos(str(input_path), str(output_path), duration_seconds)
        return FileResponse(path=str(output_path), media_type="audio/wav", filename=output_filename)
    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"Audio cutting failed: {str(e)}")


@router.post("/{audio_id}/separate-tracks")
async def separate_audio_tracks(
    audio_id: str,
    instrument: str = "guitarra",
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Separate instrument tracks from audio"""
    if not extrair_instrumento:
        raise HTTPException(status_code=501, detail="Track separation not available")
    
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    if not audio_record or str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    input_path = Path(audio_record.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    try:
        # Change to the directory where demucs will output
        import os
        original_cwd = os.getcwd()
        os.chdir(UPLOAD_DIR)
        
        extrair_instrumento(str(input_path), instrument)
        
        # Find the generated file
        base_name = input_path.stem
        output_filename = f"{base_name}_{instrument}.wav"
        output_path = UPLOAD_DIR / output_filename
        
        os.chdir(original_cwd)
        
        if output_path.exists():
            return FileResponse(path=str(output_path), media_type="audio/wav", filename=output_filename)
        else:
            raise HTTPException(status_code=500, detail="Track separation failed - output not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Track separation failed: {str(e)}")