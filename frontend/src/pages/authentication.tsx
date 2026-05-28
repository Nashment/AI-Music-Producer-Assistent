import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { userService } from '../services/user/userService';
import { isAuthenticated } from '../utils/auth';
import useLanguage from '../hooks/language/useLanguage';
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
    const { t, toggleLanguage } = useLanguage();
    const alreadyAuth = isAuthenticated();

    useEffect(() => {
        document.title = t.auth.title;
    }, [t]);

    if (alreadyAuth) return <Navigate to="/home" replace />;

    const handleGoogleLogin = async () => {
        setLoading(true);
        setError(null);
        try {
            const { authorization_url } = await userService.getGoogleAuthUrl();
            window.location.href = authorization_url;
        } catch (e: any) {
            setError(e?.message ?? t.auth.loginError);
            setLoading(false);
        }
    };

    return (
        <div className="auth-shell">
            {/* Language toggle — fora do AppHeader nesta página pública */}
            <button
                type="button"
                className="auth-lang-btn"
                onClick={toggleLanguage}
                aria-label={t.language.ariaLabel}
                title={t.language.ariaLabel}
            >
                {t.language.switchTo}
            </button>

            <section className="auth-hero">
                <div className="auth-hero-mark">♪</div>
                <h1>Music AI</h1>
                <p className="text-soft">{t.auth.subtitle}</p>
                <ul className="auth-hero-bullets">
                    <li>{t.auth.bullet1}</li>
                    <li>{t.auth.bullet2}</li>
                    <li>{t.auth.bullet3}</li>
                    <li>{t.auth.bullet4}</li>
                    <li>{t.auth.bullet5}</li>
                </ul>
            </section>

            <section className="auth-card">
                <h2>{t.auth.signIn}</h2>
                <p className="text-muted text-sm">{t.auth.signInDesc}</p>

                <button
                    type="button"
                    className="btn btn-block auth-google-btn"
                    onClick={handleGoogleLogin}
                    disabled={loading}
                >
                    {loading ? (
                        <Spinner size="sm" label={t.auth.redirecting} />
                    ) : (
                        <>
                            <span className="auth-google-mark" aria-hidden>G</span>
                            <span>{t.auth.continueGoogle}</span>
                        </>
                    )}
                </button>

                {error ? <p className="error-text">{error}</p> : null}

                <p className="auth-fineprint">{t.auth.fineprint}</p>
            </section>
        </div>
    );
}

export default AuthenticationPage;
