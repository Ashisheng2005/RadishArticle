import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.services.job_manager import job_manager

router = APIRouter(prefix="/projects/{project_id}/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(project_id: str, job_id: str):
    job = job_manager.get(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}/stream")
async def stream_job(project_id: str, job_id: str):
    job = job_manager.get(job_id)
    if not job or job.project_id != project_id:
        raise HTTPException(404, "Job not found")

    async def event_generator():
        async for ev in job_manager.subscribe(job_id):
            yield {
                "event": ev.stage,
                "data": json.dumps(ev.model_dump(), ensure_ascii=False),
            }

    return EventSourceResponse(event_generator())
