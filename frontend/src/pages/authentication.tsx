import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { userService } from '../services/user/userService';
import { isAuthenticated } from '../utils/auth';
import Spinner from '../components/Layout/Spinner';

/**
 * Landing/login. Apresenta o produto em duas colunas (hero + card de login)
 * e tem um unico CTA: entrar com Google.
 *
 * Se o utilizador ja tem token guardado em localStorage, salta directamente
 * para /home.
 */
function AuthenticationPage() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const alreadyAuth = isAuthenticated();

    useEffect(() => {
        document.title = 'Entrar — Music AI';
    }, []);

    if (alreadyAuth) return <Navigate to="/home" replace />;

    const handleGoogleLogin = async () => {
        setLoading(true);
        setError(null);
        try {
            const { authorization_url } = await userService.getGoogleAuthUrl();
            window.location.href = authorization_url;
        } catch (e: any) {
            setError(e?.message ?? 'Não foi possível iniciar o login com Google.');
            setLoading(false);
        }
    };

    return (
        <div className="auth-shell">
            <section className="auth-hero">
                <div className="auth-hero-mark">♪</div>
                <h1>Music AI</h1>
                <p className="text-soft">
                    Carrega áudio, analisa BPM e tonalidade, separa
                    instrumentos e gera novas peças — tudo num só sítio.
                </p>
                <ul className="auth-hero-bullets">
                    <li>Upload e análise automática de .mp3 / .wav</li>
                    <li>Ajuste de BPM e corte de excertos</li>
                    <li>Separação de instrumentos por IA</li>
                    <li>Pipeline de geração musical (em breve)</li>
                </ul>
            </section>

            <section className="auth-card">
                <h2>Entrar</h2>
                <p className="text-muted text-sm">
                    Usa a tua conta Google. Não criamos nem guardamos
                    passwords.
                </p>

                <button
                    type="button"
                    className="btn btn-block auth-google-btn"
                    onClick={handleGoogleLogin}
                    disabled={loading}
                >
                    {loading ? (
                        <Spinner size="sm" label="A redirecionar…" />
                    ) : (
                        <>
                            <span className="auth-google-mark" aria-hidden>G</span>
                            <span>Continuar com Google</span>
                        </>
                    )}
                </button>

                {error ? <p className="error-text">{error}</p> : null}

                <p className="auth-fineprint">
                    Ao continuar concordas com o uso responsável da plataforma
                    e com o tratamento dos teus áudios para análise.
                </p>
            </section>
        </div>
    );
}

export default AuthenticationPage;
