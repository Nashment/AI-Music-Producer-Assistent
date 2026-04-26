"""
Projects endpoints - Project management
"""

import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.project_service import ProjectService
from app.api.dependencies import get_db, get_current_user_id
from app.domain.dtos.endpoints.projects import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Create a new music project
    
    Args:
        project_data: Project information
        
    Returns:
        Created project information
    """
    service = ProjectService(db)
    project = await service.create_project(
        user_id=user_id,
        title=project_data.title,
        description=project_data.description,
        tempo=project_data.tempo
    )
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_user_projects(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Get all projects for authenticated user
    
    Returns:
        List of user projects
    """
    service = ProjectService(db)
    projects = await service.list_user_projects(user_id=user_id)
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """
    Get specific project by ID
    
    Args:
        project_id: Project identifier
        
    Returns:
        Project details
    """
    service = ProjectService(db)
    project = await service.get_project(project_id=project_id, user_id=user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Update project information"""
    service = ProjectService(db)
    update_dict = project_update.model_dump(exclude_unset=True)
    project = await service.update_project(
        project_id=project_id,
        user_id=user_id,
        update_data=update_dict
    )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Delete a project"""
    service = ProjectService(db)
    success = await service.delete_project(project_id=project_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
