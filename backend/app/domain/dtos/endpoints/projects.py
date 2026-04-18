import uuid

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    """Project creation schema."""

    title: str
    description: str
    tempo: int


class ProjectResponse(BaseModel):
    """Project response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    tempo: int
    user_id: uuid.UUID


class ProjectUpdate(BaseModel):
    """Project update schema."""

    title: str | None = None
    description: str | None = None
    tempo: int | None = None
