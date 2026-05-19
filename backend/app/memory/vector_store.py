from pathlib import Path

from app.config import get_settings
from app.memory.wiki_store import WikiStore


class WikiVectorStore:
    """Optional Chroma-backed semantic wiki search."""

    def __init__(self, wiki: WikiStore):
        self.wiki = wiki
        self.settings = get_settings()
        self._collection = None

    @property
    def enabled(self) -> bool:
        return self.settings.chroma_enabled

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb

        persist = self.wiki.project_root / ".chroma"
        persist.mkdir(exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist))
        self._collection = client.get_or_create_collection(
            name=f"wiki_{self.wiki.project_id}",
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def index_wiki(self) -> int:
        if not self.enabled:
            return 0
        col = self._get_collection()
        ids, docs, metas = [], [], []
        for rel in self.wiki.glob_wiki("**/*.md"):
            text = self.wiki.read_text(rel)
            chunk_id = rel.replace("/", "_")
            ids.append(chunk_id)
            docs.append(text[:8000])
            metas.append({"path": rel})
        if ids:
            col.upsert(ids=ids, documents=docs, metadatas=metas)
        return len(ids)

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.enabled:
            return []
        col = self._get_collection()
        if col.count() == 0:
            self.index_wiki()
        if col.count() == 0:
            return []
        result = col.query(query_texts=[query], n_results=min(k, col.count()))
        out = []
        for i, doc_id in enumerate(result["ids"][0]):
            out.append(
                {
                    "path": result["metadatas"][0][i].get("path", doc_id),
                    "snippet": result["documents"][0][i][:500],
                }
            )
        return out
