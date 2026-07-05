/**
 * Testes unitários para src/utils/common.ts.
 *
 * Cobre:
 *   - displayFileName: limpeza de storage keys (pasta + prefixo UUID)
 *   - audioDisplayName: prioridade display_name > storage_key
 *   - generationLabel: prioridade name > prompt (truncado) > fallback
 *   - notationCapabilities: gating por instrumento
 */

import { describe, it, expect } from 'vitest';
import {
    displayFileName,
    audioDisplayName,
    generationLabel,
    notationCapabilities,
} from '../../../src/utils/common';

describe('displayFileName', () => {
    it('remove a pasta e o prefixo UUID de uma storage key', () => {
        const key = 'audio/550e8400-e29b-41d4-a716-446655440000_musica.wav';
        expect(displayFileName(key)).toBe('musica.wav');
    });

    it('lida com separadores de pasta estilo Windows', () => {
        const key = 'audio\\550e8400-e29b-41d4-a716-446655440000_musica.wav';
        expect(displayFileName(key)).toBe('musica.wav');
    });

    it('devolve o basename sem alterações quando não há prefixo UUID', () => {
        expect(displayFileName('audio/musica-sem-prefixo.wav')).toBe('musica-sem-prefixo.wav');
    });

    it('devolve o fallback para valores null/undefined/vazios', () => {
        expect(displayFileName(null)).toBe('áudio');
        expect(displayFileName(undefined)).toBe('áudio');
        expect(displayFileName('')).toBe('áudio');
    });

    it('aceita um fallback customizado', () => {
        expect(displayFileName(null, 'sem nome')).toBe('sem nome');
    });

    it('devolve o fallback se o nome limpo ficar vazio (só espaços)', () => {
        expect(displayFileName('audio/   ')).toBe('áudio');
    });

    it('não remove o prefixo UUID se a capitalização for maiúscula (case-insensitive)', () => {
        const key = 'audio/550E8400-E29B-41D4-A716-446655440000_Musica.wav';
        expect(displayFileName(key)).toBe('Musica.wav');
    });
});

describe('audioDisplayName', () => {
    it('usa display_name quando definido e não vazio', () => {
        const audio = { display_name: 'A Minha Música', storage_key: 'audio/x_song.wav' };
        expect(audioDisplayName(audio)).toBe('A Minha Música');
    });

    it('ignora display_name em branco e usa o storage_key', () => {
        const audio = { display_name: '   ', storage_key: 'audio/550e8400-e29b-41d4-a716-446655440000_song.wav' };
        expect(audioDisplayName(audio)).toBe('song.wav');
    });

    it('deriva do storage_key quando display_name é null', () => {
        const audio = { display_name: null, storage_key: 'audio/550e8400-e29b-41d4-a716-446655440000_song.wav' };
        expect(audioDisplayName(audio)).toBe('song.wav');
    });

    it('deriva do storage_key quando display_name não existe', () => {
        const audio = { storage_key: 'audio/550e8400-e29b-41d4-a716-446655440000_song.wav' };
        expect(audioDisplayName(audio)).toBe('song.wav');
    });
});

describe('generationLabel', () => {
    it('usa name quando definido e não vazio', () => {
        expect(generationLabel({ name: 'Corte principal', prompt: 'Um prompt qualquer' }, 'fallback')).toBe(
            'Corte principal',
        );
    });

    it('ignora name em branco e usa o prompt', () => {
        expect(generationLabel({ name: '   ', prompt: 'Guitarra clássica' }, 'fallback')).toBe(
            'Guitarra clássica',
        );
    });

    it('trunca o prompt quando excede maxLen, com elipse', () => {
        const prompt = 'x'.repeat(60);
        const label = generationLabel({ prompt }, 'fallback', 48);
        expect(label.length).toBe(48);
        expect(label.endsWith('…')).toBe(true);
        expect(label.slice(0, -1)).toBe('x'.repeat(47));
    });

    it('não trunca o prompt quando está dentro do limite', () => {
        const prompt = 'Prompt curto';
        expect(generationLabel({ prompt }, 'fallback', 48)).toBe('Prompt curto');
    });

    it('usa o fallback quando não há name nem prompt', () => {
        expect(generationLabel({}, 'sem título')).toBe('sem título');
    });

    it('usa o fallback quando prompt é apenas espaços', () => {
        expect(generationLabel({ prompt: '   ' }, 'sem título')).toBe('sem título');
    });
});

describe('notationCapabilities', () => {
    it('bateria: sem partitura nem tablatura', () => {
        expect(notationCapabilities('bateria')).toEqual({ score: false, tab: false });
    });

    it('guitarra: partitura e tablatura', () => {
        expect(notationCapabilities('guitarra')).toEqual({ score: true, tab: true });
    });

    it('outro instrumento (ex: piano): só partitura', () => {
        expect(notationCapabilities('piano')).toEqual({ score: true, tab: false });
    });

    it('instrumento desconhecido/undefined: default seguro (só partitura)', () => {
        expect(notationCapabilities(undefined)).toEqual({ score: true, tab: false });
        expect(notationCapabilities(null)).toEqual({ score: true, tab: false });
    });

    it('é case-insensitive', () => {
        expect(notationCapabilities('GUITARRA')).toEqual({ score: true, tab: true });
        expect(notationCapabilities('Bateria')).toEqual({ score: false, tab: false });
    });
});
