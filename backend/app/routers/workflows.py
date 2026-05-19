import asyncio

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChapterWriteRequest, JobState, JobStatus, TaskType, WorldBuildRequest
from app.services.job_manager import job_manager
from app.services.project_service import ProjectService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/projects/{project_id}", tags=["workflows"])
projects = ProjectService()
workflows = WorkflowService()


def _ensure_project(project_id: str):
    try:
        projects.get_store(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@router.post("/world-build", response_model=JobStatus)
async def world_build(project_id: str, body: WorldBuildRequest, background: bool = True):
    _ensure_project(project_id)
    job_id = job_manager.create_job(project_id, TaskType.WORLD_BUILD)
    if background:
        asyncio.create_task(workflows.run_world_build_async(project_id, body, job_id))
    else:
        result = await workflows.run_world_build_sync(project_id, body)
        job = job_manager.get(job_id)
        if job:
            job.state = JobState.COMPLETED
            job.progress = 1.0
            job.result = result
    return job_manager.get(job_id)


@router.post("/chapters", response_model=JobStatus)
async def write_chapter(project_id: str, body: ChapterWriteRequest, background: bool = True):
    _ensure_project(project_id)
    job_id = job_manager.create_job(project_id, TaskType.CHAPTER_WRITE)
    if background:
        asyncio.create_task(workflows.run_chapter_write_async(project_id, body, job_id))
    else:
        result = await workflows.run_chapter_write_sync(project_id, body)
        job = job_manager.get(job_id)
        if job:
            job.state = JobState.COMPLETED
            job.progress = 1.0
            job.result = result
    return job_manager.get(job_id)


@router.post("/memory/compact", response_model=JobStatus)
async def memory_compact(project_id: str):
    _ensure_project(project_id)
    job_id = job_manager.create_job(project_id, TaskType.MEMORY_COMPACT)
    asyncio.create_task(workflows.run_memory_compact_async(project_id, job_id))
    return job_manager.get(job_id)
