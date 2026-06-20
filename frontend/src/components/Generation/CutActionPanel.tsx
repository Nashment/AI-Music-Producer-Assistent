import { useEffect, useState } from 'react';
import { generationService } from '../../services/generation/generationService';
import { GenerationResult } from '../../services/generation/generationResponseTypes';
import useLanguage from '../../hooks/language/useLanguage';
import Spinner from '../Layout/Spinner';
import { notationCapabilities } from '../../utils/common';

interface Props {
    cut: GenerationResult;
    onError: (msg: string) => void;
    /** Chamado após enfileirar notação para forçar refresh imediato no hook pai. */
    onNotationRequested?: () => void;
}

type NotationPhase = 'idle' | 'pending' | 'processing' | 'completed' | 'failed';

/** Deriva a fase a partir dos dados da geração (actualizados pelo polling do pai). */
function toPhase(status: string | null | undefined, hasKey: boolean): NotationPhase {
    // status tem prioridade sobre hasKey — ao regenerar, o status já é 'pending'
    // mas a storage_key antiga pode ainda estar na DB enquanto o worker processa.
    if (status === 'pending')    return 'pending';
    if (status === 'processing') return 'processing';
    if (status === 'failed')     return 'failed';
    if (hasKey)                  return 'completed';
    return 'idle';
}

/**
 * Painel direito quando o utilizador selecciona um corte.
 *
 * Fluxo assíncrono (replica o padrão de áudio Suno):
 *   1. Utilizador clica "Gerar" → POST /{id}/partitura|tablature (202 imediato)
 *   2. Hook pai faz polling → cut.partitura_status transita para 'processing' → 'completed'
 *   3. Quando completed → GET /{id}/partitura|tablature devolve presigned URL → iframe
 *   4. Botão "Regerar" aparece ao lado do Download — chama o mesmo endpoint POST
 */
export function CutActionPanel({ cut, onError, onNotationRequested }: Props) {
    const { t } = useLanguage();
    // Notações permitidas dependem do instrumento do corte (herdado da geração).
    const { score: podePartitura, tab: podeTablatura } = notationCapabilities(cut.instrument);

    const partituraPhase = toPhase(cut.partitura_status, !!cut.partitura_storage_key);
    const tablaturaPhase = toPhase(cut.tablatura_status, !!cut.tablatura_storage_key);

    // URLs presigned carregadas do R2 quando a fase transita para 'completed'
    const [partituraUrl, setPartituraUrl] = useState<string | null>(null);
    const [tablaturaUrl, setTablaturaUrl] = useState<string | null>(null);
    const [loadingPartUrl, setLoadingPartUrl] = useState(false);
    const [loadingTabUrl, setLoadingTabUrl] = useState(false);
    const [loadingAudio, setLoadingAudio] = useState(false);

    // Preview: Blob URL carregado on-demand para ouvir o corte antes de descarregar
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [loadingPreview, setLoadingPreview] = useState(false);

    // Limpar URLs ao mudar de corte
    useEffect(() => {
        setPartituraUrl(null);
        setTablaturaUrl(null);
        // Libertar o blob de preview do corte anterior
        setPreviewUrl(prev => {
            if (prev) URL.revokeObjectURL(prev);
            return null;
        });
    }, [cut.id]);

    // Garantir a libertação do blob ao desmontar
    useEffect(() => {
        return () => {
            if (previewUrl) URL.revokeObjectURL(previewUrl);
        };
    }, [previewUrl]);

    // Quando partitura transita para completed → buscar URL automaticamente
    useEffect(() => {
        if (partituraPhase !== 'completed' || partituraUrl || loadingPartUrl) return;
        let cancelled = false;
        setLoadingPartUrl(true);
        generationService.getPartituraUrl(cut.id)
            .then(url => { if (!cancelled) setPartituraUrl(url); })
            .catch(e => { if (!cancelled) onError(e?.detail ?? t.cutPanel.scoreError); })
            .finally(() => { if (!cancelled) setLoadingPartUrl(false); });
        return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [partituraPhase, cut.id]);

    // Quando tablatura transita para completed → buscar URL automaticamente
    useEffect(() => {
        if (tablaturaPhase !== 'completed' || tablaturaUrl || loadingTabUrl) return;
        let cancelled = false;
        setLoadingTabUrl(true);
        generationService.getTablatureUrl(cut.id)
            .then(url => { if (!cancelled) setTablaturaUrl(url); })
            .catch(e => { if (!cancelled) onError(e?.detail ?? t.cutPanel.tabError); })
            .finally(() => { if (!cancelled) setLoadingTabUrl(false); });
        return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tablaturaPhase, cut.id]);

    const handleRequestPartitura = async () => {
        // Limpar URL local para forçar re-fetch quando o worker concluir
        setPartituraUrl(null);
        try {
            await generationService.requestPartitura(cut.id);
            onNotationRequested?.();
        } catch (e: any) {
            onError(e?.detail ?? t.cutPanel.scoreError);
        }
    };

    const handleRequestTablature = async () => {
        setTablaturaUrl(null);
        try {
            await generationService.requestTablature(cut.id);
            onNotationRequested?.();
        } catch (e: any) {
            onError(e?.detail ?? t.cutPanel.tabError);
        }
    };

    const handleLoadPreview = async () => {
        if (previewUrl || loadingPreview) return;
        setLoadingPreview(true);
        try {
            const blobUrl = await generationService.fetchGenerationAudioBlobUrl(cut.id);
            setPreviewUrl(blobUrl);
        } catch (e: any) {
            onError(e?.detail ?? t.cutPanel.audioError);
        } finally {
            setLoadingPreview(false);
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

            {/* ---- Pré-escuta do corte ---- */}
            <div className="cut-action-preview">
                {previewUrl ? (
                    <audio controls src={previewUrl} className="cut-action-preview-el" />
                ) : (
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleLoadPreview}
                        disabled={loadingPreview}
                    >
                        {loadingPreview
                            ? <Spinner size="sm" label={t.cutPanel.loadingPreview} />
                            : <>{t.cutPanel.playPreview}</>}
                    </button>
                )}
            </div>

            <div className="cut-action-buttons">
                <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={handleDownloadAudio}
                    disabled={loadingAudio}
                >
                    {loadingAudio
                        ? <Spinner size="sm" label={t.cutPanel.preparing} />
                        : <>{t.cutPanel.downloadAudio}</>}
                </button>
            </div>

            {/* ---- Partitura (todos os instrumentos menos bateria) ---- */}
            {podePartitura && (
                <NotationSection
                    label={t.cutPanel.score}
                    generateLabel={t.cutPanel.generateScore}
                    downloadName={`partitura_${cut.id.slice(0, 8)}.pdf`}
                    phase={partituraPhase}
                    pdfUrl={partituraUrl}
                    loadingUrl={loadingPartUrl}
                    errorLabel={t.cutPanel.scoreError}
                    onGenerate={handleRequestPartitura}
                    retryLabel={t.cutPanel.retry}
                    regenerateLabel={t.cutPanel.regenerate}
                    downloadLabel={t.cutPanel.download}
                    generatingLabel={t.cutPanel.generating}
                />
            )}

            {/* ---- Tablatura (só guitarra) ---- */}
            {podeTablatura && (
                <NotationSection
                    label={t.cutPanel.tab}
                    generateLabel={t.cutPanel.generateTab}
                    downloadName={`tablatura_${cut.id.slice(0, 8)}.pdf`}
                    phase={tablaturaPhase}
                    pdfUrl={tablaturaUrl}
                    loadingUrl={loadingTabUrl}
                    errorLabel={t.cutPanel.tabError}
                    onGenerate={handleRequestTablature}
                    retryLabel={t.cutPanel.retry}
                    regenerateLabel={t.cutPanel.regenerate}
                    downloadLabel={t.cutPanel.download}
                    generatingLabel={t.cutPanel.generating}
                />
            )}

            {/* Instrumentos sem notação (ex.: bateria) — só download + pré-escuta */}
            {!podePartitura && !podeTablatura && (
                <p className="text-muted text-sm">{t.cutPanel.noNotation}</p>
            )}
        </div>
    );
}

// ---------------------------------------------------------------------------
// Sub-componente: encapsula o bloco visual de uma notação (partitura/tablatura)
// ---------------------------------------------------------------------------
interface NotationSectionProps {
    label: string;
    generateLabel: string;
    downloadName: string;
    phase: NotationPhase;
    pdfUrl: string | null;
    loadingUrl: boolean;
    errorLabel: string;
    onGenerate: () => void;
    retryLabel: string;
    regenerateLabel: string;
    downloadLabel: string;
    generatingLabel: string;
}

function NotationSection({
    label, generateLabel, downloadName,
    phase, pdfUrl, loadingUrl, errorLabel,
    onGenerate, retryLabel, regenerateLabel, downloadLabel, generatingLabel,
}: NotationSectionProps) {

    // Fase: ainda não pedido
    if (phase === 'idle') {
        return (
            <section className="cut-action-notation">
                <button type="button" className="btn" onClick={onGenerate}>
                    {generateLabel}
                </button>
            </section>
        );
    }

    // Fase: em processamento (pending ou processing)
    if (phase === 'pending' || phase === 'processing') {
        return (
            <section className="cut-action-notation">
                <Spinner size="sm" label={generatingLabel} />
                <span className="text-muted text-sm">{label}</span>
            </section>
        );
    }

    // Fase: falhou
    if (phase === 'failed') {
        return (
            <section className="cut-action-notation cut-action-notation--error">
                <span className="text-error text-sm">{errorLabel}</span>
                <button type="button" className="btn btn-sm" onClick={onGenerate}>
                    {retryLabel}
                </button>
            </section>
        );
    }

    // Fase: completed — PDF + Download + botão Regerar
    // O botão Regerar só aparece aqui (após primeira geração bem-sucedida)
    return (
        <section className="cut-action-pdf">
            <header className="cut-action-pdf-head">
                <strong>{label}</strong>
                <div className="cut-action-pdf-actions">
                    {pdfUrl && (
                        <a
                            href={pdfUrl}
                            download={downloadName}
                            className="btn btn-sm btn-ghost"
                        >
                            {downloadLabel}
                        </a>
                    )}
                    {/* Regerar — visível APENAS após primeira geração bem-sucedida */}
                    <button
                        type="button"
                        className="btn btn-sm btn-ghost"
                        onClick={onGenerate}
                        title={regenerateLabel}
                    >
                        {regenerateLabel}
                    </button>
                </div>
            </header>
            {loadingUrl && <Spinner size="sm" />}
            {pdfUrl && (
                <iframe src={pdfUrl} title={label} />
            )}
        </section>
    );
}

export default CutActionPanel;
