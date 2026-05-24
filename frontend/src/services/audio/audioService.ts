import { request } from '../request';
import {
    AudioAnalysisResponse,
    AudioListResponse,
    CutAudioParams,
    SeparateTracksParams,
} from './audioResponseTypes';

/**
 * Servico do dominio "audio".
 *
 * Backend (resumo de backend/app/api/endpoints/audio.py):
 *   GET    /audio/project/{projectId}              -> lista audios
 *   POST   /audio/project/{projectId}/upload       -> upload + analise (multipart)
 *   GET    /audio/analysis/{audioId}               -> metadados da analise
 *   GET    /audio/{audioId}                         -> stream/download do ficheiro
 *   DELETE /audio/{audioId}                         -> apaga
 *   POST   /audio/{audioId}/adjust-bpm?target_bpm=  -> ajusta BPM
 *   POST   /audio/{audioId}/cut?...                 -> corta intervalo
 *   POST   /audio/{audioId}/separate-tracks?...     -> separa instrumento
 */
export const audioService = {
    async listAudios(projectId: string): Promise<AudioListResponse> {
        const res = await request(`/audio/project/${projectId}`, { method: 'GET' });
        return res.json();
    },

    async uploadAudio(
        projectId: string,
        file: File,
    ): Promise<AudioAnalysisResponse> {
        const formData = new FormData();
        formData.append('file', file);
        const res = await request(`/audio/project/${projectId}/upload`, {
            method: 'POST',
            body: formData,
        });
        return res.json();
    },

    async getAudioAnalysis(audioId: string): Promise<AudioAnalysisResponse> {
        const res = await request(`/audio/analysis/${audioId}`, { method: 'GET' });
        return res.json();
    },

    /**
     * Devolve um Blob URL para reproducao/download.
     *
     * Fluxo em dois passos para evitar o conflito de auth dupla do R2:
     *   1. Pede a presigned URL ao backend (com JWT).
     *   2. Faz o download directamente do R2 usando essa URL (sem JWT).
     *      O R2 rejeita pedidos que trazem simultaneamente params de presigned
     *      URL E um header Authorization.
     */
    async fetchAudioBlobUrl(audioId: string): Promise<string> {
        const { url } = await request(`/audio/${audioId}`, { method: 'GET' }).then(r => r.json());
        const audioRes = await fetch(url);
        if (!audioRes.ok) throw new Error('Falha a obter ficheiro de audio.');
        const blob = await audioRes.blob();
        return URL.createObjectURL(blob);
    },

    async deleteAudio(audioId: string): Promise<void> {
        await request(`/audio/${audioId}`, { method: 'DELETE' });
    },

    async adjustBpm(
        audioId: string,
        targetBpm: number,
    ): Promise<AudioAnalysisResponse> {
        const res = await request(
            `/audio/${audioId}/adjust-bpm?target_bpm=${encodeURIComponent(targetBpm)}`,
            { method: 'POST' },
        );
        return res.json();
    },

    async cutAudio(
        audioId: string,
        params: CutAudioParams,
    ): Promise<AudioAnalysisResponse> {
        const qs = new URLSearchParams({
            inicio_segundos: String(params.inicio_segundos),
            fim_segundos: String(params.fim_segundos),
        }).toString();
        const res = await request(`/audio/${audioId}/cut?${qs}`, { method: 'POST' });
        return res.json();
    },

    /**
     * Endpoint devolve um ficheiro WAV directamente (FileResponse). Devolvemos
     * um Blob URL para o caller poder reproduzir/fazer download.
     */
    async separateTracks(
        audioId: string,
        params: SeparateTracksParams,
    ): Promise<string> {
        const qs = new URLSearchParams({ instrument: params.instrument }).toString();
        const res = await request(`/audio/${audioId}/separate-tracks?${qs}`, {
            method: 'POST',
        });
        const blob = await res.blob();
        return URL.createObjectURL(blob);
    },
};
