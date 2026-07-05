/**
 * Testes unitários para audioService — foco nos pontos com mais risco de
 * regressão silenciosa: construção de query strings, upload multipart, e o
 * fluxo de download em dois passos (presigned URL autenticada -> fetch
 * directo ao R2 sem header Authorization).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { audioService } from '../../../src/services/audio/audioService';

function jsonResponse(body: unknown, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
    });
}

beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal('fetch', vi.fn());
    // jsdom não implementa createObjectURL/revokeObjectURL.
    vi.stubGlobal('URL', Object.assign(URL, {
        createObjectURL: vi.fn(() => 'blob:mock-url'),
        revokeObjectURL: vi.fn(),
    }));
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe('audioService', () => {
    it('listAudios: GET /audio/project/{id}', async () => {
        const listResponse = { audios: [], total: 0 };
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(listResponse));

        const result = await audioService.listAudios('proj-1');

        expect(fetch).toHaveBeenCalledWith('/api/audio/project/proj-1', expect.objectContaining({ method: 'GET' }));
        expect(result).toEqual(listResponse);
    });

    it('uploadAudio: envia FormData com o ficheiro (sem Content-Type manual)', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'a1' }));
        const file = new File(['conteudo'], 'musica.wav', { type: 'audio/wav' });

        await audioService.uploadAudio('proj-1', file);

        const [url, init] = vi.mocked(fetch).mock.calls[0];
        expect(url).toBe('/api/audio/project/proj-1/upload');
        expect(init!.method).toBe('POST');
        expect(init!.body).toBeInstanceOf(FormData);
        expect((init!.body as FormData).get('file')).toBe(file);
        expect((init!.headers as Record<string, string>)['Content-Type']).toBeUndefined();
    });

    it('cutAudio: serializa inicio_segundos/fim_segundos como query string', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'a1' }));

        await audioService.cutAudio('a1', { inicio_segundos: 1.5, fim_segundos: 10 });

        expect(fetch).toHaveBeenCalledWith(
            '/api/audio/a1/cut?inicio_segundos=1.5&fim_segundos=10',
            expect.objectContaining({ method: 'POST' }),
        );
    });

    it('adjustBpm: codifica o target_bpm na query string', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 'a1' }));
        await audioService.adjustBpm('a1', 128);
        expect(fetch).toHaveBeenCalledWith(
            '/api/audio/a1/adjust-bpm?target_bpm=128',
            expect.objectContaining({ method: 'POST' }),
        );
    });

    it('fetchAudioBlobUrl: pede a presigned URL autenticada e depois faz fetch directo sem Authorization', async () => {
        vi.mocked(fetch)
            .mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/audio/a1.wav' }))
            .mockResolvedValueOnce(new Response(new Blob(['dados']), { status: 200 }));

        const blobUrl = await audioService.fetchAudioBlobUrl('a1');

        expect(blobUrl).toBe('blob:mock-url');
        // 1ª chamada: via request() -> passa por /api e pode levar Authorization
        expect(vi.mocked(fetch).mock.calls[0][0]).toBe('/api/audio/a1');
        // 2ª chamada: directa ao R2, sem passar pelo wrapper request()
        expect(vi.mocked(fetch).mock.calls[1][0]).toBe('https://r2.example.com/audio/a1.wav');
        expect(vi.mocked(fetch).mock.calls[1][1]).toBeUndefined();
    });

    it('fetchAudioBlobUrl: lança erro quando o download directo ao R2 falha', async () => {
        vi.mocked(fetch)
            .mockResolvedValueOnce(jsonResponse({ url: 'https://r2.example.com/audio/a1.wav' }))
            .mockResolvedValueOnce(new Response(null, { status: 403 }));

        await expect(audioService.fetchAudioBlobUrl('a1')).rejects.toThrow('Falha a obter ficheiro de audio.');
    });

    it('separateTracks: serializa instrument na query e devolve blob URL', async () => {
        vi.mocked(fetch).mockResolvedValueOnce(new Response(new Blob(['wav']), { status: 200 }));

        const blobUrl = await audioService.separateTracks('a1', { instrument: 'guitarra' });

        expect(fetch).toHaveBeenCalledWith(
            '/api/audio/a1/separate-tracks?instrument=guitarra',
            expect.objectContaining({ method: 'POST' }),
        );
        expect(blobUrl).toBe('blob:mock-url');
    });
});
