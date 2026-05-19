"""
记忆整理流水线（memory_compact）。

混合模式：
  1. Python 规则引擎 MemoryCompactor：去重实体索引、裁剪过长 plot_state、归档旧 episodic
  2. Chroma 重建向量索引，供 wiki_vector_search 语义检索
  3. 可选再调 DeepAgents wiki-curator 做语义层面的整理报告
"""

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
            if hasattr(r, "__await__"):
                await r

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
        pass  # 无 API Key 时仅保留 Python 侧整理结果

    await emit("done", "记忆整理完成", 1.0)
    return {**stats, "vectors_indexed": indexed}
