import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { audioService } from '../services/audio/audioService';
import { AudioAnalysisResponse } from '../services/audio/audioResponseTypes';
import { GenerationResult, isCut } from '../services/generation/generationResponseTypes';
import useAudioGenerations from '../hooks/generation/useAudioGenerations';
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
 * Layout em 2 colunas + painel direito multi-modo:
 *
 *   ┌───────────────────────────┬──────────────────────────────────┐
 *   │  Info do áudio + player   │  Painel direito (varia)          │
 *   │  Árvore de gerações       │   - nada selecionado: Gerar      │
 *   │   ▾ Geração #1            │   - geração: Wavesurfer + cortar │
 *   │     ✂ Corte A             │   - corte: Partitura/Tablatura   │
 *   │   ▾ Geração #2            │                                  │
 *   └───────────────────────────┴──────────────────────────────────┘
 *
 * O selectedId é o `generation_id` (string) — comum a gerações e cortes
 * porque ambos vivem na mesma tabela `generations`.
 */
function AudioDetailPage() {
    const { projectId, audioId } = useParams<{ projectId: string; audioId: string }>();
    const navigate = useNavigate();
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
                if (!cancelled) setError(e?.detail ?? 'Erro a carregar áudio.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [audioId]);

    // ----- procurar a geração/corte seleccionado na árvore ---------------
    const selected: GenerationResult | null = useMemo(() => {
        if (!selectedId) return null;
        for (const root of gens.tree) {
            if (root.generation_id === selectedId) return root;
            const c = root.cuts.find(x => x.generation_id === selectedId);
            if (c) return c;
        }
        return null;
    }, [selectedId, gens.tree]);

    // ----- handlers principais ------------------------------------------
    const handleSubmitGeneration = async (req: Parameters<typeof gens.submitGeneration>[0]) => {
        try {
            await gens.submitGeneration(req);
            toast.success('Pedido de geração submetido. A processar…');
        } catch (err) {
            toast.error(describeError(err, 'Erro a submeter geração.'));
        }
    };

    const handleCut = async (params: { inicio_segundos: number; fim_segundos: number }) => {
        if (!selected) return;
        try {
            const cut = await gens.cutGeneration(selected.generation_id, params);
            toast.success('Corte criado.');
            setSelectedId(cut.generation_id);
        } catch (err) {
            toast.error(describeError(err, 'Erro a cortar.'));
        }
    };

    const handleDelete = async () => {
        if (!audioId) return;
        setDeleting(true);
        try {
            await audioService.deleteAudio(audioId);
            toast.success('Áudio apagado.');
            navigate(`/projects/${projectId}`, { replace: true });
        } catch (err) {
            toast.error(describeError(err, 'Erro a apagar áudio.'));
            setDeleting(false);
            setConfirmDel(false);
        }
    };

    if (loading) return <Spinner block label="A carregar áudio…" />;
    if (error) return <p className="error-text">{error}</p>;
    if (!audio || !projectId || !audioId) return null;

    return (
        <div className="audio-detail-v2">
            <PageHeader
                title={basename(audio.file_path)}
                description={`${fmtDuration(audio.duration)} · ${audio.sample_rate} Hz`}
                backTo={`/projects/${projectId}`}
                backLabel="Projeto"
                actions={
                    <button
                        type="button"
                        className="btn btn-danger-ghost"
                        onClick={() => setConfirmDel(true)}
                    >
                        Apagar áudio
                    </button>
                }
            />

            <div className="audio-workspace">
                {/* ---------------- ESQUERDA ---------------- */}
                <aside className="audio-workspace-left">
                    <section className="card audio-meta-card">
                        <h3>Áudio original</h3>
                        <dl className="audio-meta-dl">
                            <dt>Duração</dt>
                            <dd>{audio.duration.toFixed(2)} s</dd>
                            <dt>Sample rate</dt>
                            <dd>{audio.sample_rate} Hz</dd>
                            <dt>BPM</dt>
                            <dd>{audio.bpm ?? '—'}</dd>
                            <dt>Tom</dt>
                            <dd>{audio.key ?? '—'}</dd>
                            <dt>Compasso</dt>
                            <dd>{audio.time_signature ?? '—'}</dd>
                        </dl>
                        <AudioPlayer audioId={audio.id} fileName={basename(audio.file_path)} />
                    </section>

                    <section className="card audio-tree-card">
                        <header className="section-title">
                            <h3>Gerações</h3>
                            {gens.loading ? <Spinner size="sm" /> : null}
                        </header>
                        {gens.error ? <p className="error-text">{gens.error}</p> : null}
                        <GenerationTree
                            tree={gens.tree}
                            selectedId={selectedId}
                            onSelect={g => setSelectedId(g.generation_id)}
                        />
                        {selectedId ? (
                            <button
                                type="button"
                                className="btn btn-ghost btn-sm audio-tree-clear"
                                onClick={() => setSelectedId(null)}
                            >
                                ← Limpar seleção
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
                title="Apagar áudio?"
                message="O ficheiro será removido do disco e da base de dados, junto com todas as gerações e cortes associados."
                confirmLabel="Apagar"
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmDel(false)}
            />
        </div>
    );
}

export default AudioDetailPage;
