"""
API Dependencies - Reusable FastAPI dependency functions
"""

import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.database import db as db_manager
from app.services.user_service import UserService


# ------------------------------------------------------------------
# Base de dados
# ------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Gere a sessão da base de dados para cada request."""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        await session.close()


# ------------------------------------------------------------------
# Autenticação JWT
# ------------------------------------------------------------------

security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> uuid.UUID:
    """
    Valida o JWT do header Authorization e devolve o UUID do utilizador.
    Lança 401 se o token for inválido ou expirado.
    """
    token = credentials.credentials
    # UserService sem db — só precisamos do verify_token
    payload = UserService().verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem identificador de utilizador.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de utilizador inválido no token.",
            headers={"WWW-Authenticate": "Bearer"},
        )