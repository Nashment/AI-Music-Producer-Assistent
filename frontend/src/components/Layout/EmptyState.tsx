import { ReactNode } from 'react';

interface Props {
    icon?: string;
    title: string;
    description?: string;
    action?: ReactNode;
}

/**
 * Empty state partilhado. Usado em listas vazias (projetos, audios, etc).
 */
export function EmptyState({ icon, title, description, action }: Props) {
    return (
        <div className="empty-state">
            {icon ? <span className="empty-state-icon">{icon}</span> : null}
            <span className="empty-state-title">{title}</span>
            {description ? <p className="text-muted text-sm">{description}</p> : null}
            {action}
        </div>
    );
}

export default EmptyState;
