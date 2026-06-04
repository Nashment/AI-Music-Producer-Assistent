import { GenerationResult } from '../../services/generation/generationResponseTypes';
import { AudioGenerationNode } from '../../hooks/generation/useAudioGenerations';
import useLanguage from '../../hooks/language/useLanguage';

interface Props {
    tree: AudioGenerationNode[];
    selectedId: string | null;
    onSelect: (gen: GenerationResult) => void;
    /** Chamado com o id quando o utilizador confirma a eliminação de uma entrada. */
    onDelete: (id: string) => void;
}

function shortPrompt(p?: string | null, noDesc?: string): string {
    if (!p) return noDesc ?? 'sem descrição';
    return p.length > 48 ? p.slice(0, 45) + '…' : p;
}

/**
 * Lista hierárquica das gerações (nível 1) e respectivos cortes (nível 2).
 *
 * Cada linha expõe um botão de eliminar (oculto por defeito, visível no hover)
 * que chama onDelete(id) — a confirmação fica a cargo do componente pai,
 * que reutiliza o ConfirmDialog já existente no design system.
 */
export function GenerationTree({ tree, selectedId, onSelect, onDelete }: Props) {
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

    return (
        <ul className="gen-tree">
            {tree.map(gen => {
                const badge = statusBadge(gen.status);
                const isSel = selectedId === gen.id;
                return (
                    <li key={gen.id} className="gen-tree-root">
                        {/* Linha: botão de seleção + botão de eliminar */}
                        <div className="gen-tree-row">
                            <button
                                type="button"
                                className={`gen-tree-item ${isSel ? 'is-selected' : ''}`}
                                onClick={() => onSelect(gen)}
                                disabled={gen.status !== 'completed'}
                                title={gen.status !== 'completed' ? t.generationTree.awaitingCompletion : undefined}
                            >
                                <span className="gen-tree-marker">▸</span>
                                <span className="gen-tree-text">
                                    <strong>{shortPrompt(gen.prompt, t.generationTree.noDesc)}</strong>
                                    <span className="text-muted text-xs">
                                        {gen.instrument ?? t.generationTree.noInstrument}
                                    </span>
                                </span>
                                <span className={badge.cls}>{badge.label}</span>
                            </button>

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

                        {gen.cuts.length > 0 ? (
                            <ul className="gen-tree-children">
                                {gen.cuts.map(cut => {
                                    const cutBadge = statusBadge(cut.status);
                                    const isCutSel = selectedId === cut.id;
                                    return (
                                        <li key={cut.id}>
                                            {/* Linha: botão de seleção + botão de eliminar */}
                                            <div className="gen-tree-row">
                                                <button
                                                    type="button"
                                                    className={`gen-tree-item gen-tree-item-cut ${isCutSel ? 'is-selected' : ''}`}
                                                    onClick={() => onSelect(cut)}
                                                >
                                                    <span className="gen-tree-marker">✂</span>
                                                    <span className="gen-tree-text">
                                                        <strong>{shortPrompt(cut.prompt, t.generationTree.noDesc)}</strong>
                                                    </span>
                                                    <span className={cutBadge.cls}>{cutBadge.label}</span>
                                                </button>

                                                <button
                                                    type="button"
                                                    className="gen-tree-delete"
                                                    title={t.generationTree.deleteLabel}
                                                    aria-label={t.generationTree.deleteLabel}
                                                    onClick={e => {
                                                        e.stopPropagation();
                                                        onDelete(cut.id);
                                                    }}
                                                >
                                                    🗑
                                                </button>
                                            </div>
                                        </li>
                                    );
                                })}
                            </ul>
                        ) : null}
                    </li>
                );
            })}
        </ul>
    );
}

export default GenerationTree;
