/**
 * Tipos de resposta do dominio "user" — alinhados com os DTOs Pydantic
 * em backend/app/domain/dtos/endpoints/user.py
 */

export type UserResponse = {
    id: string;        // uuid
    username: string;
};

export type TokenResponse = {
    access_token: string;
    token_type: string; // tipicamente "bearer"
    user: UserResponse;
};

export type OAuthStartResponse = {
    authorization_url: string;
    provider: string;
};

export type UsernameUpdate = {
    username: string;
};
