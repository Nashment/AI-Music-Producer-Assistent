import uuid
from typing import List, Optional

from pydantic import BaseModel


class AudioAnalysisResponse(BaseModel):
    """Audio analysis response schema."""

    id: uuid.UUID
    project_id: uuid.UUID
    file_path: str
    duration: float
    sample_rate: int
    bpm: Optional[int] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    parent_audio_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True


class AudioListResponse(BaseModel):
    """List of audio files response schema."""

    audios: List[AudioAnalysisResponse]
    total: int
