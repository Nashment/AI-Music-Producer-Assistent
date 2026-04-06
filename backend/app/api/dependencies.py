"""
API Dependencies - Reusable functions for endpoints
"""

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # Precisas de instalar: pip install pyjwt


from backend.app.core.config import settings

from backend.app.data.database import db as db_manager
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Gere a ligação à base de dados para cada request.
    Usa a classe Database para gerar a sessão e garante o fecho seguro.
    """
    session = db_manager.get_session()
    try:
        yield session
    finally:
        await session.close()


# --- 2. DEPENDÊNCIA DE AUTENTICAÇÃO ---
# O HTTPBearer diz ao FastAPI (e ao Swagger) para procurar um token no cabeçalho: "Authorization: Bearer <token>"
security = HTTPBearer()


def get_current_user_id() -> str:
    """
    MOCK TEMPORÁRIO PARA DESENVOLVIMENTO
    Substituir isto pela validação JWT real (que está comentada abaixo)
    quando a rota de Login for implementada.
    """
    # Garante que este UUID existe fisicamente na tabela `users` no PostgreSQL
    # para não dar erro de Chave Estrangeira (Foreign Key) quando guardar o áudio!
    return "d76c6691-81d7-4660-b883-93ba20ef4bb8"

    """
    --- LÓGICA REAL (GUARDAR PARA QUANDO A AUTH ESTIVER PRONTA) ---
    def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
        token = credentials.credentials
        SECRET_KEY = getattr(settings, "SECRET_KEY", "TEU_SEGREDO_SUPER_SEGURO")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Token inválido")
            return user_id
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Credenciais inválidas.")
    """