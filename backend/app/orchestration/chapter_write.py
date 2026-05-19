"""
章节写作流水线（chapter_write）。

与 world_build 类似，通过一条「协调者 prompt」驱动 DeepAgents，典型子 Agent 顺序：
  plot-planner → story-writer → continuity-validator → style-editor → wiki-curator

记忆策略（避免上下文爆炸）：
  - 不把全部旧章节正文塞进 prompt
  - 只注入 plot_state 摘要 + 上一章 episodic JSON + 少量人物卡路径提示
  - 详见 EpisodicMemoryStore.build_chapter_context()
"""

import json
import re
from typing import Any, Callable

from app.agents.factory import AgentFactory
from app.memory.episodic import EpisodicMemoryStore
from app.memory.schemas import EpisodicRecord
from app.memory.wiki_store import WikiStore
from app.models.schemas import WorkflowEvent


async def run_chapter_write(
    wiki: WikiStore,
    outline: str | None = None,
    auto_plot: bool = False,
    chapter_number: int | None = None,
    chapter_title: str = "",
    pov: str = "",
    on_event: Callable[[WorkflowEvent], Any] | None = None,
) -> dict:
    async def emit(stage: str, message: str, progress: float):
        if on_event:
            ev = WorkflowEvent(stage=stage, message=message, progress=progress)
            result = on_event(ev)
            if hasattr(result, "__await__"):
                await result

    ch_num = chapter_number or wiki.next_chapter_number()
    ch_file = f"ch_{ch_num:03d}.md"
    episodic = EpisodicMemoryStore(wiki)
    # 组装「写本章前 Agent 需要知道什么」的上下文包
    ctx = episodic.build_chapter_context(ch_num)

    outline_text = outline or ("请根据 plot_state 全自动构想本章情节。" if auto_plot else "")
    context_block = _format_context(ctx)

    # 协调者任务书：明确虚拟路径与委派顺序
    prompt = f"""请执行章节写作工作流（第 {ch_num} 章）。

## 章节文件
写入 /chapters/{ch_file}

## 用户梗概
{outline_text or "（无，请自动构想）"}

## POV
{pov or "第三人称"}

## 章节标题
{chapter_title or f"第{ch_num}章"}

## 已有上下文（摘要，勿要求全文）
{context_block}

## 步骤
1. plot-planner → /scratch/beats.md
2. story-writer → /chapters/{ch_file}
3. continuity-validator
4. style-editor 润色
5. wiki-curator 更新 plot_state 与 episodic
"""

    await emit("plot_plan", "情节规划…", 0.15)
    factory = AgentFactory(wiki)

    try:
        await emit("writing", "撰写正文…", 0.4)
        result = factory.invoke_orchestrator(
            prompt,
            thread_id=f"chapter-{wiki.project_id}-{ch_num}",
        )
        mode = "agent"
    except Exception as e:
        if "api" in str(e).lower() or "key" in str(e).lower():
            await emit("fallback", "无 API Key，生成占位章节", 0.5)
            _fallback_chapter(wiki, ch_num, ch_file, outline_text, chapter_title)
            mode = "fallback"
            result = {}
        else:
            raise

    await emit("style", "语风润色…", 0.75)
    await emit("wiki_update", "更新 Wiki 记忆…", 0.9)

    chapter_path = wiki.project_root / "chapters" / ch_file
    body = chapter_path.read_text(encoding="utf-8") if chapter_path.exists() else ""

    # Agent 若未写 episodic，则由 Python 侧兜底写入（保证下一章有摘要链）
    if mode == "fallback" or not (wiki.project_root / "memory" / "episodic" / f"ch_{ch_num:03d}.json").exists():
        record = _build_episodic_from_chapter(ch_num, chapter_title or f"第{ch_num}章", body, outline_text)
        episodic.save_episodic(record)
        episodic.update_entity_index(record)
        episodic.update_plot_state(f"### 第{ch_num}章\n{record.summary}")

    return {
        "mode": mode,
        "chapter": ch_num,
        "file": f"chapters/{ch_file}",
        "content_preview": body[:500],
        "messages": _extract_last_message(result) if result else "",
    }


def _format_context(ctx) -> str:
    """把 ChapterContext 压成 prompt 里的一段文字。"""
    parts = [ctx.plot_state[:2000]]
    if ctx.previous_episodic:
        parts.append(f"上一章摘要: {ctx.previous_episodic.summary}")
    for p in ctx.character_files[:3]:
        parts.append(f"(人物设定见 {p})")
    return "\n\n".join(parts)


def _fallback_chapter(wiki: WikiStore, ch_num: int, ch_file: str, outline: str, title: str) -> None:
    b = wiki.get_bootstrap()
    content = f"""---
id: ch_{ch_num:03d}
chapter: {ch_num}
title: {title or f"第{ch_num}章"}
pov: 第三人称
---

# {title or f"第{ch_num}章"}

{outline or "（待 AI 撰写正文）"}

---
*基于大纲自动生成的占位章节。配置 OPENAI_API_KEY 后可启用完整 Agent 流水线。*

{b.outline[:1000] if hasattr(b, 'outline') else ''}
"""
    wiki.write_text(f"chapters/{ch_file}", content)


def _build_episodic_from_chapter(ch_num: int, title: str, body: str, outline: str) -> EpisodicRecord:
    plain = re.sub(r"^---.*?---\s*", "", body, flags=re.DOTALL)
    summary = outline or plain[:300].replace("\n", " ")
    return EpisodicRecord(
        chapter=ch_num,
        title=title,
        summary=summary,
        character_deltas=[],
        open_threads=["待 Agent 分析"],
        foreshadowing=[],
        key_events=[summary[:120]],
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
