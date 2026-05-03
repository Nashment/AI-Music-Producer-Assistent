import { useEffect, useReducer } from 'react';
import { initialProjectState, projectReducer } from './projectReducer';
import { useProjectActions } from './useProjectActions';

/**
 * Hook de alto nivel para a pagina /projects: carrega e expoe a lista
 * de projetos, accoes de criacao e remocao.
 */
export function useProjects() {
    const [state, dispatch] = useReducer(projectReducer, initialProjectState);
    const actions = useProjectActions(dispatch);

    useEffect(() => {
        actions.loadProjects();
        // actions.loadProjects identidade e estavel via useCallback no actions
    }, [actions.loadProjects]);

    return {
        projects: state.projects,
        loading: state.loading,
        error: state.error,

        createProject: actions.createProject,
        deleteProject: actions.deleteProject,
        refresh: actions.loadProjects,
    };
}

export default useProjects;
