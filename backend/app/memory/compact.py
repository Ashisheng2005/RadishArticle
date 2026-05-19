import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.memory.episodic import EpisodicMemoryStore
from app.memory.wiki_store import WikiStore


class MemoryCompactor:
    """Merge episodic summaries, dedupe entity index, archive long plot_state."""

    PLOT_STATE_MAX_LINES = 200
    EPISODIC_ARCHIVE_EVERY = 10

    def __init__(self, wiki: WikiStore):
        self.wiki = wiki
        self.episodic = EpisodicMemoryStore(wiki)

    def run(self) -> dict:
        results: dict = {"archived": False, "entities_merged": 0, "plot_trimmed": False}

        index = self.episodic.load_index()
        entities_before = len(index.entities)
        index.entities = self._dedupe_entities(index.entities)
        results["entities_merged"] = entities_before - len(index.entities)
        self.episodic.save_index(index)

        results["plot_trimmed"] = self._trim_plot_state()
        results["archived"] = self._maybe_archive_episodic(index.last_chapter)
        return results

    def _dedupe_entities(self, entities: dict) -> dict:
        by_key: dict[str, dict] = {}
        for name, meta in entities.items():
            key = name.strip().lower()
            if key not in by_key or meta.get("last_chapter", 0) > by_key[key].get("last_chapter", 0):
                by_key[key] = {**meta, "_canonical": name}
        return {v.pop("_canonical", k): v for k, v in by_key.items()}

    def _trim_plot_state(self) -> bool:
        path = self.wiki.project_root / "wiki" / "plot_state.md"
        if not path.exists():
            return False
        fm, body = self.wiki.parse_markdown("wiki/plot_state.md")
        lines = body.splitlines()
        if len(lines) <= self.PLOT_STATE_MAX_LINES:
            return False
        kept = lines[:20] + ["\n> ... 较早剧情已归档至 memory/archives/plot_archive.md ...\n"] + lines[-(self.PLOT_STATE_MAX_LINES - 40) :]
        archive_dir = self.wiki.project_root / "memory" / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"plot_archive_{datetime.utcnow().strftime('%Y%m%d')}.md"
        archive_path.write_text("\n".join(lines[:- (self.PLOT_STATE_MAX_LINES - 40)]), encoding="utf-8")
        self.wiki.write_markdown("wiki/plot_state.md", fm or {}, "\n".join(kept))
        return True

    def _maybe_archive_episodic(self, last_chapter: int) -> bool:
        if last_chapter < self.EPISODIC_ARCHIVE_EVERY:
            return False
        episodic_dir = self.wiki.project_root / "memory" / "episodic"
        files = sorted(episodic_dir.glob("ch_*.json"))
        if len(files) < self.EPISODIC_ARCHIVE_EVERY:
            return False

        archive_dir = self.wiki.project_root / "memory" / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        vol = last_chapter // self.EPISODIC_ARCHIVE_EVERY
        archive_file = archive_dir / f"episodic_vol_{vol:02d}.json"
        if archive_file.exists():
            return False

        to_archive = files[: len(files) - 3]
        summaries: list[dict] = []
        for f in to_archive:
            summaries.append(json.loads(f.read_text(encoding="utf-8")))
        archive_file.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
