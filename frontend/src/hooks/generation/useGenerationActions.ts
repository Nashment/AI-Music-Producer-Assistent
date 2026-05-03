import { useCallback } from 'react';
import { generationService } from '../../services/generation/generationService';
import {
    CoverGenerationRequest,
    GenerationRequest,
} from '../../services/generation/generationResponseTypes';
import { GenerationAction } from './generationReducer';

export function useGenerationActions(
    dispatch: React.Dispatch<GenerationAction>,
) {
    const submitGeneration = useCallback(
        async (req: GenerationRequest) => {
            dispatch({ type: 'SET_SUBMITTING', payload: true });
            try {
                const resp = await generationService.submitGeneration(req);
                dispatch({ type: 'GENERATION_SUBMITTED', payload: resp });
                return resp;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a submeter geracao.' });
                throw e;
            }
        },
        [dispatch],
    );

    const submitCover = useCallback(
        async (req: CoverGenerationRequest) => {
            dispatch({ type: 'SET_SUBMITTING', payload: true });
            try {
                const resp = await generationService.submitCover(req);
                dispatch({ type: 'GENERATION_SUBMITTED', payload: resp });
                return resp;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a submeter cover.' });
                throw e;
            }
        },
        [dispatch],
    );

    const refreshStatus = useCallback(
        async (generationId: string) => {
            try {
                const result = await generationService.getStatus(generationId);
                dispatch({ type: 'STATUS_UPDATED', payload: result });
                return result;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a obter estado.' });
                throw e;
            }
        },
        [dispatch],
    );

    const deleteGeneration = useCallback(
        async (generationId: string) => {
            try {
                await generationService.deleteGeneration(generationId);
                dispatch({ type: 'GENERATION_DELETED', payload: generationId });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a apagar geracao.' });
                throw e;
            }
        },
        [dispatch],
    );

    return {
        submitGeneration,
        submitCover,
        refreshStatus,
        deleteGeneration,
    };
}
