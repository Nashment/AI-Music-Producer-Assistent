import { ReactNode, useEffect } from 'react';

interface Props {
    open: boolean;
    title?: string;
    onClose: () => void;
    children: ReactNode;
    size?: 'md' | 'lg';
    /** Conteudo da barra de accoes (botoes). Renderizado no fundo. */
    actions?: ReactNode;
}

/**
 * Modal acessivel minimo:
 *   - fecha com Esc,
 *   - fecha em click no backdrop,
 *   - bloqueia scroll do body enquanto aberto.
 */
export function Modal({ open, title, onClose, children, size = 'md', actions }: Props) {
    useEffect(() => {
        if (!open) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        document.addEventListener('keydown', onKey);
        const prevOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', onKey);
            document.body.style.overflow = prevOverflow;
        };
    }, [open, onClose]);

    if (!open) return null;

    return (
        <div
            className="modal-backdrop"
            onMouseDown={e => {
                if (e.target === e.currentTarget) onClose();
            }}
            role="dialog"
            aria-modal="true"
        >
            <div className={`modal ${size === 'lg' ? 'modal-lg' : ''}`.trim()}>
                {title ? (
                    <div className="modal-header">
                        <h2>{title}</h2>
                        <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={onClose}
                            aria-label="Fechar"
                        >
                            ✕
                        </button>
                    </div>
                ) : null}

                <div>{children}</div>

                {actions ? <div className="modal-actions">{actions}</div> : null}
            </div>
        </div>
    );
}

export default Modal;
