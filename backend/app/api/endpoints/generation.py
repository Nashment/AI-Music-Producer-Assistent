"""
Generation endpoints - Music generation from AI
"""

import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from enum import Enum
from sqlalchemy.orm import Session

from backend.app.api.dependencies import get_db, get_current_user_id
from backend.app.data import AudioQueries

# Audio processing utilities
try:
    from backend.worker.audio_utils.audio_to_tablature import (
        extrair_midi_do_audio, converter_midi_para_ly, 
        forcar_tablatura_no_ly, compilar_pdf_lilypond
    )
    from backend.worker.audio_utils.audio_to_partitura import exportar_pdf_automatico
except ImportError as e:
    print(f"Warning: Could not import audio processing modules: {e}")
    extrair_midi_do_audio = None
    exportar_pdf_automatico = None

router = APIRouter()


class InstrumentType(str, Enum):
    """Supported instruments"""
    PIANO = "piano"
    GUITAR = "guitar"
    VIOLIN = "violin"
    DRUMS = "drums"
    BASS = "bass"
    FLUTE = "flute"


class MusicGenreType(str, Enum):
    """Supported music genres"""
    CLASSICAL = "classical"
    JAZZ = "jazz"
    ROCK = "rock"
    POP = "pop"
    AMBIENT = "ambient"


class GenerationRequest(BaseModel):
    """Music generation request"""
    project_id: int
    audio_id: str  # Reference to uploaded audio
    prompt: str  # User instruction
    instrument: InstrumentType
    genre: MusicGenreType
    duration: int  # In seconds
    tempo_override: int | None = None


class GenerationResponse(BaseModel):
    """Generation task response"""
    generation_id: str
    status: str  # pending, processing, completed, failed
    project_id: int
    created_at: str


class GenerationResult(BaseModel):
    """Music generation result"""
    generation_id: str
    audio_url: str
    partitura_url: str | None
    tablatura_url: str | None
    midi_url: str | None
    status: str


@router.post("", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_music(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Request AI music generation
    
    Args:
        request: Generation parameters
        background_tasks: Background task queue
        
    Returns:
        Generation task status
    """
    # TODO: Implement music generation submission
    # Should queue task to worker for async processing
    # Use AI models and audio analysis
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{generation_id}", response_model=GenerationResult)
async def get_generation_result(generation_id: str):
    """
    Get generation results
    
    Args:
        generation_id: Generation task identifier
        
    Returns:
        Generated music files and metadata
    """
    # TODO: Implement result retrieval
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{generation_id}/status")
async def get_generation_status(generation_id: str):
    """
    Get generation task status
    
    Args:
        generation_id: Generation task identifier
        
    Returns:
        Task status and progress
    """
    # TODO: Monitor task status
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{generation_id}/regenerate", response_model=GenerationResponse)
async def regenerate(generation_id: str, prompt_update: dict):
    """Regenerate music with new prompt"""
    # TODO: Implement regeneration
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(generation_id: str):
    """Delete generation result"""
    # TODO: Implement deletion
    raise HTTPException(status_code=501, detail="Not implemented")


# ==========================================
# Audio Processing Endpoints (Tablature & Partitura)
# ==========================================

@router.post("/tablature/{audio_id}")
async def generate_tablature_from_audio(
    audio_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate tablature PDF from audio file"""
    if not all([extrair_midi_do_audio, converter_midi_para_ly, forcar_tablatura_no_ly, compilar_pdf_lilypond]):
        raise HTTPException(status_code=501, detail="Tablature generation not available")
    
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    if not audio_record or str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    input_path = Path(audio_record.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Use a temp directory for processing
    from backend.app.core.config import settings
    temp_dir = Path(settings.AUDIO_UPLOAD_DIR)
    base_name = input_path.stem
    midi_path = temp_dir / f"{base_name}.mid"
    ly_path = temp_dir / f"{base_name}.ly"
    pdf_path = temp_dir / f"{base_name}_tablature.pdf"
    
    try:
        if extrair_midi_do_audio(str(input_path), str(midi_path)) and \
           converter_midi_para_ly(str(midi_path), str(ly_path)) and \
           forcar_tablatura_no_ly(str(ly_path)) and \
           compilar_pdf_lilypond(str(ly_path)):
            if pdf_path.exists():
                return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=f"{base_name}_tablature.pdf")
            else:
                raise HTTPException(status_code=500, detail="PDF generation failed")
        else:
            raise HTTPException(status_code=500, detail="Tablature generation failed")
    except Exception as e:
        # Clean up temp files
        for path in [midi_path, ly_path]:
            if path.exists():
                path.unlink()
        raise HTTPException(status_code=500, detail=f"Tablature generation failed: {str(e)}")


@router.post("/partitura/{audio_id}")
async def generate_partitura_from_audio(
    audio_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Generate musical score PDF from audio file"""
    if not exportar_pdf_automatico:
        raise HTTPException(status_code=501, detail="Partitura generation not available")
    
    audio_record = AudioQueries.get_audio_file(db=db, audio_id=uuid.UUID(audio_id))
    if not audio_record or str(audio_record.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Audio not found")
    
    input_path = Path(audio_record.file_path)
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    from backend.app.core.config import settings
    temp_dir = Path(settings.AUDIO_UPLOAD_DIR)
    base_name = input_path.stem
    midi_path = temp_dir / f"{base_name}.mid"
    pdf_path = temp_dir / f"{base_name}_partitura.pdf"
    
    try:
        # First extract MIDI if needed
        if not midi_path.exists():
            if extrair_midi_do_audio:
                extrair_midi_do_audio(str(input_path), str(midi_path))
            else:
                raise HTTPException(status_code=501, detail="MIDI extraction not available")
        
        result = exportar_pdf_automatico(str(midi_path), str(pdf_path))
        if result and pdf_path.exists():
            return FileResponse(path=str(pdf_path), media_type="application/pdf", filename=f"{base_name}_partitura.pdf")
        else:
            raise HTTPException(status_code=500, detail="Partitura generation failed")
    except Exception as e:
        # Clean up temp files
        if midi_path.exists():
            midi_path.unlink()
        raise HTTPException(status_code=500, detail=f"Partitura generation failed: {str(e)}")
