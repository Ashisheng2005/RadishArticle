from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    WORLD_BUILD = "world_build"
    CHAPTER_WRITE = "chapter_write"
    MEMORY_COMPACT = "memory_compact"
    WIKI_QUERY = "wiki_query"


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProjectCreate(BaseModel):
    title: str
    genre: str = "fiction"
    tone: str = ""
    outline: str = ""
    background: str = ""
    character_notes: str = ""
    research_hints: str = ""


class ProjectBootstrap(BaseModel):
    title: str
    genre: str
    tone: str
    outline: str
    background: str
    character_notes: str
    research_hints: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectInfo(BaseModel):
    id: str
    title: str
    genre: str
    tone: str
    created_at: datetime
    chapter_count: int = 0


class WorldBuildRequest(BaseModel):
    extra_instructions: str = ""


class ChapterWriteRequest(BaseModel):
    outline: str | None = None
    auto_plot: bool = False
    chapter_number: int | None = None
    pov: str = ""
    title: str = ""


class WikiNode(BaseModel):
    path: str
    name: str
    is_dir: bool
    children: list["WikiNode"] = Field(default_factory=list)


class JobStatus(BaseModel):
    job_id: str
    project_id: str
    task_type: TaskType
    state: JobState
    stage: str = ""
    message: str = ""
    progress: float = 0.0
    result: dict[str, Any] | None = None
    error: str | None = None


class WorkflowEvent(BaseModel):
    stage: str
    message: str
    progress: float = 0.0
    data: dict[str, Any] = Field(default_factory=dict)
