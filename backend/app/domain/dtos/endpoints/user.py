import uuid

from pydantic import BaseModel


class UserResponse(BaseModel):
    """User response schema."""

    id: uuid.UUID
    username: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Authentication token response."""

    access_token: str
    token_type: str
    user: UserResponse


class OAuthStartResponse(BaseModel):
    """OAuth login start response with authorization URL."""

    authorization_url: str
    provider: str


class UsernameUpdate(BaseModel):
    """Schema for updating username."""

    username: str