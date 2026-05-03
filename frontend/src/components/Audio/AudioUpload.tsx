import { useRef, useState } from 'react';

interface Props {
    onUpload: (file: File) => Promise<unknown>;
    uploading: boolean;
}

const ACCEPT = '.mp3,.wav,audio/mpeg,audio/wav';
const MAX_BYTES = 50 * 1024 * 1024; // backend limita a 50MB

/**
 * Upload de audio com drag & drop. Valida extensao e tamanho do ficheiro
 * antes de chamar o callback (que faz o pedido multipart).
 */
export function AudioUpload({ onUpload, uploading }: Props) {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const [drag, setDrag] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const validate = (file: File): string | null => {
        if (file.size > MAX_BYTES) {
            return `Ficheiro demasiado grande (${(file.size / 1024 / 1024).toFixed(1)} MB). Limite: 50 MB.`;
        }
        const lower = file.name.toLowerCase();
        if (!lower.endsWith('.mp3') && !lower.endsWith('.wav')) {
            return 'Apenas .mp3 ou .wav são aceites.';
        }
        return null;
    };

    const handleFile = async (file: File) => {
        const err = validate(file);
        setError(err);
        if (err) return;
        try {
            await onUpload(file);
            if (inputRef.current) inputRef.current.value = '';
        } catch {
            // o caller mostra o toast — aqui deixamos o input limpo para retry
        }
    };

    return (
        <div className="audio-upload-wrap">
            <label
                className={`audio-upload-drop ${drag ? 'is-drag' : ''} ${
                    uploading ? 'is-busy' : ''
                }`}
                onDragOver={e => {
                    e.preventDefault();
                    if (!uploading) setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={async e => {
                    e.preventDefault();
                    setDrag(false);
                    if (uploading) return;
                    const file = e.dataTransfer.files?.[0];
                    if (file) await handleFile(file);
                }}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept={ACCEPT}
                    disabled={uploading}
                    onChange={async e => {
                        const f = e.target.files?.[0];
                        if (f) await handleFile(f);
                    }}
                />
                <div className="audio-upload-content">
                    <span className="audio-upload-icon">🎧</span>
                    <span className="audio-upload-title">
                        {uploading
                            ? 'A carregar e analisar…'
                            : 'Arrasta um áudio ou clica para escolher'}
                    </span>
                    <span className="audio-upload-hint">
                        .mp3 ou .wav até 50 MB
                    </span>
                </div>
            </label>

            {error ? <p className="error-text">{error}</p> : null}
        </div>
    );
}

export default AudioUpload;
