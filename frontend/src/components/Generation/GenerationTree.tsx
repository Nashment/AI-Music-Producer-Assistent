import { GenerationResult } from '../../services/generation/generationResponseTypes';
import { AudioGenerationNode } from '../../hooks/generation/useAudioGenerations';
import useLanguage from '../../hooks/language/useLanguage';

interface Props {
    tree: AudioGenerationNode[];
    selectedId: string | null;
    onSelect: (gen: GenerationResult) => void;
}

function shortPrompt(p?: string | null, noDesc?: string): string {
    if (!p) return noDesc ?? 'sem descrição';
    return p.length > 48 ? p.slice(0, 45) + '…' : p;
}

/**
 * Lista hierárquica das gerações (nível 1) e respectivos cortes (nível 2).
 */
export function GenerationTree({ tree, selectedId, onSelect }: Props) {
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

                        {gen.cuts.length > 0 ? (
                            <ul className="gen-tree-children">
                                {gen.cuts.map(cut => {
                                    const cutBadge = statusBadge(cut.status);
                                    const isCutSel = selectedId === cut.id;
                                    return (
                                        <li key={cut.id}>
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
