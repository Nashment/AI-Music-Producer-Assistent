import { useCallback, useEffect, useRef, useState } from 'react';
import { generationService } from '../../services/generation/generationService';
import {
    GenerationResult,
    GenerationRequest,
    CutGenerationRequest,
} from '../../services/generation/generationResponseTypes';

const POLL_INTERVAL_MS = 4000;
const TERMINAL = new Set(['completed', 'failed']);

export interface AudioGenerationNode extends GenerationResult {
    cuts: GenerationResult[];
}

/**
 * Hook que orquestra o conteúdo do "Painel direito" da nova vista de
 * audio:
 *
 *   1. Carrega a árvore (gerações raiz + cortes de cada uma) para um audio.
 *   2. Faz polling enquanto houver gerações em estado pending/processing,
 *      para apanhar a transição para completed/failed.
 *   3. Expõe acções: submeter geração, cortar uma geração, refresh manual.
 *
 * Não escolhe a "selecção" actual (qual geração/corte está aberto à
 * direita). Isso é local da página.
 */
export function useAudioGenerations(audioId: string | undefined) {
    const [tree, setTree] = useState<AudioGenerationNode[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [cutting, setCutting] = useState(false);

    const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
    const stopped = useRef(false);

    const buildTree = useCallback(async (audId: string): Promise<AudioGenerationNode[]> => {
        const roots = await generationService.listByAudio(audId);
        // Buscamos cortes em paralelo
        const withCuts = await Promise.all(
            roots.map(async r => {
                const cuts = await generationService.listCuts(r.generation_id);
                return { ...r, cuts } as AudioGenerationNode;
            }),
        );
        return withCuts;
    }, []);

    const refresh = useCallback(async () => {
        if (!audioId) return;
        setError(null);
        try {
            const t = await buildTree(audioId);
            setTree(t);
        } catch (e: any) {
            setError(e?.detail ?? 'Erro a carregar gerações.');
        }
    }, [audioId, buildTree]);

    const initialLoad = useCallback(async () => {
        if (!audioId) return;
        setLoading(true);
        try {
            const t = await buildTree(audioId);
            setTree(t);
        } catch (e: any) {
            setError(e?.detail ?? 'Erro a carregar gerações.');
        } finally {
            setLoading(false);
        }
    }, [audioId, buildTree]);

    // Polling enquanto houver gerações pending/processing
    const tick = useCallback(async () => {
        if (stopped.current || !audioId) return;
        const hasPending = tree.some(n => !TERMINAL.has(n.status));
        if (!hasPending) return;
        try {
            const next = await buildTree(audioId);
            setTree(next);
        } catch {
            // ignoramos erros transientes do polling
        }
        if (!stopped.current) {
            pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);
        }
    }, [audioId, tree, buildTree]);

    useEffect(() => {
        stopped.current = false;
        initialLoad();
        return () => {
            stopped.current = true;
            if (pollTimer.current) clearTimeout(pollTimer.current);
        };
    }, [initialLoad]);

    useEffect(() => {
        if (pollTimer.current) clearTimeout(pollTimer.current);
        const hasPending = tree.some(n => !TERMINAL.has(n.status));
        if (hasPending && !stopped.current) {
            pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);
        }
        return () => {
            if (pollTimer.current) clearTimeout(pollTimer.current);
        };
    }, [tree, tick]);

    const submitGeneration = useCallback(
        async (req: GenerationRequest) => {
            setSubmitting(true);
            try {
                const resp = await generationService.submitGeneration(req);
                await refresh();
                return resp;
            } finally {
                setSubmitting(false);
            }
        },
        [refresh],
    );

    const cutGeneration = useCallback(
        async (parentGenerationId: string, params: CutGenerationRequest) => {
            setCutting(true);
            try {
                const cut = await generationService.cutGeneration(parentGenerationId, params);
                await refresh();
                return cut;
            } finally {
                setCutting(false);
            }
        },
        [refresh],
    );

    const deleteGeneration = useCallback(
        async (generationId: string) => {
            await generationService.deleteGeneration(generationId);
            await refresh();
        },
        [refresh],
    );

    return {
        tree,
        loading,
        submitting,
        cutting,
        error,
        refresh,
        submitGeneration,
        cutGeneration,
        deleteGeneration,
    };
}

export default useAudioGenerations;
