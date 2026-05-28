import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import useAuth from '../../hooks/auth/useAuth';
import useLanguage from '../../hooks/language/useLanguage';

/**
 * Header global das páginas autenticadas.
 *
 * Estrutura:
 *   [logo / brand]   [home] [projetos]          [lang btn]  [user menu]
 */
export function AppHeader() {
    const { user, logout } = useAuth();
    const { t, toggleLanguage } = useLanguage();
    const navigate = useNavigate();

    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!menuOpen) return;
        const onDoc = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', onDoc);
        return () => document.removeEventListener('mousedown', onDoc);
    }, [menuOpen]);

    const handleLogout = () => {
        logout();
        navigate('/login', { replace: true });
    };

    const initial = user?.username?.[0]?.toUpperCase() ?? '·';

    return (
        <header className="app-header">
            <div className="app-header-inner">
                <Link to="/home" className="app-brand">
                    <span className="app-brand-mark">♪</span>
                    <span className="app-brand-text">Music AI</span>
                </Link>

                <nav className="app-nav">
                    <NavLink to="/home" className="app-nav-link">
                        {t.nav.home}
                    </NavLink>
                    <NavLink to="/projects" className="app-nav-link">
                        {t.nav.projects}
                    </NavLink>
                </nav>

                <div className="app-header-controls">
                    <button
                        type="button"
                        className="app-lang-btn"
                        onClick={toggleLanguage}
                        aria-label={t.language.ariaLabel}
                        title={t.language.ariaLabel}
                    >
                        {t.language.switchTo}
                    </button>

                    <div className="app-user" ref={menuRef}>
                        <button
                            type="button"
                            className="app-user-trigger"
                            onClick={() => setMenuOpen(o => !o)}
                            aria-haspopup="menu"
                            aria-expanded={menuOpen}
                        >
                            <span className="app-user-avatar">{initial}</span>
                            <span className="app-user-name">
                                {user?.username ?? t.nav.profile}
                            </span>
                            <span className="app-user-caret">▾</span>
                        </button>

                        {menuOpen ? (
                            <div className="app-user-menu" role="menu">
                                <Link
                                    to="/profile"
                                    className="app-user-menu-item"
                                    onClick={() => setMenuOpen(false)}
                                    role="menuitem"
                                >
                                    {t.nav.profile}
                                </Link>
                                <button
                                    type="button"
                                    className="app-user-menu-item app-user-menu-danger"
                                    onClick={handleLogout}
                                    role="menuitem"
                                >
                                    {t.nav.logout}
                                </button>
                            </div>
                        ) : null}
                    </div>
                </div>
            </div>
        </header>
    );
}

export default AppHeader;
