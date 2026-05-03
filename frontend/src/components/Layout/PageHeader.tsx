import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface Props {
    title: string;
    description?: string;
    backTo?: string;
    backLabel?: string;
    actions?: ReactNode;
}

/**
 * Cabeçalho local da pagina: titulo + descricao + accoes a direita.
 * Usado dentro do AppLayout para abrir cada pagina.
 */
export function PageHeader({ title, description, backTo, backLabel, actions }: Props) {
    return (
        <div className="page-header">
            <div className="page-header-text">
                {backTo ? (
                    <Link to={backTo} className="page-header-back">
                        ← {backLabel ?? 'Voltar'}
                    </Link>
                ) : null}
                <h1>{title}</h1>
                {description ? (
                    <p className="text-muted text-sm">{description}</p>
                ) : null}
            </div>
            {actions ? <div className="page-header-actions">{actions}</div> : null}
        </div>
    );
}

export default PageHeader;
