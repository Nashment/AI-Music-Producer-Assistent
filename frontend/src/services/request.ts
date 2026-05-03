import { BASE_URL } from '../utils/common';
import { clearAuth, getAccessToken } from '../utils/auth';

/**
 * Erro normalizado devolvido pelos services. O backend usa Problem Details
 * (RFC 7807) com a forma:
 *   { type, title, status, detail, instance }
 *
 * Convertemos para um objecto mais simples para a UI.
 */
export type ApiError = {
    code: string;
    title: string;
    detail: string;
    status: number;
};

/**
 * Wrapper minimalista por cima de fetch que:
 *   - prefixa o BASE_URL,
 *   - injecta o JWT no header Authorization (se existir),
 *   - normaliza erros do backend (Problem Details) para ApiError.
 *
 * Devolve sempre uma Response — o caller decide como ler o body
 * (json/blob/text). Erros sao lancados como ApiError.
 */
export async function request(
    url: string,
    options: RequestInit = {},
): Promise<Response> {
    const token = getAccessToken();

    const headers: Record<string, string> = {
        Accept: 'application/json',
        ...(options.body && !(options.body instanceof FormData)
            ? { 'Content-Type': 'application/json' }
            : {}),
        ...((options.headers as Record<string, string>) ?? {}),
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        // Token invalido/expirado: limpa estado local. A UI decide
        // o redirect via ProtectedRoute.
        clearAuth();
    }

    if (!response.ok) {
        const problem = await response.clone().json().catch(() => ({}));
        throw {
            code: problem.type ?? 'UNKNOWN_ERROR',
            title: problem.title ?? 'Erro',
            detail: problem.detail ?? response.statusText,
            status: response.status,
        } as ApiError;
    }

    return response;
}

/**
 * Verifica se o token actual ainda e valido pedindo /users/me.
 * Usado pelo ProtectedRoute.
 *
 * Se /users/me falhar por QUALQUER razao (401 token invalido, 404 user
 * apagado, 500 backend doente), limpamos o token. Caso contrario fica-se
 * preso num loop entre /home -> /login -> /home porque a Authentication
 * page so olha para o localStorage e re-redirecciona para /home.
 */
export async function checkAuth(): Promise<boolean> {
    const token = getAccessToken();
    if (!token) return false;
    try {
        const res = await fetch(`${BASE_URL}/users/me`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
            clearAuth();
            return false;
        }
        return true;
    } catch {
        // Erro de rede: nao limpamos para nao expulsar o utilizador
        // se o backend estiver momentaneamente em baixo.
        return false;
    }
}
