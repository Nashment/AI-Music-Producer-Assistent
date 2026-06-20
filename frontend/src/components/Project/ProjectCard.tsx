import { Link } from 'react-router-dom';
import { ProjectResponse } from '../../services/project/projectResponseTypes';
import InlineRename from '../Layout/InlineRename';

interface Props {
    project: ProjectResponse;
    onDelete?: (id: string) => void;
    /** Renomeia o projeto (título). Quando omitido, o lápis não aparece. */
    onRename?: (id: string, name: string) => Promise<unknown>;
}

/**
 * Cartao de projeto na lista. Liga para /projects/:id.
 */
export function ProjectCard({ project, onDelete, onRename }: Props) {
    return (
        <article className="project-card">
            <header className="project-card-head">
                {onRename ? (
                    <InlineRename
                        as="h3"
                        value={project.title}
                        onRename={name => onRename(project.id, name)}
                    />
                ) : (
                    <h3>{project.title}</h3>
                )}
            </header>
            <Link to={`/projects/${project.id}`} className="project-card-link">
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
