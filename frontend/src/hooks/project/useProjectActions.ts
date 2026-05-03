import { useCallback } from 'react';
import { projectService } from '../../services/project/projectService';
import {
    ProjectCreate,
    ProjectUpdate,
} from '../../services/project/projectResponseTypes';
import { ProjectAction } from './projectReducer';

/**
 * Conjunto de actions reutilizaveis sobre o dominio "project".
 * Cada action despacha SET_LOADING -> sucesso/erro para o reducer.
 */
export function useProjectActions(dispatch: React.Dispatch<ProjectAction>) {
    const loadProjects = useCallback(async () => {
        dispatch({ type: 'SET_LOADING', payload: true });
        try {
            const data = await projectService.listProjects();
            dispatch({ type: 'PROJECTS_LOADED', payload: data });
        } catch (e: any) {
            dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a listar projetos.' });
        }
    }, [dispatch]);

    const loadProject = useCallback(
        async (projectId: string) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                const data = await projectService.getProject(projectId);
                dispatch({ type: 'PROJECT_LOADED', payload: data });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a obter projeto.' });
            }
        },
        [dispatch],
    );

    const createProject = useCallback(
        async (input: ProjectCreate) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                const data = await projectService.createProject(input);
                dispatch({ type: 'PROJECT_CREATED', payload: data });
                return data;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a criar projeto.' });
                throw e;
            }
        },
        [dispatch],
    );

    const updateProject = useCallback(
        async (projectId: string, input: ProjectUpdate) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                const data = await projectService.updateProject(projectId, input);
                dispatch({ type: 'PROJECT_UPDATED', payload: data });
                return data;
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a actualizar projeto.' });
                throw e;
            }
        },
        [dispatch],
    );

    const deleteProject = useCallback(
        async (projectId: string) => {
            dispatch({ type: 'SET_LOADING', payload: true });
            try {
                await projectService.deleteProject(projectId);
                dispatch({ type: 'PROJECT_DELETED', payload: projectId });
            } catch (e: any) {
                dispatch({ type: 'SET_ERROR', payload: e?.detail ?? 'Erro a apagar projeto.' });
                throw e;
            }
        },
        [dispatch],
    );

    return {
        loadProjects,
        loadProject,
        createProject,
        updateProject,
        deleteProject,
    };
}
