import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';
import AudioCard from './AudioCard';

interface Props {
    projectId: string;
    audios: AudioAnalysisResponse[];
    onDelete?: (id: string) => void;
}

export function AudioList({ projectId, audios, onDelete }: Props) {
    return (
        <div className="audio-list">
            {audios.map(a => (
                <AudioCard
                    key={a.id}
                    projectId={projectId}
                    audio={a}
                    onDelete={onDelete}
                />
            ))}
        </div>
    );
}

export default AudioList;
