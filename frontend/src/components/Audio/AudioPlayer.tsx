import { useEffect, useState } from 'react';
import { audioService } from '../../services/audio/audioService';
import Spinner from '../Layout/Spinner';

interface Props {
    audioId: string;
    fileName: string;
}

/**
 * Player com lazy-load: só pede o ficheiro ao backend quando o utilizador
 * carrega em "Carregar". Recebemos um Blob URL e atribuimo-lo ao <audio>.
 *
 * Tambem expomos um botao para descarregar o ficheiro original (mesmo blob).
 */
export function AudioPlayer({ audioId, fileName }: Props) {
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Quando o audioId muda (utilizador navega), libertamos o blob anterior
        return () => {
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    }, [blobUrl]);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const url = await audioService.fetchAudioBlobUrl(audioId);
            setBlobUrl(url);
        } catch (e: any) {
            setError(e?.message ?? 'Não foi possível obter o áudio.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="audio-player">
            {!blobUrl ? (
                <div className="audio-player-placeholder">
                    <div>
                        <p className="text-soft">
                            O áudio só é descarregado quando carregares
                            "Carregar". Útil em ligações lentas.
                        </p>
                    </div>
                    <button type="button" onClick={load} disabled={loading}>
                        {loading ? (
                            <Spinner size="sm" label="A carregar…" />
                        ) : (
                            '▶ Carregar áudio'
                        )}
                    </button>
                </div>
            ) : (
                <>
                    <audio controls src={blobUrl} className="audio-player-el" />
                    <a
                        href={blobUrl}
                        download={fileName}
                        className="btn btn-secondary btn-sm"
                    >
                        ⬇ Download original
                    </a>
                </>
            )}
            {error ? <p className="error-text">{error}</p> : null}
        </div>
    );
}

export default AudioPlayer;
