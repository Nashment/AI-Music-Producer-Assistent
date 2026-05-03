import { useState } from 'react';
import {
    GenerationRequest,
    InstrumentType,
    MusicGenreType,
} from '../../services/generation/generationResponseTypes';

interface Props {
    projectId: string;
    audioId: string;
    submitting: boolean;
    onSubmit: (req: GenerationRequest) => Promise<unknown>;
}

const INSTRUMENTS: InstrumentType[] = ['piano', 'guitarra', 'bateria', 'baixo', 'outros'];
const GENRES: MusicGenreType[] = ['classical', 'jazz', 'rock', 'pop', 'ambient'];

/**
 * Formulario para submeter um pedido de geracao a partir de um audio.
 * Reflecte o GenerationRequest em backend/app/domain/dtos/endpoints/generation.py.
 */
export function GenerationForm({ projectId, audioId, submitting, onSubmit }: Props) {
    const [prompt, setPrompt] = useState('');
    const [instrument, setInstrument] = useState<InstrumentType>('guitarra');
    const [genre, setGenre] = useState<MusicGenreType | ''>('');
    const [duration, setDuration] = useState<number | ''>('');
    const [tempoOverride, setTempoOverride] = useState<number | ''>('');
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!prompt.trim()) {
            setError('O prompt nao pode estar vazio.');
            return;
        }
        try {
            await onSubmit({
                project_id: projectId,
                audio_id: audioId,
                prompt: prompt.trim(),
                instrument,
                genre: genre || undefined,
                duration: duration === '' ? undefined : Number(duration),
                tempo_override: tempoOverride === '' ? undefined : Number(tempoOverride),
            });
        } catch (err: any) {
            setError(err?.detail ?? 'Erro a submeter.');
        }
    };

    return (
        <form className="generation-form" onSubmit={handleSubmit}>
            <label>
                Prompt
                <textarea
                    value={prompt}
                    onChange={e => setPrompt(e.target.value)}
                    rows={3}
                />
            </label>

            <label>
                Instrumento
                <select
                    value={instrument}
                    onChange={e => setInstrument(e.target.value as InstrumentType)}
                >
                    {INSTRUMENTS.map(i => (
                        <option key={i} value={i}>
                            {i}
                        </option>
                    ))}
                </select>
            </label>

            <label>
                Genero (opcional)
                <select
                    value={genre}
                    onChange={e => setGenre(e.target.value as MusicGenreType | '')}
                >
                    <option value="">— sem genero —</option>
                    {GENRES.map(g => (
                        <option key={g} value={g}>
                            {g}
                        </option>
                    ))}
                </select>
            </label>

            <label>
                Duracao (segundos, opcional)
                <input
                    type="number"
                    min={0}
                    value={duration}
                    onChange={e =>
                        setDuration(e.target.value === '' ? '' : Number(e.target.value))
                    }
                />
            </label>

            <label>
                Tempo override (BPM, opcional)
                <input
                    type="number"
                    min={0}
                    value={tempoOverride}
                    onChange={e =>
                        setTempoOverride(e.target.value === '' ? '' : Number(e.target.value))
                    }
                />
            </label>

            <button type="submit" disabled={submitting}>
                {submitting ? 'A submeter…' : 'Submeter geracao'}
            </button>

            {error ? <p className="error-text">{error}</p> : null}
        </form>
    );
}

export default GenerationForm;
