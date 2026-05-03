import { useEffect, useReducer } from 'react';
import { initialProjectState, projectReducer } from './projectReducer';
import { useProjectActions } from './useProjectActions';

/**
 * Hook focado num projeto especifico (pagina /projects/:projectId).
 */
export function useProject(projectId: string | undefined) {
    const [state, dispatch] = useReducer(projectReducer, initialProjectState);
    const actions = useProjectActions(dispatch);

    useEffect(() => {
        if (projectId) actions.loadProject(projectId);
    }, [projectId, actions.loadProject]);

    return {
        project: state.current,
        loading: state.loading,
        error: state.error,

        updateProject: actions.updateProject,
        deleteProject: actions.deleteProject,
        refresh: () => projectId && actions.loadProject(projectId),
    };
}

export default useProject;
