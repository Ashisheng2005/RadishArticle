import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import yaml

from app.config import get_settings
from app.models.schemas import ProjectBootstrap, ProjectCreate, ProjectInfo, WikiNode


class WikiStore:
    """Local filesystem LLM Wiki for a novel project."""

    WIKI_SUBDIRS = [
        "wiki/canon",
        "wiki/characters",
        "wiki/locations",
        "wiki/factions",
        "chapters",
        "memory/episodic",
        "meta",
        "exports",
        "scratch",
    ]

    def __init__(self, project_id: str | None = None, root: Path | None = None):
        settings = get_settings()
        self.data_root = settings.data_root
        if root is not None:
            self.project_root = root
        elif project_id:
            self.project_root = self.data_root / project_id
        else:
            raise ValueError("project_id or root required")
        self.project_id = project_id or self.project_root.name

    @classmethod
    def list_projects(cls) -> list[ProjectInfo]:
        settings = get_settings()
        projects: list[ProjectInfo] = []
        if not settings.data_root.exists():
            return projects
        for path in sorted(settings.data_root.iterdir()):
            if not path.is_dir():
                continue
            meta = path / "meta" / "project.json"
            if not meta.exists():
                continue
            data = json.loads(meta.read_text(encoding="utf-8"))
            chapters = list((path / "chapters").glob("ch_*.md")) if (path / "chapters").exists() else []
            projects.append(
                ProjectInfo(
                    id=path.name,
                    title=data.get("title", path.name),
                    genre=data.get("genre", "fiction"),
                    tone=data.get("tone", ""),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    chapter_count=len(chapters),
                )
            )
        return projects

    @classmethod
    def create_project(cls, payload: ProjectCreate) -> "WikiStore":
        project_id = uuid.uuid4().hex[:12]
        store = cls(project_id=project_id)
        store._init_layout(payload)
        return store

    def _init_layout(self, payload: ProjectCreate) -> None:
        for sub in self.WIKI_SUBDIRS:
            (self.project_root / sub).mkdir(parents=True, exist_ok=True)

        now = datetime.utcnow()
        project_meta = {
            "id": self.project_id,
            "title": payload.title,
            "genre": payload.genre,
            "tone": payload.tone,
            "created_at": now.isoformat(),
        }
        bootstrap = ProjectBootstrap(
            title=payload.title,
            genre=payload.genre,
            tone=payload.tone,
            outline=payload.outline,
            background=payload.background,
            character_notes=payload.character_notes,
            research_hints=payload.research_hints,
            created_at=now,
        )
        self.write_json("meta/project.json", project_meta)
        self.write_json("meta/bootstrap.json", bootstrap.model_dump(mode="json"))

        self.write_markdown(
            "wiki/plot_state.md",
            {"id": "plot_state", "type": "plot", "canon_level": "soft"},
            "# 剧情进度\n\n（尚未开始）\n",
        )
        self.write_markdown(
            "wiki/timeline.md",
            {"id": "timeline", "type": "timeline", "canon_level": "soft"},
            "# 时间线\n\n",
        )
        self.write_json("memory/index.json", {"entities": {}, "last_chapter": 0})

    def read_json(self, rel_path: str) -> dict:
        path = self.project_root / rel_path
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, rel_path: str, data: dict) -> None:
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_text(self, rel_path: str) -> str:
        return (self.project_root / rel_path).read_text(encoding="utf-8")

    def write_text(self, rel_path: str, content: str) -> None:
        path = self.project_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_markdown(self, rel_path: str, frontmatter: dict, body: str) -> None:
        fm = dict(frontmatter)
        fm["last_updated"] = datetime.utcnow().isoformat()
        content = "---\n" + yaml.dump(fm, allow_unicode=True, default_flow_style=False) + "---\n" + body.lstrip()
        self.write_text(rel_path, content)

    def parse_markdown(self, rel_path: str) -> tuple[dict, str]:
        text = self.read_text(rel_path)
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not match:
            return {}, text
        fm = yaml.safe_load(match.group(1)) or {}
        return fm, match.group(2)

    def get_bootstrap(self) -> ProjectBootstrap:
        data = self.read_json("meta/bootstrap.json")
        return ProjectBootstrap(**data)

    def get_project_info(self) -> ProjectInfo:
        data = self.read_json("meta/project.json")
        chapters = list((self.project_root / "chapters").glob("ch_*.md"))
        return ProjectInfo(
            id=self.project_id,
            title=data["title"],
            genre=data.get("genre", "fiction"),
            tone=data.get("tone", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            chapter_count=len(chapters),
        )

    def next_chapter_number(self) -> int:
        chapters_dir = self.project_root / "chapters"
        if not chapters_dir.exists():
            return 1
        nums = []
        for p in chapters_dir.glob("ch_*.md"):
            m = re.match(r"ch_(\d+)", p.stem)
            if m:
                nums.append(int(m.group(1)))
        return max(nums, default=0) + 1

    def list_wiki_tree(self, sub_path: str = "wiki") -> WikiNode:
        base = self.project_root / sub_path

        def walk(path: Path, rel: str) -> WikiNode:
            children: list[WikiNode] = []
            if path.is_dir():
                for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    child_rel = f"{rel}/{child.name}".replace("\\", "/")
                    children.append(walk(child, child_rel))
            return WikiNode(path=rel, name=path.name, is_dir=path.is_dir(), children=children)

        return walk(base, sub_path.replace("\\", "/"))

    def glob_wiki(self, pattern: str = "**/*.md") -> list[str]:
        wiki_root = self.project_root / "wiki"
        return [str(p.relative_to(self.project_root)).replace("\\", "/") for p in wiki_root.glob(pattern)]

    def abs_path(self) -> Path:
        return self.project_root.resolve()
