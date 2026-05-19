import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from app.agents import prompts as P
from app.config import get_settings
from app.memory.backends import create_project_backend
from app.memory.wiki_store import WikiStore
from app.tools.vector_search import make_vector_search_tool
from app.tools.web_search import internet_search
from app.tools.wiki_tools import make_wiki_tools


class AgentFactory:
    def __init__(self, wiki: WikiStore):
        self.wiki = wiki
        self.settings = get_settings()
        if self.settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.settings.openai_api_key)
        self.backend = create_project_backend(wiki.abs_path())
        self.wiki_tools = make_wiki_tools(wiki)
        self.vector_tool = make_vector_search_tool(wiki)
        self._checkpointer = MemorySaver()

    @property
    def model(self) -> str:
        return self.settings.llm_model

    @property
    def light_model(self) -> str:
        return self.settings.llm_model_light

    def _subagents(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "research-agent",
                "description": "背景资料调研，输出 research_notes",
                "system_prompt": P.RESEARCH_PROMPT,
                "tools": [internet_search, self.vector_tool, *self.wiki_tools],
                "model": self.light_model,
            },
            {
                "name": "world-architect",
                "description": "扩写世界观并写入 wiki/canon",
                "system_prompt": P.WORLD_ARCHITECT_PROMPT,
                "tools": [self.vector_tool, *self.wiki_tools],
                "model": self.model,
            },
            {
                "name": "continuity-validator",
                "description": "校验设定连续性",
                "system_prompt": P.CONTINUITY_VALIDATOR_PROMPT,
                "tools": [self.vector_tool, *self.wiki_tools],
                "model": self.light_model,
            },
            {
                "name": "plot-planner",
                "description": "生成章节场景节拍",
                "system_prompt": P.PLOT_PLANNER_PROMPT,
                "tools": [self.vector_tool, *self.wiki_tools],
                "model": self.model,
            },
            {
                "name": "story-writer",
                "description": "撰写章节正文",
                "system_prompt": P.STORY_WRITER_PROMPT,
                "tools": self.wiki_tools,
                "model": self.model,
            },
            {
                "name": "style-editor",
                "description": "润色语风不改剧情",
                "system_prompt": P.STYLE_EDITOR_PROMPT,
                "tools": self.wiki_tools,
                "model": self.light_model,
            },
            {
                "name": "wiki-curator",
                "description": "更新 plot_state 与 episodic 摘要",
                "system_prompt": P.WIKI_CURATOR_PROMPT,
                "tools": self.wiki_tools,
                "model": self.light_model,
            },
        ]

    def create_orchestrator(self):
        return create_deep_agent(
            model=self.model,
            backend=self.backend,
            system_prompt=P.ORCHESTRATOR_PROMPT,
            subagents=self._subagents(),
            checkpointer=self._checkpointer,
        )

    def create_specialist(self, name: str):
        spec = next(s for s in self._subagents() if s["name"] == name)
        return create_deep_agent(
            model=spec.get("model", self.model),
            backend=self.backend,
            system_prompt=spec["system_prompt"],
            tools=spec.get("tools", []),
            checkpointer=self._checkpointer,
        )

    def invoke_orchestrator(self, user_message: str, thread_id: str = "default") -> dict:
        agent = self.create_orchestrator()
        config = {"configurable": {"thread_id": thread_id}}
        return agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

    def stream_orchestrator(self, user_message: str, thread_id: str = "default"):
        agent = self.create_orchestrator()
        config = {"configurable": {"thread_id": thread_id}}
        return agent.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
            stream_mode="updates",
        )
