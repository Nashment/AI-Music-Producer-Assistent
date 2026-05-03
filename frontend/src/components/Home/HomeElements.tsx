import { Link } from 'react-router-dom';

interface HomeButtonProps {
    to: string;
    label: string;
    icon?: string;
    className?: string;
}

/**
 * Botao tipico de menu da home — um <Link> estilizado.
 * Mesmo padrao do exemplo Kotlin (HomeElements.tsx).
 */
export function HomeButton({ to, label, icon, className }: HomeButtonProps) {
    return (
        <Link to={to} className={`home-button ${className ?? ''}`.trim()}>
            {icon ? <span className="home-button-icon">{icon}</span> : null}
            <span className="home-button-label">{label}</span>
        </Link>
    );
}

export default HomeButton;
