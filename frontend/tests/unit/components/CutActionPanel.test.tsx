/**
 * Testes unitários para CutActionPanel.
 *
 * Cobre:
 *   - Renderização condicional por fase (idle / pending / processing / completed / failed)
 *   - Botão "Regerar" só aparece em 'completed'
 *   - Clique em "Gerar" chama requestPartitura / requestTablature
 *   - Clique em "Regerar" chama os mesmos serviços
 *   - onNotationRequested é chamado após clique
 *   - onError é chamado quando o serviço falha
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock do serviço antes do import do componente
vi.mock('../../../src/services/generation/generationService', () => ({
    generationService: {
        requestPartitura:  vi.fn(),
        requestTablature:  vi.fn(),
        getPartituraUrl:   vi.fn(),
        getTablatureUrl:   vi.fn(),
        fetchGenerationAudioBlobUrl: vi.fn(),
    },
}));

// Mock do hook de linguagem
vi.mock('../../../src/hooks/language/useLanguage', () => ({
    default: () => ({
        t: {
            cutPanel: {
                title:          'Notação para este corte',
                defaultPrompt:  'Excerto de uma geração',
                generating:     'A gerar…',
                generateScore:  'Gerar Partitura',
                generateTab:    'Gerar Tablatura',
                preparing:      'A preparar…',
                downloadAudio:  'Descarregar Áudio',
                score:          'Partitura',
                tab:            'Tablatura',
                download:       'Download',
                scoreError:     'Erro a gerar partitura.',
                tabError:       'Erro a gerar tablatura.',
                audioError:     'Erro a descarregar áudio.',
                retry:          'Tentar novamente',
                regenerate:     'Regerar',
            },
        },
    }),
}));

import { CutActionPanel } from '../../../src/components/Generation/CutActionPanel';
import { generationService } from '../../../src/services/generation/generationService';
import type { GenerationResult } from '../../../src/services/generation/generationResponseTypes';

// ---------------------------------------------------------------------------
// Factory de corte com defaults
// ---------------------------------------------------------------------------
function makeCut(overrides: Partial<GenerationResult> = {}): GenerationResult {
    return {
        id: 'cut-test-001',
        status: 'completed',
        parent_generation_id: 'gen-001',
        prompt: 'Corte de teste',
        instrument: 'guitarra',
        audio_storage_key: 'generations/cut.wav',
        partitura_status: null,
        tablatura_status: null,
        partitura_storage_key: null,
        tablatura_storage_key: null,
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------
beforeEach(() => {
    vi.clearAllMocks();
});

afterEach(() => {
    vi.restoreAllMocks();
});

// ===========================================================================
// Renderização condicional por fase
// ===========================================================================
describe('Fase idle (sem notação)', () => {
    it('deve renderizar botão "Gerar Partitura" quando partitura não foi pedida', () => {
        // Arrange
        const cut = makeCut({ partitura_status: null, partitura_storage_key: null });
        // Act
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        // Assert
        expect(screen.getByText('Gerar Partitura')).toBeInTheDocument();
    });

    it('deve renderizar botão "Gerar Tablatura" quando tablatura não foi pedida', () => {
        const cut = makeCut();
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        expect(screen.getByText('Gerar Tablatura')).toBeInTheDocument();
    });

    it('não deve renderizar botão "Regerar" na fase idle', () => {
        const cut = makeCut();
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        expect(screen.queryByText('Regerar')).not.toBeInTheDocument();
    });
});

describe('Fase pending / processing', () => {
    it('deve mostrar spinner "a gerar" quando partitura_status é pending', () => {
        const cut = makeCut({ partitura_status: 'pending', partitura_storage_key: null });
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        expect(screen.getByText('A gerar…')).toBeInTheDocument();
        // Botão "Gerar Partitura" não aparece durante o processamento
        expect(screen.queryByText('Gerar Partitura')).not.toBeInTheDocument();
    });

    it('deve mostrar spinner quando tablatura_status é processing', () => {
        const cut = makeCut({ tablatura_status: 'processing', tablatura_storage_key: null });
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        // O spinner aparece para a tablatura (texto "A gerar…")
        const spinners = screen.getAllByText('A gerar…');
        expect(spinners.length).toBeGreaterThanOrEqual(1);
    });
});

describe('Fase failed', () => {
    it('deve mostrar mensagem de erro e botão "Tentar novamente" para partitura falhada', () => {
        const cut = makeCut({ partitura_status: 'failed', partitura_storage_key: null });
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);
        expect(screen.getByText('Erro a gerar partitura.')).toBeInTheDocument();
        expect(screen.getByText('Tentar novamente')).toBeInTheDocument();
    });
});

describe('Fase completed', () => {
    it('deve mostrar botão "Regerar" após geração bem-sucedida', async () => {
        // Arrange — completed com chave R2
        const cut = makeCut({
            partitura_status: 'completed',
            partitura_storage_key: 'partitura/cut-test-001.pdf',
        });
        vi.mocked(generationService.getPartituraUrl).mockResolvedValueOnce(
            'https://r2.example.com/partitura.pdf'
        );

        // Act
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);

        // Assert — botão Regerar visível
        await waitFor(() => {
            expect(screen.getByTitle('Regerar')).toBeInTheDocument();
        });
    });

    it('deve mostrar link de Download ao lado do botão Regerar', async () => {
        const cut = makeCut({
            partitura_status: 'completed',
            partitura_storage_key: 'partitura/cut-test-001.pdf',
        });
        vi.mocked(generationService.getPartituraUrl).mockResolvedValueOnce(
            'https://r2.example.com/partitura.pdf'
        );

        render(<CutActionPanel cut={cut} onError={vi.fn()} />);

        await waitFor(() => {
            expect(screen.getByText('Download')).toBeInTheDocument();
        });
    });
});

// ===========================================================================
// Fluxo de clique: "Gerar" e "Regerar"
// ===========================================================================
describe('Clique em "Gerar Partitura"', () => {
    it('deve chamar generationService.requestPartitura com o id correcto', async () => {
        // Arrange
        const cut = makeCut();
        const onNotationRequested = vi.fn();
        vi.mocked(generationService.requestPartitura).mockResolvedValueOnce({
            ...cut,
            partitura_status: 'pending',
        });

        render(
            <CutActionPanel
                cut={cut}
                onError={vi.fn()}
                onNotationRequested={onNotationRequested}
            />
        );

        // Act
        fireEvent.click(screen.getByText('Gerar Partitura'));

        // Assert
        await waitFor(() => {
            expect(generationService.requestPartitura).toHaveBeenCalledWith('cut-test-001');
            expect(onNotationRequested).toHaveBeenCalledTimes(1);
        });
    });

    it('deve chamar generationService.requestTablature com o id correcto', async () => {
        const cut = makeCut();
        vi.mocked(generationService.requestTablature).mockResolvedValueOnce({
            ...cut,
            tablatura_status: 'pending',
        });

        render(<CutActionPanel cut={cut} onError={vi.fn()} onNotationRequested={vi.fn()} />);

        fireEvent.click(screen.getByText('Gerar Tablatura'));

        await waitFor(() => {
            expect(generationService.requestTablature).toHaveBeenCalledWith('cut-test-001');
        });
    });

    it('deve chamar onError quando requestPartitura falha', async () => {
        // Arrange
        const cut = makeCut();
        const onError = vi.fn();
        vi.mocked(generationService.requestPartitura).mockRejectedValueOnce(
            { detail: 'Fila indisponível.' }
        );

        render(<CutActionPanel cut={cut} onError={onError} />);

        // Act
        fireEvent.click(screen.getByText('Gerar Partitura'));

        // Assert
        await waitFor(() => {
            expect(onError).toHaveBeenCalledWith('Fila indisponível.');
        });
    });
});

describe('Clique em "Regerar" (fase completed)', () => {
    it('deve chamar requestPartitura ao clicar em Regerar', async () => {
        const cut = makeCut({
            partitura_status: 'completed',
            partitura_storage_key: 'partitura/cut-test-001.pdf',
        });
        vi.mocked(generationService.getPartituraUrl).mockResolvedValueOnce(
            'https://r2.example.com/partitura.pdf'
        );
        vi.mocked(generationService.requestPartitura).mockResolvedValueOnce({
            ...cut,
            partitura_status: 'pending',
            partitura_storage_key: null,
        });

        const onNotationRequested = vi.fn();
        render(
            <CutActionPanel cut={cut} onError={vi.fn()} onNotationRequested={onNotationRequested} />
        );

        // Aguardar que a fase completed renderize o botão Regerar
        await waitFor(() => expect(screen.getByTitle('Regerar')).toBeInTheDocument());

        // Act
        fireEvent.click(screen.getByTitle('Regerar'));

        // Assert
        await waitFor(() => {
            expect(generationService.requestPartitura).toHaveBeenCalledWith('cut-test-001');
            expect(onNotationRequested).toHaveBeenCalled();
        });
    });
});

// ===========================================================================
// Fetch de URL automático quando fase transita para completed
// ===========================================================================
describe('Fetch automático de presigned URL', () => {
    it('deve chamar getPartituraUrl automaticamente quando partitura_status é completed', async () => {
        // Arrange
        const cut = makeCut({
            partitura_status: 'completed',
            partitura_storage_key: 'partitura/cut-test-001.pdf',
        });
        vi.mocked(generationService.getPartituraUrl).mockResolvedValueOnce(
            'https://r2.example.com/partitura.pdf'
        );

        // Act
        render(<CutActionPanel cut={cut} onError={vi.fn()} />);

        // Assert — URL foi pedida automaticamente ao montar
        await waitFor(() => {
            expect(generationService.getPartituraUrl).toHaveBeenCalledWith('cut-test-001');
        });
    });

    it('deve chamar getTablatureUrl automaticamente quando tablatura_status é completed', async () => {
        const cut = makeCut({
            tablatura_status: 'completed',
            tablatura_storage_key: 'tablature/cut-test-001.pdf',
        });
        vi.mocked(generationService.getTablatureUrl).mockResolvedValueOnce(
            'https://r2.example.com/tablature.pdf'
        );

        render(<CutActionPanel cut={cut} onError={vi.fn()} />);

        await waitFor(() => {
            expect(generationService.getTablatureUrl).toHaveBeenCalledWith('cut-test-001');
        });
    });

    it('não deve chamar getPartituraUrl se já tem URL em memória (evitar re-fetch)', async () => {
        // Ao re-render com o mesmo cut, o useEffect não deve re-disparar
        const cut = makeCut({
            partitura_status: 'completed',
            partitura_storage_key: 'partitura/cut-test-001.pdf',
        });
        vi.mocked(generationService.getPartituraUrl).mockResolvedValue(
            'https://r2.example.com/partitura.pdf'
        );

        const { rerender } = render(<CutActionPanel cut={cut} onError={vi.fn()} />);

        await waitFor(() => {
            expect(generationService.getPartituraUrl).toHaveBeenCalledTimes(1);
        });

        // Re-render com o mesmo cut (simula polling que não muda a chave)
        rerender(<CutActionPanel cut={cut} onError={vi.fn()} />);

        await waitFor(() => {
            // Deve continuar com apenas 1 chamada
            expect(generationService.getPartituraUrl).toHaveBeenCalledTimes(1);
        });
    });
});
