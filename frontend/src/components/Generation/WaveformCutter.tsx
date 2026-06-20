import { useCallback, useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin, { Region } from 'wavesurfer.js/dist/plugins/regions.esm.js';
import { generationService } from '../../services/generation/generationService';
import { GenerationResult } from '../../services/generation/generationResponseTypes';
import useLanguage from '../../hooks/language/useLanguage';
import Spinner from '../Layout/Spinner';

interface Props {
    generation: GenerationResult;
    cutting: boolean;
    onCut: (params: { inicio_segundos: number; fim_segundos: number }) => Promise<unknown>;
}

const MAX_WINDOW = 45; // segundos — limite imposto pelo backend

function fmtTime(s: number): string {
    const m = Math.floor(s / 60);
    const sec = (s % 60).toFixed(2);
    return `${m}:${sec.padStart(5, '0')}`;
}

function clamp(v: number, lo: number, hi: number) {
    return Math.min(Math.max(v, lo), hi);
}

/**
 * Visualizador estilo Audacity com Wavesurfer.js v7.
 */
export function WaveformCutter({ generation, cutting, onCut }: Props) {
    const { t } = useLanguage();
    const containerRef = useRef<HTMLDivElement | null>(null);
    const wsRef = useRef<WaveSurfer | null>(null);
    const regionsRef = useRef<ReturnType<typeof RegionsPlugin.create> | null>(null);
    const regionRef = useRef<Region | null>(null);
    const blobUrlRef = useRef<string | null>(null);

    const [duration, setDuration] = useState(0);
    const [start, setStart] = useState(0);
    const [end, setEnd] = useState(0);
    const [playing, setPlaying] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const syncRegionToValues = useCallback((s: number, e: number) => {
        const r = regionRef.current;
        if (!r) return;
        r.setOptions({ start: s, end: e });
    }, []);

    const enforceLimits = useCallback(
        (s: number, e: number, anchor: 'start' | 'end' = 'end'): [number, number] => {
            let ns = clamp(s, 0, duration);
            let ne = clamp(e, 0, duration);
            if (ne <= ns) ne = Math.min(duration, ns + 0.05);
            if (ne - ns > MAX_WINDOW) {
                if (anchor === 'end') ns = ne - MAX_WINDOW;
                else ne = ns + MAX_WINDOW;
            }
            ns = clamp(ns, 0, duration);
            ne = clamp(ne, 0, duration);
            return [ns, ne];
        },
        [duration],
    );

    useEffect(() => {
        if (!containerRef.current) return;
        let cancelled = false;

        setLoading(true);
        setError(null);
        setStart(0);
        setEnd(0);
        setDuration(0);

        const regionsPlugin = RegionsPlugin.create();
        const ws = WaveSurfer.create({
            container: containerRef.current,
            waveColor: 'rgba(124, 92, 255, 0.45)',
            progressColor: 'rgba(124, 92, 255, 0.95)',
            cursorColor: '#fff',
            cursorWidth: 1,
            height: 120,
            barWidth: 2,
            barGap: 1,
            barRadius: 2,
            normalize: true,
            plugins: [regionsPlugin],
        });
        wsRef.current = ws;
        regionsRef.current = regionsPlugin;

        (async () => {
            try {
                const url = await generationService.fetchGenerationAudioBlobUrl(generation.id);
                if (cancelled) {
                    URL.revokeObjectURL(url);
                    return;
                }
                blobUrlRef.current = url;
                await ws.load(url);
            } catch (e: any) {
                if (!cancelled) setError(e?.message ?? t.waveform.loadError);
                setLoading(false);
            }
        })();

        ws.on('ready', () => {
            if (cancelled) return;
            const dur = ws.getDuration();
            setDuration(dur);
            const s = 0;
            const e = Math.min(MAX_WINDOW, dur);
            setStart(s);
            setEnd(e);

            regionRef.current = regionsPlugin.addRegion({
                start: s,
                end: e,
                color: 'rgba(67, 211, 192, 0.18)',
                drag: true,
                resize: true,
            });
            setLoading(false);
        });

        ws.on('play', () => setPlaying(true));
        ws.on('pause', () => setPlaying(false));
        ws.on('finish', () => setPlaying(false));

        regionsPlugin.on('region-updated', (r: Region) => {
            const dur = ws.getDuration() || 1;
            let ns = clamp(r.start, 0, dur);
            let ne = clamp(r.end, 0, dur);
            if (ne <= ns) ne = Math.min(dur, ns + 0.05);
            if (ne - ns > MAX_WINDOW) {
                ns = ne - MAX_WINDOW;
            }
            ns = clamp(ns, 0, dur);
            ne = clamp(ne, 0, dur);
            if (ns !== r.start || ne !== r.end) {
                r.setOptions({ start: ns, end: ne });
            }
            setStart(ns);
            setEnd(ne);
        });

        return () => {
            cancelled = true;
            try {
                ws.destroy();
            } catch {
                /* noop */
            }
            wsRef.current = null;
            regionsRef.current = null;
            regionRef.current = null;
            if (blobUrlRef.current) {
                URL.revokeObjectURL(blobUrlRef.current);
                blobUrlRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [generation.id]);

    const handleDownload = () => {
        const url = blobUrlRef.current;
        if (!url) return;
        const a = document.createElement('a');
        a.href = url;
        a.download = `geracao_${generation.id.slice(0, 8)}.wav`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    const togglePlay = () => {
        const ws = wsRef.current;
        if (!ws) return;
        if (playing) ws.pause();
        else {
            const r = regionRef.current;
            if (r) ws.setTime(r.start);
            ws.play();
        }
    };

    const handleStart = (val: number) => {
        const [s, e] = enforceLimits(val, end, 'start');
        setStart(s);
        setEnd(e);
        syncRegionToValues(s, e);
    };

    const handleEnd = (val: number) => {
        const [s, e] = enforceLimits(start, val, 'end');
        setStart(s);
        setEnd(e);
        syncRegionToValues(s, e);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (cutting || end <= start) return;
        await onCut({ inicio_segundos: Number(start.toFixed(3)), fim_segundos: Number(end.toFixed(3)) });
    };

    const window = Math.max(0, end - start);
    const exceeds = window > MAX_WINDOW + 0.001;

    return (
        <div className="waveform-cutter">
            <header>
                <h3>{t.waveform.title}</h3>
                <p className="text-muted text-sm">
                    {t.waveform.desc} <strong>{MAX_WINDOW}s</strong>.
                </p>
            </header>

            <div className="waveform-container" ref={containerRef} />

            {loading ? (
                <div className="waveform-loading">
                    <Spinner size="sm" label={t.waveform.loadingWaveform} />
                </div>
            ) : null}

            {error ? <p className="error-text">{error}</p> : null}

            {!loading && !error ? (
                <>
                    <div className="waveform-controls">
                        <button type="button" className="btn btn-secondary" onClick={togglePlay}>
                            {playing ? t.waveform.pause : t.waveform.play}
                        </button>
                        <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={handleDownload}
                        >
                            {t.waveform.download}
                        </button>
                        <span className="text-muted text-sm">
                            {t.waveform.totalDuration} {fmtTime(duration)} · {t.waveform.currentWindow}{' '}
                            <strong className={exceeds ? 'error-text' : ''}>{fmtTime(window)}</strong>
                        </span>
                    </div>

                    <form onSubmit={handleSubmit} className="waveform-form">
                        <div className="waveform-sliders">
                            <div className="field">
                                <label htmlFor="cut-start">
                                    {t.waveform.startLabel} — <span className="text-mono">{fmtTime(start)}</span>
                                </label>
                                <input
                                    id="cut-start"
                                    type="range"
                                    min={0}
                                    max={Math.max(0, duration - 0.05)}
                                    step={0.05}
                                    value={start}
                                    onChange={e => handleStart(Number(e.target.value))}
                                />
                            </div>
                            <div className="field">
                                <label htmlFor="cut-end">
                                    {t.waveform.endLabel} — <span className="text-mono">{fmtTime(end)}</span>
                                </label>
                                <input
                                    id="cut-end"
                                    type="range"
                                    min={0.05}
                                    max={duration}
                                    step={0.05}
                                    value={end}
                                    onChange={e => handleEnd(Number(e.target.value))}
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-block"
                            disabled={cutting || end <= start || exceeds}
                        >
                            {cutting ? t.waveform.cutting : t.waveform.cut}
                        </button>
                    </form>
                </>
            ) : null}
        </div>
    );
}

export default WaveformCutter;
