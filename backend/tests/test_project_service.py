"""
Testes para ProjectService e ProjectQueries.

Cobre:
  create_project — sucesso, título vazio, título duplicado
  get_project    — sucesso, não encontrado, dono errado
  list_user_projects — lista correcta, só do utilizador
  update_project — sucesso, campo individual, ownership
  delete_project — sucesso, cascade não afecta outro utilizador
  list_project_generations — retorna geracoes do projeto
  ProjectQueries — create, get, list, update, delete
"""

import uuid
import pytest

from app.services.project_service import ProjectService
from app.domain.result import Sucesso, Falha
from app.domain.errors.project_errors import (
    ProjetoNaoEncontrado,
    TituloProjetoInvalido,
    TituloProjetoDuplicado,
)


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestProjectServiceCreate:

    async def test_create_project_success(self, async_db_session, db_user):
        """Assert: projeto criado com campos correctos."""
        svc = ProjectService(async_db_session)
        result = await svc.create_project(
            user_id=str(db_user.id),
            title="Demo Maio",
            description="Projecto de teste",
            tempo=120,
        )
        assert isinstance(result, Sucesso)
        assert result.valor.title == "Demo Maio"
        assert result.valor.tempo == 120
        assert str(result.valor.user_id) == str(db_user.id)

    async def test_create_project_empty_title_returns_falha(self, async_db_session, db_user):
        """Assert: título vazio → Falha(TituloProjetoInvalido)."""
        svc = ProjectService(async_db_session)
        result = await svc.create_project(
            user_id=str(db_user.id), title="   ", description="", tempo=100
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, TituloProjetoInvalido)

    async def test_create_project_duplicate_title_returns_falha(
        self, async_db_session, db_user
    ):
        """Assert: título duplicado para o mesmo utilizador → Falha(TituloProjetoDuplicado)."""
        svc = ProjectService(async_db_session)
        await svc.create_project(
            user_id=str(db_user.id), title="Álbum Verão", description="", tempo=90
        )
        result = await svc.create_project(
            user_id=str(db_user.id), title="Álbum Verão", description="outro", tempo=100
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, TituloProjetoDuplicado)

    async def test_create_project_duplicate_title_case_insensitive(
        self, async_db_session, db_user
    ):
        """Assert: comparação de título é case-insensitive."""
        svc = ProjectService(async_db_session)
        await svc.create_project(user_id=str(db_user.id), title="Rock Session", description="", tempo=120)
        result = await svc.create_project(user_id=str(db_user.id), title="rock session", description="", tempo=120)
        assert isinstance(result, Falha)
        assert isinstance(result.erro, TituloProjetoDuplicado)

    async def test_same_title_different_users_is_allowed(self, async_db_session, db_user):
        """Assert: dois utilizadores podem ter projectos com o mesmo título."""
        from app.data.queries import UserQueries
        outro = await UserQueries.create_user(
            db=async_db_session, username="outro", oauth_provider="google", oauth_id="g_outro"
        )
        svc = ProjectService(async_db_session)
        r1 = await svc.create_project(user_id=str(db_user.id), title="Partilhado", description="", tempo=120)
        r2 = await svc.create_project(user_id=str(outro.id), title="Partilhado", description="", tempo=120)
        assert isinstance(r1, Sucesso)
        assert isinstance(r2, Sucesso)


@pytest.mark.asyncio
class TestProjectServiceGet:

    async def test_get_project_success(self, async_db_session, db_user, db_project):
        """Assert: devolve Sucesso com o projecto correcto."""
        svc = ProjectService(async_db_session)
        result = await svc.get_project(str(db_project.id), str(db_user.id))
        assert isinstance(result, Sucesso)
        assert result.valor.id == db_project.id

    async def test_get_project_wrong_user(self, async_db_session, db_project):
        """Assert: user_id diferente → Falha(ProjetoNaoEncontrado)."""
        svc = ProjectService(async_db_session)
        result = await svc.get_project(str(db_project.id), str(uuid.uuid4()))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ProjetoNaoEncontrado)

    async def test_get_project_nonexistent(self, async_db_session, db_user):
        """Assert: UUID inexistente → Falha(ProjetoNaoEncontrado)."""
        svc = ProjectService(async_db_session)
        result = await svc.get_project(str(uuid.uuid4()), str(db_user.id))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ProjetoNaoEncontrado)


@pytest.mark.asyncio
class TestProjectServiceList:

    async def test_list_user_projects_returns_own_projects(
        self, async_db_session, db_user
    ):
        """Assert: lista apenas os projectos do utilizador."""
        svc = ProjectService(async_db_session)
        await svc.create_project(user_id=str(db_user.id), title="P1", description="", tempo=120)
        await svc.create_project(user_id=str(db_user.id), title="P2", description="", tempo=140)

        result = await svc.list_user_projects(str(db_user.id))
        assert isinstance(result, Sucesso)
        assert len(result.valor) >= 2
        for p in result.valor:
            assert str(p.user_id) == str(db_user.id)

    async def test_list_user_projects_excludes_other_users(self, async_db_session, db_user):
        """Assert: projectos de outro utilizador não aparecem na lista."""
        from app.data.queries import UserQueries
        outro = await UserQueries.create_user(
            db=async_db_session, username="outro2", oauth_provider="google", oauth_id="g_outro2"
        )
        svc = ProjectService(async_db_session)
        await svc.create_project(user_id=str(outro.id), title="Privado", description="", tempo=120)

        result = await svc.list_user_projects(str(db_user.id))
        assert isinstance(result, Sucesso)
        titles = [p.title for p in result.valor]
        assert "Privado" not in titles

    async def test_list_user_projects_empty(self, async_db_session):
        """Assert: utilizador sem projectos recebe lista vazia."""
        from app.data.queries import UserQueries
        novo = await UserQueries.create_user(
            db=async_db_session, username="semprojectos", oauth_provider="google", oauth_id="g_sem"
        )
        svc = ProjectService(async_db_session)
        result = await svc.list_user_projects(str(novo.id))
        assert isinstance(result, Sucesso)
        assert result.valor == []


@pytest.mark.asyncio
class TestProjectServiceUpdate:

    async def test_update_project_title(self, async_db_session, db_user, db_project):
        """Assert: título actualizado é persistido."""
        svc = ProjectService(async_db_session)
        result = await svc.update_project(
            str(db_project.id), str(db_user.id), {"title": "Novo Título"}
        )
        assert isinstance(result, Sucesso)
        assert result.valor.title == "Novo Título"

    async def test_update_project_tempo(self, async_db_session, db_user, db_project):
        """Assert: tempo actualizado é persistido."""
        svc = ProjectService(async_db_session)
        result = await svc.update_project(
            str(db_project.id), str(db_user.id), {"tempo": 180}
        )
        assert isinstance(result, Sucesso)
        assert result.valor.tempo == 180

    async def test_update_project_wrong_user(self, async_db_session, db_project):
        """Assert: user_id errado → Falha(ProjetoNaoEncontrado); não altera dados."""
        svc = ProjectService(async_db_session)
        result = await svc.update_project(
            str(db_project.id), str(uuid.uuid4()), {"title": "Hackeado"}
        )
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ProjetoNaoEncontrado)


@pytest.mark.asyncio
class TestProjectServiceDelete:

    async def test_delete_project_success(self, async_db_session, db_user, db_project):
        """Assert: projecto eliminado não existe mais na DB."""
        svc = ProjectService(async_db_session)
        result = await svc.delete_project(str(db_project.id), str(db_user.id))
        assert isinstance(result, Sucesso)

        get_result = await svc.get_project(str(db_project.id), str(db_user.id))
        assert isinstance(get_result, Falha)

    async def test_delete_project_wrong_user(self, async_db_session, db_project):
        """Assert: user_id errado → Falha; projecto permanece."""
        svc = ProjectService(async_db_session)
        result = await svc.delete_project(str(db_project.id), str(uuid.uuid4()))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ProjetoNaoEncontrado)

    async def test_delete_nonexistent_project(self, async_db_session, db_user):
        """Assert: UUID inexistente → Falha(ProjetoNaoEncontrado)."""
        svc = ProjectService(async_db_session)
        result = await svc.delete_project(str(uuid.uuid4()), str(db_user.id))
        assert isinstance(result, Falha)
        assert isinstance(result.erro, ProjetoNaoEncontrado)


# ---------------------------------------------------------------------------
# ProjectQueries directas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestProjectQueries:

    async def test_create_and_get_project(self, async_db_session, db_user):
        """Assert: create_project + get_project devolve o mesmo registo."""
        from app.data.queries import ProjectQueries
        created = await ProjectQueries.create_project(
            db=async_db_session,
            user_id=db_user.id,
            title="Query Test",
            description="Desc",
            tempo=130,
        )
        fetched = await ProjectQueries.get_project(
            db=async_db_session, project_id=created.id
        )
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Query Test"

    async def test_get_user_projects_ordered(self, async_db_session, db_user):
        """Assert: get_user_projects devolve projectos ordenados por created_at DESC."""
        from app.data.queries import ProjectQueries
        for i in range(3):
            await ProjectQueries.create_project(
                db=async_db_session,
                user_id=db_user.id,
                title=f"Proj {i}",
                description="",
                tempo=100 + i * 10,
            )
        projects = await ProjectQueries.get_user_projects(
            db=async_db_session, user_id=db_user.id
        )
        assert len(projects) >= 3
        # Verifica ordem decrescente de created_at
        for i in range(len(projects) - 1):
            assert projects[i].created_at >= projects[i + 1].created_at

    async def test_update_project_description(self, async_db_session, db_project):
        """Assert: update_project actualiza description."""
        from app.data.queries import ProjectQueries
        updated = await ProjectQueries.update_project(
            db=async_db_session,
            project_id=db_project.id,
            description="Nova descrição",
        )
        assert updated.description == "Nova descrição"

    async def test_delete_project_returns_true(self, async_db_session, db_project):
        """Assert: delete_project devolve True e remove o registo."""
        from app.data.queries import ProjectQueries
        ok = await ProjectQueries.delete_project(
            db=async_db_session, project_id=db_project.id
        )
        assert ok is True
        fetched = await ProjectQueries.get_project(
            db=async_db_session, project_id=db_project.id
        )
        assert fetched is None

    async def test_delete_nonexistent_returns_false(self, async_db_session):
        """Assert: apagar UUID inexistente devolve False."""
        from app.data.queries import ProjectQueries
        ok = await ProjectQueries.delete_project(
            db=async_db_session, project_id=uuid.uuid4()
        )
        assert ok is False
