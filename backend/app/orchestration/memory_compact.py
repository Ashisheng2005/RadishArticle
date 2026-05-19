from typing import Any, Callable

from app.agents.factory import AgentFactory
from app.memory.compact import MemoryCompactor
from app.memory.vector_store import WikiVectorStore
from app.memory.wiki_store import WikiStore
from app.models.schemas import WorkflowEvent


async def run_memory_compact(
    wiki: WikiStore,
    reindex_vectors: bool = True,
    on_event: Callable[[WorkflowEvent], Any] | None = None,
) -> dict:
    async def emit(stage: str, message: str, progress: float):
        if on_event:
            ev = WorkflowEvent(stage=stage, message=message, progress=progress)
            result = on_event(ev)
            if hasattr(result, "__await__"):
                await result

    await emit("compact", "整理记忆索引…", 0.2)
    compactor = MemoryCompactor(wiki)
    stats = compactor.run()

    await emit("vector", "重建向量索引…", 0.6)
    indexed = 0
    if reindex_vectors:
        vs = WikiVectorStore(wiki)
        indexed = vs.index_wiki()

    await emit("agent_review", "Agent 复核…", 0.8)
    try:
        factory = AgentFactory(wiki)
        factory.invoke_orchestrator(
            "委派 wiki-curator 检查重复实体与 plot_state，输出整理报告到 /scratch/compact_report.md",
            thread_id=f"compact-{wiki.project_id}",
        )
    except Exception:
        pass

    await emit("done", "记忆整理完成", 1.0)
    return {**stats, "vectors_indexed": indexed}
