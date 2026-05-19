from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WikiFrontmatter(BaseModel):
    id: str = ""
    type: str = "note"
    canon_level: str = "soft"  # hard | soft | draft
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = Field(default_factory=list)


class CharacterDelta(BaseModel):
    character: str
    changes: str


class EpisodicRecord(BaseModel):
    chapter: int
    title: str = ""
    summary: str
    character_deltas: list[CharacterDelta] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)
    key_events: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryIndex(BaseModel):
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict)
    last_chapter: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChapterContext(BaseModel):
    plot_state: str
    previous_episodic: EpisodicRecord | None = None
    character_files: list[str] = Field(default_factory=list)
    location_files: list[str] = Field(default_factory=list)
    extra_paths: list[str] = Field(default_factory=list)
