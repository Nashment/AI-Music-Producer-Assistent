import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import useProject from '../hooks/project/useProject';
import useAudios from '../hooks/audio/useAudios';
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

    if (loading && !project) return <Spinner block label="A carregar projeto…" />;
    if (error) return <p className="error-text">{error}</p>;
    if (!project) return null;

    const handleEdit = async (data: ProjectCreate | ProjectUpdate) => {
        setEditing(true);
        try {
            await updateProject(project.id, data as ProjectUpdate);
            toast.success('Projeto actualizado.');
            setEditOpen(false);
        } catch (err) {
            toast.error(describeError(err, 'Erro a actualizar.'));
            throw err;
        } finally {
            setEditing(false);
        }
    };

    const handleDeleteProject = async () => {
        setDeletingProject(true);
        try {
            await deleteProject(project.id);
            toast.success('Projeto apagado.');
            navigate('/projects', { replace: true });
        } catch (err) {
            toast.error(describeError(err, 'Erro a apagar projeto.'));
            setDeletingProject(false);
            setConfirmDelProject(false);
        }
    };

    const handleUpload = async (file: File) => {
        try {
            const a = await audios.uploadAudio(file);
            toast.success(`Áudio "${file.name}" carregado.`);
            return a;
        } catch (err) {
            toast.error(describeError(err, 'Falha no upload.'));
            throw err;
        }
    };

    const handleDeleteAudio = async () => {
        if (!confirmDelAudioId) return;
        setDeletingAudio(true);
        try {
            await audios.deleteAudio(confirmDelAudioId);
            toast.success('Áudio apagado.');
            setConfirmDelAudioId(null);
        } catch (err) {
            toast.error(describeError(err, 'Erro a apagar áudio.'));
        } finally {
            setDeletingAudio(false);
        }
    };

    return (
        <div className="project-detail">
            <PageHeader
                title={project.title}
                description={project.description || 'sem descrição'}
                backTo="/projects"
                backLabel="Projetos"
                actions={
                    <>
                        <span className="badge badge-primary">{project.tempo} BPM</span>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setEditOpen(true)}
                        >
                            Editar
                        </button>
                        <button
                            type="button"
                            className="btn btn-danger-ghost"
                            onClick={() => setConfirmDelProject(true)}
                        >
                            Apagar
                        </button>
                    </>
                }
            />

            <section className="card project-audio-panel">
                <div className="section-title">
                    <h2>Áudios</h2>
                    <span className="text-muted text-sm">
                        {audios.audios.length} ficheiro(s) · upload .mp3 / .wav até 50MB
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
                    <Spinner block label="A carregar áudios…" />
                ) : null}

                {!audios.loading && audios.audios.length === 0 ? (
                    <EmptyState
                        icon="🎧"
                        title="Sem áudios neste projeto"
                        description="Faz upload de um .mp3 ou .wav para o backend analisar."
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
                title="Editar projeto"
                onClose={() => !editing && setEditOpen(false)}
            >
                <ProjectForm
                    initial={project}
                    submitting={editing}
                    submitLabel="Guardar alterações"
                    onSubmit={handleEdit}
                    onCancel={() => setEditOpen(false)}
                />
            </Modal>

            <ConfirmDialog
                open={confirmDelProject}
                title="Apagar projeto?"
                message={
                    <>
                        Vais apagar <strong>{project.title}</strong>. Áudios e
                        gerações associados também serão removidos.
                    </>
                }
                confirmLabel="Apagar"
                danger
                busy={deletingProject}
                onConfirm={handleDeleteProject}
                onCancel={() => setConfirmDelProject(false)}
            />

            <ConfirmDialog
                open={!!confirmDelAudioId}
                title="Apagar áudio?"
                message="O ficheiro será removido do disco e da base de dados."
                confirmLabel="Apagar"
                danger
                busy={deletingAudio}
                onConfirm={handleDeleteAudio}
                onCancel={() => setConfirmDelAudioId(null)}
            />
        </div>
    );
}

export default ProjectDetailPage;
