"""
Project Service - Project management business logic

Os metodos deste servico devolvem Resultado[ProjetoErro, T] em vez de
lancar excecoes. A traducao para HTTP fica exclusivamente no endpoint.
"""

import uuid

from app.data import ProjectQueries, GenerationQueries
from app.domain.result import Resultado, Sucesso, Falha
from app.domain.errors.project_errors import (
    ProjetoNaoEncontrado,
    TituloProjetoInvalido,
    TituloProjetoDuplicado,
)


class ProjectService:
    def __init__(self, db_session):
        self.db = db_session

    async def create_project(
        self, user_id: str, title: str, description: str, tempo: int
    ) -> Resultado:
        """Cria um novo projeto, validando titulo e unicidade."""
        clean_title = title.strip()
        if not clean_title:
            return Falha(TituloProjetoInvalido())

        existing = await ProjectQueries.get_user_projects(db=self.db, user_id=user_id)
        if any(p.title.strip().lower() == clean_title.lower() for p in existing):
            return Falha(TituloProjetoDuplicado(titulo=clean_title))

        projeto = await ProjectQueries.create_project(
            db=self.db,
            user_id=user_id,
            title=clean_title,
            description=description,
            tempo=tempo,
        )
        return Sucesso(projeto)

    async def get_project(self, project_id: str, user_id: str) -> Resultado:
        """Obtem o projeto e verifica o dono. Nao distingue nao-existe de nao-e-teu."""
        project = await ProjectQueries.get_project(db=self.db, project_id=uuid.UUID(project_id))
        if not project or str(project.user_id) != user_id:
            return Falha(ProjetoNaoEncontrado(project_id=project_id))
        return Sucesso(project)

    async def list_user_projects(self, user_id: str) -> Resultado:
        """Lista todos os projetos do utilizador."""
        projects = await ProjectQueries.get_user_projects(db=self.db, user_id=user_id)
        return Sucesso(projects)

    async def update_project(
        self, project_id: str, user_id: str, update_data: dict
    ) -> Resultado:
        """Atualiza os dados do projeto apos verificar o dono."""
        resultado = await self.get_project(project_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        updated = await ProjectQueries.update_project(
            db=self.db,
            project_id=uuid.UUID(project_id),
            **update_data,
        )
        return Sucesso(updated)

    async def delete_project(self, project_id: str, user_id: str) -> Resultado:
        """Apaga o projeto (e em cascade as geracoes associadas) apos verificar o dono."""
        resultado = await self.get_project(project_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        await ProjectQueries.delete_project(db=self.db, project_id=uuid.UUID(project_id))
        return Sucesso(None)

    async def list_project_generations(self, project_id: str, user_id: str) -> Resultado:
        """Lista todas as geracoes de IA de um projeto."""
        resultado = await self.get_project(project_id, user_id)
        if isinstance(resultado, Falha):
            return resultado
        generations = await GenerationQueries.get_project_generations(
            db=self.db, project_id=uuid.UUID(project_id)
        )
        return Sucesso(generations)
