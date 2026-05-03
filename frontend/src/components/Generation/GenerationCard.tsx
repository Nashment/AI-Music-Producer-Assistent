import { GenerationResult } from '../../services/generation/generationResponseTypes';

interface Props {
    generation: GenerationResult;
    onDelete?: (id: string) => void;
}

/**
 * Cartao de uma geracao na lista de detalhes do audio. Mostra estado e
 * links/info disponiveis.
 */
export function GenerationCard({ generation, onDelete }: Props) {
    return (
        <div className={`generation-card status-${generation.status}`}>
            <header className="generation-card-header">
                <span className="generation-card-id">
                    {generation.generation_id.slice(0, 8)}…
                </span>
                <span className="generation-card-status">{generation.status}</span>
            </header>

            <ul className="generation-card-files">
                {generation.audio_file_path ? <li>audio: {generation.audio_file_path}</li> : null}
                {generation.midi_file_path ? <li>midi: {generation.midi_file_path}</li> : null}
                {generation.partitura_file_path ? <li>partitura: {generation.partitura_file_path}</li> : null}
                {generation.tablatura_file_path ? <li>tablatura: {generation.tablatura_file_path}</li> : null}
            </ul>

            {generation.error_message ? (
                <p className="generation-card-error">{generation.error_message}</p>
            ) : null}

            {onDelete ? (
                <button
                    type="button"
                    className="generation-card-delete"
                    onClick={() => onDelete(generation.generation_id)}
                >
                    Apagar
                </button>
            ) : null}
        </div>
    );
}

export default GenerationCard;
