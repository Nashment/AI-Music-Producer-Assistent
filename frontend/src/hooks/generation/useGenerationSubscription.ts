import { useEffect, useRef } from 'react';
import { GenerationAction } from './generationReducer';
import { generationService } from '../../services/generation/generationService';

const TERMINAL_STATUSES = new Set(['completed', 'failed']);

/**
 * "Subscription" para uma geracao especifica.
 *
 * Como o backend nao expoe SSE para o dominio de geracao, fazemos polling
 * ao endpoint /generation/{id}/status ate o estado ser terminal.
 * A interface deste hook segue o padrao do useGameSubscription do exemplo
 * Kotlin (efeito side-only que despacha actions).
 */
export function useGenerationSubscription(
    generationId: string | undefined,
    dispatch: React.Dispatch<GenerationAction>,
    options: { intervalMs?: number } = {},
) {
    const intervalMs = options.intervalMs ?? 3000;
    const stoppedRef = useRef(false);

    useEffect(() => {
        if (!generationId) return;
        stoppedRef.current = false;

        let timer: ReturnType<typeof setTimeout> | null = null;

        const tick = async () => {
            if (stoppedRef.current) return;
            try {
                const result = await generationService.getStatus(generationId);
                dispatch({ type: 'STATUS_UPDATED', payload: result });
                if (TERMINAL_STATUSES.has(result.status)) return; // para o ciclo
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro polling status.' });
            }
            timer = setTimeout(tick, intervalMs);
        };

        tick();

        return () => {
            stoppedRef.current = true;
            if (timer) clearTimeout(timer);
        };
    }, [generationId, dispatch, intervalMs]);
}
