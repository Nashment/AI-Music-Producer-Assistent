/**
 * Testes unitários para projectService — verifica URL, método HTTP e
 * corpo enviados a request(), usando fetch mockado (request() é real).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { projectService } from '../../../src/services/project/projectService';

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
    });
}

beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('projectService', () => {
    it('createProject: POST /projects com o body serializado', async () => {
        const created = { id: 'p1', title: 'Novo', description: '', tempo: 120, user_id: 'u1' };
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(created));

        const result = await projectService.createProject({ title: 'Novo', description: '', tempo: 120 });

        expect(fetch).toHaveBeenCalledWith(
            '/api/projects',
            expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: 'Novo', description: '', tempo: 120 }) }),
        );
        expect(result).toEqual(created);
    });

    it('listProjects: GET /projects devolve a lista', async () => {
        const projects = [{ id: 'p1', title: 'A', description: '', tempo: 100, user_id: 'u1' }];
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(projects));

        const result = await projectService.listProjects();

        expect(fetch).toHaveBeenCalledWith('/api/projects', expect.objectContaining({ method: 'GET' }));
        expect(result).toEqual(projects);
    });

    it('getProject: GET /projects/{id}', async () => {
        const project = { id: 'p1', title: 'A', description: '', tempo: 100, user_id: 'u1' };
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(project));

        const result = await projectService.getProject('p1');

        expect(fetch).toHaveBeenCalledWith('/api/projects/p1', expect.objectContaining({ method: 'GET' }));
        expect(result).toEqual(project);
    });

    it('updateProject: PUT /projects/{id} com o body serializado', async () => {
        const updated = { id: 'p1', title: 'Novo título', description: '', tempo: 100, user_id: 'u1' };
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(updated));

        const result = await projectService.updateProject('p1', { title: 'Novo título' });

        expect(fetch).toHaveBeenCalledWith(
            '/api/projects/p1',
            expect.objectContaining({ method: 'PUT', body: JSON.stringify({ title: 'Novo título' }) }),
        );
        expect(result).toEqual(updated);
    });

    it('deleteProject: DELETE /projects/{id}', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
        await projectService.deleteProject('p1');
        expect(fetch).toHaveBeenCalledWith('/api/projects/p1', expect.objectContaining({ method: 'DELETE' }));
    });

    it('propaga o ApiError normalizado quando o backend devolve erro', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            jsonResponse({ type: 'FORBIDDEN', title: 'Proibido', detail: 'Sem permissão.' }, 403),
        );

        await expect(projectService.getProject('p1')).rejects.toEqual({
            code: 'FORBIDDEN',
            title: 'Proibido',
            detail: 'Sem permissão.',
            status: 403,
        });
    });
});
