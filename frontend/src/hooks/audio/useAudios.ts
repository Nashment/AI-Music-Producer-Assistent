import { useEffect, useReducer } from 'react';
import { audioReducer, initialAudioState } from './audioReducer';
import { useAudioActions } from './useAudioActions';

/**
 * Hook para listar e gerir audios de um projeto.
 *
 * Backend nao expoe SSE para audio: usamos polling/refresh manual atraves
 * das actions devolvidas. A "subscription" aqui resume-se ao load inicial.
 */
export function useAudios(projectId: string | undefined) {
    const [state, dispatch] = useReducer(audioReducer, initialAudioState);
    const actions = useAudioActions(dispatch);

    useEffect(() => {
        if (projectId) actions.loadAudios(projectId);
    }, [projectId, actions.loadAudios]);

    return {
        audios: state.audios,
        loading: state.loading,
        uploading: state.uploading,
        error: state.error,

        uploadAudio: (file: File) =>
            projectId
                ? actions.uploadAudio(projectId, file)
                : Promise.reject(new Error('projectId em falta')),
        deleteAudio: actions.deleteAudio,
        adjustBpm: actions.adjustBpm,
        cutAudio: actions.cutAudio,
        separateTracks: actions.separateTracks,
        refresh: () => projectId && actions.loadAudios(projectId),
    };
}

export default useAudios;
