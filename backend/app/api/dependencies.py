"""
API Dependencies - Reusable functions for endpoints
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt  # Precisas de instalar: pip install pyjwt


# Importa as tuas configurações (onde deves ter a tua SECRET_KEY guardada)
from backend.app.core.config import settings

from typing import Generator
# Importamos a tua instância global 'db' e damos-lhe um apelido para não confundir com a variável local
from backend.app.data.database import db as db_manager

def get_db() -> Generator:
    """
    Gere a ligação à base de dados para cada request.
    Usa a tua classe Database para gerar a sessão e garante o fecho seguro.
    """
    # Usamos o teu método criado especificamente para isto!
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


# --- 2. DEPENDÊNCIA DE AUTENTICAÇÃO ---
# O HTTPBearer diz ao FastAPI (e ao Swagger) para procurar um token no cabeçalho: "Authorization: Bearer <token>"
security = HTTPBearer()


def get_current_user_id() -> str:
    """
    ⚠️ MOCK TEMPORÁRIO PARA DESENVOLVIMENTO
    Substitui isto pela validação JWT real (que está comentada abaixo)
    quando a rota de Login for implementada.
    """
    # Garante que este UUID existe fisicamente na tua tabela `users` no PostgreSQL
    # para não dar erro de Chave Estrangeira (Foreign Key) quando guardares o áudio!
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