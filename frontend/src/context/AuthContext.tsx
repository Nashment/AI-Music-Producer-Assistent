import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { userService } from '../services/user/userService';
import {
    clearAuth,
    getAccessToken,
    getStoredUser,
    isAuthenticated,
    saveAuth,
    StoredUser,
} from '../utils/auth';

/* -------------------------------------------------------------------------- */
/*  Tipos                                                                       */
/* -------------------------------------------------------------------------- */

interface AuthContextValue {
    user: StoredUser | null;
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
    logout: () => void;
}

/* -------------------------------------------------------------------------- */
/*  Context                                                                     */
/* -------------------------------------------------------------------------- */

const AuthContext = createContext<AuthContextValue | null>(null);

/* -------------------------------------------------------------------------- */
/*  Provider                                                                    */
/* -------------------------------------------------------------------------- */

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<StoredUser | null>(getStoredUser());
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const refresh = useCallback(async () => {
        if (!isAuthenticated()) return;
        setLoading(true);
        setError(null);
        try {
            const me = await userService.getMe();
            const updated: StoredUser = { id: me.id, username: me.username };
            setUser(updated);
            // Atualiza o localStorage para que o estado persista entre reloads
            const token = getAccessToken();
            if (token) saveAuth(token, updated);
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

    return (
        <AuthContext.Provider value={{ user, loading, error, refresh, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

/* -------------------------------------------------------------------------- */
/*  Hook de consumo                                                             */
/* -------------------------------------------------------------------------- */

export function useAuthContext(): AuthContextValue {
    const ctx = useContext(AuthContext);
    if (!ctx) {
        throw new Error('useAuthContext deve ser usado dentro de <AuthProvider>');
    }
    return ctx;
}

export default AuthContext;
