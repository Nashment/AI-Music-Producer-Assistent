interface Props {
    error: string;
}

export function ProjectError({ error }: Props) {
    return <div className="project-error">{error}</div>;
}

export default ProjectError;
