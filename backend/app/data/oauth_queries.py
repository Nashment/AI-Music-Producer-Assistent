"""
Data access service for OAuth operations (Privacy-First & UUID Base)
"""

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from .models import User, OAuthProvider


class OAuthQueries:
    """OAuth and user database operations"""

    @staticmethod
    def get_or_create_user(
        db: Session,
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
        user = db.query(User).filter(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        ).first()

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
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
        """Get user by UUID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_oauth(
        db: Session,
        oauth_provider: OAuthProvider,
        oauth_id: str
    ) -> Optional[User]:
        """Get user by OAuth provider and provider's user ID"""
        return db.query(User).filter(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id
        ).first()

    @staticmethod
    def delete_user(db: Session, user_id: uuid.UUID) -> bool:
        """Delete user account"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False