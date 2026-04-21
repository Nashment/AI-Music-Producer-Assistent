"""
Authentication Service - OAuth and JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import os
from enum import Enum

from app.core.config import settings


class OAuthProvider(str, Enum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class AuthService:
    """
    Service for OAuth authentication and JWT token management
    """

    def __init__(self, data_accessor=None):
        """
        Initialize auth service
        
        Args:
            data_accessor: Data access layer instance
        """
        self.data = data_accessor
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.token_expiration_hours = 24

    def create_access_token(self, user_id: str) -> str:
        """
        Create JWT access token for authenticated user
        
        Args:
            user_id: User UUID as string
            
        Returns:
            JWT token string
        """
        to_encode = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiration_hours),
            "iat": datetime.utcnow()
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            print("Token has expired")
            return None
        except jwt.InvalidTokenError:
            print("Invalid token")
            return None

    async def oauth_login_google(self, code: str, db) -> Dict:
        """
        Handle Google OAuth login flow
        
        Args:
            code: Authorization code from Google OAuth
            db: Database session
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
            
            google = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = google.fetch_token(
                "https://accounts.google.com/o/oauth2/token",
                code=code
            )
            
            user_info = google.get("https://www.googleapis.com/oauth2/v2/userinfo").json()
            
            user = await self._get_or_create_user(
                db=db,
                provider=OAuthProvider.GOOGLE,
                provider_id=user_info.get("id"),
                username=user_info.get("email", "").split("@")[0] or user_info.get("name", "user")
            )
            
            jwt_token = self.create_access_token(str(user.id))
            
            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in Google OAuth: {e}")
            return {"error": str(e)}

    async def oauth_login_github(self, code: str, db) -> Dict:
        """
        Handle GitHub OAuth login flow
        
        Args:
            code: Authorization code from GitHub OAuth
            db: Database session
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("GITHUB_CLIENT_ID")
            client_secret = os.getenv("GITHUB_CLIENT_SECRET")
            redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:3000/auth/github/callback")
            
            github = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = github.fetch_token(
                "https://github.com/login/oauth/access_token",
                code=code
            )
            
            user_info = github.get("https://api.github.com/user").json()
            
            user = await self._get_or_create_user(
                db=db,
                provider=OAuthProvider.GITHUB,
                provider_id=str(user_info.get("id")),
                username=user_info.get("login", "user")
            )
            
            jwt_token = self.create_access_token(str(user.id))
            
            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in GitHub OAuth: {e}")
            return {"error": str(e)}

    async def oauth_login_microsoft(self, code: str, db) -> Dict:
        """
        Handle Microsoft OAuth login flow
        
        Args:
            code: Authorization code from Microsoft OAuth
            db: Database session
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("MICROSOFT_CLIENT_ID")
            client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
            redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:3000/auth/microsoft/callback")
            
            microsoft = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = microsoft.fetch_token(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                code=code
            )
            
            user_info = microsoft.get("https://graph.microsoft.com/v1.0/me").json()
            
            user = await self._get_or_create_user(
                db=db,
                provider=OAuthProvider.MICROSOFT,
                provider_id=user_info.get("id"),
                username=user_info.get("mailNickname") or user_info.get("displayName", "user")
            )
            
            jwt_token = self.create_access_token(str(user.id))
            
            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in Microsoft OAuth: {e}")
            return {"error": str(e)}

    async def _get_or_create_user(
        self,
        db,
        provider: OAuthProvider,
        provider_id: str,
        username: str,
    ):
        """
        Get existing user or create new one from OAuth data
        
        Args:
            db: Database session
            provider: OAuth provider (google, github, microsoft)
            provider_id: User ID from provider
            username: Username from provider
            
        Returns:
            User object
        """
        from app.data.oauth_queries import OAuthQueries
        from app.data.models import OAuthProvider as ModelOAuthProvider

        model_provider = ModelOAuthProvider(provider.value)
        user = await OAuthQueries.get_or_create_user(
            db=db,
            oauth_provider=model_provider,
            oauth_id=provider_id,
            username=username
        )
        return user
