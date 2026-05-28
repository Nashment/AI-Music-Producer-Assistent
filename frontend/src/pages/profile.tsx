import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { userService } from '../services/user/userService';
import useAuth from '../hooks/auth/useAuth';
import useTheme from '../hooks/theme/useTheme';
import useLanguage from '../hooks/language/useLanguage';
import PageHeader from '../components/Layout/PageHeader';
import ConfirmDialog from '../components/Layout/ConfirmDialog';
import Spinner from '../components/Layout/Spinner';
import { useToast, describeError } from '../components/Layout/Toast';

/**
 * /profile — gestão da conta:
 *   - vê username actual,
 *   - actualiza username,
 *   - apaga conta (com confirmação).
 */
function ProfilePage() {
    const { user, refresh, logout } = useAuth();
    const { theme, toggleTheme } = useTheme();
    const { t } = useLanguage();
    const navigate = useNavigate();
    const toast = useToast();

    const [username, setUsername] = useState('');
    const [saving, setSaving] = useState(false);
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (user) setUsername(user.username);
    }, [user]);

    const dirty = (user?.username ?? '') !== username.trim();

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!username.trim()) {
            toast.error(t.profile.usernameEmpty);
            return;
        }
        if (!dirty) return;
        setSaving(true);
        try {
            await userService.updateUsername(username.trim());
            await refresh();
            toast.success(t.profile.usernameSaved);
        } catch (err) {
            toast.error(describeError(err, t.profile.saveError));
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await userService.deleteMe();
            logout();
            toast.success(t.profile.accountDeleted);
            navigate('/login', { replace: true });
        } catch (err) {
            toast.error(describeError(err, t.profile.accountDeleteError));
            setDeleting(false);
            setConfirmOpen(false);
        }
    };

    if (!user) return <Spinner block label={t.profile.loading} />;

    return (
        <div className="profile">
            <PageHeader
                title={t.profile.title}
                description={t.profile.description}
                backTo="/home"
                backLabel={t.profile.backLabel}
            />

            <section className="card profile-card">
                <h3>{t.profile.basicInfo}</h3>
                <form onSubmit={handleSave} className="profile-form">
                    <div className="field">
                        <label htmlFor="username">{t.profile.usernameLabel}</label>
                        <input
                            id="username"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder={t.profile.usernamePlaceholder}
                        />
                        <span className="field-hint">
                            {t.profile.internalId} <span className="text-mono">{user.id}</span>
                        </span>
                    </div>

                    <div className="profile-form-actions">
                        <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => setUsername(user.username)}
                            disabled={!dirty || saving}
                        >
                            {t.profile.revert}
                        </button>
                        <button type="submit" disabled={!dirty || saving}>
                            {saving ? t.profile.saving : t.profile.saveChanges}
                        </button>
                    </div>
                </form>
            </section>

            <section className="card profile-card">
                <h3>{t.profile.preferences}</h3>
                <div className="profile-theme-row">
                    <div className="profile-theme-info">
                        <span className="profile-theme-label">{t.profile.theme}</span>
                        <span className="profile-theme-desc text-muted text-sm">
                            {theme === 'dark' ? t.profile.themeDark : t.profile.themeLight}
                        </span>
                    </div>
                    <button
                        type="button"
                        className={`theme-switch${theme === 'light' ? ' theme-switch--light' : ''}`}
                        onClick={toggleTheme}
                        aria-label={`Mudar para tema ${theme === 'dark' ? 'claro' : 'escuro'}`}
                        role="switch"
                        aria-checked={theme === 'light'}
                    >
                        <span className="theme-switch-track">
                            <span className="theme-switch-icon theme-switch-icon--dark">🌙</span>
                            <span className="theme-switch-icon theme-switch-icon--light">☀️</span>
                        </span>
                        <span className="theme-switch-thumb" />
                    </button>
                </div>
            </section>

            <section className="card profile-danger">
                <h3>{t.profile.dangerZone}</h3>
                <p className="text-muted text-sm">{t.profile.dangerDesc}</p>
                <button
                    type="button"
                    className="btn btn-danger-ghost"
                    onClick={() => setConfirmOpen(true)}
                >
                    {t.profile.deleteAccount}
                </button>
            </section>

            <ConfirmDialog
                open={confirmOpen}
                title={t.profile.confirmDeleteTitle}
                message={t.profile.confirmDeleteMsg}
                confirmLabel={t.profile.confirmDeleteLabel}
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmOpen(false)}
            />
        </div>
    );
}

export default ProfilePage;
