from langchain.tools import tool

from app.memory.vector_store import WikiVectorStore
from app.memory.wiki_store import WikiStore


def make_vector_search_tool(wiki: WikiStore):
    store = WikiVectorStore(wiki)

    @tool
    def wiki_vector_search(query: str, max_results: int = 5) -> str:
        """Semantic search across wiki documents using embeddings."""
        if not store.enabled:
            return "Vector search disabled (CHROMA_ENABLED=false)."
        hits = store.search(query, k=max_results)
        if not hits:
            return "No semantic matches."
        return "\n\n".join(f"## {h['path']}\n{h['snippet']}" for h in hits)

    return wiki_vector_search
