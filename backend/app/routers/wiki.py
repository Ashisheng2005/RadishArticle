from fastapi import APIRouter, HTTPException, Query

from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects/{project_id}/wiki", tags=["wiki"])
service = ProjectService()


@router.get("/tree")
async def wiki_tree(project_id: str, path: str = Query("wiki", alias="path")):
    try:
        return service.get_wiki_tree(project_id, path)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@router.get("/file")
async def read_wiki_file(project_id: str, path: str = Query(..., description="Relative path e.g. wiki/plot_state.md")):
    try:
        content = service.read_wiki_file(project_id, path)
        return {"path": path, "content": content}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
