"""
工作流服务：API / CLI 的统一入口。

调用链（以异步世界观构建为例）：
  POST /world-build
    → WorkflowService.run_world_build_async
    → job_manager 后台任务 + SSE 队列
    → AgentRouter.run(WORLD_BUILD)
    → run_world_build → AgentFactory.invoke_orchestrator

同步版本（CLI 使用）跳过 JobManager，直接 await router.run()。
"""

from app.models.schemas import (
    ChapterWriteRequest,
    TaskType,
    WorkflowEvent,
    WorldBuildRequest,
)
from app.orchestration.router import AgentRouter
from app.services.job_manager import job_manager
from app.services.project_service import ProjectService


class WorkflowService:
    def __init__(self):
        self.projects = ProjectService()
        self.router = AgentRouter()

    async def run_world_build_async(
        self,
        project_id: str,
        request: WorldBuildRequest,
        job_id: str,
    ) -> None:
        wiki = self.projects.get_store(project_id)

        async def on_event(ev: WorkflowEvent):
            await job_manager.emit(job_id, ev)

        async def work():
            result = await self.router.run(
                TaskType.WORLD_BUILD,
                wiki,
                params={"extra_instructions": request.extra_instructions},
                on_event=on_event,
            )
            job = job_manager.get(job_id)
            if job:
                job.result = result

        await job_manager.run_in_background(job_id, work)

    async def run_chapter_write_async(
        self,
        project_id: str,
        request: ChapterWriteRequest,
        job_id: str,
    ) -> None:
        wiki = self.projects.get_store(project_id)

        async def on_event(ev: WorkflowEvent):
            await job_manager.emit(job_id, ev)

        async def work():
            result = await self.router.run(
                TaskType.CHAPTER_WRITE,
                wiki,
                params={
                    "outline": request.outline,
                    "auto_plot": request.auto_plot,
                    "chapter_number": request.chapter_number,
                    "title": request.title,
                    "pov": request.pov,
                },
                on_event=on_event,
            )
            job = job_manager.get(job_id)
            if job:
                job.result = result

        await job_manager.run_in_background(job_id, work)

    async def run_memory_compact_async(self, project_id: str, job_id: str) -> None:
        wiki = self.projects.get_store(project_id)

        async def on_event(ev: WorkflowEvent):
            await job_manager.emit(job_id, ev)

        async def work():
            result = await self.router.run(
                TaskType.MEMORY_COMPACT,
                wiki,
                on_event=on_event,
            )
            job = job_manager.get(job_id)
            if job:
                job.result = result

        await job_manager.run_in_background(job_id, work)

    async def run_world_build_sync(self, project_id: str, request: WorldBuildRequest) -> dict:
        wiki = self.projects.get_store(project_id)
        return await self.router.run(
            TaskType.WORLD_BUILD,
            wiki,
            params={"extra_instructions": request.extra_instructions},
        )

    async def run_chapter_write_sync(self, project_id: str, request: ChapterWriteRequest) -> dict:
        wiki = self.projects.get_store(project_id)
        return await self.router.run(
            TaskType.CHAPTER_WRITE,
            wiki,
            params={
                "outline": request.outline,
                "auto_plot": request.auto_plot,
                "chapter_number": request.chapter_number,
                "title": request.title,
                "pov": request.pov,
            },
        )
