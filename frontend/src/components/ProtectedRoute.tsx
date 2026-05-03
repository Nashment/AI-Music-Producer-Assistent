import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { checkAuth } from '../services/request';
import Spinner from './Layout/Spinner';

/**
 * Guarda de rota: verifica se ha um token valido. Enquanto verifica
 * mostra "Loading..."; se falhar redirecciona para /login.
 *
 * Mesmo padrao que o exemplo Kotlin tinha, mas adaptado para JWT em vez
 * de sessao por cookie.
 */
export function ProtectedRoute() {
    const [isAuth, setIsAuth] = useState<boolean | null>(null);

    useEffect(() => {
        let cancelled = false;
        const verify = async () => {
            const ok = await checkAuth();
            if (!cancelled) setIsAuth(ok);
        };
        verify();
        return () => {
            cancelled = true;
        };
    }, []);

    if (isAuth === null) {
        return <Spinner block size="lg" label="A verificar sessão…" />;
    }
    if (!isAuth) return <Navigate to="/login" replace />;

    return <Outlet />;
}

export default ProtectedRoute;
