import uuid
from typing import List, Optional

from pydantic import BaseModel


class AudioAnalysisResponse(BaseModel):
    """Audio analysis response schema."""

    id: uuid.UUID
    project_id: uuid.UUID
    storage_key: str
    display_name: Optional[str] = None
    duration: float
    sample_rate: int
    bpm: Optional[int] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    parent_audio_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class AudioRename(BaseModel):
    """Pedido para renomear um audio (nome amigavel)."""

    display_name: str


class AudioListResponse(BaseModel):
    """List of audio files response schema."""

    audios: List[AudioAnalysisResponse]
    total: int
