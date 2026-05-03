import { Link } from 'react-router-dom';
import { ProjectResponse } from '../../services/project/projectResponseTypes';

interface Props {
    project: ProjectResponse;
    onDelete?: (id: string) => void;
}

/**
 * Cartao de projeto na lista. Liga para /projects/:id.
 */
export function ProjectCard({ project, onDelete }: Props) {
    return (
        <article className="project-card">
            <Link to={`/projects/${project.id}`} className="project-card-link">
                <header className="project-card-head">
                    <h3>{project.title}</h3>
                    <span className="badge badge-primary">{project.tempo} BPM</span>
                </header>
                <p className="project-card-desc">
                    {project.description || (
                        <span className="text-muted">sem descrição</span>
                    )}
                </p>
            </Link>

            {onDelete ? (
                <button
                    type="button"
                    className="btn btn-danger-ghost btn-sm project-card-delete"
                    onClick={e => {
                        e.preventDefault();
                        onDelete(project.id);
                    }}
                >
                    Apagar
                </button>
            ) : null}
        </article>
    );
}

export default ProjectCard;
