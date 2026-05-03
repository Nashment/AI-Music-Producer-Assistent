import { ProjectResponse } from '../../services/project/projectResponseTypes';

/**
 * Reducer do dominio "project". Espelha o padrao usado no exemplo Kotlin
 * (lobbyReducer / gameReducer): estado + lista de actions.
 */

export interface ProjectState {
    projects: ProjectResponse[];
    current: ProjectResponse | null;
    loading: boolean;
    error: string | null;
}

export const initialProjectState: ProjectState = {
    projects: [],
    current: null,
    loading: false,
    error: null,
};

export type ProjectAction =
    | { type: 'SET_LOADING'; payload: boolean }
    | { type: 'SET_ERROR'; payload: string }
    | { type: 'PROJECTS_LOADED'; payload: ProjectResponse[] }
    | { type: 'PROJECT_LOADED'; payload: ProjectResponse }
    | { type: 'PROJECT_CREATED'; payload: ProjectResponse }
    | { type: 'PROJECT_UPDATED'; payload: ProjectResponse }
    | { type: 'PROJECT_DELETED'; payload: string }
    | { type: 'CLEAR_CURRENT' };

export function projectReducer(
    state: ProjectState,
    action: ProjectAction,
): ProjectState {
    switch (action.type) {
        case 'SET_LOADING':
            return { ...state, loading: action.payload };

        case 'SET_ERROR':
            return { ...state, error: action.payload, loading: false };

        case 'PROJECTS_LOADED':
            return { ...state, projects: action.payload, loading: false, error: null };

        case 'PROJECT_LOADED':
            return { ...state, current: action.payload, loading: false, error: null };

        case 'PROJECT_CREATED':
            return {
                ...state,
                projects: [...state.projects, action.payload],
                current: action.payload,
                loading: false,
                error: null,
            };

        case 'PROJECT_UPDATED':
            return {
                ...state,
                projects: state.projects.map(p =>
                    p.id === action.payload.id ? action.payload : p,
                ),
                current:
                    state.current && state.current.id === action.payload.id
                        ? action.payload
                        : state.current,
                loading: false,
                error: null,
            };

        case 'PROJECT_DELETED':
            return {
                ...state,
                projects: state.projects.filter(p => p.id !== action.payload),
                current:
                    state.current && state.current.id === action.payload
                        ? null
                        : state.current,
                loading: false,
                error: null,
            };

        case 'CLEAR_CURRENT':
            return { ...state, current: null };

        default:
            return state;
    }
}
