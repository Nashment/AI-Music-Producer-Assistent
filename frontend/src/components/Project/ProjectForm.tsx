import { useEffect, useState } from 'react';
import {
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
} from '../../services/project/projectResponseTypes';
import useLanguage from '../../hooks/language/useLanguage';

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
    const { t } = useLanguage();
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
            setError(t.projectForm.titleRequired);
            return;
        }
        if (tempo < 1 || tempo > 400) {
            setError(t.projectForm.tempoRange);
            return;
        }
        try {
            await onSubmit({
                title: title.trim(),
                description: description.trim(),
                tempo,
            });
        } catch (err: any) {
            setError(err?.detail ?? t.projectForm.saveError);
        }
    };

    return (
        <form className="project-form" onSubmit={handleSubmit}>
            <div className="field">
                <label htmlFor="project-title">{t.projectForm.titleLabel}</label>
                <input
                    id="project-title"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder={t.projectForm.titlePlaceholder}
                    autoFocus
                />
            </div>

            <div className="field">
                <label htmlFor="project-description">{t.projectForm.descLabel}</label>
                <textarea
                    id="project-description"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    placeholder={t.projectForm.descPlaceholder}
                />
            </div>

            <div className="field">
                <label htmlFor="project-tempo">{t.projectForm.tempoLabel}</label>
                <input
                    id="project-tempo"
                    type="number"
                    min={1}
                    max={400}
                    value={tempo}
                    onChange={e => setTempo(Number(e.target.value))}
                />
                <span className="field-hint">{t.projectForm.tempoHint}</span>
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
                        {t.projectForm.cancel}
                    </button>
                ) : null}
                <button type="submit" disabled={submitting}>
                    {submitting ? t.projectForm.saving : (submitLabel ?? t.projectForm.save)}
                </button>
            </div>
        </form>
    );
}

export default ProjectForm;
