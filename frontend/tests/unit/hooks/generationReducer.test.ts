/**
 * Testes unitários para generationReducer (reducer puro, sem I/O) e para o
 * helper isCut() de generationResponseTypes.ts.
 */

import { describe, it, expect } from 'vitest';
import {
    generationReducer,
    initialGenerationState,
    GenerationState,
} from '../../../src/hooks/generation/generationReducer';
import {
    isCut,
    GenerationResponse,
    GenerationResult,
} from '../../../src/services/generation/generationResponseTypes';

function makeSubmission(overrides: Partial<GenerationResponse> = {}): GenerationResponse {
    return {
        id: 'gen-1',
        status: 'pending',
        project_id: 'proj-1',
        prompt: 'Guitarra clássica',
        ...overrides,
    };
}

function makeResult(overrides: Partial<GenerationResult> = {}): GenerationResult {
    return {
        id: 'gen-1',
        status: 'completed',
        ...overrides,
    };
}

describe('generationReducer', () => {
    it('estado inicial tem valores por defeito', () => {
        expect(initialGenerationState).toEqual({
            submissions: [],
            statusById: {},
            loading: false,
            submitting: false,
            error: null,
        });
    });

    it('SET_LOADING altera apenas loading', () => {
        const s = generationReducer(initialGenerationState, { type: 'SET_LOADING', payload: true });
        expect(s.loading).toBe(true);
    });

    it('SET_SUBMITTING altera apenas submitting', () => {
        const s = generationReducer(initialGenerationState, { type: 'SET_SUBMITTING', payload: true });
        expect(s.submitting).toBe(true);
    });

    it('SET_ERROR define error e desliga loading e submitting', () => {
        const start: GenerationState = { ...initialGenerationState, loading: true, submitting: true };
        const s = generationReducer(start, { type: 'SET_ERROR', payload: 'falhou' });
        expect(s.error).toBe('falhou');
        expect(s.loading).toBe(false);
        expect(s.submitting).toBe(false);
    });

    it('GENERATION_SUBMITTED adiciona à lista de submissões e desliga submitting', () => {
        const sub = makeSubmission();
        const start: GenerationState = { ...initialGenerationState, submitting: true, error: 'x' };
        const s = generationReducer(start, { type: 'GENERATION_SUBMITTED', payload: sub });
        expect(s.submissions).toEqual([sub]);
        expect(s.submitting).toBe(false);
        expect(s.error).toBeNull();
    });

    it('STATUS_UPDATED indexa o resultado por id e limpa loading/error', () => {
        const result = makeResult({ id: 'gen-1', status: 'processing' });
        const start: GenerationState = { ...initialGenerationState, loading: true, error: 'x' };
        const s = generationReducer(start, { type: 'STATUS_UPDATED', payload: result });
        expect(s.statusById['gen-1']).toEqual(result);
        expect(s.loading).toBe(false);
        expect(s.error).toBeNull();
    });

    it('STATUS_UPDATED preserva entradas anteriores de outros ids', () => {
        const first = makeResult({ id: 'gen-1' });
        const second = makeResult({ id: 'gen-2' });
        let s = generationReducer(initialGenerationState, { type: 'STATUS_UPDATED', payload: first });
        s = generationReducer(s, { type: 'STATUS_UPDATED', payload: second });
        expect(s.statusById).toEqual({ 'gen-1': first, 'gen-2': second });
    });

    it('GENERATION_DELETED remove das submissões e do statusById', () => {
        const sub = makeSubmission({ id: 'gen-1' });
        const otherSub = makeSubmission({ id: 'gen-2' });
        const result = makeResult({ id: 'gen-1' });
        const start: GenerationState = {
            ...initialGenerationState,
            submissions: [sub, otherSub],
            statusById: { 'gen-1': result },
        };
        const s = generationReducer(start, { type: 'GENERATION_DELETED', payload: 'gen-1' });
        expect(s.submissions).toEqual([otherSub]);
        expect(s.statusById).toEqual({});
    });

    it('GENERATION_DELETED de um id inexistente não lança e não altera nada', () => {
        const sub = makeSubmission({ id: 'gen-1' });
        const start: GenerationState = { ...initialGenerationState, submissions: [sub] };
        const s = generationReducer(start, { type: 'GENERATION_DELETED', payload: 'nao-existe' });
        expect(s.submissions).toEqual([sub]);
        expect(s.statusById).toEqual({});
    });

    it('acção desconhecida devolve o mesmo estado (default)', () => {
        // @ts-expect-error testar robustez a acções fora do union type
        const s = generationReducer(initialGenerationState, { type: 'UNKNOWN' });
        expect(s).toEqual(initialGenerationState);
    });
});

describe('isCut', () => {
    it('devolve true quando tem parent_generation_id', () => {
        expect(isCut(makeResult({ parent_generation_id: 'gen-parent' }))).toBe(true);
    });

    it('devolve false quando parent_generation_id é null', () => {
        expect(isCut(makeResult({ parent_generation_id: null }))).toBe(false);
    });

    it('devolve false quando parent_generation_id não está definido', () => {
        expect(isCut(makeResult())).toBe(false);
    });
});
