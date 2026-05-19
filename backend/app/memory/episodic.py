from datetime import datetime

from app.memory.schemas import ChapterContext, EpisodicRecord, MemoryIndex
from app.memory.wiki_store import WikiStore


class EpisodicMemoryStore:
    def __init__(self, wiki: WikiStore):
        self.wiki = wiki

    def load_index(self) -> MemoryIndex:
        data = self.wiki.read_json("memory/index.json")
        return MemoryIndex(**data)

    def save_index(self, index: MemoryIndex) -> None:
        index.updated_at = datetime.utcnow()
        self.wiki.write_json("memory/index.json", index.model_dump(mode="json"))

    def save_episodic(self, record: EpisodicRecord) -> str:
        rel = f"memory/episodic/ch_{record.chapter:03d}.json"
        self.wiki.write_json(rel, record.model_dump(mode="json"))
        return rel

    def load_episodic(self, chapter: int) -> EpisodicRecord | None:
        rel = f"memory/episodic/ch_{chapter:03d}.json"
        path = self.wiki.project_root / rel
        if not path.exists():
            return None
        data = self.wiki.read_json(rel)
        return EpisodicRecord(**data)

    def update_plot_state(self, summary_block: str) -> None:
        _, body = self.wiki.parse_markdown("wiki/plot_state.md")
        new_body = body.rstrip() + "\n\n" + summary_block.strip() + "\n"
        fm, _ = self.wiki.parse_markdown("wiki/plot_state.md")
        self.wiki.write_markdown("wiki/plot_state.md", fm or {"id": "plot_state"}, new_body)

    def update_entity_index(self, record: EpisodicRecord) -> None:
        index = self.load_index()
        index.last_chapter = record.chapter
        for delta in record.character_deltas:
            index.entities.setdefault(delta.character, {})
            index.entities[delta.character]["last_chapter"] = record.chapter
            index.entities[delta.character]["last_state"] = delta.changes
        self.save_index(index)

    def build_chapter_context(self, chapter_num: int, mentioned: list[str] | None = None) -> ChapterContext:
        plot_state = self.wiki.read_text("wiki/plot_state.md")
        prev = self.load_episodic(chapter_num - 1) if chapter_num > 1 else None

        character_files: list[str] = []
        location_files: list[str] = []
        chars_dir = self.wiki.project_root / "wiki" / "characters"
        locs_dir = self.wiki.project_root / "wiki" / "locations"
        if mentioned:
            for name in mentioned:
                slug = name.replace(" ", "_").lower()
                cp = chars_dir / f"{slug}.md"
                lp = locs_dir / f"{slug}.md"
                if cp.exists():
                    character_files.append(f"wiki/characters/{slug}.md")
                if lp.exists():
                    location_files.append(f"wiki/locations/{slug}.md")
        else:
            character_files = [
                f"wiki/characters/{p.name}"
                for p in chars_dir.glob("*.md")
            ][:5]
            location_files = [
                f"wiki/locations/{p.name}"
                for p in locs_dir.glob("*.md")
            ][:3]

        extra = ["wiki/timeline.md", "wiki/canon/tone.md", "wiki/canon/world.md"]
        extra = [p for p in extra if (self.wiki.project_root / p).exists()]

        return ChapterContext(
            plot_state=plot_state,
            previous_episodic=prev,
            character_files=character_files,
            location_files=location_files,
            extra_paths=extra,
        )
