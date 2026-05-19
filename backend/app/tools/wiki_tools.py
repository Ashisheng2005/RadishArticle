from langchain.tools import tool

from app.memory.wiki_store import WikiStore


def make_wiki_tools(wiki: WikiStore) -> list:
    """Read-only wiki tools for agents outside deepagents FS."""

    @tool
    def wiki_read(path: str) -> str:
        """Read a project wiki file by relative path (e.g. wiki/plot_state.md)."""
        try:
            return wiki.read_text(path)
        except FileNotFoundError:
            return f"File not found: {path}"

    @tool
    def wiki_list(directory: str = "wiki") -> str:
        """List markdown files under a wiki subdirectory."""
        base = wiki.project_root / directory
        if not base.exists():
            return "Directory not found."
        files = [str(p.relative_to(wiki.project_root)).replace("\\", "/") for p in base.rglob("*.md")]
        return "\n".join(sorted(files)) or "(empty)"

    @tool
    def wiki_search(query: str, max_results: int = 5) -> str:
        """Keyword search across wiki markdown files."""
        query_lower = query.lower()
        hits: list[str] = []
        for rel in wiki.glob_wiki("**/*.md"):
            try:
                content = wiki.read_text(rel)
                if query_lower in content.lower():
                    snippet = content[:400].replace("\n", " ")
                    hits.append(f"## {rel}\n{snippet}...")
            except OSError:
                continue
            if len(hits) >= max_results:
                break
        return "\n\n".join(hits) if hits else "No matches."

    return [wiki_read, wiki_list, wiki_search]
