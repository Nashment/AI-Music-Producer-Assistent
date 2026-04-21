"""
Project Service - Project management business logic
"""

import uuid
from typing import List, Optional
# Importamos as Queries necessárias (assume-se que estão no teu __init__.py de data)
from app.data import ProjectQueries, GenerationQueries


class ProjectService:
    """
    Service for project operations
    """

    def __init__(self, db_session):
        """
        Initialize service

        Args:
            db_session: A sessão ativa do SQLAlchemy (injeção de dependência do FastAPI)
        """
        self.db = db_session

    async def create_project(self, user_id: str, title: str, description: str, tempo: int):
        """Create a new music project"""
        clean_title = title.strip()

        if not clean_title:
            raise ValueError("O título do projeto não pode estar vazio.")

        try:
            projeto = await ProjectQueries.create_project(
                db=self.db,
                user_id=uuid.UUID(user_id),
                title=clean_title,
                description=description,
                tempo=tempo
            )
            return projeto
        except Exception as e:
            print(f"Erro ao criar projeto: {e}")
            raise

    async def get_project(self, project_id: str, user_id: str):
        """Get project details with authorization check"""
        project = await ProjectQueries.get_project(db=self.db, project_id=uuid.UUID(project_id))

        if not project:
            return None

        # VERIFICAÇÃO DE SEGURANÇA: Este projeto pertence a este utilizador?
        if str(project.user_id) != user_id:
            raise PermissionError("Não tens autorização para aceder a este projeto.")

        return project

    async def list_user_projects(self, user_id: str):
        """List all projects for a user"""
        projetos = await ProjectQueries.get_user_projects(db=self.db, user_id=uuid.UUID(user_id))
        return projetos

    async def update_project(self, project_id: str, user_id: str, update_data: dict):
        """Update project information"""
        # 1. Verifica se o projeto existe e pertence ao utilizador
        await self.get_project(project_id, user_id)

        # 2. Se não deu erro de permissão acima, podemos atualizar em segurança
        projeto_atualizado = await ProjectQueries.update_project(
            db=self.db,
            project_id=uuid.UUID(project_id),
            **update_data  # Desempacota o dicionário (ex: {"title": "Novo Título", "tempo": 140})
        )
        return projeto_atualizado

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project"""
        # 1. Verifica a propriedade do projeto (Segurança)
        await self.get_project(project_id, user_id)

        # 2. Apaga o projeto. A lógica de CASCADE que definimos nos modelos
        #    (ondelete="CASCADE") vai limpar automaticamente as gerações associadas na base de dados!
        sucesso = await ProjectQueries.delete_project(db=self.db, project_id=uuid.UUID(project_id))
        return sucesso

    async def list_project_generations(self, project_id: str, user_id: str):
        """List all music generations for a project"""
        # 1. Verifica se o utilizador tem acesso ao projeto
        await self.get_project(project_id, user_id)

        # 2. Vai buscar o histórico de gerações de IA deste projeto
        geracoes = await GenerationQueries.get_project_generations(db=self.db, project_id=uuid.UUID(project_id))
        return geracoes