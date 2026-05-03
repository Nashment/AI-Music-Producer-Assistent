import { request } from '../request';
import { BASE_URL } from '../../utils/common';
import { saveAuth, clearAuth } from '../../utils/auth';
import {
    OAuthStartResponse,
    TokenResponse,
    UserResponse,
} from './userResponseTypes';

/**
 * Servico do dominio "user".
 *
 * Responsabilidades:
 *   - Iniciar fluxo OAuth Google.
 *   - Trocar code por JWT no callback.
 *   - Ler/actualizar/apagar o utilizador autenticado.
 *
 * Backend: prefixo /users (a request() ja prefixa /api -> /api/v1).
 */
export const userService = {
    /**
     * GET /users/auth/google/login
     * Devolve o URL para onde o frontend deve redireccionar o utilizador.
     *
     * NOTA: nao usamos request() porque este endpoint nao exige token e
     * queremos manter o erro mais simples.
     */
    async getGoogleAuthUrl(): Promise<OAuthStartResponse> {
        const res = await fetch(`${BASE_URL}/users/auth/google/login`);
        if (!res.ok) throw new Error('Falha a obter URL de login Google.');
        return res.json();
    },

    /**
     * GET /users/auth/google/callback?code=...
     * Recebe o "code" devolvido pelo Google e troca-o por um JWT.
     * Persiste o token e o utilizador via utils/auth.
     */
    async exchangeGoogleCode(code: string): Promise<TokenResponse> {
        const res = await fetch(
            `${BASE_URL}/users/auth/google/callback?code=${encodeURIComponent(code)}`,
        );
        if (!res.ok) {
            const problem = await res.json().catch(() => ({}));
            throw {
                code: problem.type ?? 'OAUTH_FAILURE',
                title: problem.title ?? 'Auth failed',
                detail: problem.detail ?? 'Falha na autenticacao Google.',
                status: res.status,
            };
        }
        const data: TokenResponse = await res.json();
        saveAuth(data.access_token, { id: data.user.id, username: data.user.username });
        return data;
    },

    /**
     * GET /users/me
     */
    async getMe(): Promise<UserResponse> {
        const res = await request('/users/me', { method: 'GET' });
        return res.json();
    },

    /**
     * PUT /users/me — actualiza o username.
     */
    async updateUsername(username: string): Promise<UserResponse> {
        const res = await request('/users/me', {
            method: 'PUT',
            body: JSON.stringify({ username }),
        });
        return res.json();
    },

    /**
     * DELETE /users/me — apaga conta. Limpa estado local.
     */
    async deleteMe(): Promise<void> {
        await request('/users/me', { method: 'DELETE' });
        clearAuth();
    },

    /**
     * Logout local — o backend nao expoe endpoint de logout (JWT stateless),
     * por isso simplesmente apagamos o token.
     */
    logout(): void {
        clearAuth();
    },
};
