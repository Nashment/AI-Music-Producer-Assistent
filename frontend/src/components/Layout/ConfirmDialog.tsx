import { ReactNode } from 'react';
import Modal from './Modal';

interface Props {
    open: boolean;
    title: string;
    message: ReactNode;
    confirmLabel?: string;
    cancelLabel?: string;
    danger?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
    busy?: boolean;
}

/**
 * Dialogo de confirmacao por cima do Modal genrico.
 * Usado para "apagar conta", "apagar projeto", "apagar audio".
 */
export function ConfirmDialog({
    open,
    title,
    message,
    confirmLabel = 'Confirmar',
    cancelLabel = 'Cancelar',
    danger,
    onConfirm,
    onCancel,
    busy,
}: Props) {
    return (
        <Modal
            open={open}
            title={title}
            onClose={onCancel}
            actions={
                <>
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={onCancel}
                        disabled={busy}
                    >
                        {cancelLabel}
                    </button>
                    <button
                        type="button"
                        className={danger ? 'btn btn-danger' : 'btn'}
                        onClick={onConfirm}
                        disabled={busy}
                    >
                        {busy ? 'A processar…' : confirmLabel}
                    </button>
                </>
            }
        >
            <p className="text-soft">{message}</p>
        </Modal>
    );
}

export default ConfirmDialog;
