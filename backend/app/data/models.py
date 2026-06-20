"""
SQLAlchemy ORM models (Privacy-First & UUID Base)
"""

import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, Enum, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class OAuthProvider(str, enum.Enum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    APPLE = "apple"


class GenerationStatusEnum(str, enum.Enum):
    """Generation status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User model - Strict OAuth based authentication (Minimal Data)"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(128), unique=True, index=True, nullable=False)

    oauth_provider = Column(String(50), nullable=False)
    oauth_id = Column(String(255), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth_provider_id"),
    )

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    audio_files = relationship("AudioFile", back_populates="owner", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """Music project model"""
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("user_id", "title", name="uq_projects_user_title"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    tempo = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    audio_files = relationship("AudioFile", back_populates="project")
    generations = relationship("Generation", back_populates="project", cascade="all, delete-orphan")


class AudioFile(Base):
    """Uploaded audio file model"""
    __tablename__ = "audio_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    parent_audio_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="SET NULL"), nullable=True)

    # Chave R2 do ficheiro no Cloudflare (ex: "audio/{uuid}_{filename}")
    storage_key = Column(String(512), nullable=False)
    # Nome amigavel definido pelo utilizador (opcional). Quando nulo, o
    # frontend mostra o nome original derivado da storage_key.
    display_name = Column(String(255), nullable=True)
    file_size = Column(Integer)
    duration = Column(Float)
    sample_rate = Column(Integer)

    bpm = Column(Integer)
    key = Column(String(32))
    time_signature = Column(String(32))

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="audio_files")
    project = relationship("Project", back_populates="audio_files")
    generations = relationship("Generation", back_populates="audio_file")
    parent = relationship("AudioFile", remote_side="AudioFile.id", foreign_keys="AudioFile.parent_audio_id", backref="cuts")


class Generation(Base):
    """Music generation task model"""
    __tablename__ = "generations"

    # Identificador unico - usado em todos os contextos (API, Celery, FK)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="SET NULL"))

    parent_generation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generations.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Nome amigavel definido pelo utilizador (opcional). Quando nulo, o
    # frontend mostra um rotulo derivado do prompt.
    name = Column(String(255), nullable=True)

    prompt = Column(Text, nullable=False)
    instrument = Column(String(128))
    genre = Column(String(128))
    duration = Column(Integer)
    tempo_override = Column(Integer)

    status = Column(Enum(GenerationStatusEnum), default=GenerationStatusEnum.PENDING)

    # Chaves R2 dos ficheiros gerados
    audio_storage_key = Column(String(512))
    midi_storage_key = Column(String(512))
    partitura_storage_key = Column(String(512))
    tablatura_storage_key = Column(String(512))

    # Estado do processamento de notação em background
    # Valores: null | 'pending' | 'processing' | 'completed' | 'failed'
    partitura_status = Column(String(32), nullable=True)
    tablatura_status = Column(String(32), nullable=True)

    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="generations")
    project = relationship("Project", back_populates="generations")
    audio_file = relationship("AudioFile", back_populates="generations")
    parent = relationship(
        "Generation",
        remote_side="Generation.id",
        foreign_keys="Generation.parent_generation_id",
        backref="cuts",
    )
