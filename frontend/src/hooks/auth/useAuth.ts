import { useCallback, useEffect, useState } from 'react';
import { userService } from '../../services/user/userService';
import { clearAuth, getStoredUser, isAuthenticated, StoredUser } from '../../utils/auth';

/**
 * Hook simples de autenticacao para a UI.
 *
 * Devolve:
 *   - user: utilizador actual (em memoria a partir do localStorage),
 *   - loading: a carregar /users/me na primeira render,
 *   - error: erro de comunicacao,
 *   - logout: helper que limpa o token e devolve o caller a "/login".
 */
export function useAuth() {
    const [user, setUser] = useState<StoredUser | null>(getStoredUser());
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        if (!isAuthenticated()) return;
        setLoading(true);
        setError(null);
        try {
            const me = await userService.getMe();
            setUser({ id: me.id, username: me.username });
        } catch (e: any) {
            setError(e?.detail ?? 'Falha a carregar utilizador.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const logout = useCallback(() => {
        clearAuth();
        setUser(null);
    }, []);

    return { user, loading, error, refresh, logout };
}

export default useAuth;
