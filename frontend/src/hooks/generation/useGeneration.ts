import { useReducer } from 'react';
import {
    generationReducer,
    initialGenerationState,
} from './generationReducer';
import { useGenerationActions } from './useGenerationActions';
import { useGenerationSubscription } from './useGenerationSubscription';

/**
 * Hook unificado para uma geracao em curso. Junta actions + polling.
 * Equivalente ao useGame do exemplo Kotlin.
 */
export function useGeneration(generationId?: string) {
    const [state, dispatch] = useReducer(
        generationReducer,
        initialGenerationState,
    );
    const actions = useGenerationActions(dispatch);

    useGenerationSubscription(generationId, dispatch);

    return {
        submissions: state.submissions,
        statusById: state.statusById,
        currentStatus: generationId ? state.statusById[generationId] ?? null : null,
        submitting: state.submitting,
        loading: state.loading,
        error: state.error,

        submitGeneration: actions.submitGeneration,
        submitCover: actions.submitCover,
        refreshStatus: actions.refreshStatus,
        deleteGeneration: actions.deleteGeneration,
    };
}

export default useGeneration;
