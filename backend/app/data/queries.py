"""
SQL Queries and Database Operations (Privacy-First & UUID Base)
"""

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional
from .models import User, Project, AudioFile, Generation, GenerationStatusEnum, OAuthProvider


class UserQueries:
    """User database queries"""

    @staticmethod
    async def create_user(db: AsyncSession, username: str, oauth_provider: OAuthProvider, oauth_id: str) -> User:
        """
        Create new user record (OAuth strictly)
        """
        user = User(
            username=username,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_oauth(db: AsyncSession, oauth_provider: OAuthProvider, oauth_id: str) -> Optional[User]:
        """
        Get user by their OAuth provider and ID (Substitui o antigo get_by_email)
        """
        stmt = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        """
        Get user by public username
        """
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Get user by UUID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Optional[User]:
        """Update user fields"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
        """Delete user"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            await db.delete(user)
            await db.commit()
            return True
        return False


class ProjectQueries:
    """Project database queries"""

    @staticmethod
    async def create_project(db: AsyncSession, user_id: uuid.UUID, title: str, description: str, tempo: int) -> Project:
        """Create new project"""
        project = Project(user_id=user_id, title=title, description=description, tempo=tempo)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
        """Get project by UUID"""
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_projects(db: AsyncSession, user_id: uuid.UUID) -> List[Project]:
        """Get all projects for user"""
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_project(db: AsyncSession, project_id: uuid.UUID, **kwargs) -> Optional[Project]:
        """Update project fields"""
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if project:
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            await db.commit()
            await db.refresh(project)
        return project

    @staticmethod
    async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> bool:
        """Delete project"""
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        if project:
            await db.delete(project)
            await db.commit()
            return True
        return False


class AudioQueries:
    """Audio file database queries"""

    @staticmethod
    async def create_audio_file(
        db: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        file_path: str,
        file_size: int,
        duration: float,
        sample_rate: int,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None,
        parent_audio_id: Optional[uuid.UUID] = None
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
            time_signature=time_signature,
            parent_audio_id=parent_audio_id
        )
        db.add(audio)
        await db.commit()
        # Force refresh to retrieve the generated UUID from database
        await db.refresh(audio, attribute_names=['id'])
        return audio

    @staticmethod
    async def get_audio_file(db: AsyncSession, audio_id: uuid.UUID) -> Optional[AudioFile]:
        """Get audio file by UUID"""
        stmt = select(AudioFile).where(AudioFile.id == audio_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_project_audio_files(db: AsyncSession, project_id: uuid.UUID) -> List[AudioFile]:
        """Get all audio files in project"""
        stmt = select(AudioFile).where(AudioFile.project_id == project_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_audio_analysis(
        db: AsyncSession,
        audio_id: uuid.UUID,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None
    ) -> Optional[AudioFile]:
        """Update audio analysis results"""
        stmt = select(AudioFile).where(AudioFile.id == audio_id)
        result = await db.execute(stmt)
        audio = result.scalar_one_or_none()
        if audio:
            if bpm is not None:
                audio.bpm = bpm
            if key is not None:
                audio.key = key
            if time_signature is not None:
                audio.time_signature = time_signature
            await db.commit()
            await db.refresh(audio)
        return audio

    @staticmethod
    async def delete_audio_file(db: AsyncSession, audio_id: uuid.UUID) -> bool:
        """Delete audio file"""
        stmt = select(AudioFile).where(AudioFile.id == audio_id)
        result = await db.execute(stmt)
        audio = result.scalar_one_or_none()
        if audio:
            await db.delete(audio)
            await db.commit()
            return True
        return False


class GenerationQueries:
    """Music generation database queries"""

    @staticmethod
    async def create_generation(
        db: AsyncSession,
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
        await db.commit()
        await db.refresh(generation)
        return generation

    @staticmethod
    async def get_generation(db: AsyncSession, generation_id: str) -> Optional[Generation]:
        """Get generation by its specific generation_id"""
        stmt = select(Generation).where(Generation.generation_id == generation_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_project_generations(db: AsyncSession, project_id: uuid.UUID) -> List[Generation]:
        """Get all generations in project"""
        stmt = select(Generation).where(
            Generation.project_id == project_id
        ).order_by(Generation.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_generation_status(
        db: AsyncSession,
        generation_id: str,
        status: GenerationStatusEnum,
        audio_path: Optional[str] = None,
        midi_path: Optional[str] = None,
        partitura_path: Optional[str] = None,
        tablatura_path: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[Generation]:
        """Update generation status and results"""
        stmt = select(Generation).where(Generation.generation_id == generation_id)
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()
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
            await db.commit()
            await db.refresh(generation)
        return generation

    @staticmethod
    async def delete_generation(db: AsyncSession, generation_id: str) -> bool:
        """Delete generation"""
        stmt = select(Generation).where(Generation.generation_id == generation_id)
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()
        if generation:
            await db.delete(generation)
            await db.commit()
            return True
        return False
