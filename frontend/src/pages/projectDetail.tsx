import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useProject from '../hooks/project/useProject';
import useAudios from '../hooks/audio/useAudios';
import useLanguage from '../hooks/language/useLanguage';
import AudioList from '../components/Audio/AudioList';
import AudioUpload from '../components/Audio/AudioUpload';
import PageHeader from '../components/Layout/PageHeader';
import Spinner from '../components/Layout/Spinner';
import EmptyState from '../components/Layout/EmptyState';
import Modal from '../components/Layout/Modal';
import ConfirmDialog from '../components/Layout/ConfirmDialog';
import ProjectForm from '../components/Project/ProjectForm';
import { useToast, describeError } from '../components/Layout/Toast';
import {
    ProjectCreate,
    ProjectUpdate,
} from '../services/project/projectResponseTypes';

/**
 * /projects/:projectId — vista do projeto:
 *   - cabeçalho com info + botões editar/eliminar,
 *   - área de áudios com upload + lista,
 *   - confirmações em modais.
 */
function ProjectDetailPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { t } = useLanguage();
    const toast = useToast();

    const { project, loading, error, updateProject, deleteProject } =
        useProject(projectId);
    const audios = useAudios(projectId);

    const [editOpen, setEditOpen] = useState(false);
    const [editing, setEditing] = useState(false);

    const [confirmDelProject, setConfirmDelProject] = useState(false);
    const [deletingProject, setDeletingProject] = useState(false);

    const [confirmDelAudioId, setConfirmDelAudioId] = useState<string | null>(null);
    const [deletingAudio, setDeletingAudio] = useState(false);

    if (loading && !project) return <Spinner block label={t.projectDetail.loading} />;
    if (error) return <p className="error-text">{error}</p>;
    if (!project) return null;

    const handleEdit = async (data: ProjectCreate | ProjectUpdate) => {
        setEditing(true);
        try {
            await updateProject(project.id, data as ProjectUpdate);
            toast.success(t.projectDetail.updated);
            setEditOpen(false);
        } catch (err) {
            toast.error(describeError(err, t.projectDetail.updateError));
            throw err;
        } finally {
            setEditing(false);
        }
    };

    const handleDeleteProject = async () => {
        setDeletingProject(true);
        try {
            await deleteProject(project.id);
            toast.success(t.projectDetail.projectDeleted);
            navigate('/projects', { replace: true });
        } catch (err) {
            toast.error(describeError(err, t.projectDetail.projectDeleteError));
            setDeletingProject(false);
            setConfirmDelProject(false);
        }
    };

    const handleUpload = async (file: File) => {
        try {
            const a = await audios.uploadAudio(file);
            toast.success(t.projectDetail.audioUploaded.replace('{name}', file.name));
            return a;
        } catch (err) {
            toast.error(describeError(err, t.projectDetail.uploadError));
            throw err;
        }
    };

    const handleDeleteAudio = async () => {
        if (!confirmDelAudioId) return;
        setDeletingAudio(true);
        try {
            await audios.deleteAudio(confirmDelAudioId);
            toast.success(t.projectDetail.audioDeleted);
            setConfirmDelAudioId(null);
        } catch (err) {
            toast.error(describeError(err, t.projectDetail.audioDeleteError));
        } finally {
            setDeletingAudio(false);
        }
    };

    return (
        <div className="project-detail">
            <PageHeader
                title={project.title}
                description={project.description || t.projectDetail.noDescription}
                backTo="/projects"
                backLabel={t.projectDetail.back}
                actions={
                    <>
                        <span className="badge badge-primary">{project.tempo} BPM</span>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setEditOpen(true)}
                        >
                            {t.projectDetail.edit}
                        </button>
                        <button
                            type="button"
                            className="btn btn-danger-ghost"
                            onClick={() => setConfirmDelProject(true)}
                        >
                            {t.projectDetail.delete}
                        </button>
                    </>
                }
            />

            <section className="card project-audio-panel">
                <div className="section-title">
                    <h2>{t.projectDetail.audios}</h2>
                    <span className="text-muted text-sm">
                        {audios.audios.length} {t.projectDetail.audiosLoading.includes('ficheiro') ? 'ficheiro(s)' : 'file(s)'} · upload .mp3 / .wav até 50MB
                    </span>
                </div>

                <AudioUpload
                    onUpload={handleUpload}
                    uploading={audios.uploading}
                />

                {audios.error ? (
                    <p className="error-text">{audios.error}</p>
                ) : null}

                {audios.loading && audios.audios.length === 0 ? (
                    <Spinner block label={t.projectDetail.audiosLoading} />
                ) : null}

                {!audios.loading && audios.audios.length === 0 ? (
                    <EmptyState
                        icon="🎧"
                        title={t.projectDetail.noAudios}
                        description={t.projectDetail.noAudiosDesc}
                    />
                ) : (
                    <AudioList
                        projectId={project.id}
                        audios={audios.audios}
                        onDelete={id => setConfirmDelAudioId(id)}
                    />
                )}
            </section>

            <Modal
                open={editOpen}
                title={t.projectDetail.editModal}
                onClose={() => !editing && setEditOpen(false)}
            >
                <ProjectForm
                    initial={project}
                    submitting={editing}
                    submitLabel={t.projectDetail.saveChanges}
                    onSubmit={handleEdit}
                    onCancel={() => setEditOpen(false)}
                />
            </Modal>

            <ConfirmDialog
                open={confirmDelProject}
                title={t.projectDetail.confirmDeleteProject}
                message={
                    <>
                        {t.projects.confirmDeletePrefix}{' '}
                        <strong>{project.title}</strong>.{' '}
                        {t.projectDetail.confirmDeleteProjectMsg}
                    </>
                }
                confirmLabel={t.projectDetail.confirmDeleteLabel}
                danger
                busy={deletingProject}
                onConfirm={handleDeleteProject}
                onCancel={() => setConfirmDelProject(false)}
            />

            <ConfirmDialog
                open={!!confirmDelAudioId}
                title={t.projectDetail.confirmDeleteAudio}
                message={t.projectDetail.confirmDeleteAudioMsg}
                confirmLabel={t.projectDetail.confirmDeleteLabel}
                danger
                busy={deletingAudio}
                onConfirm={handleDeleteAudio}
                onCancel={() => setConfirmDelAudioId(null)}
            />
        </div>
    );
}

export default ProjectDetailPage;
