import asyncio
import uuid
from collections import defaultdict
from typing import Any, AsyncIterator, Callable

from app.models.schemas import JobState, JobStatus, TaskType, WorkflowEvent


class JobManager:
    """In-memory async job tracking with event queues for SSE."""

    def __init__(self):
        self._jobs: dict[str, JobStatus] = {}
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def create_job(self, project_id: str, task_type: TaskType) -> str:
        job_id = uuid.uuid4().hex[:16]
        self._jobs[job_id] = JobStatus(
            job_id=job_id,
            project_id=project_id,
            task_type=task_type,
            state=JobState.PENDING,
        )
        return job_id

    def get(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    async def emit(self, job_id: str, event: WorkflowEvent) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.stage = event.stage
            job.message = event.message
            job.progress = event.progress
            job.state = JobState.RUNNING
        await self._queues[job_id].put(event)

    async def complete(self, job_id: str, result: dict[str, Any] | None = None) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.state = JobState.COMPLETED
            job.progress = 1.0
            job.result = result
        await self._queues[job_id].put(WorkflowEvent(stage="done", message="完成", progress=1.0))

    async def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.state = JobState.FAILED
            job.error = error
        await self._queues[job_id].put(WorkflowEvent(stage="error", message=error, progress=0.0))

    async def subscribe(self, job_id: str) -> AsyncIterator[WorkflowEvent]:
        queue = self._queues[job_id]
        while True:
            event = await queue.get()
            yield event
            if event.stage in ("done", "error"):
                break

    async def run_in_background(
        self,
        job_id: str,
        coro_factory: Callable[[], Any],
    ) -> None:
        try:
            await coro_factory()
            if self._jobs[job_id].state != JobState.FAILED:
                await self.complete(job_id)
        except Exception as e:
            await self.fail(job_id, str(e))


job_manager = JobManager()
