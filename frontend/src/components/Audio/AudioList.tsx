import { AudioAnalysisResponse } from '../../services/audio/audioResponseTypes';
import AudioCard from './AudioCard';

interface Props {
    projectId: string;
    audios: AudioAnalysisResponse[];
    onDelete?: (id: string) => void;
    onRename?: (id: string, name: string) => Promise<unknown>;
}

export function AudioList({ projectId, audios, onDelete, onRename }: Props) {
    return (
        <div className="audio-list">
            {audios.map(a => (
                <AudioCard
                    key={a.id}
                    projectId={projectId}
                    audio={a}
                    onDelete={onDelete}
                    onRename={onRename}
                />
            ))}
        </div>
    );
}

export default AudioList;
