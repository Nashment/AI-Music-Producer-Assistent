interface Props {
    /** Mensagem opcional ao lado do spinner. */
    label?: string;
    size?: 'sm' | 'lg';
    block?: boolean;
}

/**
 * Spinner partilhado. Em modo `block` ocupa a largura toda e centra
 * verticalmente — bom para estados de loading de pagina.
 */
export function Spinner({ label, size, block }: Props) {
    const cls = `spinner ${size === 'lg' ? 'spinner-lg' : ''}`.trim();

    if (block) {
        return (
            <div className="page-loading">
                <div className={cls} />
                {label ? <p className="text-muted text-sm mt-4">{label}</p> : null}
            </div>
        );
    }
    return (
        <span className="flex items-center gap-2">
            <span className={cls} />
            {label ? <span className="text-muted text-sm">{label}</span> : null}
        </span>
    );
}

export default Spinner;
