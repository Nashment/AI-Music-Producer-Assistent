/**
 * Testes unitários para src/services/request.ts — o wrapper central usado
 * por TODOS os services (project, audio, generation, user). Um bug aqui
 * propaga-se silenciosamente a toda a aplicação, por isso é o ponto de
 * maior alavancagem para testes na camada de serviços.
 *
 * Cobre:
 *   - Prefixo BASE_URL ('/api')
 *   - Injecção do header Authorization quando há token
 *   - Ausência do header quando não há token
 *   - Content-Type: application/json quando body não é FormData
 *   - Sem Content-Type quando body é FormData (deixa o browser definir o boundary)
 *   - clearAuth() ao receber 401
 *   - Normalização de erros (Problem Details -> ApiError) em respostas não-ok
 *   - Fallback quando o corpo de erro não é JSON válido
 *   - checkAuth(): sem token, sucesso, falha (limpa auth), erro de rede (não limpa)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { request, checkAuth } from '../../../src/services/request';
import { saveAuth, clearAuth, getAccessToken } from '../../../src/utils/auth';

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

describe('request()', () => {
    it('prefixa a URL com BASE_URL (/api)', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
        await request('/projects', { method: 'GET' });
        expect(fetch).toHaveBeenCalledWith('/api/projects', expect.any(Object));
    });

    it('injecta o header Authorization quando há token guardado', async () => {
        saveAuth('token-123', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

        await request('/projects', { method: 'GET' });

        const [, init] = vi.mocked(fetch).mock.calls[0];
        expect((init!.headers as Record<string, string>)['Authorization']).toBe('Bearer token-123');
    });

    it('não injecta Authorization quando não há token', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
        await request('/projects', { method: 'GET' });
        const [, init] = vi.mocked(fetch).mock.calls[0];
        expect((init!.headers as Record<string, string>)['Authorization']).toBeUndefined();
    });

    it('define Content-Type: application/json quando o body não é FormData', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
        await request('/projects', { method: 'POST', body: JSON.stringify({ a: 1 }) });
        const [, init] = vi.mocked(fetch).mock.calls[0];
        expect((init!.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    });

    it('não define Content-Type quando o body é FormData (upload)', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
        const fd = new FormData();
        fd.append('file', new Blob(['x']), 'a.wav');
        await request('/audio/project/p1/upload', { method: 'POST', body: fd });
        const [, init] = vi.mocked(fetch).mock.calls[0];
        expect((init!.headers as Record<string, string>)['Content-Type']).toBeUndefined();
    });

    it('limpa a autenticação quando a resposta é 401', async () => {
        saveAuth('token-expirado', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: 'Token inválido' }, 401));

        await expect(request('/users/me', { method: 'GET' })).rejects.toBeDefined();
        expect(getAccessToken()).toBeNull();
    });

    it('lança ApiError normalizado a partir de Problem Details em respostas não-ok', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            jsonResponse(
                { type: 'NOT_FOUND', title: 'Não encontrado', detail: 'Projeto não existe.' },
                404,
            ),
        );

        await expect(request('/projects/xyz', { method: 'GET' })).rejects.toEqual({
            code: 'NOT_FOUND',
            title: 'Não encontrado',
            detail: 'Projeto não existe.',
            status: 404,
        });
    });

    it('usa fallback quando o corpo de erro não é JSON válido', async () => {
        const badJsonResponse = new Response('<html>500</html>', {
            status: 500,
            statusText: 'Internal Server Error',
            headers: { 'Content-Type': 'text/html' },
        });
        vi.mocked(fetch).mockResolvedValueOnce(badJsonResponse);

        await expect(request('/projects', { method: 'GET' })).rejects.toEqual({
            code: 'UNKNOWN_ERROR',
            title: 'Erro',
            detail: 'Internal Server Error',
            status: 500,
        });
    });

    it('devolve a Response tal e qual quando o pedido é bem-sucedido', async () => {
        const res = jsonResponse({ id: 'p1' });
        vi.mocked(fetch).mockResolvedValueOnce(res);
        const result = await request('/projects/p1', { method: 'GET' });
        expect(result).toBe(res);
    });
});

describe('checkAuth()', () => {
    it('devolve false imediatamente (sem fetch) quando não há token', async () => {
        const ok = await checkAuth();
        expect(ok).toBe(false);
        expect(fetch).not.toHaveBeenCalled();
    });

    it('devolve true quando /users/me responde ok', async () => {
        saveAuth('token-válido', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'u1' }));

        const ok = await checkAuth();

        expect(ok).toBe(true);
        expect(fetch).toHaveBeenCalledWith(
            '/api/users/me',
            expect.objectContaining({ headers: { Authorization: 'Bearer token-válido' } }),
        );
    });

    it('limpa a auth e devolve false quando /users/me responde com erro', async () => {
        saveAuth('token-expirado', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({}, 401));

        const ok = await checkAuth();

        expect(ok).toBe(false);
        expect(getAccessToken()).toBeNull();
    });

    it('devolve false SEM limpar a auth quando há um erro de rede (backend em baixo)', async () => {
        saveAuth('token-válido', { id: 'u1', username: 'nash' });
        vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

        const ok = await checkAuth();

        expect(ok).toBe(false);
        // Não deve expulsar o utilizador só porque o backend está momentaneamente em baixo.
        expect(getAccessToken()).toBe('token-válido');
    });
});
