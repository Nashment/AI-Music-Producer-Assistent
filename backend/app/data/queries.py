"""
SQL Queries and Database Operations (Privacy-First & UUID Base)
"""

import uuid
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from .models import User, Project, AudioFile, Generation, GenerationStatusEnum, OAuthProvider


class UserQueries:
    """User database queries"""

    @staticmethod
    def create_user(db: Session, username: str, oauth_provider: OAuthProvider, oauth_id: str) -> User:
        """
        Create new user record (OAuth strictly)
        """
        user = User(
            username=username,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_oauth(db: Session, oauth_provider: OAuthProvider, oauth_id: str) -> Optional[User]:
        """
        Get user by their OAuth provider and ID (Substitui o antigo get_by_email)
        """
        return db.query(User).filter(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        ).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        Get user by public username
        """
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Get user by UUID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def update_user(db: Session, user_id: uuid.UUID, **kwargs) -> Optional[User]:
        """Update user fields"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: uuid.UUID) -> bool:
        """Delete user"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False


class ProjectQueries:
    """Project database queries"""

    @staticmethod
    def create_project(db: Session, user_id: uuid.UUID, title: str, description: str, tempo: int) -> Project:
        """Create new project"""
        project = Project(user_id=user_id, title=title, description=description, tempo=tempo)
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def get_project(db: Session, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by UUID"""
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_user_projects(db: Session, user_id: uuid.UUID) -> List[Project]:
        """Get all projects for user"""
        return db.query(Project).filter(Project.user_id == user_id).order_by(Project.created_at.desc()).all()

    @staticmethod
    def update_project(db: Session, project_id: uuid.UUID, **kwargs) -> Optional[Project]:
        """Update project fields"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            db.commit()
            db.refresh(project)
        return project

    @staticmethod
    def delete_project(db: Session, project_id: uuid.UUID) -> bool:
        """Delete project"""
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            db.delete(project)
            db.commit()
            return True
        return False


class AudioQueries:
    """Audio file database queries"""

    @staticmethod
    def create_audio_file(
        db: Session,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID],
        file_path: str,
        file_size: int,
        duration: float,
        sample_rate: int,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None
    ) -> AudioFile:
        """Create audio file record"""
        audio = AudioFile(
            user_id=user_id,
            project_id=project_id,
            file_path=file_path,
            file_size=file_size,
            duration=duration,
            sample_rate=sample_rate,
            bpm=bpm,
            key=key,
            time_signature=time_signature
        )
        db.add(audio)
        db.commit()
        db.refresh(audio)
        return audio

    @staticmethod
    def get_audio_file(db: Session, audio_id: uuid.UUID) -> Optional[AudioFile]:
        """Get audio file by UUID"""
        return db.query(AudioFile).filter(AudioFile.id == audio_id).first()

    @staticmethod
    def get_project_audio_files(db: Session, project_id: uuid.UUID) -> List[AudioFile]:
        """Get all audio files in project"""
        return db.query(AudioFile).filter(AudioFile.project_id == project_id).all()

    @staticmethod
    def update_audio_analysis(
        db: Session,
        audio_id: uuid.UUID,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None
    ) -> Optional[AudioFile]:
        """Update audio analysis results"""
        audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
        if audio:
            if bpm is not None:
                audio.bpm = bpm
            if key is not None:
                audio.key = key
            if time_signature is not None:
                audio.time_signature = time_signature
            db.commit()
            db.refresh(audio)
        return audio

    @staticmethod
    def delete_audio_file(db: Session, audio_id: uuid.UUID) -> bool:
        """Delete audio file"""
        audio = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
        if audio:
            db.delete(audio)
            db.commit()
            return True
        return False


class GenerationQueries:
    """Music generation database queries"""

    @staticmethod
    def create_generation(
        db: Session,
        generation_id: str,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        audio_file_id: Optional[uuid.UUID],
        prompt: str,
        instrument: str,
        genre: str,
        duration: int,
        tempo_override: Optional[int] = None
    ) -> Generation:
        """Create generation task record"""
        generation = Generation(
            generation_id=generation_id,
            user_id=user_id,
            project_id=project_id,
            audio_file_id=audio_file_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override
        )
        db.add(generation)
        db.commit()
        db.refresh(generation)
        return generation

    @staticmethod
    def get_generation(db: Session, generation_id: str) -> Optional[Generation]:
        """Get generation by its specific generation_id"""
        return db.query(Generation).filter(Generation.generation_id == generation_id).first()

    @staticmethod
    def get_project_generations(db: Session, project_id: uuid.UUID) -> List[Generation]:
        """Get all generations in project"""
        return db.query(Generation).filter(
            Generation.project_id == project_id
        ).order_by(Generation.created_at.desc()).all()

    @staticmethod
    def update_generation_status(
        db: Session,
        generation_id: str,
        status: GenerationStatusEnum,
        audio_path: Optional[str] = None,
        midi_path: Optional[str] = None,
        partitura_path: Optional[str] = None,
        tablatura_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Generation]:
        """Update generation status and results"""
        generation = db.query(Generation).filter(Generation.generation_id == generation_id).first()
        if generation:
            generation.status = status
            if audio_path:
                generation.audio_file_path = audio_path
            if midi_path:
                generation.midi_file_path = midi_path
            if partitura_path:
                generation.partitura_file_path = partitura_path
            if tablatura_path:
                generation.tablatura_file_path = tablatura_path
            if error_message:
                generation.error_message = error_message
            if status == GenerationStatusEnum.COMPLETED:
                generation.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(generation)
        return generation

    @staticmethod
    def delete_generation(db: Session, generation_id: str) -> bool:
        """Delete generation"""
        generation = db.query(Generation).filter(Generation.generation_id == generation_id).first()
        if generation:
            db.delete(generation)
            db.commit()
            return True
        return False