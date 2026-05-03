import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { projectService } from '../services/project/projectService';

/**
 * Pagina /projects/new — formulario de criacao.
 */
function ProjectCreationPage() {
    const navigate = useNavigate();
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [tempo, setTempo] = useState<number>(120);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!title.trim()) {
            setError('Titulo obrigatorio.');
            return;
        }
        setSaving(true);
        try {
            const project = await projectService.createProject({
                title: title.trim(),
                description: description.trim(),
                tempo,
            });
            navigate(`/projects/${project.id}`, { replace: true });
        } catch (err: any) {
            setError(err?.detail ?? 'Erro a criar projeto.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="project-creation">
            <header>
                <Link to="/projects">← Projetos</Link>
                <h1>Novo projeto</h1>
            </header>

            <form onSubmit={handleSubmit}>
                <label>
                    Titulo
                    <input value={title} onChange={e => setTitle(e.target.value)} />
                </label>
                <label>
                    Descricao
                    <textarea
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                    />
                </label>
                <label>
                    Tempo (BPM)
                    <input
                        type="number"
                        min={1}
                        value={tempo}
                        onChange={e => setTempo(Number(e.target.value))}
                    />
                </label>
                <button type="submit" disabled={saving}>
                    {saving ? 'A criar…' : 'Criar projeto'}
                </button>
                {error ? <p className="error-text">{error}</p> : null}
            </form>
        </div>
    );
}

export default ProjectCreationPage;
