import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import useAuth from '../hooks/auth/useAuth';
import useLanguage from '../hooks/language/useLanguage';
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
    const { t } = useLanguage();
    const [projects, setProjects] = useState<ProjectResponse[] | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        document.title = t.home.title;
        let cancelled = false;
        (async () => {
            try {
                const data = await projectService.listProjects();
                if (!cancelled) setProjects(data);
            } catch (e: any) {
                if (!cancelled) setError(e?.detail ?? t.home.loadError);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [t]);

    const recent = (projects ?? []).slice(-3).reverse();

    return (
        <div className="home">
            <section className="home-hero">
                <div>
                    <h1>{t.home.greeting.replace('{name}', user?.username ?? 'músico')}</h1>
                    <p className="text-soft">{t.home.subtitle}</p>
                </div>

                <div className="home-stats">
                    <div className="home-stat-card">
                        <span className="home-stat-label">{t.home.projects}</span>
                        <span className="home-stat-value">
                            {projects === null ? '—' : projects.length}
                        </span>
                    </div>
                    <Link to="/projects" className="btn btn-secondary">
                        {t.home.viewAll}
                    </Link>
                </div>
            </section>

            <section className="home-quick">
                <h2>{t.home.shortcuts}</h2>
                <div className="home-quick-grid">
                    <Link to="/projects" className="home-quick-card">
                        <span className="home-quick-icon">🎼</span>
                        <span className="home-quick-title">{t.home.myProjects}</span>
                        <span className="home-quick-desc">{t.home.myProjectsDesc}</span>
                    </Link>
                    <Link to="/profile" className="home-quick-card">
                        <span className="home-quick-icon">👤</span>
                        <span className="home-quick-title">{t.nav.profile}</span>
                        <span className="home-quick-desc">{t.home.profileDesc}</span>
                    </Link>
                </div>
            </section>

            <section className="home-recent">
                <div className="section-title">
                    <h2>{t.home.recentProjects}</h2>
                    <Link to="/projects" className="text-sm">
                        {t.home.viewAll}
                    </Link>
                </div>

                {projects === null && !error ? (
                    <Spinner block label={t.home.loading} />
                ) : null}

                {error ? <p className="error-text">{error}</p> : null}

                {projects && projects.length === 0 ? (
                    <EmptyState
                        icon="🎼"
                        title={t.home.noProjects}
                        description={t.home.noProjectsDesc}
                        action={
                            <Link to="/projects" className="btn">
                                {t.home.createProject}
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
                                            {p.description || t.home.noDescription}
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
