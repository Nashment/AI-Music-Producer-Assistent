/**
 * Testes unitários para projectReducer (reducer puro, sem I/O).
 */

import { describe, it, expect } from 'vitest';
import {
    projectReducer,
    initialProjectState,
    ProjectState,
} from '../../../src/hooks/project/projectReducer';
import type { ProjectResponse } from '../../../src/services/project/projectResponseTypes';

function makeProject(overrides: Partial<ProjectResponse> = {}): ProjectResponse {
    return {
        id: 'proj-1',
        title: 'Projeto Teste',
        description: 'Descrição',
        tempo: 120,
        user_id: 'user-1',
        ...overrides,
    };
}

describe('projectReducer', () => {
    it('estado inicial tem valores por defeito', () => {
        expect(initialProjectState).toEqual({
            projects: [],
            current: null,
            loading: false,
            error: null,
        });
    });

    it('SET_LOADING altera apenas loading', () => {
        const s = projectReducer(initialProjectState, { type: 'SET_LOADING', payload: true });
        expect(s.loading).toBe(true);
        expect(s.projects).toEqual([]);
    });

    it('SET_ERROR define error e desliga loading', () => {
        const start: ProjectState = { ...initialProjectState, loading: true };
        const s = projectReducer(start, { type: 'SET_ERROR', payload: 'falhou' });
        expect(s.error).toBe('falhou');
        expect(s.loading).toBe(false);
    });

    it('PROJECTS_LOADED substitui a lista e limpa loading/error', () => {
        const projects = [makeProject({ id: 'a' }), makeProject({ id: 'b' })];
        const start: ProjectState = { ...initialProjectState, loading: true, error: 'x' };
        const s = projectReducer(start, { type: 'PROJECTS_LOADED', payload: projects });
        expect(s.projects).toEqual(projects);
        expect(s.loading).toBe(false);
        expect(s.error).toBeNull();
    });

    it('PROJECT_LOADED define current', () => {
        const project = makeProject();
        const s = projectReducer(initialProjectState, { type: 'PROJECT_LOADED', payload: project });
        expect(s.current).toEqual(project);
    });

    it('PROJECT_CREATED adiciona à lista e define como current', () => {
        const existing = makeProject({ id: 'a' });
        const created = makeProject({ id: 'b' });
        const start: ProjectState = { ...initialProjectState, projects: [existing] };
        const s = projectReducer(start, { type: 'PROJECT_CREATED', payload: created });
        expect(s.projects).toEqual([existing, created]);
        expect(s.current).toEqual(created);
    });

    it('PROJECT_UPDATED substitui o projeto na lista e no current se coincidir', () => {
        const original = makeProject({ id: 'a', title: 'Antigo' });
        const updated = makeProject({ id: 'a', title: 'Novo' });
        const start: ProjectState = { ...initialProjectState, projects: [original], current: original };
        const s = projectReducer(start, { type: 'PROJECT_UPDATED', payload: updated });
        expect(s.projects).toEqual([updated]);
        expect(s.current).toEqual(updated);
    });

    it('PROJECT_UPDATED não mexe no current se for outro projeto', () => {
        const other = makeProject({ id: 'other' });
        const updated = makeProject({ id: 'a', title: 'Novo' });
        const start: ProjectState = {
            ...initialProjectState,
            projects: [makeProject({ id: 'a' })],
            current: other,
        };
        const s = projectReducer(start, { type: 'PROJECT_UPDATED', payload: updated });
        expect(s.current).toEqual(other);
    });

    it('PROJECT_DELETED remove da lista e limpa current se era o eliminado', () => {
        const toDelete = makeProject({ id: 'a' });
        const keep = makeProject({ id: 'b' });
        const start: ProjectState = {
            ...initialProjectState,
            projects: [toDelete, keep],
            current: toDelete,
        };
        const s = projectReducer(start, { type: 'PROJECT_DELETED', payload: 'a' });
        expect(s.projects).toEqual([keep]);
        expect(s.current).toBeNull();
    });

    it('PROJECT_DELETED mantém current se não era o eliminado', () => {
        const keep = makeProject({ id: 'b' });
        const start: ProjectState = {
            ...initialProjectState,
            projects: [makeProject({ id: 'a' }), keep],
            current: keep,
        };
        const s = projectReducer(start, { type: 'PROJECT_DELETED', payload: 'a' });
        expect(s.current).toEqual(keep);
    });

    it('CLEAR_CURRENT limpa apenas current', () => {
        const start: ProjectState = { ...initialProjectState, current: makeProject() };
        const s = projectReducer(start, { type: 'CLEAR_CURRENT' });
        expect(s.current).toBeNull();
    });

    it('acção desconhecida devolve o mesmo estado (default)', () => {
        // @ts-expect-error testar robustez a acções fora do union type
        const s = projectReducer(initialProjectState, { type: 'UNKNOWN' });
        expect(s).toEqual(initialProjectState);
    });
});
