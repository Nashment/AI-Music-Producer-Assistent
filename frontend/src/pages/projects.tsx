import { useMemo, useState } from 'react';
import useProjects from '../hooks/project/useProjects';
import useLanguage from '../hooks/language/useLanguage';
import ProjectList from '../components/Project/ProjectList';
import ProjectForm from '../components/Project/ProjectForm';
import PageHeader from '../components/Layout/PageHeader';
import EmptyState from '../components/Layout/EmptyState';
import Spinner from '../components/Layout/Spinner';
import Modal from '../components/Layout/Modal';
import ConfirmDialog from '../components/Layout/ConfirmDialog';
import { useToast, describeError } from '../components/Layout/Toast';
import {
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
} from '../services/project/projectResponseTypes';

type SortKey = 'name' | 'tempo';

/**
 * /projects — lista, pesquisa, ordenacao + criacao via modal.
 * Eliminacao com confirmacao.
 */
function ProjectsPage() {
    const { projects, loading, error, createProject, deleteProject } = useProjects();
    const { t } = useLanguage();
    const toast = useToast();

    const [createOpen, setCreateOpen] = useState(false);
    const [creating, setCreating] = useState(false);

    const [confirmDel, setConfirmDel] = useState<ProjectResponse | null>(null);
    const [deleting, setDeleting] = useState(false);

    const [search, setSearch] = useState('');
    const [sort, setSort] = useState<SortKey>('name');

    const visible = useMemo(() => {
        const q = search.trim().toLowerCase();
        const filtered = q
            ? projects.filter(
                  p =>
                      p.title.toLowerCase().includes(q) ||
                      p.description.toLowerCase().includes(q),
              )
            : projects;
        const sorted = [...filtered].sort((a, b) =>
            sort === 'name'
                ? a.title.localeCompare(b.title)
                : a.tempo - b.tempo,
        );
        return sorted;
    }, [projects, search, sort]);

    const handleCreate = async (data: ProjectCreate | ProjectUpdate) => {
        setCreating(true);
        try {
            await createProject(data as ProjectCreate);
            toast.success(t.projects.created);
            setCreateOpen(false);
        } catch (err) {
            toast.error(describeError(err, t.projects.createError));
            throw err;
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async () => {
        if (!confirmDel) return;
        setDeleting(true);
        try {
            await deleteProject(confirmDel.id);
            toast.success(t.projects.deleted);
            setConfirmDel(null);
        } catch (err) {
            toast.error(describeError(err, t.projects.deleteError));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="projects">
            <PageHeader
                title={t.projects.title}
                description={t.projects.description}
                actions={
                    <button type="button" onClick={() => setCreateOpen(true)}>
                        {t.projects.newProject}
                    </button>
                }
            />

            <div className="projects-toolbar card">
                <input
                    type="search"
                    placeholder={t.projects.search}
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />
                <select
                    value={sort}
                    onChange={e => setSort(e.target.value as SortKey)}
                    aria-label={t.projects.sortLabel}
                >
                    <option value="name">{t.projects.sortName}</option>
                    <option value="tempo">{t.projects.sortTempo}</option>
                </select>
            </div>

            {loading && projects.length === 0 ? (
                <Spinner block label={t.projects.loading} />
            ) : null}

            {error ? <p className="error-text">{error}</p> : null}

            {!loading && projects.length === 0 && !error ? (
                <EmptyState
                    icon="🎼"
                    title={t.projects.noProjects}
                    description={t.projects.noProjectsDesc}
                    action={
                        <button type="button" onClick={() => setCreateOpen(true)}>
                            {t.projects.createProject}
                        </button>
                    }
                />
            ) : null}

            {projects.length > 0 && visible.length === 0 ? (
                <EmptyState
                    icon="🔍"
                    title={t.projects.noResults}
                    description={t.projects.noResultsDesc.replace('{search}', search)}
                />
            ) : null}

            {visible.length > 0 ? (
                <ProjectList
                    projects={visible}
                    onDelete={id => {
                        const p = projects.find(x => x.id === id) ?? null;
                        setConfirmDel(p);
                    }}
                />
            ) : null}

            <Modal
                open={createOpen}
                title={t.projects.modalTitle}
                onClose={() => !creating && setCreateOpen(false)}
            >
                <ProjectForm
                    submitting={creating}
                    submitLabel={t.projects.createProject.replace('+ ', '')}
                    onSubmit={handleCreate}
                    onCancel={() => setCreateOpen(false)}
                />
            </Modal>

            <ConfirmDialog
                open={!!confirmDel}
                title={t.projects.confirmDeleteTitle}
                message={
                    <>
                        {t.projects.confirmDeletePrefix}{' '}
                        <strong>{confirmDel?.title}</strong>.{' '}
                        {t.projects.confirmDeleteMsg}
                    </>
                }
                confirmLabel={t.projects.confirmDeleteLabel}
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmDel(null)}
            />
        </div>
    );
}

export default ProjectsPage;
