"""Typer CLI for RadishArticle — shares backend services."""

import asyncio
import sys
from pathlib import Path

# Ensure backend package is importable
_ROOT = Path(__file__).resolve().parents[1]
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import typer
from rich.console import Console
from rich.table import Table

from app.models.schemas import ChapterWriteRequest, ProjectCreate, WorldBuildRequest
from app.services.project_service import ProjectService
from app.services.workflow_service import WorkflowService

app = typer.Typer(name="radish", help="RadishArticle 小说自动化 CLI")
projects_app = typer.Typer(help="项目管理")
app.add_typer(projects_app, name="projects")

console = Console()
_project_svc = ProjectService()
_workflow_svc = WorkflowService()


@projects_app.command("list")
def list_projects():
    rows = _project_svc.list_projects()
    table = Table(title="小说项目")
    table.add_column("ID")
    table.add_column("标题")
    table.add_column("章节数")
    for p in rows:
        table.add_row(p.id, p.title, str(p.chapter_count))
    console.print(table)


@projects_app.command("create")
def create_project(
    title: str = typer.Option(..., prompt=True),
    genre: str = typer.Option("fiction"),
    tone: str = typer.Option("", prompt="基调"),
    outline: str = typer.Option("", prompt="大纲"),
    background: str = typer.Option("", prompt="背景"),
    character_notes: str = typer.Option("", prompt="人设"),
):
    payload = ProjectCreate(
        title=title,
        genre=genre,
        tone=tone,
        outline=outline,
        background=background,
        character_notes=character_notes,
    )
    info = _project_svc.create_project(payload)
    console.print(f"[green]已创建项目[/green] {info.id} — {info.title}")


@app.command("world-build")
def world_build_cmd(
    project_id: str,
    extra: str = typer.Option("", help="额外说明"),
):
    async def _run():
        return await _workflow_svc.run_world_build_sync(
            project_id, WorldBuildRequest(extra_instructions=extra)
        )

    console.print(f"[cyan]构建世界观[/cyan] {project_id} …")
    result = asyncio.run(_run())
    console.print(result)


@app.command("write-chapter")
def write_chapter_cmd(
    project_id: str,
    outline: str = typer.Option(None, help="章节梗概"),
    auto_plot: bool = typer.Option(False, help="全自动构想情节"),
    chapter: int = typer.Option(None, help="章节号"),
    title: str = typer.Option(""),
):
    req = ChapterWriteRequest(
        outline=outline,
        auto_plot=auto_plot,
        chapter_number=chapter,
        title=title,
    )

    async def _run():
        return await _workflow_svc.run_chapter_write_sync(project_id, req)

    console.print(f"[cyan]写作章节[/cyan] {project_id} …")
    result = asyncio.run(_run())
    console.print(result)


@app.command("compact-memory")
def compact_memory_cmd(project_id: str):
    from app.models.schemas import TaskType
    from app.orchestration.router import AgentRouter

    async def _run():
        wiki = _project_svc.get_store(project_id)
        router = AgentRouter()
        return await router.run(TaskType.MEMORY_COMPACT, wiki)

    console.print(f"[cyan]整理记忆[/cyan] {project_id} …")
    result = asyncio.run(_run())
    console.print(result)


if __name__ == "__main__":
    app()
