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
 * modos: titulo + descricao.
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
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setTitle(initial?.title ?? '');
        setDescription(initial?.description ?? '');
    }, [initial?.id]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        if (!title.trim()) {
            setError(t.projectForm.titleRequired);
            return;
        }
        try {
            await onSubmit({
                title: title.trim(),
                description: description.trim(),
                // BPM removido da UI; mantemos um valor por omissão para
                // compatibilidade com o backend, que ainda espera o campo.
                tempo: initial?.tempo ?? 120,
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
