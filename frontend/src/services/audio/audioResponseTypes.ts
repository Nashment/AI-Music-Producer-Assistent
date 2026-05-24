/**
 * Tipos de resposta do dominio "audio" — espelham os DTOs em
 * backend/app/domain/dtos/endpoints/audio.py
 */

export type AudioAnalysisResponse = {
    id: string;            // uuid
    project_id: string;    // uuid
    storage_key: string;   // chave R2/S3 (ex: audio/uuid_filename.mp3)
    duration: number;
    sample_rate: number;
    bpm?: number | null;
    key?: string | null;
    time_signature?: string | null;
    parent_audio_id?: string | null;
};

export type AudioListResponse = {
    audios: AudioAnalysisResponse[];
    total: number;
};

export type CutAudioParams = {
    inicio_segundos: number;
    fim_segundos: number;
};

export type SeparateTracksParams = {
    instrument: string; // ex: "guitarra"
};
