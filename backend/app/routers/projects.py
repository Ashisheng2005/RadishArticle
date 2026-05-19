from fastapi import APIRouter, HTTPException

from app.models.schemas import ProjectCreate, ProjectInfo
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])
service = ProjectService()


@router.get("", response_model=list[ProjectInfo])
async def list_projects():
    return service.list_projects()


@router.post("", response_model=ProjectInfo, status_code=201)
async def create_project(payload: ProjectCreate):
    return service.create_project(payload)


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str):
    try:
        return service.get_store(project_id).get_project_info()
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
