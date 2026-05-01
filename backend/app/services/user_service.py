"""
User Service - User management and Google OAuth business logic

Os metodos deste servico devolvem Resultado[UtilizadorErro, T] em vez de
lancar excecoes. A traducao para HTTP fica exclusivamente no endpoint.
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
from app.domain.result import Resultado, Sucesso, Falha
from app.domain.errors.user_errors import (
    UtilizadorNaoEncontrado,
    UsernameInvalido,
    UsernameDuplicado,
    FalhaAutenticacaoGoogle,
)


class UserService:
    GOOGLE_TOKEN_URL    = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_AUTH_URL     = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(self, db_session=None):
        self.db = db_session
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise RuntimeError("JWT_SECRET_KEY nao esta definida. Configure no .env")
        self.algorithm              = os.getenv("JWT_ALGORITHM", "HS256")
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
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    # ------------------------------------------------------------------
    # Google OAuth
    # ------------------------------------------------------------------

    def get_google_authorization_url(self) -> str:
        """Devolve o URL de autorizacao do Google para redirecionar o utilizador."""
        params = {
            "client_id":     os.getenv("GOOGLE_CLIENT_ID"),
            "redirect_uri":  os.getenv("GOOGLE_REDIRECT_URI"),
            "response_type": "code",
            "scope":         "openid email profile",
            "access_type":   "offline",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GOOGLE_AUTH_URL}?{query}"

    async def google_oauth_login(self, code: str) -> Resultado:
        """
        Trata o callback do Google OAuth.
        Troca o code por token, obtem dados do utilizador, cria/recupera conta e devolve JWT.
        """
        try:
            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    self.GOOGLE_TOKEN_URL,
                    data={
                        "code":          code,
                        "client_id":     os.getenv("GOOGLE_CLIENT_ID"),
                        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                        "redirect_uri":  os.getenv("GOOGLE_REDIRECT_URI"),
                        "grant_type":    "authorization_code",
                    },
                )
                token_response.raise_for_status()
                tokens = token_response.json()

                user_info_response = await client.get(
                    self.GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {tokens['access_token']}"},
                )
                user_info_response.raise_for_status()
                user_info = user_info_response.json()

        except Exception as e:
            return Falha(FalhaAutenticacaoGoogle(detalhe=str(e)))

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

        return Sucesso({
            "access_token": self.create_access_token(str(user.id)),
            "token_type":   "bearer",
            "user":         {"id": str(user.id), "username": user.username},
        })

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    async def get_user(self, user_id: uuid.UUID) -> Resultado:
        """Obtem o utilizador pelo UUID."""
        user = await UserQueries.get_user_by_id(db=self.db, user_id=user_id)
        if not user:
            return Falha(UtilizadorNaoEncontrado(user_id=user_id))
        return Sucesso(user)

    async def update_username(self, user_id: uuid.UUID, username: str) -> Resultado:
        """Actualiza o username do utilizador, validando unicidade."""
        clean_username = username.strip()
        if not clean_username:
            return Falha(UsernameInvalido())

        existing = await UserQueries.get_user_by_username(db=self.db, username=clean_username)
        if existing and existing.id != user_id:
            return Falha(UsernameDuplicado(username=clean_username))

        user = await UserQueries.update_user(db=self.db, user_id=user_id, username=clean_username)
        if not user:
            return Falha(UtilizadorNaoEncontrado(user_id=user_id))
        return Sucesso(user)

    async def delete_user(self, user_id: uuid.UUID) -> Resultado:
        """Apaga a conta do utilizador."""
        success = await UserQueries.delete_user(db=self.db, user_id=user_id)
        if not success:
            return Falha(UtilizadorNaoEncontrado(user_id=user_id))
        return Sucesso(None)
