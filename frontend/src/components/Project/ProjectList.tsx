import { ProjectResponse } from '../../services/project/projectResponseTypes';
import ProjectCard from './ProjectCard';

interface Props {
    projects: ProjectResponse[];
    onDelete?: (id: string) => void;
    onRename?: (id: string, name: string) => Promise<unknown>;
}

export function ProjectList({ projects, onDelete, onRename }: Props) {
    return (
        <div className="project-list">
            {projects.map(p => (
                <ProjectCard
                    key={p.id}
                    project={p}
                    onDelete={onDelete}
                    onRename={onRename}
                />
            ))}
        </div>
    );
}

export default ProjectList;
