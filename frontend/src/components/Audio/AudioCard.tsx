import { Link } from 'react-router-dom';
import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';
import useLanguage from '../../hooks/language/useLanguage';
import { audioDisplayName } from '../../utils/common';
import InlineRename from '../Layout/InlineRename';

interface Props {
    projectId: string;
    audio: AudioAnalysisResponse;
    onDelete?: (id: string) => void;
    /** Renomeia o áudio. Quando omitido, o lápis não aparece. */
    onRename?: (id: string, name: string) => Promise<unknown>;
}

function formatDuration(s: number): string {
    if (!Number.isFinite(s)) return '—';
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
}

export function AudioCard({ projectId, audio, onDelete, onRename }: Props) {
    const { t } = useLanguage();
    const name = audioDisplayName(audio);

    return (
        <article className="audio-card">
            <header className="audio-card-head">
                <span className="audio-card-icon">🎵</span>
                {onRename ? (
                    <InlineRename
                        as="h4"
                        value={name}
                        onRename={n => onRename(audio.id, n)}
                    />
                ) : (
                    <h4 title={name}>{name}</h4>
                )}
            </header>
            <Link
                to={`/projects/${projectId}/audio/${audio.id}`}
                className="audio-card-link"
            >
                <ul className="audio-card-meta">
                    <li>{formatDuration(audio.duration)}</li>
                    <li>{audio.sample_rate} Hz</li>
                    {audio.bpm ? <li>{audio.bpm} BPM</li> : null}
                    {audio.key ? <li>{t.audioCard.key} {audio.key}</li> : null}
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
                    {t.audioCard.delete}
                </button>
            ) : null}
        </article>
    );
}

export default AudioCard;
