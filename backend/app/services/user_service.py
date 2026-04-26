"""
User Service - User management and Google OAuth business logic
"""

import uuid
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict

import httpx
import jwt

from app.data.models import OAuthProvider as ModelOAuthProvider
from app.data import UserQueries
from app.data.oauth_queries import OAuthQueries


class UserService:
    """
    Service for user operations and Google OAuth authentication.
    """

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(self, db_session=None):
        """
        Initialize service.

        Args:
            db_session: Sessão activa do SQLAlchemy (injecção de dependência do FastAPI).
                        Opcional para operações que não precisam de DB (ex: gerar URL).
        """
        self.db = db_session
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise RuntimeError("JWT_SECRET_KEY não está definida. Configure no .env")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.token_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    def create_access_token(self, user_id: str) -> str:
        """Cria um JWT para o utilizador autenticado."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(hours=self.token_expiration_hours),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica e descodifica um JWT. Devolve o payload ou None."""
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    # ------------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------------

    def get_google_authorization_url(self) -> str:
        """Devolve o URL de autorização do Google para redirecionar o utilizador."""
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GOOGLE_AUTH_URL}?{query}"

    async def google_oauth_login(self, code: str) -> Dict:
        """
        Trata o callback do Google OAuth.
        Troca o code por um token, obtém os dados do utilizador,
        cria ou recupera a conta, e devolve um JWT.

        Args:
            code: Authorization code recebido do Google

        Returns:
            Dict com access_token, token_type e user
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        async with httpx.AsyncClient() as client:
            # 1. Trocar o code pelo access_token
            token_response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            tokens = token_response.json()

            # 2. Obter informação do utilizador
            user_info_response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()

        # 3. Criar ou recuperar utilizador via OAuthQueries
        username = (
            user_info.get("email", "").split("@")[0]
            or user_info.get("name", "user")
        )
        user = await OAuthQueries.get_or_create_user(
            db=self.db,
            oauth_provider=ModelOAuthProvider.GOOGLE,
            oauth_id=user_info["id"],
            username=username,
        )

        # 4. Gerar JWT
        jwt_token = self.create_access_token(str(user.id))

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "username": user.username,
            },
        }

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    async def get_user(self, user_id: uuid.UUID):
        """Devolve o utilizador pelo UUID."""
        return await UserQueries.get_user_by_id(db=self.db, user_id=user_id)

    async def update_username(self, user_id: uuid.UUID, username: str):
        """Actualiza o username do utilizador."""
        clean_username = username.strip()
        if not clean_username:
            raise ValueError("O username não pode estar vazio.")

        existing = await UserQueries.get_user_by_username(db=self.db, username=clean_username)
        if existing and existing.id != user_id:
            raise ValueError(f"O username '{clean_username}' já está em uso.")

        return await UserQueries.update_user(db=self.db, user_id=user_id, username=clean_username)

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """Apaga a conta do utilizador."""
        return await UserQueries.delete_user(db=self.db, user_id=user_id)