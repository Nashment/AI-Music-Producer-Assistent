import { GenerationResult } from '../../services/generation/generationResponseTypes';
import GenerationCard from './GenerationCard';

interface Props {
    generations: GenerationResult[];
    onDelete?: (id: string) => void;
}

export function GenerationList({ generations, onDelete }: Props) {
    if (generations.length === 0) {
        return <div className="generation-list-empty">Sem geracoes ainda.</div>;
    }
    return (
        <div className="generation-list">
            {generations.map(g => (
                <GenerationCard
                    key={g.generation_id}
                    generation={g}
                    onDelete={onDelete}
                />
            ))}
        </div>
    );
}

export default GenerationList;
