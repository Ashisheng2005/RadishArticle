"""
DeepAgents 虚拟文件系统（Backend）配置。

Agent 工具看到的统一路径（如 /wiki/canon/world.md）由 CompositeBackend 按前缀路由：

  /wiki/      → FilesystemBackend → 磁盘 data/projects/{id}/wiki/
  /chapters/  → FilesystemBackend → 磁盘 .../chapters/
  /meta/      → FilesystemBackend → 磁盘 .../meta/
  /memory/    → FilesystemBackend → 磁盘 .../memory/
  其他路径     → StateBackend      → 存在 LangGraph 状态里（如 /scratch/），仅当前 thread 有效

virtual_mode=True：Agent 只能访问虚拟根下的路径，防止越界写宿主机其它目录。
"""

from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend


def create_project_backend(project_root: Path) -> CompositeBackend:
    root = project_root.resolve()

    # 每个路由绑定一块真实目录；Agent 内路径 /wiki/xxx 映射为 wiki/xxx
    wiki_backend = FilesystemBackend(root_dir=str(root / "wiki"), virtual_mode=True)
    chapters_backend = FilesystemBackend(root_dir=str(root / "chapters"), virtual_mode=True)
    meta_backend = FilesystemBackend(root_dir=str(root / "meta"), virtual_mode=True)
    memory_backend = FilesystemBackend(root_dir=str(root / "memory"), virtual_mode=True)

    return CompositeBackend(
        # 默认后端：未匹配前缀时走这里，/scratch/ 等临时文件落在此
        default=StateBackend(),
        routes={
            "/wiki/": wiki_backend,
            "/chapters/": chapters_backend,
            "/meta/": meta_backend,
            "/memory/": memory_backend,
        },
    )
