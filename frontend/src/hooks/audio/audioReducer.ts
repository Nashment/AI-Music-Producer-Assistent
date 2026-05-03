import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';

export interface AudioState {
    audios: AudioAnalysisResponse[];
    current: AudioAnalysisResponse | null;
    loading: boolean;
    uploading: boolean;
    error: string | null;
}

export const initialAudioState: AudioState = {
    audios: [],
    current: null,
    loading: false,
    uploading: false,
    error: null,
};

export type AudioAction =
    | { type: 'SET_LOADING'; payload: boolean }
    | { type: 'SET_UPLOADING'; payload: boolean }
    | { type: 'SET_ERROR'; payload: string }
    | { type: 'AUDIOS_LOADED'; payload: AudioAnalysisResponse[] }
    | { type: 'AUDIO_LOADED'; payload: AudioAnalysisResponse }
    | { type: 'AUDIO_UPLOADED'; payload: AudioAnalysisResponse }
    | { type: 'AUDIO_UPDATED'; payload: AudioAnalysisResponse }
    | { type: 'AUDIO_DELETED'; payload: string }
    | { type: 'CLEAR_CURRENT' };

export function audioReducer(state: AudioState, action: AudioAction): AudioState {
    switch (action.type) {
        case 'SET_LOADING':
            return { ...state, loading: action.payload };

        case 'SET_UPLOADING':
            return { ...state, uploading: action.payload };

        case 'SET_ERROR':
            return { ...state, error: action.payload, loading: false, uploading: false };

        case 'AUDIOS_LOADED':
            return { ...state, audios: action.payload, loading: false, error: null };

        case 'AUDIO_LOADED':
            return { ...state, current: action.payload, loading: false, error: null };

        case 'AUDIO_UPLOADED':
            return {
                ...state,
                audios: [...state.audios, action.payload],
                uploading: false,
                error: null,
            };

        case 'AUDIO_UPDATED':
            return {
                ...state,
                audios: state.audios.map(a =>
                    a.id === action.payload.id ? action.payload : a,
                ),
                current:
                    state.current && state.current.id === action.payload.id
                        ? action.payload
                        : state.current,
                error: null,
            };

        case 'AUDIO_DELETED':
            return {
                ...state,
                audios: state.audios.filter(a => a.id !== action.payload),
                current:
                    state.current && state.current.id === action.payload
                        ? null
                        : state.current,
                error: null,
            };

        case 'CLEAR_CURRENT':
            return { ...state, current: null };

        default:
            return state;
    }
}
