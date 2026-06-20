/**
 * Constantes globais da aplicacao.
 *
 * BASE_URL e o prefixo das chamadas API a partir do browser. O proxy
 * configurado no vite.config.ts reescreve "/api" -> "/api/v1" no backend.
 */
export const BASE_URL = '/api';

/**
 * Devolve um nome de ficheiro "limpo" para mostrar ao utilizador.
 *
 * As storage keys têm o formato "audio/{uuid}_{nome-original}", pelo que o
 * basename ainda traz o prefixo UUID gerado no backend. Aqui removemos a pasta
 * e o prefixo UUID, deixando apenas o nome original do ficheiro.
 */
const UUID_PREFIX =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_/i;

export function displayFileName(
    storageKeyOrName: string | null | undefined,
    fallback = 'áudio',
): string {
    if (!storageKeyOrName) return fallback;
    const base = storageKeyOrName.split(/[\\/]/).pop() ?? fallback;
    const cleaned = base.replace(UUID_PREFIX, '');
    return cleaned.trim() || fallback;
}

/**
 * Nome a mostrar para um áudio: usa o nome amigável definido pelo utilizador
 * (display_name) quando existe; senão deriva do storage_key (sem o UUID).
 */
export function audioDisplayName(
    audio: { display_name?: string | null; storage_key: string },
    fallback = 'áudio',
): string {
    const custom = audio.display_name?.trim();
    if (custom) return custom;
    return displayFileName(audio.storage_key, fallback);
}

/**
 * Rótulo a mostrar para uma geração/corte: usa o nome amigável (name) quando
 * existe; senão um excerto do prompt; senão o fallback fornecido.
 */
export function generationLabel(
    gen: { name?: string | null; prompt?: string | null },
    fallback: string,
    maxLen = 48,
): string {
    const custom = gen.name?.trim();
    if (custom) return custom;
    const p = gen.prompt?.trim();
    if (p) return p.length > maxLen ? p.slice(0, maxLen - 1) + '…' : p;
    return fallback;
}

/**
 * Notações permitidas por instrumento (gating de partitura/tablatura na UI):
 *   - tablatura: só guitarra (instrumento de trastes);
 *   - partitura: todos menos bateria;
 *   - bateria: nenhuma (fica só com download + pré-escuta).
 * Instrumentos desconhecidos: partitura sim, tablatura não (default seguro).
 */
export function notationCapabilities(
    instrument?: string | null,
): { score: boolean; tab: boolean } {
    const i = (instrument ?? '').toLowerCase();
    return {
        score: i !== 'bateria',
        tab: i === 'guitarra',
    };
}
