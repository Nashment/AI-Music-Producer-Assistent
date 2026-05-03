import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { userService } from '../services/user/userService';
import useAuth from '../hooks/auth/useAuth';
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
            toast.error('Username não pode ser vazio.');
            return;
        }
        if (!dirty) return;
        setSaving(true);
        try {
            await userService.updateUsername(username.trim());
            await refresh();
            toast.success('Username actualizado.');
        } catch (err) {
            toast.error(describeError(err, 'Erro a guardar.'));
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await userService.deleteMe();
            logout();
            toast.success('Conta apagada.');
            navigate('/login', { replace: true });
        } catch (err) {
            toast.error(describeError(err, 'Erro a apagar conta.'));
            setDeleting(false);
            setConfirmOpen(false);
        }
    };

    if (!user) return <Spinner block label="A carregar perfil…" />;

    return (
        <div className="profile">
            <PageHeader
                title="Perfil"
                description="Configura a tua conta."
                backTo="/home"
                backLabel="Home"
            />

            <section className="card profile-card">
                <h3>Informação básica</h3>
                <form onSubmit={handleSave} className="profile-form">
                    <div className="field">
                        <label htmlFor="username">Username</label>
                        <input
                            id="username"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            placeholder="Ex: joaomusic"
                        />
                        <span className="field-hint">
                            ID interno: <span className="text-mono">{user.id}</span>
                        </span>
                    </div>

                    <div className="profile-form-actions">
                        <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => setUsername(user.username)}
                            disabled={!dirty || saving}
                        >
                            Reverter
                        </button>
                        <button type="submit" disabled={!dirty || saving}>
                            {saving ? 'A guardar…' : 'Guardar alterações'}
                        </button>
                    </div>
                </form>
            </section>

            <section className="card profile-danger">
                <h3>Zona perigosa</h3>
                <p className="text-muted text-sm">
                    Apagar a conta remove o teu utilizador, projetos e áudios.
                    Esta acção é irreversível.
                </p>
                <button
                    type="button"
                    className="btn btn-danger-ghost"
                    onClick={() => setConfirmOpen(true)}
                >
                    Apagar conta
                </button>
            </section>

            <ConfirmDialog
                open={confirmOpen}
                title="Apagar conta?"
                message={
                    <>
                        Esta acção é <strong>irreversível</strong>. Vais
                        perder todos os projetos e áudios associados.
                    </>
                }
                confirmLabel="Sim, apagar"
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmOpen(false)}
            />
        </div>
    );
}

export default ProfilePage;
