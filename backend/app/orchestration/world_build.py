import json
from typing import Any, Callable

from app.agents.factory import AgentFactory
from app.memory.wiki_store import WikiStore
from app.models.schemas import WorkflowEvent


def _bootstrap_context(wiki: WikiStore) -> str:
    b = wiki.get_bootstrap()
    return f"""请执行世界观构建工作流：

## 用户输入
- 标题: {b.title}
- 类型: {b.genre}
- 基调: {b.tone}
- 大纲: {b.outline}
- 背景: {b.background}
- 人设: {b.character_notes}
- 调研提示: {b.research_hints}

## 步骤
1. 委派 research-agent 调研并写入 /scratch/research_notes.md
2. 委派 world-architect 生成 wiki/canon 与人物/地点条目
3. 委派 continuity-validator 校验，若有 error 则修正后重验
4. 委派 wiki-curator 确认 plot_state 初始状态

项目根目录在宿主路径: {wiki.abs_path()}
虚拟路径 /wiki/ /meta/ /memory/ /chapters/ 与 /scratch/ 可用。
"""


async def run_world_build(
    wiki: WikiStore,
    extra_instructions: str = "",
    on_event: Callable[[WorkflowEvent], Any] | None = None,
) -> dict:
    async def emit(stage: str, message: str, progress: float):
        if on_event:
            ev = WorkflowEvent(stage=stage, message=message, progress=progress)
            result = on_event(ev)
            if hasattr(result, "__await__"):
                await result

    await emit("research", "启动背景调研…", 0.1)
    factory = AgentFactory(wiki)
    prompt = _bootstrap_context(wiki)
    if extra_instructions:
        prompt += f"\n\n额外说明: {extra_instructions}"

    await emit("world_architect", "构建世界观…", 0.35)
    try:
        result = factory.invoke_orchestrator(prompt, thread_id=f"world-{wiki.project_id}")
    except Exception as e:
        if "api" in str(e).lower() or "key" in str(e).lower():
            await emit("fallback", "无 API Key，使用模板初始化 wiki", 0.5)
            _fallback_world_build(wiki)
            await emit("wiki_curator", "Wiki 已初始化", 1.0)
            return {"mode": "fallback", "project_id": wiki.project_id}
        raise

    await emit("validate", "连续性校验…", 0.7)
    await emit("wiki_curator", "写入 Wiki…", 0.9)

    validation_path = wiki.project_root / "scratch" / "validation_report.json"
    validation = {}
    if validation_path.exists():
        validation = json.loads(validation_path.read_text(encoding="utf-8"))

    return {
        "mode": "agent",
        "project_id": wiki.project_id,
        "validation": validation,
        "messages": _extract_last_message(result),
    }


def _fallback_world_build(wiki: WikiStore) -> None:
    """Seed canon files when LLM is unavailable (dev/demo)."""
    b = wiki.get_bootstrap()
    wiki.write_markdown(
        "wiki/canon/world.md",
        {"id": "world", "type": "canon", "canon_level": "hard"},
        f"# 世界设定\n\n{b.background}\n\n{b.outline}\n",
    )
    wiki.write_markdown(
        "wiki/canon/rules.md",
        {"id": "rules", "type": "canon", "canon_level": "hard"},
        "# 世界规则\n\n（待 Agent 完善）\n",
    )
    wiki.write_markdown(
        "wiki/canon/tone.md",
        {"id": "tone", "type": "canon", "canon_level": "hard"},
        f"# 叙事基调\n\n{b.tone}\n",
    )
    if b.character_notes.strip():
        wiki.write_markdown(
            "wiki/characters/protagonist.md",
            {"id": "protagonist", "type": "character", "canon_level": "soft"},
            f"# 主角\n\n{b.character_notes}\n",
        )
    _, body = wiki.parse_markdown("wiki/plot_state.md")
    wiki.write_markdown(
        "wiki/plot_state.md",
        {"id": "plot_state", "type": "plot", "canon_level": "soft"},
        body + f"\n\n## 开篇设定\n\n基于大纲：{b.outline[:500]}\n",
    )


def _extract_last_message(result: dict) -> str:
    messages = result.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    if hasattr(last, "content"):
        return str(last.content)
    if isinstance(last, dict):
        return str(last.get("content", ""))
    return str(last)
