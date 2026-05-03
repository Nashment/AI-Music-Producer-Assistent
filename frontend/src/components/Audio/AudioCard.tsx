import { Link } from 'react-router-dom';
import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';

interface Props {
    projectId: string;
    audio: AudioAnalysisResponse;
    onDelete?: (id: string) => void;
}

function basename(p: string): string {
    return p.split(/[\\/]/).pop() ?? 'audio';
}

function formatDuration(s: number): string {
    if (!Number.isFinite(s)) return '—';
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

export function AudioCard({ projectId, audio, onDelete }: Props) {
    return (
        <article className="audio-card">
            <Link
                to={`/projects/${projectId}/audio/${audio.id}`}
                className="audio-card-link"
            >
                <header className="audio-card-head">
                    <span className="audio-card-icon">🎵</span>
                    <h4 title={basename(audio.file_path)}>
                        {basename(audio.file_path)}
                    </h4>
                </header>
                <ul className="audio-card-meta">
                    <li>{formatDuration(audio.duration)}</li>
                    <li>{audio.sample_rate} Hz</li>
                    {audio.bpm ? <li>{audio.bpm} BPM</li> : null}
                    {audio.key ? <li>tom {audio.key}</li> : null}
                </ul>
            </Link>
            {onDelete ? (
                <button
                    type="button"
                    className="btn btn-danger-ghost btn-sm audio-card-delete"
                    onClick={e => {
                        e.preventDefault();
                        onDelete(audio.id);
                    }}
                >
                    Apagar
                </button>
            ) : null}
        </article>
    );
}

export default AudioCard;
