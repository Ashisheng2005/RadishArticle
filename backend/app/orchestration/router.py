from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.memory.wiki_store import WikiStore
from app.models.schemas import TaskType, WorkflowEvent
from app.orchestration.chapter_write import run_chapter_write
from app.orchestration.memory_compact import run_memory_compact
from app.orchestration.world_build import run_world_build


class RouterState(TypedDict, total=False):
    task_type: str
    project_id: str
    wiki: WikiStore
    params: dict
    result: dict
    on_event: Callable[[WorkflowEvent], Any]


async def _node_world_build(state: RouterState) -> RouterState:
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
    return state.get("task_type", TaskType.WORLD_BUILD.value)


class AgentRouter:
    """LangGraph dispatcher for novel workflows."""

    def __init__(self):
        graph = StateGraph(RouterState)
        graph.add_node("world_build", _node_world_build)
        graph.add_node("chapter_write", _node_chapter_write)
        graph.add_node("memory_compact", _node_memory_compact)

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
        state: RouterState = {
            "task_type": task_type.value,
            "project_id": wiki.project_id,
            "wiki": wiki,
            "params": params or {},
            "on_event": on_event,
        }
        final = await self._graph.ainvoke(state)
        return final.get("result", {})
