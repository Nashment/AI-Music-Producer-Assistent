import { useMemo, useState } from 'react';
import useProjects from '../hooks/project/useProjects';
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
            toast.success('Projeto criado.');
            setCreateOpen(false);
        } catch (err) {
            toast.error(describeError(err, 'Erro a criar projeto.'));
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
            toast.success('Projeto apagado.');
            setConfirmDel(null);
        } catch (err) {
            toast.error(describeError(err, 'Erro a apagar projeto.'));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <div className="projects">
            <PageHeader
                title="Projetos"
                description="Cada projeto agrupa áudios e gerações relacionados."
                actions={
                    <button type="button" onClick={() => setCreateOpen(true)}>
                        + Novo projeto
                    </button>
                }
            />

            <div className="projects-toolbar card">
                <input
                    type="search"
                    placeholder="Pesquisar por título ou descrição…"
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />
                <select
                    value={sort}
                    onChange={e => setSort(e.target.value as SortKey)}
                    aria-label="Ordenar"
                >
                    <option value="name">Ordenar: Nome</option>
                    <option value="tempo">Ordenar: BPM</option>
                </select>
            </div>

            {loading && projects.length === 0 ? (
                <Spinner block label="A carregar projetos…" />
            ) : null}

            {error ? <p className="error-text">{error}</p> : null}

            {!loading && projects.length === 0 && !error ? (
                <EmptyState
                    icon="🎼"
                    title="Ainda não tens projetos"
                    description="Cria o teu primeiro projeto para começares a carregar áudios."
                    action={
                        <button type="button" onClick={() => setCreateOpen(true)}>
                            + Criar projeto
                        </button>
                    }
                />
            ) : null}

            {projects.length > 0 && visible.length === 0 ? (
                <EmptyState
                    icon="🔍"
                    title="Nenhum projeto bate com a pesquisa"
                    description={`Não encontrei resultados para “${search}”.`}
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
                title="Novo projeto"
                onClose={() => !creating && setCreateOpen(false)}
            >
                <ProjectForm
                    submitting={creating}
                    submitLabel="Criar projeto"
                    onSubmit={handleCreate}
                    onCancel={() => setCreateOpen(false)}
                />
            </Modal>

            <ConfirmDialog
                open={!!confirmDel}
                title="Apagar projeto?"
                message={
                    <>
                        Vais apagar <strong>{confirmDel?.title}</strong>. Os
                        áudios e gerações associados também serão removidos.
                    </>
                }
                confirmLabel="Apagar"
                danger
                busy={deleting}
                onConfirm={handleDelete}
                onCancel={() => setConfirmDel(null)}
            />
        </div>
    );
}

export default ProjectsPage;
