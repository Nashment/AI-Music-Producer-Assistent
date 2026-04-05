"""
Authentication Service - OAuth and JWT token management
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import os
from enum import Enum

from backend.app.core.config import settings


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

    def create_access_token(self, user_id: int, email: str) -> str:
        """
        Create JWT access token for authenticated user
        
        Args:
            user_id: User database ID
            email: User email
            
        Returns:
            JWT token string
        """
        to_encode = {
            "sub": str(user_id),
            "email": email,
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

    async def oauth_login_google(self, code: str) -> Dict:
        """
        Handle Google OAuth login flow
        
        Args:
            code: Authorization code from Google OAuth
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            # Import authlib only when needed
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
            
            # Exchange code for token
            google = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = google.fetch_token(
                "https://accounts.google.com/o/oauth2/token",
                code=code
            )
            
            # Get user info
            user_info = google.get("https://www.googleapis.com/oauth2/v2/userinfo").json()
            
            # Find or create user
            user = await self._get_or_create_user(
                provider=OAuthProvider.GOOGLE,
                provider_id=user_info.get("id"),
                email=user_info.get("email"),
                username=user_info.get("email").split("@")[0],
                profile_picture_url=user_info.get("picture"),
                full_name=user_info.get("name"),
                access_token=token.get("access_token")
            )
            
            # Create JWT token
            jwt_token = self.create_access_token(user.id, user.email)
            
            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "profile_picture_url": user.profile_picture_url
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in Google OAuth: {e}")
            return {"error": str(e)}

    async def oauth_login_github(self, code: str) -> Dict:
        """
        Handle GitHub OAuth login flow
        
        Args:
            code: Authorization code from GitHub OAuth
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("GITHUB_CLIENT_ID")
            client_secret = os.getenv("GITHUB_CLIENT_SECRET")
            redirect_uri = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:3000/auth/github/callback")
            
            # Exchange code for token
            github = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = github.fetch_token(
                "https://github.com/login/oauth/access_token",
                code=code
            )
            
            # Get user info
            user_info = github.get("https://api.github.com/user").json()
            
            # Find or create user
            user = await self._get_or_create_user(
                provider=OAuthProvider.GITHUB,
                provider_id=str(user_info.get("id")),
                email=user_info.get("email"),
                username=user_info.get("login"),
                profile_picture_url=user_info.get("avatar_url"),
                full_name=user_info.get("name"),
                access_token=token.get("access_token")
            )
            
            # Create JWT token
            jwt_token = self.create_access_token(user.id, user.email)
            
            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "profile_picture_url": user.profile_picture_url
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in GitHub OAuth: {e}")
            return {"error": str(e)}

    async def oauth_login_microsoft(self, code: str) -> Dict:
        """
        Handle Microsoft OAuth login flow
        
        Args:
            code: Authorization code from Microsoft OAuth
            
        Returns:
            Dict with user info and JWT token
        """
        try:
            from authlib.integrations.requests_client import OAuth2Session
            
            client_id = os.getenv("MICROSOFT_CLIENT_ID")
            client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
            redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:3000/auth/microsoft/callback")
            
            # Exchange code for token
            microsoft = OAuth2Session(
                client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri
            )
            
            token = microsoft.fetch_token(
                "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                code=code
            )
            
            # Get user info
            user_info = microsoft.get("https://graph.microsoft.com/v1.0/me").json()
            
            # Find or create user
            user = await self._get_or_create_user(
                provider=OAuthProvider.MICROSOFT,
                provider_id=user_info.get("id"),
                email=user_info.get("userPrincipalName"),
                username=user_info.get("mailNickname"),
                profile_picture_url=None,  # Get from /me/photo if needed
                full_name=user_info.get("displayName"),
                access_token=token.get("access_token")
            )
            
            # Create JWT token
            jwt_token = self.create_access_token(user.id, user.email)
            
            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "profile_picture_url": user.profile_picture_url
                },
                "access_token": jwt_token,
                "token_type": "bearer"
            }
        except Exception as e:
            print(f"Error in Microsoft OAuth: {e}")
            return {"error": str(e)}

    async def _get_or_create_user(
        self,
        provider: OAuthProvider,
        provider_id: str,
        email: str,
        username: str,
        profile_picture_url: Optional[str] = None,
        full_name: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        """
        Get existing user or create new one from OAuth data
        
        Args:
            provider: OAuth provider (google, github, microsoft)
            provider_id: User ID from provider
            email: User email
            username: Username from provider
            profile_picture_url: Profile picture URL
            full_name: Full name from provider
            access_token: OAuth access token
            
        Returns:
            User object
        """
        # TODO: Implement with data accessor
        # 1. Check if user exists by oauth_provider + oauth_id
        # 2. If exists, update token if needed and return
        # 3. If not exists, create new user
        pass
