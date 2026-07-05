/**
 * Testes unitários para useAudioGenerations — o hook mais arriscado do
 * projeto: orquestra o carregamento da árvore (gerações + cortes) e faz
 * polling condicional enquanto houver estados não-terminais.
 *
 * Cobre:
 *   - Carregamento inicial da árvore (roots + cuts em paralelo)
 *   - Ausência de polling quando tudo está em estado terminal
 *   - Início de polling quando há status/partitura/tablatura pending|processing
 *   - Paragem do polling ao desmontar (sem chamadas extra após unmount)
 *   - Tratamento de erro no carregamento inicial e no refresh
 *   - Ações submitGeneration / cutGeneration / deleteGeneration (chamam o
 *     serviço, depois fazem refresh, e alternam a respectiva flag de loading)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';

vi.mock('../../../src/services/generation/generationService', () => ({
    generationService: {
        listByAudio: vi.fn(),
        listCuts: vi.fn(),
        submitGeneration: vi.fn(),
        cutGeneration: vi.fn(),
        deleteGeneration: vi.fn(),
    },
}));

import useAudioGenerations from '../../../src/hooks/generation/useAudioGenerations';
import { generationService } from '../../../src/services/generation/generationService';
import type { GenerationResult } from '../../../src/services/generation/generationResponseTypes';

const AUDIO_ID = 'audio-001';

function makeRoot(overrides: Partial<GenerationResult> = {}): GenerationResult {
    return {
        id: 'gen-root-1',
        status: 'completed',
        partitura_status: null,
        tablatura_status: null,
        ...overrides,
    };
}

beforeEach(() => {
    vi.clearAllMocks();
});

afterEach(() => {
    vi.useRealTimers();
});

describe('carregamento inicial', () => {
    it('carrega raízes e os cortes de cada uma, montando a árvore', async () => {
        const root = makeRoot({ id: 'gen-1' });
        const cut = makeRoot({ id: 'cut-1', parent_generation_id: 'gen-1' });
        vi.mocked(generationService.listByAudio).mockResolvedValueOnce([root]);
        vi.mocked(generationService.listCuts).mockResolvedValueOnce([cut]);

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));

        expect(result.current.loading).toBe(true);

        await waitFor(() => expect(result.current.loading).toBe(false));

        expect(generationService.listByAudio).toHaveBeenCalledWith(AUDIO_ID);
        expect(generationService.listCuts).toHaveBeenCalledWith('gen-1');
        expect(result.current.tree).toEqual([{ ...root, cuts: [cut] }]);
    });

    it('não faz nada se audioId for undefined', async () => {
        const { result } = renderHook(() => useAudioGenerations(undefined));
        expect(result.current.loading).toBe(false);
        expect(generationService.listByAudio).not.toHaveBeenCalled();
        expect(result.current.tree).toEqual([]);
    });

    it('define error quando listByAudio falha', async () => {
        vi.mocked(generationService.listByAudio).mockRejectedValueOnce({ detail: 'Erro no servidor.' });

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));

        await waitFor(() => expect(result.current.error).toBe('Erro no servidor.'));
        expect(result.current.loading).toBe(false);
    });

    it('usa mensagem de fallback quando o erro não tem "detail"', async () => {
        vi.mocked(generationService.listByAudio).mockRejectedValueOnce(new Error('boom'));

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));

        await waitFor(() => expect(result.current.error).toBe('Erro a carregar gerações.'));
    });
});

describe('polling condicional', () => {
    it('não reagenda polling quando tudo está em estado terminal e sem notação pendente', async () => {
        vi.useFakeTimers();
        const root = makeRoot({ status: 'completed', partitura_status: null, tablatura_status: null });
        vi.mocked(generationService.listByAudio).mockResolvedValue([root]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);

        renderHook(() => useAudioGenerations(AUDIO_ID));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });

        const callsAfterInitialLoad = vi.mocked(generationService.listByAudio).mock.calls.length;
        expect(callsAfterInitialLoad).toBe(1);

        // Avança bem mais que o intervalo de polling (4s) — não deve haver nova chamada.
        await act(async () => {
            await vi.advanceTimersByTimeAsync(20_000);
        });

        expect(generationService.listByAudio).toHaveBeenCalledTimes(1);
    });

    it('reagenda polling (novo fetch) quando um root está com status pending', async () => {
        vi.useFakeTimers();
        const pendingRoot = makeRoot({ status: 'pending' });
        vi.mocked(generationService.listByAudio).mockResolvedValue([pendingRoot]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);

        renderHook(() => useAudioGenerations(AUDIO_ID));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        expect(generationService.listByAudio).toHaveBeenCalledTimes(1);

        // Passa o intervalo de polling (4000ms) — deve ter feito um novo fetch.
        await act(async () => {
            await vi.advanceTimersByTimeAsync(4000);
        });
        expect(generationService.listByAudio).toHaveBeenCalledTimes(2);
    });

    it('reagenda polling quando partitura_status de um corte está processing', async () => {
        vi.useFakeTimers();
        const root = makeRoot({ status: 'completed' });
        const cutProcessing = makeRoot({
            id: 'cut-1',
            parent_generation_id: root.id,
            status: 'completed',
            partitura_status: 'processing',
        });
        vi.mocked(generationService.listByAudio).mockResolvedValue([root]);
        vi.mocked(generationService.listCuts).mockResolvedValue([cutProcessing]);

        renderHook(() => useAudioGenerations(AUDIO_ID));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        expect(generationService.listByAudio).toHaveBeenCalledTimes(1);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(4000);
        });
        expect(generationService.listByAudio).toHaveBeenCalledTimes(2);
    });

    it('para o polling ao desmontar (sem chamadas extra depois do unmount)', async () => {
        vi.useFakeTimers();
        const pendingRoot = makeRoot({ status: 'pending' });
        vi.mocked(generationService.listByAudio).mockResolvedValue([pendingRoot]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);

        const { unmount } = renderHook(() => useAudioGenerations(AUDIO_ID));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        const callsBeforeUnmount = vi.mocked(generationService.listByAudio).mock.calls.length;

        unmount();

        await act(async () => {
            await vi.advanceTimersByTimeAsync(60_000);
        });

        expect(generationService.listByAudio).toHaveBeenCalledTimes(callsBeforeUnmount);
    });

    it('ignora erros transientes de polling sem propagar para o estado error', async () => {
        vi.useFakeTimers();
        const pendingRoot = makeRoot({ status: 'pending' });
        vi.mocked(generationService.listByAudio)
            .mockResolvedValueOnce([pendingRoot])
            .mockRejectedValueOnce(new Error('falha transiente'));
        vi.mocked(generationService.listCuts).mockResolvedValue([]);

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        expect(result.current.error).toBeNull();

        await act(async () => {
            await vi.advanceTimersByTimeAsync(4000);
        });

        // O erro do polling é engolido propositadamente (ver comentário no hook).
        expect(result.current.error).toBeNull();
    });
});

describe('ações', () => {
    it('submitGeneration chama o serviço, depois refresh, e alterna submitting', async () => {
        vi.mocked(generationService.listByAudio).mockResolvedValue([]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);
        vi.mocked(generationService.submitGeneration).mockResolvedValueOnce({
            id: 'gen-new', status: 'pending', project_id: 'proj-1', prompt: 'x',
        });

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));
        await waitFor(() => expect(result.current.loading).toBe(false));

        expect(result.current.submitting).toBe(false);

        await act(async () => {
            await result.current.submitGeneration({
                project_id: 'proj-1', audio_id: AUDIO_ID, prompt: 'x', instrument: 'guitarra',
            });
        });

        expect(generationService.submitGeneration).toHaveBeenCalled();
        // refresh() foi chamado após o submit: listByAudio chamado mais de 1 vez
        expect(vi.mocked(generationService.listByAudio).mock.calls.length).toBeGreaterThanOrEqual(2);
        expect(result.current.submitting).toBe(false);
    });

    it('cutGeneration chama o serviço, depois refresh, e alterna cutting', async () => {
        vi.mocked(generationService.listByAudio).mockResolvedValue([]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);
        vi.mocked(generationService.cutGeneration).mockResolvedValueOnce(makeRoot({ id: 'cut-1' }));

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
            await result.current.cutGeneration('gen-1', { inicio_segundos: 0, fim_segundos: 10 });
        });

        expect(generationService.cutGeneration).toHaveBeenCalledWith('gen-1', { inicio_segundos: 0, fim_segundos: 10 });
        expect(result.current.cutting).toBe(false);
    });

    it('deleteGeneration chama o serviço e depois refresh', async () => {
        vi.mocked(generationService.listByAudio).mockResolvedValue([]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);
        vi.mocked(generationService.deleteGeneration).mockResolvedValueOnce(undefined);

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
            await result.current.deleteGeneration('gen-1');
        });

        expect(generationService.deleteGeneration).toHaveBeenCalledWith('gen-1');
        expect(vi.mocked(generationService.listByAudio).mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    it('mantém submitting=false mesmo quando o serviço falha (finally)', async () => {
        vi.mocked(generationService.listByAudio).mockResolvedValue([]);
        vi.mocked(generationService.listCuts).mockResolvedValue([]);
        vi.mocked(generationService.submitGeneration).mockRejectedValueOnce(new Error('falhou'));

        const { result } = renderHook(() => useAudioGenerations(AUDIO_ID));
        await waitFor(() => expect(result.current.loading).toBe(false));

        await act(async () => {
            await expect(
                result.current.submitGeneration({
                    project_id: 'proj-1', audio_id: AUDIO_ID, prompt: 'x', instrument: 'guitarra',
                }),
            ).rejects.toThrow('falhou');
        });

        expect(result.current.submitting).toBe(false);
    });
});
