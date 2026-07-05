/**
 * Testes unitários para audioReducer (reducer puro, sem I/O).
 */

import { describe, it, expect } from 'vitest';
import {
    audioReducer,
    initialAudioState,
    AudioState,
} from '../../../src/hooks/audio/audioReducer';
import type { AudioAnalysisResponse } from '../../../src/services/audio/audioResponseTypes';

function makeAudio(overrides: Partial<AudioAnalysisResponse> = {}): AudioAnalysisResponse {
    return {
        id: 'audio-1',
        project_id: 'proj-1',
        storage_key: 'audio/x_song.wav',
        duration: 30,
        sample_rate: 44100,
        ...overrides,
    };
}

describe('audioReducer', () => {
    it('estado inicial tem valores por defeito', () => {
        expect(initialAudioState).toEqual({
            audios: [],
            current: null,
            loading: false,
            uploading: false,
            error: null,
        });
    });

    it('SET_LOADING altera apenas loading', () => {
        const s = audioReducer(initialAudioState, { type: 'SET_LOADING', payload: true });
        expect(s.loading).toBe(true);
    });

    it('SET_UPLOADING altera apenas uploading', () => {
        const s = audioReducer(initialAudioState, { type: 'SET_UPLOADING', payload: true });
        expect(s.uploading).toBe(true);
    });

    it('SET_ERROR define error e desliga loading e uploading', () => {
        const start: AudioState = { ...initialAudioState, loading: true, uploading: true };
        const s = audioReducer(start, { type: 'SET_ERROR', payload: 'falhou' });
        expect(s.error).toBe('falhou');
        expect(s.loading).toBe(false);
        expect(s.uploading).toBe(false);
    });

    it('AUDIOS_LOADED substitui a lista e limpa loading/error', () => {
        const audios = [makeAudio({ id: 'a' }), makeAudio({ id: 'b' })];
        const start: AudioState = { ...initialAudioState, loading: true, error: 'x' };
        const s = audioReducer(start, { type: 'AUDIOS_LOADED', payload: audios });
        expect(s.audios).toEqual(audios);
        expect(s.loading).toBe(false);
        expect(s.error).toBeNull();
    });

    it('AUDIO_LOADED define current', () => {
        const audio = makeAudio();
        const s = audioReducer(initialAudioState, { type: 'AUDIO_LOADED', payload: audio });
        expect(s.current).toEqual(audio);
    });

    it('AUDIO_UPLOADED adiciona à lista e desliga uploading', () => {
        const existing = makeAudio({ id: 'a' });
        const uploaded = makeAudio({ id: 'b' });
        const start: AudioState = { ...initialAudioState, audios: [existing], uploading: true };
        const s = audioReducer(start, { type: 'AUDIO_UPLOADED', payload: uploaded });
        expect(s.audios).toEqual([existing, uploaded]);
        expect(s.uploading).toBe(false);
    });

    it('AUDIO_UPDATED substitui na lista e no current se coincidir', () => {
        const original = makeAudio({ id: 'a', display_name: 'Antigo' });
        const updated = makeAudio({ id: 'a', display_name: 'Novo' });
        const start: AudioState = { ...initialAudioState, audios: [original], current: original };
        const s = audioReducer(start, { type: 'AUDIO_UPDATED', payload: updated });
        expect(s.audios).toEqual([updated]);
        expect(s.current).toEqual(updated);
    });

    it('AUDIO_UPDATED não mexe no current se for outro áudio', () => {
        const other = makeAudio({ id: 'other' });
        const updated = makeAudio({ id: 'a', display_name: 'Novo' });
        const start: AudioState = {
            ...initialAudioState,
            audios: [makeAudio({ id: 'a' })],
            current: other,
        };
        const s = audioReducer(start, { type: 'AUDIO_UPDATED', payload: updated });
        expect(s.current).toEqual(other);
    });

    it('AUDIO_DELETED remove da lista e limpa current se era o eliminado', () => {
        const toDelete = makeAudio({ id: 'a' });
        const keep = makeAudio({ id: 'b' });
        const start: AudioState = {
            ...initialAudioState,
            audios: [toDelete, keep],
            current: toDelete,
        };
        const s = audioReducer(start, { type: 'AUDIO_DELETED', payload: 'a' });
        expect(s.audios).toEqual([keep]);
        expect(s.current).toBeNull();
    });

    it('AUDIO_DELETED mantém current se não era o eliminado', () => {
        const keep = makeAudio({ id: 'b' });
        const start: AudioState = {
            ...initialAudioState,
            audios: [makeAudio({ id: 'a' }), keep],
            current: keep,
        };
        const s = audioReducer(start, { type: 'AUDIO_DELETED', payload: 'a' });
        expect(s.current).toEqual(keep);
    });

    it('CLEAR_CURRENT limpa apenas current', () => {
        const start: AudioState = { ...initialAudioState, current: makeAudio() };
        const s = audioReducer(start, { type: 'CLEAR_CURRENT' });
        expect(s.current).toBeNull();
    });

    it('acção desconhecida devolve o mesmo estado (default)', () => {
        // @ts-expect-error testar robustez a acções fora do union type
        const s = audioReducer(initialAudioState, { type: 'UNKNOWN' });
        expect(s).toEqual(initialAudioState);
    });
});
