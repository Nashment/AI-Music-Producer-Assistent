/**
 * Pequena camada para guardar e ler o JWT emitido pelo backend.
 *
 * O backend expoe Google OAuth e devolve um TokenResponse com:
 *   { access_token, token_type, user }
 *
 * Por simplicidade guardamos o token em localStorage. Esta funcao concentra
 * o acesso para que possamos no futuro trocar para httpOnly cookies, sem
 * mexer em todos os services.
 */

const STORAGE_KEY = 'music_ai.access_token';
const USER_KEY = 'music_ai.current_user';

export type StoredUser = {
    id: string;
    username: string;
};

export function saveAuth(token: string, user: StoredUser): void {
    localStorage.setItem(STORAGE_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getAccessToken(): string | null {
    return localStorage.getItem(STORAGE_KEY);
}

export function getStoredUser(): StoredUser | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
        return JSON.parse(raw) as StoredUser;
    } catch {
        return null;
    }
}

export function clearAuth(): void {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
    return getAccessToken() !== null;
}
