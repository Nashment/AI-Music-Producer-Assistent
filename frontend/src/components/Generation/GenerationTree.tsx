import { GenerationResult } from '../../services/generation/generationResponseTypes';
import { AudioGenerationNode } from '../../hooks/generation/useAudioGenerations';
import useLanguage from '../../hooks/language/useLanguage';
import { generationLabel } from '../../utils/common';
import InlineRename from '../Layout/InlineRename';

interface Props {
    tree: AudioGenerationNode[];
    selectedId: string | null;
    onSelect: (gen: GenerationResult) => void;
    /** Chamado com o id quando o utilizador confirma a eliminação de uma entrada. */
    onDelete: (id: string) => void;
    /** Renomeia a geração/corte. Quando omitido, o lápis não aparece. */
    onRename?: (id: string, name: string) => Promise<unknown>;
}

/**
 * Lista hierárquica das gerações (nível 1) e respectivos cortes (nível 2).
 *
 * Cada linha permite seleccionar, renomear (lápis) e eliminar. O lápis e o
 * input de rename param a propagação para não dispararem a selecção.
 */
export function GenerationTree({ tree, selectedId, onSelect, onDelete, onRename }: Props) {
    const { t } = useLanguage();

    const statusBadge = (status: string): { cls: string; label: string } => {
        switch (status) {
            case 'completed':
                return { cls: 'badge badge-success', label: t.generationTree.statusCompleted };
            case 'failed':
                return { cls: 'badge badge-danger', label: t.generationTree.statusFailed };
            case 'processing':
                return { cls: 'badge badge-warning', label: t.generationTree.statusProcessing };
            default:
                return { cls: 'badge badge-primary', label: status };
        }
    };

    if (tree.length === 0) {
        return (
            <p className="text-muted text-sm gen-tree-empty">
                {t.generationTree.empty}
            </p>
        );
    }

    /** Renderiza uma linha (geração raiz ou corte). */
    const renderRow = (
        gen: GenerationResult,
        opts: { marker: string; isCut: boolean },
    ) => {
        const badge = statusBadge(gen.status);
        const isSel = selectedId === gen.id;
        const selectable = opts.isCut || gen.status === 'completed';
        const label = generationLabel(gen, t.generationTree.noDesc);

        return (
            <div className="gen-tree-row">
                <div
                    className={`gen-tree-item ${opts.isCut ? 'gen-tree-item-cut' : ''} ${
                        isSel ? 'is-selected' : ''
                    } ${selectable ? '' : 'is-disabled'}`}
                    role="button"
                    tabIndex={selectable ? 0 : -1}
                    title={selectable ? undefined : t.generationTree.awaitingCompletion}
                    onClick={() => selectable && onSelect(gen)}
                    onKeyDown={e => {
                        if (selectable && (e.key === 'Enter' || e.key === ' ')) {
                            e.preventDefault();
                            onSelect(gen);
                        }
                    }}
                >
                    <span className="gen-tree-marker">{opts.marker}</span>
                    <span className="gen-tree-text">
                        {onRename ? (
                            <InlineRename
                                as="span"
                                value={label}
                                onRename={n => onRename(gen.id, n)}
                            />
                        ) : (
                            <strong>{label}</strong>
                        )}
                        {!opts.isCut ? (
                            <span className="text-muted text-xs">
                                {gen.instrument ?? t.generationTree.noInstrument}
                            </span>
                        ) : null}
                    </span>
                    <span className={badge.cls}>{badge.label}</span>
                </div>

                <button
                    type="button"
                    className="gen-tree-delete"
                    title={t.generationTree.deleteLabel}
                    aria-label={t.generationTree.deleteLabel}
                    onClick={e => {
                        e.stopPropagation();
                        onDelete(gen.id);
                    }}
                >
                    🗑
                </button>
            </div>
        );
    };

    return (
        <ul className="gen-tree">
            {tree.map(gen => (
                <li key={gen.id} className="gen-tree-root">
                    {renderRow(gen, { marker: '▸', isCut: false })}

                    {gen.cuts.length > 0 ? (
                        <ul className="gen-tree-children">
                            {gen.cuts.map(cut => (
                                <li key={cut.id}>
                                    {renderRow(cut, { marker: '✂', isCut: true })}
                                </li>
                            ))}
                        </ul>
                    ) : null}
                </li>
            ))}
        </ul>
    );
}

export default GenerationTree;
