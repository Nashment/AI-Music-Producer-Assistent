"""
Data access service for OAuth operations (Privacy-First & UUID Base)
"""

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, OAuthProvider


class OAuthQueries:
    """OAuth and user database operations"""

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        oauth_provider: OAuthProvider,
        oauth_id: str,
        username: str
    ) -> User:
        """
        Verifica se o utilizador já existe através do seu ID anónimo do provedor.
        Se não existir, cria uma conta nova apenas com o username escolhido.

        Args:
            db: Database session
            oauth_provider: OAuth provider (google, github, microsoft, apple)
            oauth_id: User ID fornecido pelo provider
            username: O nome público que o utilizador escolheu para a app

        Returns:
            User object (existente ou recém-criado)
        """
        # Tenta encontrar o utilizador pela combinação provedor + ID
        stmt = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # Se já existe, devolve-o logo (já não precisamos de atualizar tokens na BD)
        if user:
            return user

        # Se não existe, cria a nova conta anónima
        user = User(
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            username=username
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Get user by UUID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_oauth(
        db: AsyncSession,
        oauth_provider: OAuthProvider,
        oauth_id: str
    ) -> Optional[User]:
        """Get user by OAuth provider and provider's user ID"""
        stmt = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: uuid.UUID) -> bool:
        """Delete user account"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            await db.delete(user)
            await db.commit()
            return True
        return False