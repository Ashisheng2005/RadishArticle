"""
AgentRouter：应用层的「工作流分发器」（LangGraph StateGraph）。

与 DeepAgents 的关系：
  - 本模块只做「选哪条业务流水线」：world_build / chapter_write / memory_compact
  - 每条流水线内部再调用 AgentFactory.invoke_orchestrator()，由 DeepAgents 负责多 Agent 协作
  - 相当于两层图：
      LangGraph(AgentRouter)  →  节点函数 run_*  →  DeepAgents(协调者 + 子 Agent)

这样拆分的好处：
  - API/CLI 只需传 task_type，不必了解子 Agent 细节
  - on_event 回调可上报阶段进度给 SSE，与 Agent 内部步骤解耦
"""

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.memory.wiki_store import WikiStore
from app.models.schemas import TaskType, WorkflowEvent
from app.orchestration.chapter_write import run_chapter_write
from app.orchestration.memory_compact import run_memory_compact
from app.orchestration.world_build import run_world_build


class RouterState(TypedDict, total=False):
    """LangGraph 节点之间传递的状态包。"""

    task_type: str
    project_id: str
    wiki: WikiStore
    params: dict  # 各流水线特有参数（梗概、章节号等）
    result: dict
    on_event: Callable[[WorkflowEvent], Any]  # 可选，用于推送 SSE


async def _node_world_build(state: RouterState) -> RouterState:
    """节点：世界观构建。"""
    wiki = state["wiki"]
    params = state.get("params", {})
    on_event = state.get("on_event")

    async def wrapped(ev: WorkflowEvent):
        if on_event:
            r = on_event(ev)
            if hasattr(r, "__await__"):
                await r

    result = await run_world_build(
        wiki,
        extra_instructions=params.get("extra_instructions", ""),
        on_event=wrapped if on_event else None,
    )
    return {**state, "result": result}


async def _node_chapter_write(state: RouterState) -> RouterState:
    """节点：章节写作。"""
    wiki = state["wiki"]
    params = state.get("params", {})
    on_event = state.get("on_event")

    async def wrapped(ev: WorkflowEvent):
        if on_event:
            r = on_event(ev)
            if hasattr(r, "__await__"):
                await r

    result = await run_chapter_write(
        wiki,
        outline=params.get("outline"),
        auto_plot=params.get("auto_plot", False),
        chapter_number=params.get("chapter_number"),
        chapter_title=params.get("title", ""),
        pov=params.get("pov", ""),
        on_event=wrapped if on_event else None,
    )
    return {**state, "result": result}


async def _node_memory_compact(state: RouterState) -> RouterState:
    """节点：记忆压缩与向量索引重建。"""
    wiki = state["wiki"]
    on_event = state.get("on_event")

    async def wrapped(ev: WorkflowEvent):
        if on_event:
            r = on_event(ev)
            if hasattr(r, "__await__"):
                await r

    result = await run_memory_compact(wiki, on_event=wrapped if on_event else None)
    return {**state, "result": result}


def _route_task(state: RouterState) -> str:
    """条件边：根据 task_type 选择入口节点名。"""
    return state.get("task_type", TaskType.WORLD_BUILD.value)


class AgentRouter:
    """
    编译后的 LangGraph 图，对外暴露 run()。

    图结构：
        START --[task_type]--> world_build | chapter_write | memory_compact --> END
    """

    def __init__(self):
        graph = StateGraph(RouterState)
        graph.add_node("world_build", _node_world_build)
        graph.add_node("chapter_write", _node_chapter_write)
        graph.add_node("memory_compact", _node_memory_compact)

        # 从 START 按 task_type 分流到三个节点之一
        graph.add_conditional_edges(
            START,
            _route_task,
            {
                TaskType.WORLD_BUILD.value: "world_build",
                TaskType.CHAPTER_WRITE.value: "chapter_write",
                TaskType.MEMORY_COMPACT.value: "memory_compact",
            },
        )
        graph.add_edge("world_build", END)
        graph.add_edge("chapter_write", END)
        graph.add_edge("memory_compact", END)
        self._graph = graph.compile()

    async def run(
        self,
        task_type: TaskType,
        wiki: WikiStore,
        params: dict | None = None,
        on_event: Callable[[WorkflowEvent], Any] | None = None,
    ) -> dict:
        """执行一次工作流，返回业务结果 dict（写入 result 字段）。"""
        state: RouterState = {
            "task_type": task_type.value,
            "project_id": wiki.project_id,
            "wiki": wiki,
            "params": params or {},
            "on_event": on_event,
        }
        final = await self._graph.ainvoke(state)
        return final.get("result", {})
