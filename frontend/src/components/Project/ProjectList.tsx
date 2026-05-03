import { ProjectResponse } from '../../services/project/projectResponseTypes';
import ProjectCard from './ProjectCard';

interface Props {
    projects: ProjectResponse[];
    onDelete?: (id: string) => void;
}

export function ProjectList({ projects, onDelete }: Props) {
    return (
        <div className="project-list">
            {projects.map(p => (
                <ProjectCard key={p.id} project={p} onDelete={onDelete} />
            ))}
        </div>
    );
}

export default ProjectList;
