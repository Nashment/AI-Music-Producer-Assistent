import { useEffect, useRef, useState } from 'react';
import useLanguage from '../../hooks/language/useLanguage';
import Spinner from './Spinner';

type TitleTag = 'h1' | 'h2' | 'h3' | 'h4' | 'span';

interface Props {
    /** Texto atual a mostrar/editar. */
    value: string;
    /** Chamado ao guardar. Deve lançar em caso de erro (mantém o modo edição). */
    onRename: (next: string) => Promise<unknown>;
    /** Elemento usado para mostrar o texto (default: span). */
    as?: TitleTag;
    className?: string;
    /** Quando true, clicar no texto também entra em edição (default false). */
    editOnTextClick?: boolean;
}

/**
 * Controlo de rename inline e reutilizável: mostra o texto + um ícone de lápis;
 * ao clicar, troca para um input com guardar/cancelar. Enter guarda, Esc cancela.
 *
 * Pára a propagação dos cliques para poder ser usado dentro de linhas
 * clicáveis (ex.: árvore de gerações) sem disparar a seleção.
 */
export function InlineRename({
    value,
    onRename,
    as = 'span',
    className,
    editOnTextClick = false,
}: Props) {
    const { t } = useLanguage();
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(value);
    const [saving, setSaving] = useState(false);
    const inputRef = useRef<HTMLInputElement | null>(null);

    useEffect(() => {
        if (editing) {
            setDraft(value);
            // foco no próximo tick para garantir que o input já existe
            requestAnimationFrame(() => inputRef.current?.select());
        }
    }, [editing, value]);

    const start = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setEditing(true);
    };

    const cancel = () => {
        setEditing(false);
        setDraft(value);
    };

    const save = async () => {
        const next = draft.trim();
        if (!next || next === value.trim()) {
            cancel();
            return;
        }
        setSaving(true);
        try {
            await onRename(next);
            setEditing(false);
        } catch {
            // o caller mostra o toast; mantemos o modo edição para retry
        } finally {
            setSaving(false);
        }
    };

    if (editing) {
        return (
            <span
                className={`inline-rename is-editing ${className ?? ''}`}
                onClick={e => e.stopPropagation()}
            >
                <input
                    ref={inputRef}
                    className="inline-rename-input"
                    value={draft}
                    placeholder={t.rename.placeholder}
                    disabled={saving}
                    autoFocus
                    onChange={e => setDraft(e.target.value)}
                    onKeyDown={e => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            void save();
                        } else if (e.key === 'Escape') {
                            e.preventDefault();
                            cancel();
                        }
                    }}
                    onClick={e => e.stopPropagation()}
                />
                {saving ? (
                    <Spinner size="sm" />
                ) : (
                    <>
                        <button
                            type="button"
                            className="inline-rename-btn inline-rename-save"
                            title={t.rename.save}
                            aria-label={t.rename.save}
                            onClick={e => {
                                e.stopPropagation();
                                void save();
                            }}
                        >
                            ✓
                        </button>
                        <button
                            type="button"
                            className="inline-rename-btn inline-rename-cancel"
                            title={t.rename.cancel}
                            aria-label={t.rename.cancel}
                            onClick={e => {
                                e.stopPropagation();
                                cancel();
                            }}
                        >
                            ✕
                        </button>
                    </>
                )}
            </span>
        );
    }

    const Tag = as;
    return (
        <span className={`inline-rename ${className ?? ''}`}>
            <Tag
                className="inline-rename-text"
                onClick={editOnTextClick ? start : undefined}
                style={editOnTextClick ? { cursor: 'text' } : undefined}
            >
                {value}
            </Tag>
            <button
                type="button"
                className="inline-rename-btn inline-rename-edit"
                title={t.rename.edit}
                aria-label={t.rename.edit}
                onClick={start}
            >
                ✎
            </button>
        </span>
    );
}

export default InlineRename;
