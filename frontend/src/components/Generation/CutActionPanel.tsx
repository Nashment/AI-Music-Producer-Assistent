import { useEffect, useRef, useState } from 'react';
import { generationService } from '../../services/generation/generationService';
import { GenerationResult } from '../../services/generation/generationResponseTypes';
import useLanguage from '../../hooks/language/useLanguage';
import Spinner from '../Layout/Spinner';

interface Props {
    cut: GenerationResult;
    onError: (msg: string) => void;
}

/**
 * Painel direito quando o utilizador selecciona um corte.
 * Duas acções: gerar partitura PDF e gerar tablatura PDF.
 */
export function CutActionPanel({ cut, onError }: Props) {
    const { t } = useLanguage();
    const [partituraUrl, setPartituraUrl] = useState<string | null>(null);
    const [tabUrl, setTabUrl] = useState<string | null>(null);
    const [loadingPart, setLoadingPart] = useState(false);
    const [loadingTab, setLoadingTab] = useState(false);
    const [loadingAudio, setLoadingAudio] = useState(false);

    const partituraUrlRef = useRef<string | null>(null);
    const tabUrlRef = useRef<string | null>(null);
    partituraUrlRef.current = partituraUrl;
    tabUrlRef.current = tabUrl;

    useEffect(() => {
        return () => {
            if (partituraUrlRef.current) URL.revokeObjectURL(partituraUrlRef.current);
            if (tabUrlRef.current) URL.revokeObjectURL(tabUrlRef.current);
        };
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
            onError(e?.detail ?? t.cutPanel.scoreError);
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
            onError(e?.detail ?? t.cutPanel.tabError);
        } finally {
            setLoadingTab(false);
        }
    };

    const handleDownloadAudio = async () => {
        setLoadingAudio(true);
        try {
            const blobUrl = await generationService.fetchGenerationAudioBlobUrl(cut.id);
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = `corte_${cut.id.slice(0, 8)}.wav`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(blobUrl), 10_000);
        } catch (e: any) {
            onError(e?.detail ?? t.cutPanel.audioError);
        } finally {
            setLoadingAudio(false);
        }
    };

    return (
        <div className="cut-action-panel">
            <header>
                <h3>{t.cutPanel.title}</h3>
                <p className="text-muted text-sm">
                    {cut.prompt || t.cutPanel.defaultPrompt}
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
                        <Spinner size="sm" label={t.cutPanel.generating} />
                    ) : (
                        <>{t.cutPanel.generateScore}</>
                    )}
                </button>
                <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleTablature}
                    disabled={loadingTab}
                >
                    {loadingTab ? (
                        <Spinner size="sm" label={t.cutPanel.generating} />
                    ) : (
                        <>{t.cutPanel.generateTab}</>
                    )}
                </button>
                <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={handleDownloadAudio}
                    disabled={loadingAudio}
                >
                    {loadingAudio ? (
                        <Spinner size="sm" label={t.cutPanel.preparing} />
                    ) : (
                        <>{t.cutPanel.downloadAudio}</>
                    )}
                </button>
            </div>

            {partituraUrl ? (
                <section className="cut-action-pdf">
                    <header className="cut-action-pdf-head">
                        <strong>{t.cutPanel.score}</strong>
                        <a href={partituraUrl} download={`partitura_${cut.id.slice(0, 8)}.pdf`}>
                            {t.cutPanel.download}
                        </a>
                    </header>
                    <iframe src={partituraUrl} title={t.cutPanel.score} />
                </section>
            ) : null}

            {tabUrl ? (
                <section className="cut-action-pdf">
                    <header className="cut-action-pdf-head">
                        <strong>{t.cutPanel.tab}</strong>
                        <a href={tabUrl} download={`tablatura_${cut.id.slice(0, 8)}.pdf`}>
                            {t.cutPanel.download}
                        </a>
                    </header>
                    <iframe src={tabUrl} title={t.cutPanel.tab} />
                </section>
            ) : null}
        </div>
    );
}

export default CutActionPanel;
