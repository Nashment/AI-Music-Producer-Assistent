import { request } from '../request';
import { BASE_URL } from '../../utils/common';
import { getAccessToken } from '../../utils/auth';
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
     * Devolve o URL absoluto para download/streaming. Anexa o token como
     * query string nao e seguro: por isso usamos fetch com Authorization
     * header e devolvemos um Blob URL para uso em <audio src=...>.
     */
    async fetchAudioBlobUrl(audioId: string): Promise<string> {
        const token = getAccessToken();
        const res = await fetch(`${BASE_URL}/audio/${audioId}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error('Falha a obter ficheiro de audio.');
        const blob = await res.blob();
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
