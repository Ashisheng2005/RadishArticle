from app.config import get_settings
from app.memory.wiki_store import WikiStore
from app.models.schemas import ProjectCreate, ProjectInfo, WikiNode


class ProjectService:
    def list_projects(self) -> list[ProjectInfo]:
        return WikiStore.list_projects()

    def create_project(self, payload: ProjectCreate) -> ProjectInfo:
        store = WikiStore.create_project(payload)
        return store.get_project_info()

    def get_store(self, project_id: str) -> WikiStore:
        path = get_settings().data_root / project_id
        if not path.exists():
            raise FileNotFoundError(f"Project not found: {project_id}")
        return WikiStore(project_id=project_id)

    def get_wiki_tree(self, project_id: str, sub_path: str = "wiki") -> WikiNode:
        return self.get_store(project_id).list_wiki_tree(sub_path)

    def read_wiki_file(self, project_id: str, rel_path: str) -> str:
        return self.get_store(project_id).read_text(rel_path)
