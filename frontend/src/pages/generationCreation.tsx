import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import GenerationForm from '../components/Generation/GenerationForm';
import useGeneration from '../hooks/generation/useGeneration';
import { GenerationResult } from '../services/generation/generationResponseTypes';

/**
 * Pagina /projects/:projectId/audio/:audioId/generate.
 *
 * Submete o pedido e mostra o estado actual. O hook useGeneration faz o
 * polling automatico via useGenerationSubscription.
 */
function GenerationCreationPage() {
    const { projectId, audioId } = useParams<{
        projectId: string;
        audioId: string;
    }>();
    const navigate = useNavigate();

    const [submittedId, setSubmittedId] = useState<string | undefined>();
    const gen = useGeneration(submittedId);

    if (!projectId || !audioId) return null;

    const status: GenerationResult | null = gen.currentStatus;

    return (
        <div className="generation-creation">
            <header>
                <Link to={`/projects/${projectId}/audio/${audioId}`}>
                    ← Audio
                </Link>
                <h1>Nova geracao</h1>
            </header>

            {!submittedId ? (
                <GenerationForm
                    projectId={projectId}
                    audioId={audioId}
                    submitting={gen.submitting}
                    onSubmit={async req => {
                        const r = await gen.submitGeneration(req);
                        setSubmittedId(r.generation_id);
                    }}
                />
            ) : (
                <section className="generation-status">
                    <p>Geracao submetida (id: {submittedId}).</p>
                    <p>Estado actual: {status?.status ?? 'desconhecido'}</p>

                    {status?.error_message ? (
                        <p className="error-text">{status.error_message}</p>
                    ) : null}

                    {status?.audio_file_path ? (
                        <p>Audio gerado: {status.audio_file_path}</p>
                    ) : null}
                    {status?.partitura_file_path ? (
                        <p>Partitura: {status.partitura_file_path}</p>
                    ) : null}
                    {status?.tablatura_file_path ? (
                        <p>Tablatura: {status.tablatura_file_path}</p>
                    ) : null}

                    <button
                        type="button"
                        onClick={() =>
                            navigate(`/projects/${projectId}/audio/${audioId}`)
                        }
                    >
                        Voltar ao audio
                    </button>
                </section>
            )}

            {gen.error ? <p className="error-text">{gen.error}</p> : null}
        </div>
    );
}

export default GenerationCreationPage;
