import { useEffect, useState } from 'react';
import {
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
} from '../../services/project/projectResponseTypes';

interface Props {
    /** Quando passado, o form arranca preenchido em modo edicao. */
    initial?: ProjectResponse;
    submitting: boolean;
    submitLabel?: string;
    onSubmit: (data: ProjectCreate | ProjectUpdate) => Promise<unknown>;
    onCancel?: () => void;
}

/**
 * Form partilhado para criar/editar projeto. Usa o mesmo shape em ambos os
 * modos: titulo + descricao + tempo (BPM).
 */
export function ProjectForm({
    initial,
    submitting,
    submitLabel,
    onSubmit,
    onCancel,
}: Props) {
    const [title, setTitle] = useState(initial?.title ?? '');
    const [description, setDescription] = useState(initial?.description ?? '');
    const [tempo, setTempo] = useState<number>(initial?.tempo ?? 120);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setTitle(initial?.title ?? '');
        setDescription(initial?.description ?? '');
        setTempo(initial?.tempo ?? 120);
    }, [initial?.id]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!title.trim()) {
            setError('O título é obrigatório.');
            return;
        }
        if (tempo < 1 || tempo > 400) {
            setError('Tempo (BPM) tem de estar entre 1 e 400.');
            return;
        }
        try {
            await onSubmit({
                title: title.trim(),
                description: description.trim(),
                tempo,
            });
        } catch (err: any) {
            setError(err?.detail ?? 'Erro ao guardar.');
        }
    };

    return (
        <form className="project-form" onSubmit={handleSubmit}>
            <div className="field">
                <label htmlFor="project-title">Título</label>
                <input
                    id="project-title"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="Ex: Demo Maio"
                    autoFocus
                />
            </div>

            <div className="field">
                <label htmlFor="project-description">Descrição</label>
                <textarea
                    id="project-description"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder="O que estás a tentar fazer?"
                />
            </div>

            <div className="field">
                <label htmlFor="project-tempo">Tempo (BPM)</label>
                <input
                    id="project-tempo"
                    type="number"
                    min={1}
                    max={400}
                    value={tempo}
                    onChange={e => setTempo(Number(e.target.value))}
                />
                <span className="field-hint">
                    Usado como referência para análises e geração.
                </span>
            </div>

            {error ? <p className="error-text">{error}</p> : null}

            <div className="project-form-actions">
                {onCancel ? (
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={onCancel}
                        disabled={submitting}
                    >
                        Cancelar
                    </button>
                ) : null}
                <button type="submit" disabled={submitting}>
                    {submitting ? 'A guardar…' : submitLabel ?? 'Guardar'}
                </button>
            </div>
        </form>
    );
}

export default ProjectForm;
