import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';

interface Props {
    audio: AudioAnalysisResponse;
    blobUrl?: string | null;
}

/**
 * Painel de detalhe de um audio — metadados de analise + player.
 */
export function AudioDetails({ audio, blobUrl }: Props) {
    return (
        <div className="audio-details">
            <h2>{audio.file_path.split(/[\\/]/).pop() ?? 'audio'}</h2>

            <dl className="audio-details-meta">
                <dt>Duracao</dt>
                <dd>{audio.duration.toFixed(2)}s</dd>

                <dt>Sample rate</dt>
                <dd>{audio.sample_rate} Hz</dd>

                <dt>BPM</dt>
                <dd>{audio.bpm ?? 'n/d'}</dd>

                <dt>Tonalidade</dt>
                <dd>{audio.key ?? 'n/d'}</dd>

                <dt>Compasso</dt>
                <dd>{audio.time_signature ?? 'n/d'}</dd>
            </dl>

            {blobUrl ? (
                <audio controls src={blobUrl} className="audio-details-player" />
            ) : (
                <div className="audio-details-player-empty">
                    Player desligado (carregar para reproduzir).
                </div>
            )}
        </div>
    );
}

export default AudioDetails;
