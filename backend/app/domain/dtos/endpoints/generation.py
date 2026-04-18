import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class InstrumentType(str, Enum):
    PIANO = "piano"
    GUITAR = "guitar"
    VIOLIN = "violin"
    DRUMS = "drums"
    BASS = "bass"
    FLUTE = "flute"


class MusicGenreType(str, Enum):
    CLASSICAL = "classical"
    JAZZ = "jazz"
    ROCK = "rock"
    POP = "pop"
    AMBIENT = "ambient"


class GenerationRequest(BaseModel):
    """Music generation request."""
    project_id: uuid.UUID
    audio_id: uuid.UUID
    prompt: str
    instrument: InstrumentType
    genre: MusicGenreType
    duration: int
    tempo_override: Optional[int] = None


class GenerationResponse(BaseModel):
    """Generation task response — returned immediately after submission."""
    generation_id: str
    status: str
    project_id: uuid.UUID
    prompt: str
    instrument: Optional[str] = None
    genre: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationResult(BaseModel):
    """Full generation result — returned when polling for status/result."""
    generation_id: str
    status: str
    audio_file_path: Optional[str] = None
    midi_file_path: Optional[str] = None
    partitura_file_path: Optional[str] = None
    tablatura_file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
