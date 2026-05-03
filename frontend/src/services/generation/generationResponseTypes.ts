/**
 * Tipos de resposta do dominio "generation" — espelham os DTOs em
 * backend/app/domain/dtos/endpoints/generation.py
 */

export type InstrumentType = 'piano' | 'guitarra' | 'bateria' | 'baixo' | 'outros';
export type MusicGenreType = 'classical' | 'jazz' | 'rock' | 'pop' | 'ambient';

export type GenerationStatus = 'pending' | 'processing' | 'completed' | 'failed' | string;

export type GenerationRequest = {
    project_id: string;   // uuid
    audio_id: string;     // uuid
    prompt: string;
    instrument: InstrumentType;
    genre?: MusicGenreType;
    duration?: number;
    tempo_override?: number;
};

export type CoverGenerationRequest = GenerationRequest & {
    upload_url?: string;
    audio_weight?: number; // 0.0 - 1.0
};

export type GenerationResponse = {
    generation_id: string;
    status: GenerationStatus;
    project_id: string;
    prompt: string;
    instrument?: string;
    genre?: string | null;
    parent_generation_id?: string | null;
    created_at?: string | null;
};

export type GenerationResult = {
    generation_id: string;
    status: GenerationStatus;
    project_id?: string | null;
    audio_file_id?: string | null;
    parent_generation_id?: string | null;
    prompt?: string | null;
    instrument?: string | null;
    audio_file_path?: string | null;
    midi_file_path?: string | null;
    partitura_file_path?: string | null;
    tablatura_file_path?: string | null;
    error_message?: string | null;
    created_at?: string | null;
    completed_at?: string | null;
};

export type CutGenerationRequest = {
    inicio_segundos: number;
    fim_segundos: number;
};

export type GenerationListResponse = {
    generations: GenerationResult[];
};

/**
 * Helper: distinguir uma geração raiz de um corte. Cortes são generations
 * com parent_generation_id != null.
 */
export function isCut(g: GenerationResult): boolean {
    return !!g.parent_generation_id;
}
