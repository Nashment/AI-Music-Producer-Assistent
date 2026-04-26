"""
User endpoints - Google OAuth authentication and user management
"""

import uuid

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.api.dependencies import get_db, get_current_user_id
from app.domain.dtos.endpoints.user import (
    OAuthStartResponse,
    TokenResponse,
    UserResponse,
    UsernameUpdate,
)

router = APIRouter()


# ==========================================
# OAuth Login Endpoints
# ==========================================

@router.get("/auth/google/login", response_model=OAuthStartResponse)
async def start_google_oauth():
    """
    Devolve o URL de autorização do Google.
    O frontend deve redirecionar o utilizador para este URL.
    """
    service = UserService()
    url = service.get_google_authorization_url()
    return OAuthStartResponse(authorization_url=url, provider="google")


@router.get("/auth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Callback do Google OAuth.
    O Google redireciona para aqui com o 'code' após o utilizador autorizar.
    """
    try:
        service = UserService(db)
        result = await service.google_oauth_login(code=code)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falha na autenticação Google: {str(e)}",
        )

    return TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        user=UserResponse(**result["user"]),
    )


# ==========================================
# User Profile Endpoints
# ==========================================

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Devolve o perfil do utilizador autenticado."""
    service = UserService(db)
    user = await service.get_user(user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
    return user


@router.put("/me", response_model=UserResponse)
async def update_username(
    update_data: UsernameUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Actualiza o username do utilizador autenticado."""
    service = UserService(db)
    try:
        user = await service.update_username(user_id=user_id, username=update_data.username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Apaga a conta do utilizador autenticado."""
    service = UserService(db)
    success = await service.delete_user(user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilizador não encontrado.")