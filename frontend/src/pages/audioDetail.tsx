import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { audioService } from '../services/audio/audioService';
import { AudioAnalysisResponse } from '../services/audio/audioResponseTypes';
import { GenerationResult, isCut } from '../services/generation/generationResponseTypes';
import useAudioGenerations from '../hooks/generation/useAudioGenerations';
import useLanguage from '../hooks/language/useLanguage';
import AudioPlayer from '../components/Audio/AudioPlayer';
import GenerateMusicPanel from '../components/Generation/GenerateMusicPanel';
import WaveformCutter from '../components/Generation/WaveformCutter';
import CutActionPanel from '../components/Generation/CutActionPanel';
import GenerationTree from '../components/Generation/GenerationTree';
import PageHeader from '../components/Layout/PageHeader';
import Spinner from '../components/Layout/Spinner';
import ConfirmDialog from '../components/Layout/ConfirmDialog';
import { useToast, describeError } from '../components/Layout/Toast';

function basename(p: string): string {
    return p.split(/[\\/]/).pop() ?? 'audio';
}
function fmtDuration(s: number): string {
    if (!Number.isFinite(s)) return '—';
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

/**
 * /projects/:projectId/audio/:audioId
 *
 * Layout em 2 colunas + painel direito multi-modo.
 */
function AudioDetailPage() {
    const { projectId, audioId } = useParams<{ projectId: string; audioId: string }>();
    const navigate = useNavigate();
    const { t } = useLanguage();
    const toast = useToast();

    // ----- estado: áudio (original) ------------------------------------
    const [audio, setAudio] = useState<AudioAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [confirmDel, setConfirmDel] = useState(false);
    const [deleting, setDeleting] = useState(false);

    // ----- estado: gerações + cortes -----------------------------------
    const gens = useAudioGenerations(audioId);
    const [selectedId, setSelectedId] = useState<string | null>(null);

    // ----- carregar metadados do áudio ----------------------------------
    useEffect(() => {
        if (!audioId) return;
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const data = await audioService.getAudioAnalysis(audioId);
                if (!cancelled) setAudio(data);
            } catch (e: any) {
                if (!cancelled) setError(e?.detail ?? t.audioDetail.loadError);
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [audioId, t]);

    // ----- procurar a geração/corte seleccionado na árvore ---------------
    const selected: GenerationResult | null = useMemo(() => {
        if (!selectedId) return null;
        for (const root of gens.tree) {
            if (root.id === selectedId) return root;
            const c = root.cuts.find(x => x.id === selectedId);
            if (c) return c;
        }
        return null;
    }, [selectedId, gens.tree]);

    // ----- handlers principais ------------------------------------------
    const handleSubmitGeneration = async (req: Parameters<typeof gens.submitGeneration>[0]) => {
        try {
            await gens.submitGeneration(req);
            toast.success(t.audioDetail.generationSubmitted);
        } catch (err) {
            toast.error(describeError(err, t.audioDetail.generationError));
        }
    };

    const handleCut = async (params: { inicio_segundos: number; fim_segundos: number }) => {
        if (!selected) return;
        try {
            const cut = await gens.cutGeneration(selected.id, params);
            toast.success(t.audioDetail.cutCreated);
            setSelectedId(cut.id);
        } catch (err) {
            toast.error(describeError(err, t.audioDetail.cutError));
        }
    };

    const handleDelete = async () => {
        if (!audioId) return;
        setDeleting(true);
        try {
            await audioService.deleteAudio(audioId);
            toast.success(t.audioDetail.audioDeleted);
            navigate(`/projects/${projectId}`, { replace: true });
        } catch (err) {
            toast.error(describeError(err, t.audioDetail.audioDeleteError));
            setDeleting(false);
            setConfirmDel(false);
        }
    };

    if (loading) return <Spinner block label={t.audioDetail.loading} />;
    if (error) return <p className="error-text">{error}</p>;
    if (!audio || !projectId || !audioId) return null;

    return (
        <div className="audio-detail-v2">
            <PageHeader
                title={basename(audio.storage_key)}
                description={`${fmtDuration(audio.duration)} · ${audio.sample_rate} Hz`}
                backTo={`/projects/${projectId}`}
                backLabel={t.audioDetail.back}
                actions={
                    <button
                        type="button"
                        className="btn btn-danger-ghost"
                        onClick={() => setConfirmDel(true)}
                    >
                        {t.audioDetail.deleteAudio}
                    </button>
                }
            />

            <div className="audio-workspace">
                {/* ---------------- ESQUERDA ---------------- */}
                <aside className="audio-workspace-left">
                    <section className="card audio-meta-card">
                        <h3>{t.audioDetail.originalAudio}</h3>
                        <dl className="audio-meta-dl">
                            <dt>{t.audioDetail.duration}</dt>
                            <dd>{audio.duration.toFixed(2)} s</dd>
                            <dt>{t.audioDetail.sampleRate}</dt>
                            <dd>{audio.sample_rate} Hz</dd>
                            <dt>{t.audioDetail.bpm}</dt>
                            <dd>{audio.bpm ?? '—'}</dd>
                            <dt>{t.audioDetail.key}</dt>
                            <dd>{audio.key ?? '—'}</dd>
                            <dt>{t.audioDetail.timeSignature}</dt>
                            <dd>{audio.time_signature ?? '—'}</dd>
                        </dl>
                        <AudioPlayer audioId={audio.id} fileName={basename(audio.storage_key)} />
                    </section>

                    <section className="card audio-tree-card">
                        <header className="section-title">
                            <h3>{t.audioDetail.generations}</h3>
                            {gens.loading ? <Spinner size="sm" /> : null}
                        </header>
                        {gens.error ? <p className="error-text">{gens.error}</p> : null}
                        <GenerationTree
                            tree={gens.tree}
                            selectedId={selectedId}
                            onSelect={g => setSelectedId(g.id)}
                        />
                        {selectedId ? (
                            <button
                                type="button"
                                className="btn btn-ghost btn-sm audio-tree-clear"
                                onClick={() => setSelectedId(null)}
                            >
                                {t.audioDetail.clearSelection}
                            </button>
                        ) : null}
                    </section>
                </aside>

                {/* ---------------- DIREITA ---------------- */}
                <section className="audio-workspace-right">
                    {selected === null ? (
                        <div className="card">
                            <GenerateMusicPanel
                                projectId={projectId}
                                audioId={audioId}
                                submitting={gens.submitting}
                                onSubmit={handleSubmitGeneration}
                            />
                        </div>
                    ) : isCut(selected) ? (
                        <div className="card">
                            <CutActionPanel
                                cut={selected}
                                onError={msg => toast.error(msg)}
                            />
                        </div>
                    ) : (
                        <div className="card">
                            <WaveformCutter
                                generation={selected}
                                cutting={gens.cutting}
                                onCut={handleCut}
                            />
                        </div>
                    )}
                </section>
            </div>

            <ConfirmDialog
                open={confirmDel}
                title={t.audioDetail.confirmDeleteTitle}
                message={t.audioDetail.confirmDeleteMsg}
                confirmLabel={t.audioDetail.confirmDeleteLabel}
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmDel(false)}
            />
        </div>
    );
}

export default AudioDetailPage;
