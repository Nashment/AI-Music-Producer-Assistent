import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import useAuth from '../hooks/auth/useAuth';
import { projectService } from '../services/project/projectService';
import { ProjectResponse } from '../services/project/projectResponseTypes';
import Spinner from '../components/Layout/Spinner';
import EmptyState from '../components/Layout/EmptyState';

/**
 * /home — dashboard de entrada. Mostra:
 *   - saudacao + total de projetos,
 *   - atalhos rapidos,
 *   - ultimos projetos.
 */
function HomePage() {
    const { user } = useAuth();
    const [projects, setProjects] = useState<ProjectResponse[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        document.title = 'Home — Music AI';
        let cancelled = false;
        (async () => {
            try {
                const data = await projectService.listProjects();
                if (!cancelled) setProjects(data);
            } catch (e: any) {
                if (!cancelled) setError(e?.detail ?? 'Erro a carregar projetos.');
            }
        })();
        return () => {
            cancelled = true;
        };
    }, []);

    const recent = (projects ?? []).slice(-3).reverse();

    return (
        <div className="home">
            <section className="home-hero">
                <div>
                    <h1>Olá, {user?.username ?? 'músico'} 👋</h1>
                    <p className="text-soft">
                        Pronto para a tua próxima ideia? Cria um projeto, faz
                        upload de áudio e deixa a análise tratar do resto.
                    </p>
                </div>

                <div className="home-stats">
                    <div className="home-stat-card">
                        <span className="home-stat-label">Projetos</span>
                        <span className="home-stat-value">
                            {projects === null ? '—' : projects.length}
                        </span>
                    </div>
                    <Link to="/projects" className="btn btn-secondary">
                        Ver todos →
                    </Link>
                </div>
            </section>

            <section className="home-quick">
                <h2>Atalhos</h2>
                <div className="home-quick-grid">
                    <Link to="/projects" className="home-quick-card">
                        <span className="home-quick-icon">🎼</span>
                        <span className="home-quick-title">Os meus projetos</span>
                        <span className="home-quick-desc">
                            Vê e gere as tuas sessões de trabalho.
                        </span>
                    </Link>
                    <Link to="/profile" className="home-quick-card">
                        <span className="home-quick-icon">👤</span>
                        <span className="home-quick-title">Perfil</span>
                        <span className="home-quick-desc">
                            Edita o teu username ou apaga conta.
                        </span>
                    </Link>
                </div>
            </section>

            <section className="home-recent">
                <div className="section-title">
                    <h2>Projetos recentes</h2>
                    <Link to="/projects" className="text-sm">
                        Ver todos →
                    </Link>
                </div>

                {projects === null && !error ? (
                    <Spinner block label="A carregar…" />
                ) : null}

                {error ? <p className="error-text">{error}</p> : null}

                {projects && projects.length === 0 ? (
                    <EmptyState
                        icon="🎼"
                        title="Ainda sem projetos"
                        description="Cria o teu primeiro projeto para começar a carregar áudios."
                        action={
                            <Link to="/projects" className="btn">
                                Criar projeto
                            </Link>
                        }
                    />
                ) : null}

                {projects && projects.length > 0 ? (
                    <ul className="home-recent-list">
                        {recent.map(p => (
                            <li key={p.id}>
                                <Link to={`/projects/${p.id}`} className="home-recent-item">
                                    <div>
                                        <strong>{p.title}</strong>
                                        <p className="text-muted text-sm">
                                            {p.description || 'sem descrição'}
                                        </p>
                                    </div>
                                    <span className="badge badge-primary">
                                        {p.tempo} BPM
                                    </span>
                                </Link>
                            </li>
                        ))}
                    </ul>
                ) : null}
            </section>
        </div>
    );
}

export default HomePage;
