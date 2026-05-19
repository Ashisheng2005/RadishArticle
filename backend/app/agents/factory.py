"""
DeepAgents 工厂：把「模型 + 虚拟文件系统 + 子 Agent」组装成可运行的 LangGraph 图。

架构分层（由外到内）：
  API/CLI → WorkflowService → AgentRouter(LangGraph) → run_world_build/chapter_write
           → AgentFactory.invoke_orchestrator() → create_deep_agent 返回的 CompiledStateGraph

DeepAgents 核心概念：
  1. create_deep_agent()：生成带内置工具（ls/read_file/write_file/task/write_todos 等）的 Agent 图
  2. backend：Agent 读写文件的「虚拟路径」映射到真实存储（见 memory/backends.py）
  3. subagents：协调者可通过 task 工具把子任务交给专家 Agent，各自隔离上下文
  4. checkpointer：按 thread_id 持久化对话与 scratch 状态，便于多轮续写
"""

import os
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
    """为单个小说项目创建 Deep Agent 实例。"""

    def __init__(self, wiki: WikiStore):
        self.wiki = wiki
        self.settings = get_settings()
        if self.settings.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self.settings.openai_api_key)

        # 虚拟文件系统：Agent 里写 /wiki/xxx 会落到项目目录的 wiki/ 下
        self.backend = create_project_backend(wiki.abs_path())

        # 补充工具：DeepAgents 自带文件工具走 backend；下面是直接读 WikiStore 的快捷工具
        self.wiki_tools = make_wiki_tools(wiki)
        self.vector_tool = make_vector_search_tool(wiki)

        # 内存检查点：同一 thread_id 的多轮 invoke 可共享 scratch 与消息历史
        self._checkpointer = MemorySaver()

    @property
    def model(self) -> str:
        """主模型，用于协调者与重任务子 Agent（provider:model 格式）。"""
        return self.settings.llm_model

    @property
    def light_model(self) -> str:
        """轻量模型，用于校验、润色等短任务，节省成本。"""
        return self.settings.llm_model_light

    def _subagents(self) -> list[dict[str, Any]]:
        """
        声明式子 Agent 列表，会注册到协调者的 SubAgentMiddleware。

        每个 dict 对应 DeepAgents 文档中的 SubAgent 规格：
          - name: 协调者 task 工具里使用的标识
          - description: 帮助协调者决定何时委派
          - system_prompt: 专家角色指令（可约定读写哪些虚拟路径）
          - tools: 除内置文件工具外的额外工具
          - model: 可选，覆盖协调者默认模型
        """
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
        """
        创建「协调者」Deep Agent。

        内置能力（无需手写）：
          - write_todos：拆解任务
          - task：调用 _subagents() 中的专家
          - ls/read_file/write_file/edit_file：通过 backend 操作虚拟路径
          - SummarizationMiddleware：上下文过长时自动压缩历史消息
        """
        return create_deep_agent(
            model=self.model,
            backend=self.backend,
            system_prompt=P.ORCHESTRATOR_PROMPT,
            subagents=self._subagents(),
            checkpointer=self._checkpointer,
        )

    def create_specialist(self, name: str):
        """单独创建某一专家 Agent（当前流水线未用，便于调试单个角色）。"""
        spec = next(s for s in self._subagents() if s["name"] == name)
        return create_deep_agent(
            model=spec.get("model", self.model),
            backend=self.backend,
            system_prompt=spec["system_prompt"],
            tools=spec.get("tools", []),
            checkpointer=self._checkpointer,
        )

    def invoke_orchestrator(self, user_message: str, thread_id: str = "default") -> dict:
        """
        同步执行一轮协调者任务。

        user_message：通常由 world_build/chapter_write 拼好的「工作流说明书」，
                      里面写明要委派哪些子 Agent、读写哪些路径。
        thread_id：同一项目/章节建议用不同 id，避免 scratch 串台。
        返回 state dict，其中 messages 为完整对话轨迹。
        """
        agent = self.create_orchestrator()
        config = {"configurable": {"thread_id": thread_id}}
        return agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

    def stream_orchestrator(self, user_message: str, thread_id: str = "default"):
        """流式版本，可按 stream_mode='updates' 推送到前端 SSE（扩展用）。"""
        agent = self.create_orchestrator()
        config = {"configurable": {"thread_id": thread_id}}
        return agent.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
            stream_mode="updates",
        )
