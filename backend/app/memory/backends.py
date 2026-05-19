from pathlib import Path

from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend


def create_project_backend(project_root: Path) -> CompositeBackend:
    """Composite virtual FS: wiki/chapters on disk, scratch in thread state."""
    root = project_root.resolve()
    wiki_backend = FilesystemBackend(root_dir=str(root / "wiki"), virtual_mode=True)
    chapters_backend = FilesystemBackend(root_dir=str(root / "chapters"), virtual_mode=True)
    meta_backend = FilesystemBackend(root_dir=str(root / "meta"), virtual_mode=True)
    memory_backend = FilesystemBackend(root_dir=str(root / "memory"), virtual_mode=True)

    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/wiki/": wiki_backend,
            "/chapters/": chapters_backend,
            "/meta/": meta_backend,
            "/memory/": memory_backend,
        },
    )
