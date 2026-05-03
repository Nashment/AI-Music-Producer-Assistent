import {
    GenerationResponse,
    GenerationResult,
} from '../../services/generation/generationResponseTypes';

/**
 * Reducer do dominio "generation".
 *
 * O backend de geracao e assincrono: submete-se -> recebe-se generation_id ->
 * faz-se polling de /generation/{id}/status ate completed/failed.
 * O reducer mantem uma lista de "tarefas em curso" + o resultado final.
 */

export interface GenerationState {
    submissions: GenerationResponse[];   // pedidos submetidos (lista)
    statusById: Record<string, GenerationResult>; // estado actual por id
    loading: boolean;
    submitting: boolean;
    error: string | null;
}

export const initialGenerationState: GenerationState = {
    submissions: [],
    statusById: {},
    loading: false,
    submitting: false,
    error: null,
};

export type GenerationAction =
    | { type: 'SET_LOADING'; payload: boolean }
    | { type: 'SET_SUBMITTING'; payload: boolean }
    | { type: 'SET_ERROR'; payload: string }
    | { type: 'GENERATION_SUBMITTED'; payload: GenerationResponse }
    | { type: 'STATUS_UPDATED'; payload: GenerationResult }
    | { type: 'GENERATION_DELETED'; payload: string };

export function generationReducer(
    state: GenerationState,
    action: GenerationAction,
): GenerationState {
    switch (action.type) {
        case 'SET_LOADING':
            return { ...state, loading: action.payload };

        case 'SET_SUBMITTING':
            return { ...state, submitting: action.payload };

        case 'SET_ERROR':
            return { ...state, error: action.payload, loading: false, submitting: false };

        case 'GENERATION_SUBMITTED':
            return {
                ...state,
                submissions: [...state.submissions, action.payload],
                submitting: false,
                error: null,
            };

        case 'STATUS_UPDATED':
            return {
                ...state,
                statusById: {
                    ...state.statusById,
                    [action.payload.generation_id]: action.payload,
                },
                loading: false,
                error: null,
            };

        case 'GENERATION_DELETED': {
            const { [action.payload]: _, ...rest } = state.statusById;
            return {
                ...state,
                submissions: state.submissions.filter(
                    s => s.generation_id !== action.payload,
                ),
                statusById: rest,
            };
        }

        default:
            return state;
    }
}
