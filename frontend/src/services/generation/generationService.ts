import { request } from '../request';
import { BASE_URL } from '../../utils/common';
import { getAccessToken } from '../../utils/auth';
import {
    GenerationRequest,
    CoverGenerationRequest,
    GenerationResponse,
    GenerationResult,
    GenerationListResponse,
    CutGenerationRequest,
} from './generationResponseTypes';

/**
 * Servico do dominio "generation".
 *
 * Backend (resumo de backend/app/api/endpoints/generation.py):
 *   POST   /generation                          -> submete pedido de musica
 *   POST   /generation/cover                    -> submete pedido de cover
 *   GET    /generation/{id}/status              -> estado actual
 *   GET    /generation/{id}                     -> resultado completo
 *   DELETE /generation/{id}                     -> apaga geracao
 *
 *   GET    /generation/by-audio/{audio_id}      -> gerações raiz de um audio
 *   GET    /generation/{id}/cuts                -> cortes (filhos) de uma geracao
 *   GET    /generation/{id}/audio               -> stream do audio fisico (Blob)
 *   POST   /generation/{id}/cut                 -> cria corte (parent_generation_id)
 *   POST   /generation/{id}/partitura           -> partitura PDF (a partir do audio da geracao)
 *   POST   /generation/{id}/tablature           -> tablatura PDF (a partir do audio da geracao)
 *
 * Os endpoints antigos POST /generation/partitura/{audio_id} e
 * POST /generation/tablature/{audio_id} permanecem para compatibilidade.
 */
export const generationService = {
    async submitGeneration(req: GenerationRequest): Promise<GenerationResponse> {
        const res = await request('/generation', {
            method: 'POST',
            body: JSON.stringify(req),
        });
        return res.json();
    },

    async submitCover(req: CoverGenerationRequest): Promise<GenerationResponse> {
        const res = await request('/generation/cover', {
            method: 'POST',
            body: JSON.stringify(req),
        });
        return res.json();
    },

    async getStatus(generationId: string): Promise<GenerationResult> {
        const res = await request(`/generation/${generationId}/status`, { method: 'GET' });
        return res.json();
    },

    async getResult(generationId: string): Promise<GenerationResult> {
        const res = await request(`/generation/${generationId}`, { method: 'GET' });
        return res.json();
    },

    async deleteGeneration(generationId: string): Promise<void> {
        await request(`/generation/${generationId}`, { method: 'DELETE' });
    },

    // -----------------------------------------------------------------
    // Hierarquia: gerações por áudio + cortes
    // -----------------------------------------------------------------

    async listByAudio(audioId: string): Promise<GenerationResult[]> {
        const res = await request(`/generation/by-audio/${audioId}`, { method: 'GET' });
        const data: GenerationListResponse = await res.json();
        return data.generations;
    },

    async listCuts(generationId: string): Promise<GenerationResult[]> {
        const res = await request(`/generation/${generationId}/cuts`, { method: 'GET' });
        const data: GenerationListResponse = await res.json();
        return data.generations;
    },

    /** Devolve um Blob URL para reproduzir/visualizar o áudio da geração. */
    async fetchGenerationAudioBlobUrl(generationId: string): Promise<string> {
        const token = getAccessToken();
        const res = await fetch(`${BASE_URL}/generation/${generationId}/audio`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error('Não foi possível obter o áudio da geração.');
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },

    async cutGeneration(
        generationId: string,
        params: CutGenerationRequest,
    ): Promise<GenerationResult> {
        const res = await request(`/generation/${generationId}/cut`, {
            method: 'POST',
            body: JSON.stringify(params),
        });
        return res.json();
    },

    /** PDF a partir de um áudio cru (audio_id). */
    async generateTablatureFromAudio(audioId: string): Promise<string> {
        const res = await request(`/generation/tablature/${audioId}`, { method: 'POST' });
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },

    /** PDF a partir de um áudio cru (audio_id). */
    async generatePartituraFromAudio(audioId: string): Promise<string> {
        const res = await request(`/generation/partitura/${audioId}`, { method: 'POST' });
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },

    /** PDF a partir do áudio de uma geração (típico para cortes). */
    async generateTablatureFromGeneration(generationId: string): Promise<string> {
        const res = await request(`/generation/${generationId}/tablature`, { method: 'POST' });
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },

    /** PDF a partir do áudio de uma geração (típico para cortes). */
    async generatePartituraFromGeneration(generationId: string): Promise<string> {
        const res = await request(`/generation/${generationId}/partitura`, { method: 'POST' });
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },
};
