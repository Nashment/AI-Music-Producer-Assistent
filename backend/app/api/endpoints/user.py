"""
User endpoints - Google OAuth authentication and user management

Responsabilidades desta camada:
  - Receber pedidos HTTP e validar os parametros de entrada.
  - Chamar o servico e obter um Resultado[UtilizadorErro, T].
  - Mapear UtilizadorErro -> HTTP Problem Details (_handle_user_error).
  - Construir a resposta HTTP de sucesso.

O que NAO esta aqui:
  - Logica de negocio (esta no servico).
  - Excecoes genericas do Python (o servico nunca as lanca para ca).
"""

import uuid
from typing import Callable

from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.api.dependencies import get_db, get_current_user_id
from app.domain.result import Sucesso, Falha
from app.domain.errors.user_errors import (
    UtilizadorNaoEncontrado,
    UsernameInvalido,
    UsernameDuplicado,
    FalhaAutenticacaoGoogle,
    UtilizadorErro,
)
from app.domain.dtos.endpoints.user import (
    OAuthStartResponse,
    TokenResponse,
    UserResponse,
    UsernameUpdate,
)

router = APIRouter()


# ===========================================================================
# Tratamento de erros HTTP
# ===========================================================================

def _problem_json(status_code: int, type_slug: str, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type":     f"/errors/{type_slug}",
            "title":    title,
            "status":   status_code,
            "detail":   detail,
            "instance": instance,
        },
        media_type="application/problem+json",
    )


def _handle_user_error(erro: UtilizadorErro, instance: str) -> JSONResponse:
    match erro:
        case UtilizadorNaoEncontrado():
            # Em todos os endpoints /me o user_id vem do JWT. Se nao existe
            # na BD (ex: BD foi recriada), o token e efectivamente invalido
            # — devolvemos 401 para o frontend limpar o token e re-fazer login,
            # em vez de 404 que faz o ProtectedRoute entrar em loop.
            return _problem_json(401, "autenticacao-falhada", "Sessao Invalida",
                "O utilizador associado a este token ja nao existe. Faz login novamente.", instance)
        case UsernameInvalido():
            return _problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                "O username nao pode estar vazio.", instance)
        case UsernameDuplicado(username=u):
            return _problem_json(409, "username-duplicado", "Username Duplicado",
                f"O username '{u}' ja esta em uso.", instance)
        case FalhaAutenticacaoGoogle():
            return _problem_json(401, "autenticacao-falhada", "Autenticacao Falhada",
                "Nao foi possivel autenticar com o Google. Verifique o codigo e tente novamente.", instance)
        case _:
            return _problem_json(500, "erro-interno", "Erro Interno",
                "Ocorreu um erro inesperado no servico de utilizador.", instance)


def _handle_result(
    resultado: Sucesso | Falha,
    instance: str,
    success_factory: Callable,
) -> Response:
    match resultado:
        case Falha(erro=erro):
            return _handle_user_error(erro, instance)
        case Sucesso(valor=valor):
            return success_factory(valor)


# ===========================================================================
# Endpoints
# ===========================================================================

@router.get("/auth/google/login", response_model=OAuthStartResponse)
async def start_google_oauth():
    """Devolve o URL de autorizacao do Google."""
    service = UserService()
    url = service.get_google_authorization_url()
    return OAuthStartResponse(authorization_url=url, provider="google")


@router.get("/auth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Callback do Google OAuth."""
    resultado = await UserService(db).google_oauth_login(code=code)
    return _handle_result(
        resultado,
        instance="/api/v1/user/auth/google/callback",
        success_factory=lambda r: TokenResponse(
            access_token=r["access_token"],
            token_type=r["token_type"],
            user=UserResponse(**r["user"]),
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve o perfil do utilizador autenticado."""
    resultado = await UserService(db).get_user(user_id=user_id)
    return _handle_result(
        resultado,
        instance="/api/v1/user/me",
        success_factory=lambda user: user,
    )


@router.put("/me", response_model=UserResponse)
async def update_username(
    update_data: UsernameUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Actualiza o username do utilizador autenticado."""
    resultado = await UserService(db).update_username(user_id=user_id, username=update_data.username)
    return _handle_result(
        resultado,
        instance="/api/v1/user/me",
        success_factory=lambda user: user,
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Apaga a conta do utilizador autenticado."""
    resultado = await UserService(db).delete_user(user_id=user_id)
    return _handle_result(
        resultado,
        instance="/api/v1/user/me",
        success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )
