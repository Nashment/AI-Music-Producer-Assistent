"""
Projects endpoints - Project management

Responsabilidades desta camada:
  - Receber pedidos HTTP e validar os parametros de entrada.
  - Chamar o servico e obter um Resultado[ProjetoErro, T].
  - Mapear ProjetoErro -> HTTP Problem Details (_handle_project_error).
  - Construir a resposta HTTP de sucesso.

O que NAO esta aqui:
  - Logica de negocio (esta no servico).
  - Excecoes genericas do Python (o servico nunca as lanca para ca).
"""

import uuid
from typing import Callable, List

from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project_service import ProjectService
from app.api.dependencies import get_db, get_current_user_id
from app.domain.result import Sucesso, Falha
from app.domain.errors.project_errors import (
    ProjetoNaoEncontrado,
    TituloProjetoInvalido,
    TituloProjetoDuplicado,
    ProjetoErro,
)
from app.domain.dtos.endpoints.projects import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


# ===========================================================================
# Tratamento de erros HTTP
# ===========================================================================

def _problem_json(status_code: int, type_slug: str, title: str, detail: str, instance: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type":     f"/errors/{type_slug}",
            "title":    title,
            "status":   status_code,
            "detail":   detail,
            "instance": instance,
        },
        media_type="application/problem+json",
    )


def _handle_project_error(erro: ProjetoErro, instance: str) -> JSONResponse:
    match erro:
        case ProjetoNaoEncontrado():
            return _problem_json(404, "recurso-nao-encontrado", "Recurso Nao Encontrado",
                "O projeto pedido nao foi encontrado.", instance)
        case TituloProjetoInvalido():
            return _problem_json(400, "requisicao-invalida", "Requisicao Invalida",
                "O titulo do projeto nao pode estar vazio.", instance)
        case TituloProjetoDuplicado(titulo=t):
            return _problem_json(409, "titulo-duplicado", "Titulo Duplicado",
                f"Ja existe um projeto com o titulo '{t}'.", instance)
        case _:
            return _problem_json(500, "erro-interno", "Erro Interno",
                "Ocorreu um erro inesperado no servico de projetos.", instance)


def _handle_result(
    resultado: Sucesso | Falha,
    instance: str,
    success_factory: Callable,
) -> Response:
    match resultado:
        case Falha(erro=erro):
            return _handle_project_error(erro, instance)
        case Sucesso(valor=valor):
            return success_factory(valor)


# ===========================================================================
# Endpoints
# ===========================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Create a new music project."""
    resultado = await ProjectService(db).create_project(
        user_id=str(user_id),
        title=project_data.title,
        description=project_data.description,
        tempo=project_data.tempo,
    )
    return _handle_result(
        resultado,
        instance="/api/v1/projects",
        success_factory=lambda project: project,
    )


@router.get("", response_model=List[ProjectResponse])
async def list_user_projects(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get all projects for authenticated user."""
    resultado = await ProjectService(db).list_user_projects(user_id=str(user_id))
    return _handle_result(
        resultado,
        instance="/api/v1/projects",
        success_factory=lambda projects: projects,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get specific project by ID."""
    resultado = await ProjectService(db).get_project(project_id=project_id, user_id=str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/projects/{project_id}",
        success_factory=lambda project: project,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update project information."""
    resultado = await ProjectService(db).update_project(
        project_id=project_id,
        user_id=str(user_id),
        update_data=project_update.model_dump(exclude_unset=True),
    )
    return _handle_result(
        resultado,
        instance=f"/api/v1/projects/{project_id}",
        success_factory=lambda project: project,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Delete a project."""
    resultado = await ProjectService(db).delete_project(project_id=project_id, user_id=str(user_id))
    return _handle_result(
        resultado,
        instance=f"/api/v1/projects/{project_id}",
        success_factory=lambda _: Response(status_code=status.HTTP_204_NO_CONTENT),
    )
