"""
backend/routes/projects.py
Router de gerenciamento de projetos (CRUD + otimistic locking).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.auth import require_token
from backend.models import ProjectUpdateRequest
from backend.routes.deps import project_service
from backend.services.projects import ConflictError, NotFoundError

router = APIRouter()


@router.get("/api/v1/projects/{project_id}", tags=["Projects"])
async def get_project(
    project_id: str,
    _: None = Depends(require_token),
):
    """
    Retorna os metadados de um projeto pelo seu ID.
    Retorna 404 se o projeto não existir.
    """
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")
    return project


@router.put("/api/v1/projects/{project_id}", tags=["Projects"])
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    _: None = Depends(require_token),
):
    """
    Atualiza metadados de projeto com Optimistic Locking.
    Requer o campo 'version' correspondente à versão atual no banco.
    """
    try:
        updated = project_service.update_project(
            project_id=project_id,
            updates=req.model_dump(exclude={"version"}, exclude_unset=True),
            expected_version=req.version,
        )
        return updated
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
