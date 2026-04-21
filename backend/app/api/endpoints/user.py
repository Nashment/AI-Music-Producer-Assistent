"""
User endpoints - OAuth authentication and user management
"""

import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthService
from app.data import UserQueries
from app.api.dependencies import get_db, get_current_user_id
from app.domain.dtos.endpoints.user import (
    OAuthCallbackRequest,
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
async def start_google_oauth(redirect_uri: str = "http://localhost:3000/auth/google/callback"):
    """Start Google OAuth login flow"""
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")

        google = OAuth2Session(client_id, redirect_uri=redirect_uri, scope="openid email profile")
        uri, state = google.create_authorization_url("https://accounts.google.com/o/oauth2/auth")
        return {"authorization_url": uri, "provider": "google"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


@router.get("/auth/github/login", response_model=OAuthStartResponse)
async def start_github_oauth(redirect_uri: str = "http://localhost:3000/auth/github/callback"):
    """Start GitHub OAuth login flow"""
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os

        client_id = os.getenv("GITHUB_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

        github = OAuth2Session(client_id, redirect_uri=redirect_uri, scope="user:email")
        uri, state = github.create_authorization_url("https://github.com/login/oauth/authorize")
        return {"authorization_url": uri, "provider": "github"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


@router.get("/auth/microsoft/login", response_model=OAuthStartResponse)
async def start_microsoft_oauth(redirect_uri: str = "http://localhost:3000/auth/microsoft/callback"):
    """Start Microsoft OAuth login flow"""
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os

        client_id = os.getenv("MICROSOFT_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Microsoft OAuth not configured")

        microsoft = OAuth2Session(client_id, redirect_uri=redirect_uri, scope="openid email profile")
        uri, state = microsoft.create_authorization_url(
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        return {"authorization_url": uri, "provider": "microsoft"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


# ==========================================
# OAuth Callback Endpoints
# ==========================================

@router.post("/auth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Google OAuth callback handler"""
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_google(request.code, db)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return TokenResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result["user"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/github/callback", response_model=TokenResponse)
async def github_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """GitHub OAuth callback handler"""
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_github(request.code, db)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return TokenResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result["user"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/microsoft/callback", response_model=TokenResponse)
async def microsoft_oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """Microsoft OAuth callback handler"""
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_microsoft(request.code, db)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))

        return TokenResponse(
            access_token=result["access_token"],
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result["user"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


# ==========================================
# User Profile Endpoints
# ==========================================

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Get current authenticated user profile"""
    user = await UserQueries.get_user_by_id(db=db, user_id=uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: UsernameUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Update user profile (username)"""
    user = await UserQueries.update_user(
        db=db,
        user_id=uuid.UUID(user_id),
        username=update_data.username
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Delete user account"""
    success = await UserQueries.delete_user(db=db, user_id=uuid.UUID(user_id))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.get("/auth/google/login", response_model=OAuthStartResponse)
async def start_google_oauth(redirect_uri: str = "http://localhost:3000/auth/google/callback"):
    """
    Start Google OAuth login flow
    
    Returns:
        Authorization URL to redirect user to Google
    """
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os
        
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        google = OAuth2Session(
            client_id,
            redirect_uri=redirect_uri,
            scope="openid email profile"
        )
        
        uri, state = google.create_authorization_url(
            "https://accounts.google.com/o/oauth2/auth"
        )
        
        return {
            "authorization_url": uri,
            "provider": "google"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


@router.get("/auth/github/login", response_model=OAuthStartResponse)
async def start_github_oauth(redirect_uri: str = "http://localhost:3000/auth/github/callback"):
    """
    Start GitHub OAuth login flow
    
    Returns:
        Authorization URL to redirect user to GitHub
    """
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os
        
        client_id = os.getenv("GITHUB_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
        
        github = OAuth2Session(
            client_id,
            redirect_uri=redirect_uri,
            scope="user:email"
        )
        
        uri, state = github.create_authorization_url(
            "https://github.com/login/oauth/authorize"
        )
        
        return {
            "authorization_url": uri,
            "provider": "github"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


@router.get("/auth/microsoft/login", response_model=OAuthStartResponse)
async def start_microsoft_oauth(redirect_uri: str = "http://localhost:3000/auth/microsoft/callback"):
    """
    Start Microsoft OAuth login flow
    
    Returns:
        Authorization URL to redirect user to Microsoft
    """
    try:
        from authlib.integrations.requests_client import OAuth2Session
        import os
        
        client_id = os.getenv("MICROSOFT_CLIENT_ID")
        if not client_id:
            raise HTTPException(status_code=500, detail="Microsoft OAuth not configured")
        
        microsoft = OAuth2Session(
            client_id,
            redirect_uri=redirect_uri,
            scope="openid email profile"
        )
        
        uri, state = microsoft.create_authorization_url(
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        
        return {
            "authorization_url": uri,
            "provider": "microsoft"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initialization failed: {str(e)}")


# ==========================================
# OAuth Callback Endpoints
# ==========================================

@router.post("/auth/google/callback", response_model=TokenResponse)
async def google_oauth_callback(request: OAuthCallbackRequest):
    """
    Google OAuth callback handler
    
    Args:
        request: OAuth callback with authorization code
        
    Returns:
        User info and JWT token
    """
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_google(request.code)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return TokenResponse(
            access_token=result.get("access_token"),
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result.get("user"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/github/callback", response_model=TokenResponse)
async def github_oauth_callback(request: OAuthCallbackRequest):
    """
    GitHub OAuth callback handler
    
    Args:
        request: OAuth callback with authorization code
        
    Returns:
        User info and JWT token
    """
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_github(request.code)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return TokenResponse(
            access_token=result.get("access_token"),
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result.get("user"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/auth/microsoft/callback", response_model=TokenResponse)
async def microsoft_oauth_callback(request: OAuthCallbackRequest):
    """
    Microsoft OAuth callback handler
    
    Args:
        request: OAuth callback with authorization code
        
    Returns:
        User info and JWT token
    """
    try:
        auth_service = AuthService()
        result = await auth_service.oauth_login_microsoft(request.code)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return TokenResponse(
            access_token=result.get("access_token"),
            token_type=result.get("token_type", "bearer"),
            user=UserResponse(**result.get("user"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


# ==========================================
# User Profile Endpoints
# ==========================================

@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: str = None):
    """
    Get current authenticated user profile
    
    Requires:
        Authorization header with JWT token: "Bearer <token>"
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Extract token from Bearer scheme
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        
        auth_service = AuthService()
        
        payload = auth_service.verify_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # TODO: Get user from database using user_id from payload
        # user = await self.data.get_user(int(payload.get("sub")))
        
        raise HTTPException(status_code=501, detail="User lookup not implemented yet")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: dict,
    authorization: str = None
):
    """
    Update user profile
    
    Requires:
        Authorization header with JWT token: "Bearer <token>"
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        auth_service = AuthService()
        
        scheme, token = authorization.split()
        payload = auth_service.verify_token(token)
        
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # TODO: Update user profile in database
        
        raise HTTPException(status_code=501, detail="Profile update not implemented yet")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(authorization: str = None):
    """
    Delete user account
    
    Requires:
        Authorization header with JWT token: "Bearer <token>"
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        auth_service = AuthService()
        
        scheme, token = authorization.split()
        payload = auth_service.verify_token(token)
        
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # TODO: Delete user from database
        
        raise HTTPException(status_code=501, detail="Account deletion not implemented yet")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
