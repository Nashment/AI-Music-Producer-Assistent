import { useState } from 'react';
import {
    GenerationRequest,
    InstrumentType,
} from '../../services/generation/generationResponseTypes';

interface Props {
    projectId: string;
    audioId: string;
    submitting: boolean;
    onSubmit: (req: GenerationRequest) => Promise<unknown>;
}

// Os instrumentos suportados pela aplicação. "voz" foi removido
// intencionalmente — esta app é apenas para instrumentos.
const INSTRUMENTS: InstrumentType[] = ['guitarra', 'piano', 'bateria', 'baixo', 'outros'];

/**
 * Painel direito (modo "default" da página de áudio): submete um pedido
 * de geração de música pela IA usando o áudio original como semente.
 *
 * Restrições:
 *   - O botão "Gerar Música" só está activo se prompt e instrumento
 *     estiverem preenchidos.
 *   - Não usa o endpoint de cover — chama o endpoint normal POST /generation.
 */
export function GenerateMusicPanel({ projectId, audioId, submitting, onSubmit }: Props) {
    const [prompt, setPrompt] = useState('');
    const [instrument, setInstrument] = useState<InstrumentType | ''>('');

    const canSubmit = prompt.trim().length > 0 && instrument !== '';

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canSubmit) return;
        await onSubmit({
            project_id: projectId,
            audio_id: audioId,
            prompt: prompt.trim(),
            instrument: instrument as InstrumentType,
        });
        setPrompt('');
    };

    return (
        <div className="generate-panel">
            <header>
                <h3>Gerar nova música</h3>
                <p className="text-muted text-sm">
                    Descreve o que queres ouvir e escolhe o instrumento. A IA
                    usa este áudio original como referência.
                </p>
            </header>

            <form onSubmit={handleSubmit} className="generate-panel-form">
                <div className="field">
                    <label htmlFor="gen-prompt">Prompt</label>
                    <textarea
                        id="gen-prompt"
                        value={prompt}
                        onChange={e => setPrompt(e.target.value)}
                        rows={4}
                        placeholder="Ex: solo melódico em estilo blues, lento e expressivo"
                    />
                </div>

                <div className="field">
                    <label htmlFor="gen-instrument">Instrumento</label>
                    <select
                        id="gen-instrument"
                        value={instrument}
                        onChange={e => setInstrument(e.target.value as InstrumentType | '')}
                    >
                        <option value="" disabled>
                            — escolhe um instrumento —
                        </option>
                        {INSTRUMENTS.map(i => (
                            <option key={i} value={i}>
                                {i}
                            </option>
                        ))}
                    </select>
                </div>

                <button type="submit" disabled={!canSubmit || submitting} className="btn btn-block">
                    {submitting ? 'A submeter…' : '🎶 Gerar música'}
                </button>
            </form>
        </div>
    );
}

export default GenerateMusicPanel;
