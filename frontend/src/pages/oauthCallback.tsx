import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { userService } from '../services/user/userService';
import Spinner from '../components/Layout/Spinner';

/**
 * Pagina /auth/callback. O Google redirecciona o browser para aqui com
 * ?code=... — trocamos esse code pelo JWT no backend, guardamos via
 * utils/auth.ts e seguimos para /home.
 */
function OAuthCallbackPage() {
    const [params] = useSearchParams();
    const navigate = useNavigate();
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const code = params.get('code');
        if (!code) {
            setError('Código OAuth em falta na URL.');
            return;
        }
        (async () => {
            try {
                await userService.exchangeGoogleCode(code);
                navigate('/home', { replace: true });
            } catch (e: any) {
                setError(e?.detail ?? 'Falha a trocar o código Google por token.');
            }
        })();
    }, [params, navigate]);

    if (error) {
        return (
            <div className="auth-callback">
                <h2>Erro de autenticação</h2>
                <p className="error-text">{error}</p>
                <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => navigate('/login', { replace: true })}
                >
                    Voltar ao login
                </button>
            </div>
        );
    }

    return (
        <div className="auth-callback">
            <Spinner size="lg" block label="A concluir login…" />
        </div>
    );
}

export default OAuthCallbackPage;
