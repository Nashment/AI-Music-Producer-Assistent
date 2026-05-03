import { request } from '../request';
import {
    ProjectResponse,
    ProjectCreate,
    ProjectUpdate,
} from './projectResponseTypes';

/**
 * Servico do dominio "project".
 *
 * Backend (resumo de backend/app/api/endpoints/projects.py):
 *   POST   /projects             -> cria projeto
 *   GET    /projects             -> lista projetos do utilizador
 *   GET    /projects/{id}        -> obtem projeto
 *   PUT    /projects/{id}        -> actualiza projeto
 *   DELETE /projects/{id}        -> apaga projeto
 */
export const projectService = {
    async createProject(data: ProjectCreate): Promise<ProjectResponse> {
        const res = await request('/projects', {
            method: 'POST',
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async listProjects(): Promise<ProjectResponse[]> {
        const res = await request('/projects', { method: 'GET' });
        return res.json();
    },

    async getProject(projectId: string): Promise<ProjectResponse> {
        const res = await request(`/projects/${projectId}`, { method: 'GET' });
        return res.json();
    },

    async updateProject(
        projectId: string,
        data: ProjectUpdate,
    ): Promise<ProjectResponse> {
        const res = await request(`/projects/${projectId}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
        return res.json();
    },

    async deleteProject(projectId: string): Promise<void> {
        await request(`/projects/${projectId}`, { method: 'DELETE' });
    },
};
