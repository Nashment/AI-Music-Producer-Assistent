import { useState } from 'react';
import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';

interface Props {
    audio: AudioAnalysisResponse;
    onAdjustBpm: (targetBpm: number) => Promise<unknown>;
    onCut: (params: { inicio_segundos: number; fim_segundos: number }) => Promise<unknown>;
    onSeparateTracks: (params: { instrument: string }) => Promise<string>;
}

type AudioInstrument = 'guitarra' | 'piano' | 'bateria' | 'baixo' | 'voz';

const INSTRUMENTS: AudioInstrument[] = [
    'guitarra',
    'piano',
    'bateria',
    'baixo',
    'voz',
];

/**
 * Painel com as 3 operacoes do dominio de audio:
 *   - Ajustar BPM (POST /audio/{id}/adjust-bpm?target_bpm=)
 *   - Cortar (POST /audio/{id}/cut?inicio_segundos=&fim_segundos=)
 *   - Separar instrumentos (POST /audio/{id}/separate-tracks?instrument=)
 *
 * Cada operacao tem um pequeno form proprio. As accoes sao tratadas pelo
 * caller — este componente so se preocupa com inputs/feedback.
 */
export function AudioToolsPanel({ audio, onAdjustBpm, onCut, onSeparateTracks }: Props) {
    const [targetBpm, setTargetBpm] = useState<number>(audio.bpm ?? 120);
    const [bpmBusy, setBpmBusy] = useState(false);

    const [cutStart, setCutStart] = useState(0);
    const [cutEnd, setCutEnd] = useState(Math.min(30, audio.duration));
    const [cutBusy, setCutBusy] = useState(false);

    const [instr, setInstr] = useState<AudioInstrument>('guitarra');
    const [sepBusy, setSepBusy] = useState(false);
    const [sepUrl, setSepUrl] = useState<string | null>(null);

    const handleBpm = async (e: React.FormEvent) => {
        e.preventDefault();
        if (targetBpm < 30 || targetBpm > 260) return;
        setBpmBusy(true);
        try {
            await onAdjustBpm(targetBpm);
        } finally {
            setBpmBusy(false);
        }
    };

    const handleCut = async (e: React.FormEvent) => {
        e.preventDefault();
        if (cutStart < 0 || cutEnd <= cutStart) return;
        setCutBusy(true);
        try {
            await onCut({ inicio_segundos: cutStart, fim_segundos: cutEnd });
        } finally {
            setCutBusy(false);
        }
    };

    const handleSeparate = async (e: React.FormEvent) => {
        e.preventDefault();
        setSepBusy(true);
        setSepUrl(null);
        try {
            const url = await onSeparateTracks({ instrument: instr });
            setSepUrl(url);
        } finally {
            setSepBusy(false);
        }
    };

    return (
        <div className="audio-tools">
            {/* BPM */}
            <section className="audio-tool card">
                <header>
                    <h3>Ajustar BPM</h3>
                    <p className="text-muted text-sm">
                        Estica/comprime o áudio para o tempo desejado.
                    </p>
                </header>
                <form onSubmit={handleBpm} className="audio-tool-form">
                    <div className="field">
                        <label htmlFor="target-bpm">BPM alvo</label>
                        <input
                            id="target-bpm"
                            type="number"
                            min={30}
                            max={260}
                            value={targetBpm}
                            onChange={e => setTargetBpm(Number(e.target.value))}
                        />
                        <span className="field-hint">
                            Atual: {audio.bpm ? `${audio.bpm} BPM` : 'n/d'}
                        </span>
                    </div>
                    <button type="submit" disabled={bpmBusy}>
                        {bpmBusy ? 'A processar…' : 'Aplicar'}
                    </button>
                </form>
            </section>

            {/* Cut */}
            <section className="audio-tool card">
                <header>
                    <h3>Cortar excerto</h3>
                    <p className="text-muted text-sm">
                        Extrai um intervalo do áudio (em segundos).
                    </p>
                </header>
                <form onSubmit={handleCut} className="audio-tool-form">
                    <div className="audio-tool-row">
                        <div className="field">
                            <label htmlFor="cut-start">Início (s)</label>
                            <input
                                id="cut-start"
                                type="number"
                                min={0}
                                step="0.1"
                                value={cutStart}
                                onChange={e => setCutStart(Number(e.target.value))}
                            />
                        </div>
                        <div className="field">
                            <label htmlFor="cut-end">Fim (s)</label>
                            <input
                                id="cut-end"
                                type="number"
                                min={0}
                                step="0.1"
                                value={cutEnd}
                                onChange={e => setCutEnd(Number(e.target.value))}
                            />
                        </div>
                    </div>
                    <span className="field-hint">
                        Duração total: {audio.duration.toFixed(1)} s
                    </span>
                    <button type="submit" disabled={cutBusy}>
                        {cutBusy ? 'A processar…' : 'Cortar'}
                    </button>
                </form>
            </section>

            {/* Separate */}
            <section className="audio-tool card">
                <header>
                    <h3>Separar instrumento</h3>
                    <p className="text-muted text-sm">
                        Isola uma faixa do mix (a operação devolve um WAV).
                    </p>
                </header>
                <form onSubmit={handleSeparate} className="audio-tool-form">
                    <div className="field">
                        <label htmlFor="separate-instr">Instrumento</label>
                        <select
                            id="separate-instr"
                            value={instr}
                            onChange={e => setInstr(e.target.value as AudioInstrument)}
                        >
                            {INSTRUMENTS.map(i => (
                                <option key={i} value={i}>
                                    {i}
                                </option>
                            ))}
                        </select>
                    </div>
                    <button type="submit" disabled={sepBusy}>
                        {sepBusy ? 'A processar…' : 'Separar'}
                    </button>

                    {sepUrl ? (
                        <div className="audio-tool-result">
                            <audio controls src={sepUrl} />
                            <a
                                href={sepUrl}
                                download={`${instr}.wav`}
                                className="btn btn-secondary btn-sm"
                            >
                                ⬇ Download {instr}.wav
                            </a>
                        </div>
                    ) : null}
                </form>
            </section>
        </div>
    );
}

export type { AudioInstrument };
export const ALL_AUDIO_INSTRUMENTS: AudioInstrument[] = INSTRUMENTS;

export default AudioToolsPanel;
