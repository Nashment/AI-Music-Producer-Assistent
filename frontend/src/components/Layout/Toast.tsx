import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from 'react';

type ToastKind = 'success' | 'error' | 'info';

export interface ToastItem {
    id: number;
    kind: ToastKind;
    message: string;
}

interface ToastApi {
    show: (message: string, kind?: ToastKind) => void;
    success: (message: string) => void;
    error: (message: string) => void;
    info: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const ICONS: Record<ToastKind, string> = {
    success: '✅',
    error: '⚠️',
    info: 'ℹ️',
};

/**
 * Toaster minimalista, baseado em context.
 * Cada toast desaparece automaticamente apos 4s.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
    const [items, setItems] = useState<ToastItem[]>([]);

    const remove = useCallback((id: number) => {
        setItems(curr => curr.filter(t => t.id !== id));
    }, []);

    const show = useCallback(
        (message: string, kind: ToastKind = 'info') => {
            const id = Date.now() + Math.random();
            setItems(curr => [...curr, { id, kind, message }]);
            setTimeout(() => remove(id), 4000);
        },
        [remove],
    );

    const api = useMemo<ToastApi>(
        () => ({
            show,
            success: m => show(m, 'success'),
            error: m => show(m, 'error'),
            info: m => show(m, 'info'),
        }),
        [show],
    );

    return (
        <ToastContext.Provider value={api}>
            {children}
            <div className="toaster" aria-live="polite">
                {items.map(t => (
                    <div key={t.id} className={`toast toast-${t.kind}`}>
                        <span className="toast-icon">{ICONS[t.kind]}</span>
                        <span className="toast-message">{t.message}</span>
                        <button
                            type="button"
                            className="toast-close"
                            onClick={() => remove(t.id)}
                            aria-label="Fechar"
                        >
                            ✕
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

/**
 * Hook para mostrar toasts.
 * Lanca erro se for usado fora do ToastProvider.
 */
export function useToast(): ToastApi {
    const ctx = useContext(ToastContext);
    if (!ctx) throw new Error('useToast precisa de <ToastProvider>');
    return ctx;
}

/**
 * Util: ler `detail` de um ApiError de forma segura.
 */
export function describeError(err: unknown, fallback = 'Erro inesperado.'): string {
    if (!err) return fallback;
    if (typeof err === 'string') return err;
    const anyErr = err as { detail?: string; message?: string };
    return anyErr.detail || anyErr.message || fallback;
}
