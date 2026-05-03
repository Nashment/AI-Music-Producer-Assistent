import { useEffect, useState } from 'react';
import { generationService } from '../../services/generation/generationService';
import { GenerationResult } from '../../services/generation/generationResponseTypes';
import Spinner from '../Layout/Spinner';

interface Props {
    cut: GenerationResult;
    onError: (msg: string) => void;
}

/**
 * Painel direito quando o utilizador selecciona um corte. Apenas duas
 * acções: gerar partitura PDF e gerar tablatura PDF — ambos a partir do
 * áudio físico do corte (POST /generation/{id}/partitura ou /tablature).
 *
 * Cada PDF é mostrado num <iframe> embutido + botão de download.
 */
export function CutActionPanel({ cut, onError }: Props) {
    const [partituraUrl, setPartituraUrl] = useState<string | null>(null);
    const [tabUrl, setTabUrl] = useState<string | null>(null);
    const [loadingPart, setLoadingPart] = useState(false);
    const [loadingTab, setLoadingTab] = useState(false);

    // Liberta blob URLs ao desmontar / mudar de corte
    useEffect(() => {
        return () => {
            if (partituraUrl) URL.revokeObjectURL(partituraUrl);
            if (tabUrl) URL.revokeObjectURL(tabUrl);
        };
    }, [partituraUrl, tabUrl]);

    // Quando se muda para outro corte, limpamos os PDFs antigos
    useEffect(() => {
        setPartituraUrl(null);
        setTabUrl(null);
    }, [cut.generation_id]);

    const handlePartitura = async () => {
        setLoadingPart(true);
        try {
            const url = await generationService.generatePartituraFromGeneration(cut.generation_id);
            setPartituraUrl(url);
        } catch (e: any) {
            onError(e?.detail ?? 'Erro a gerar partitura.');
        } finally {
            setLoadingPart(false);
        }
    };

    const handleTablature = async () => {
        setLoadingTab(true);
        try {
            const url = await generationService.generateTablatureFromGeneration(cut.generation_id);
            setTabUrl(url);
        } catch (e: any) {
            onError(e?.detail ?? 'Erro a gerar tablatura.');
        } finally {
            setLoadingTab(false);
        }
    };

    return (
        <div className="cut-action-panel">
            <header>
                <h3>Notação para este corte</h3>
                <p className="text-muted text-sm">
                    {cut.prompt || 'Excerto de uma geração'}
                </p>
            </header>

            <div className="cut-action-buttons">
                <button
                    type="button"
                    className="btn"
                    onClick={handlePartitura}
                    disabled={loadingPart}
                >
                    {loadingPart ? (
                        <Spinner size="sm" label="A gerar…" />
                    ) : (
                        <>📄 Gerar Partitura</>
                    )}
                </button>
                <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleTablature}
                    disabled={loadingTab}
                >
                    {loadingTab ? (
                        <Spinner size="sm" label="A gerar…" />
                    ) : (
                        <>🎼 Gerar Tablatura</>
                    )}
                </button>
            </div>

            {partituraUrl ? (
                <section className="cut-action-pdf">
                    <header className="cut-action-pdf-head">
                        <strong>Partitura</strong>
                        <a href={partituraUrl} download={`partitura_${cut.generation_id.slice(0, 8)}.pdf`}>
                            ⬇ Download
                        </a>
                    </header>
                    <iframe src={partituraUrl} title="Partitura PDF" />
                </section>
            ) : null}

            {tabUrl ? (
                <section className="cut-action-pdf">
                    <header className="cut-action-pdf-head">
                        <strong>Tablatura</strong>
                        <a href={tabUrl} download={`tablatura_${cut.generation_id.slice(0, 8)}.pdf`}>
                            ⬇ Download
                        </a>
                    </header>
                    <iframe src={tabUrl} title="Tablatura PDF" />
                </section>
            ) : null}
        </div>
    );
}

export default CutActionPanel;
