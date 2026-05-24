import { useEffect, useRef, useState } from 'react';
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

    // Refs mantêm sempre os valores actuais — essencial para os cleanups
    // de useEffect não usarem closures com valores antigos.
    const partituraUrlRef = useRef<string | null>(null);
    const tabUrlRef = useRef<string | null>(null);
    partituraUrlRef.current = partituraUrl;
    tabUrlRef.current = tabUrl;

    // Revoga os blob URLs apenas ao desmontar o componente.
    // NÃO colocar [partituraUrl, tabUrl] como deps: se tabUrl mudar e
    // o cleanup correr com partituraUrl ainda válido, o blob da partitura
    // seria revogado enquanto o utilizador ainda podia estar a fazer download.
    useEffect(() => {
        return () => {
            if (partituraUrlRef.current) URL.revokeObjectURL(partituraUrlRef.current);
            if (tabUrlRef.current) URL.revokeObjectURL(tabUrlRef.current);
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Quando se muda para outro corte, revogamos os blobs antigos e limpamos.
    useEffect(() => {
        return () => {
            if (partituraUrlRef.current) URL.revokeObjectURL(partituraUrlRef.current);
            if (tabUrlRef.current) URL.revokeObjectURL(tabUrlRef.current);
            setPartituraUrl(null);
            setTabUrl(null);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [cut.id]);

    const handlePartitura = async () => {
        setLoadingPart(true);
        try {
            const url = await generationService.generatePartituraFromGeneration(cut.id);
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
            const url = await generationService.generateTablatureFromGeneration(cut.id);
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
                        <a href={partituraUrl} download={`partitura_${cut.id.slice(0, 8)}.pdf`}>
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
                        <a href={tabUrl} download={`tablatura_${cut.id.slice(0, 8)}.pdf`}>
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
