/**
 * Testes unitários para generationService — implementação real (o teste do
 * hook useAudioGenerations mocka este módulo inteiro, por isso a
 * implementação em si fica sem cobertura direta). Foco nos endpoints com
 * mais nuance: listagem hierárquica, presigned URLs de notação e o fluxo de
 * download de áudio em dois passos.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { generationService } from '../../../src/services/generation/generationService';

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
    });
}

beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
    vi.stubGlobal('URL', Object.assign(URL, {
        createObjectURL: vi.fn(() => 'blob:mock-url'),
        revokeObjectURL: vi.fn(),
    }));
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('listByAudio / listCuts', () => {
    it('listByAudio: GET /generation/by-audio/{id} e desembrulha "generations"', async () => {
        const generations = [{ id: 'g1', status: 'completed' }];
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ generations }));

        const result = await generationService.listByAudio('audio-1');

        expect(fetch).toHaveBeenCalledWith('/api/generation/by-audio/audio-1', expect.objectContaining({ method: 'GET' }));
        expect(result).toEqual(generations);
    });

    it('listCuts: GET /generation/{id}/cuts e desembrulha "generations"', async () => {
        const cuts = [{ id: 'c1', status: 'completed', parent_generation_id: 'g1' }];
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ generations: cuts }));

        const result = await generationService.listCuts('g1');

        expect(fetch).toHaveBeenCalledWith('/api/generation/g1/cuts', expect.objectContaining({ method: 'GET' }));
        expect(result).toEqual(cuts);
    });
});

describe('notação (partitura/tablatura)', () => {
    it('requestPartitura: POST /generation/{id}/partitura (fire-and-forget)', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'g1', partitura_status: 'pending' }, 202));
        const result = await generationService.requestPartitura('g1');
        expect(fetch).toHaveBeenCalledWith('/api/generation/g1/partitura', expect.objectContaining({ method: 'POST' }));
        expect(result.partitura_status).toBe('pending');
    });

    it('getPartituraUrl: GET /generation/{id}/partitura devolve a presigned URL', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/p.pdf' }));
        const url = await generationService.getPartituraUrl('g1');
        expect(fetch).toHaveBeenCalledWith('/api/generation/g1/partitura', expect.objectContaining({ method: 'GET' }));
        expect(url).toBe('https://r2.example.com/p.pdf');
    });

    it('getTablatureUrl: GET /generation/{id}/tablature devolve a presigned URL', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/t.pdf' }));
        const url = await generationService.getTablatureUrl('g1');
        expect(fetch).toHaveBeenCalledWith('/api/generation/g1/tablature', expect.objectContaining({ method: 'GET' }));
        expect(url).toBe('https://r2.example.com/t.pdf');
    });

    it('propaga o ApiError quando o pedido de notação falha (ex: fila indisponível)', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(
            jsonResponse({ type: 'QUEUE_UNAVAILABLE', title: 'Indisponível', detail: 'Fila indisponível.' }, 503),
        );
        await expect(generationService.requestPartitura('g1')).rejects.toEqual({
            code: 'QUEUE_UNAVAILABLE',
            title: 'Indisponível',
            detail: 'Fila indisponível.',
            status: 503,
        });
    });
});

describe('cutGeneration', () => {
    it('POST /generation/{id}/cut com inicio_segundos/fim_segundos no body', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'cut-1', status: 'pending' }));

        await generationService.cutGeneration('g1', { inicio_segundos: 0, fim_segundos: 15 });

        expect(fetch).toHaveBeenCalledWith(
            '/api/generation/g1/cut',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ inicio_segundos: 0, fim_segundos: 15 }),
            }),
        );
    });
});

describe('fetchGenerationAudioBlobUrl', () => {
    it('pede a presigned URL autenticada e depois faz fetch directo sem Authorization', async () => {
        vi.mocked(fetch)
            .mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/gen/g1.wav' }))
            .mockResolvedValueOnce(new Response(new Blob(['dados']), { status: 200 }));

        const blobUrl = await generationService.fetchGenerationAudioBlobUrl('g1');

        expect(blobUrl).toBe('blob:mock-url');
        expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/generation/g1/audio');
        expect(vi.mocked(fetch).mock.calls[1][0]).toBe('https://r2.example.com/gen/g1.wav');
        expect(vi.mocked(fetch).mock.calls[1][1]).toBeUndefined();
    });

    it('lança erro quando o download directo ao R2 falha', async () => {
        vi.mocked(fetch)
            .mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/gen/g1.wav' }))
            .mockResolvedValueOnce(new Response(null, { status: 403 }));

        await expect(generationService.fetchGenerationAudioBlobUrl('g1')).rejects.toThrow(
            'Não foi possível obter o áudio da geração.',
        );
    });
});

describe('renameGeneration / deleteGeneration', () => {
    it('renameGeneration: PATCH /generation/{id} com o nome', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'g1', name: 'Novo nome' }));
        const result = await generationService.renameGeneration('g1', 'Novo nome');
        expect(fetch).toHaveBeenCalledWith(
            '/api/generation/g1',
            expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ name: 'Novo nome' }) }),
        );
        expect(result.name).toBe('Novo nome');
    });

    it('deleteGeneration: DELETE /generation/{id}', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
        await generationService.deleteGeneration('g1');
        expect(fetch).toHaveBeenCalledWith('/api/generation/g1', expect.objectContaining({ method: 'DELETE' }));
    });
});
