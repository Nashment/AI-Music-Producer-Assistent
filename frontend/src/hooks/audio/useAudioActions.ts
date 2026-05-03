import { useCallback } from 'react';
import { audioService } from '../../services/audio/audioService';
import {
    CutAudioParams,
    SeparateTracksParams,
} from '../../services/audio/audioResponseTypes';
import { AudioAction } from './audioReducer';

export function useAudioActions(dispatch: React.Dispatch<AudioAction>) {
    const loadAudios = useCallback(
        async (projectId: string) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                const data = await audioService.listAudios(projectId);
                dispatch({ type: 'AUDIOS_LOADED', payload: data.audios });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a listar audios.' });
            }
        },
        [dispatch],
    );

    const loadAudio = useCallback(
        async (audioId: string) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                const data = await audioService.getAudioAnalysis(audioId);
                dispatch({ type: 'AUDIO_LOADED', payload: data });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a obter audio.' });
            }
        },
        [dispatch],
    );

    const uploadAudio = useCallback(
        async (projectId: string, file: File) => {
            dispatch({ type: 'SET_UPLOADING', payload: true });
            try {
                const data = await audioService.uploadAudio(projectId, file);
                dispatch({ type: 'AUDIO_UPLOADED', payload: data });
                return data;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a fazer upload.' });
                throw e;
            }
        },
        [dispatch],
    );

    const deleteAudio = useCallback(
        async (audioId: string) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                await audioService.deleteAudio(audioId);
                dispatch({ type: 'AUDIO_DELETED', payload: audioId });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a apagar audio.' });
                throw e;
            }
        },
        [dispatch],
    );

    const adjustBpm = useCallback(
        async (audioId: string, targetBpm: number) => {
            try {
                const data = await audioService.adjustBpm(audioId, targetBpm);
                dispatch({ type: 'AUDIO_UPDATED', payload: data });
                return data;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a ajustar BPM.' });
                throw e;
            }
        },
        [dispatch],
    );

    const cutAudio = useCallback(
        async (audioId: string, params: CutAudioParams) => {
            try {
                const data = await audioService.cutAudio(audioId, params);
                dispatch({ type: 'AUDIO_UPLOADED', payload: data });
                return data;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a cortar audio.' });
                throw e;
            }
        },
        [dispatch],
    );

    const separateTracks = useCallback(
        async (audioId: string, params: SeparateTracksParams) => {
            try {
                return await audioService.separateTracks(audioId, params);
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a separar instrumentos.' });
                throw e;
            }
        },
        [dispatch],
    );

    return {
        loadAudios,
        loadAudio,
        uploadAudio,
        deleteAudio,
        adjustBpm,
        cutAudio,
        separateTracks,
    };
}
