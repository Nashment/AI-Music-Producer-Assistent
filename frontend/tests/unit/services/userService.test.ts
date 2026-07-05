/**
 * Testes unitários para userService — fluxo OAuth Google (fora do wrapper
 * request()) e operações autenticadas sobre /users/me.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { userService } from '../../../src/services/user/userService';
import { getAccessToken, getStoredUser, saveAuth } from '../../../src/utils/auth';

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
    });
}

beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('getGoogleAuthUrl', () => {
    it('faz GET direto (sem passar por request()) e devolve o URL', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            jsonResponse({ authorization_url: 'https://accounts.google.com/x', provider: 'google' }),
        );

        const result = await userService.getGoogleAuthUrl();

        expect(fetch).toHaveBeenCalledWith('/api/users/auth/google/login');
        expect(result.authorization_url).toBe('https://accounts.google.com/x');
    });

    it('lança erro simples quando a resposta não é ok', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 500 }));
        await expect(userService.getGoogleAuthUrl()).rejects.toThrow('Falha a obter URL de login Google.');
    });
});

describe('exchangeGoogleCode', () => {
    it('troca o code por um token, persiste a auth e devolve os dados', async () => {
        const tokenResponse = {
            access_token: 'jwt-abc',
            token_type: 'bearer',
            user: { id: 'u1', username: 'nash' },
        };
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(tokenResponse));

        const result = await userService.exchangeGoogleCode('code-123');

        expect(fetch).toHaveBeenCalledWith('/api/users/auth/google/callback?code=code-123');
        expect(result).toEqual(tokenResponse);
        expect(getAccessToken()).toBe('jwt-abc');
        expect(getStoredUser()).toEqual({ id: 'u1', username: 'nash' });
    });

    it('lança um erro estruturado e NÃO persiste auth quando a troca falha', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            jsonResponse({ type: 'OAUTH_ERROR', title: 'Falhou', detail: 'Code inválido.' }, 400),
        );

        await expect(userService.exchangeGoogleCode('code-invalido')).rejects.toEqual({
            code: 'OAUTH_ERROR',
            title: 'Falhou',
            detail: 'Code inválido.',
            status: 400,
        });
        expect(getAccessToken()).toBeNull();
    });

    it('usa valores de fallback quando o corpo de erro não é JSON válido', async () => {
        const badResponse = new Response('erro raw', { status: 502 });
        vi.mocked(fetch).mockResolvedValueOnce(badResponse);

        await expect(userService.exchangeGoogleCode('x')).rejects.toEqual({
            code: 'OAUTH_FAILURE',
            title: 'Auth failed',
            detail: 'Falha na autenticacao Google.',
            status: 502,
        });
    });
});

describe('operações autenticadas (via request())', () => {
    it('getMe: GET /users/me', async () => {
        saveAuth('jwt-abc', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'u1', username: 'nash' }));

        const result = await userService.getMe();

        expect(fetch).toHaveBeenCalledWith(
            '/api/users/me',
            expect.objectContaining({ method: 'GET', headers: expect.objectContaining({ Authorization: 'Bearer jwt-abc' }) }),
        );
        expect(result).toEqual({ id: 'u1', username: 'nash' });
    });

    it('updateUsername: PUT /users/me com o novo username', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'u1', username: 'novo-nome' }));

        const result = await userService.updateUsername('novo-nome');

        expect(fetch).toHaveBeenCalledWith(
            '/api/users/me',
            expect.objectContaining({ method: 'PUT', body: JSON.stringify({ username: 'novo-nome' }) }),
        );
        expect(result.username).toBe('novo-nome');
    });

    it('deleteMe: DELETE /users/me e limpa a auth local', async () => {
        saveAuth('jwt-abc', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

        await userService.deleteMe();

        expect(fetch).toHaveBeenCalledWith('/api/users/me', expect.objectContaining({ method: 'DELETE' }));
        expect(getAccessToken()).toBeNull();
    });
});

describe('logout', () => {
    it('limpa a auth local sem chamar a rede', () => {
        saveAuth('jwt-abc', { id: 'u1', username: 'nash' });
        userService.logout();
        expect(getAccessToken()).toBeNull();
        expect(fetch).not.toHaveBeenCalled();
    });
});
