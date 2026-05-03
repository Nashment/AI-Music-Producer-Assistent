import { GenerationResult } from '../../services/generation/generationResponseTypes';
import { AudioGenerationNode } from '../../hooks/generation/useAudioGenerations';

interface Props {
    tree: AudioGenerationNode[];
    selectedId: string | null;
    onSelect: (gen: GenerationResult) => void;
}

function statusBadge(status: string): { cls: string; label: string } {
    switch (status) {
        case 'completed':
            return { cls: 'badge badge-success', label: 'pronto' };
        case 'failed':
            return { cls: 'badge badge-danger', label: 'falhou' };
        case 'processing':
            return { cls: 'badge badge-warning', label: 'processando' };
        default:
            return { cls: 'badge badge-primary', label: status };
    }
}

function shortPrompt(p?: string | null): string {
    if (!p) return 'sem descrição';
    return p.length > 48 ? p.slice(0, 45) + '…' : p;
}

/**
 * Lista hierárquica das gerações (nível 1) e respectivos cortes
 * (nível 2). Renderiza-se na sidebar esquerda do AudioDetail.
 *
 * O selector "selectedId" é o generation_id (string), comum a gerações e
 * cortes (porque cortes também são entradas em `generations`).
 */
export function GenerationTree({ tree, selectedId, onSelect }: Props) {
    if (tree.length === 0) {
        return (
            <p className="text-muted text-sm gen-tree-empty">
                Sem gerações ainda. Cria a primeira no painel à direita.
            </p>
        );
    }

    return (
        <ul className="gen-tree">
            {tree.map(gen => {
                const badge = statusBadge(gen.status);
                const isSel = selectedId === gen.generation_id;
                return (
                    <li key={gen.generation_id} className="gen-tree-root">
                        <button
                            type="button"
                            className={`gen-tree-item ${isSel ? 'is-selected' : ''}`}
                            onClick={() => onSelect(gen)}
                            disabled={gen.status !== 'completed'}
                            title={gen.status !== 'completed' ? 'Aguarda conclusão' : undefined}
                        >
                            <span className="gen-tree-marker">▸</span>
                            <span className="gen-tree-text">
                                <strong>{shortPrompt(gen.prompt)}</strong>
                                <span className="text-muted text-xs">
                                    {gen.instrument ?? 'instrumento n/d'}
                                </span>
                            </span>
                            <span className={badge.cls}>{badge.label}</span>
                        </button>

                        {gen.cuts.length > 0 ? (
                            <ul className="gen-tree-children">
                                {gen.cuts.map(cut => {
                                    const cutBadge = statusBadge(cut.status);
                                    const isCutSel = selectedId === cut.generation_id;
                                    return (
                                        <li key={cut.generation_id}>
                                            <button
                                                type="button"
                                                className={`gen-tree-item gen-tree-item-cut ${isCutSel ? 'is-selected' : ''}`}
                                                onClick={() => onSelect(cut)}
                                            >
                                                <span className="gen-tree-marker">✂</span>
                                                <span className="gen-tree-text">
                                                    <strong>{shortPrompt(cut.prompt)}</strong>
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
