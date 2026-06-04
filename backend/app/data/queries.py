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
        user = User(username=username, oauth_provider=oauth_provider, oauth_id=oauth_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_oauth(db: AsyncSession, oauth_provider: OAuthProvider, oauth_id: str) -> Optional[User]:
        stmt = select(User).where(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> Optional[User]:
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
        project = Project(user_id=user_id, title=title, description=description, tempo=tempo)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Optional[Project]:
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_projects(db: AsyncSession, user_id: uuid.UUID) -> List[Project]:
        stmt = select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_project(db: AsyncSession, project_id: uuid.UUID, **kwargs) -> Optional[Project]:
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
        storage_key: str,
        file_size: int,
        duration: float,
        sample_rate: int,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None,
        parent_audio_id: Optional[uuid.UUID] = None,
    ) -> AudioFile:
        audio = AudioFile(
            user_id=user_id,
            project_id=project_id,
            storage_key=storage_key,
            file_size=file_size,
            duration=duration,
            sample_rate=sample_rate,
            bpm=bpm,
            key=key,
            time_signature=time_signature,
            parent_audio_id=parent_audio_id,
        )
        db.add(audio)
        await db.commit()
        await db.refresh(audio, attribute_names=["id"])
        return audio

    @staticmethod
    async def get_audio_file(db: AsyncSession, audio_id: uuid.UUID) -> Optional[AudioFile]:
        stmt = select(AudioFile).where(AudioFile.id == audio_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_project_audio_files(db: AsyncSession, project_id: uuid.UUID) -> List[AudioFile]:
        stmt = select(AudioFile).where(AudioFile.project_id == project_id)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_audio_analysis(
        db: AsyncSession,
        audio_id: uuid.UUID,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        time_signature: Optional[str] = None,
    ) -> Optional[AudioFile]:
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
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        audio_file_id: Optional[uuid.UUID],
        prompt: str,
        instrument: str,
        gen_id: Optional[uuid.UUID] = None,
        genre: Optional[str] = None,
        duration: Optional[int] = None,
        tempo_override: Optional[int] = None,
        parent_generation_id: Optional[uuid.UUID] = None,
        status: GenerationStatusEnum = GenerationStatusEnum.PENDING,
        audio_storage_key: Optional[str] = None,
    ) -> Generation:
        """Cria um registo de geracao.

        gen_id permite pre-definir o UUID (util para Celery tasks que precisam
        do id antes de fazer o commit).  Se omitido, a DB gera automaticamente.
        """
        generation = Generation(
            id=gen_id or uuid.uuid4(),
            user_id=user_id,
            project_id=project_id,
            audio_file_id=audio_file_id,
            prompt=prompt,
            instrument=instrument,
            genre=genre,
            duration=duration,
            tempo_override=tempo_override,
            parent_generation_id=parent_generation_id,
            status=status,
            audio_storage_key=audio_storage_key,
        )
        if status == GenerationStatusEnum.COMPLETED:
            generation.completed_at = datetime.utcnow()
        db.add(generation)
        await db.commit()
        await db.refresh(generation)
        return generation

    @staticmethod
    async def get_generation(db: AsyncSession, generation_id: str) -> Optional[Generation]:
        """Obtem uma geracao pelo seu UUID (aceita string ou UUID)."""
        try:
            gen_uuid = uuid.UUID(str(generation_id))
        except (ValueError, AttributeError):
            return None
        stmt = select(Generation).where(Generation.id == gen_uuid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_generations_by_audio(
        db: AsyncSession,
        audio_file_id: uuid.UUID,
        only_roots: bool = True,
    ) -> List[Generation]:
        stmt = select(Generation).where(Generation.audio_file_id == audio_file_id)
        if only_roots:
            stmt = stmt.where(Generation.parent_generation_id.is_(None))
        stmt = stmt.order_by(Generation.created_at.desc())
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def list_cuts_of_generation(
        db: AsyncSession, parent_generation_uuid: uuid.UUID
    ) -> List[Generation]:
        stmt = (
            select(Generation)
            .where(Generation.parent_generation_id == parent_generation_uuid)
            .order_by(Generation.created_at.asc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_project_generations(db: AsyncSession, project_id: uuid.UUID) -> List[Generation]:
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
        audio_key: Optional[str] = None,
        midi_key: Optional[str] = None,
        partitura_key: Optional[str] = None,
        tablatura_key: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Optional[Generation]:
        """Atualiza o estado e as chaves R2 de uma geracao."""
        try:
            gen_uuid = uuid.UUID(str(generation_id))
        except (ValueError, AttributeError):
            return None
        stmt = select(Generation).where(Generation.id == gen_uuid)
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()
        if generation:
            generation.status = status
            if audio_key:
                generation.audio_storage_key = audio_key
            if midi_key:
                generation.midi_storage_key = midi_key
            if partitura_key:
                generation.partitura_storage_key = partitura_key
            if tablatura_key:
                generation.tablatura_storage_key = tablatura_key
            if error_message:
                generation.error_message = error_message
            if status == GenerationStatusEnum.COMPLETED:
                generation.completed_at = datetime.utcnow()
            await db.commit()
            await db.refresh(generation)
        return generation

    @staticmethod
    async def delete_generation(db: AsyncSession, generation_id: str) -> bool:
        """Apaga uma geracao pelo seu UUID."""
        try:
            gen_uuid = uuid.UUID(str(generation_id))
        except (ValueError, AttributeError):
            return False
        stmt = select(Generation).where(Generation.id == gen_uuid)
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()
        if generation:
            await db.delete(generation)
            await db.commit()
            return True
        return False

    @staticmethod
    async def update_notation_status(
        db: AsyncSession,
        generation_id: str,
        notation_type: str,
        status: str,
        storage_key: Optional[str] = None,
        error_message: Optional[str] = None,
        clear_storage_key: bool = False,
    ) -> Optional[Generation]:
        """Atualiza o estado e a chave R2 de partitura ou tablatura
        de forma independente do estado geral da geração (áudio).

        notation_type: 'partitura' | 'tablatura'
        status: 'pending' | 'processing' | 'completed' | 'failed'
        """
        try:
            gen_uuid = uuid.UUID(str(generation_id))
        except (ValueError, AttributeError):
            return None
        stmt = select(Generation).where(Generation.id == gen_uuid)
        result = await db.execute(stmt)
        generation = result.scalar_one_or_none()
        if generation:
            if notation_type == "partitura":
                generation.partitura_status = status
                if storage_key:
                    generation.partitura_storage_key = storage_key
                elif clear_storage_key:
                    generation.partitura_storage_key = None
                if status == "failed" and error_message:
                    generation.error_message = error_message
            elif notation_type == "tablatura":
                generation.tablatura_status = status
                if storage_key:
                    generation.tablatura_storage_key = storage_key
                elif clear_storage_key:
                    generation.tablatura_storage_key = None
                if status == "failed" and error_message:
                    generation.error_message = error_message
            await db.commit()
            await db.refresh(generation)
        return generation
