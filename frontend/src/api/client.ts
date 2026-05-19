const API = "/api";

export interface ProjectInfo {
  id: string;
  title: string;
  genre: string;
  tone: string;
  created_at: string;
  chapter_count: number;
}

export interface WikiNode {
  path: string;
  name: string;
  is_dir: boolean;
  children: WikiNode[];
}

export interface JobStatus {
  job_id: string;
  project_id: string;
  task_type: string;
  state: string;
  stage: string;
  message: string;
  progress: number;
  result?: Record<string, unknown>;
  error?: string;
}

export async function listProjects(): Promise<ProjectInfo[]> {
  const r = await fetch(`${API}/projects`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function createProject(body: Record<string, string>): Promise<ProjectInfo> {
  const r = await fetch(`${API}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function startWorldBuild(projectId: string, extra = ""): Promise<JobStatus> {
  const r = await fetch(`${API}/projects/${projectId}/world-build`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extra_instructions: extra }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function startChapterWrite(
  projectId: string,
  body: { outline?: string; auto_plot?: boolean; title?: string }
): Promise<JobStatus> {
  const r = await fetch(`${API}/projects/${projectId}/chapters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function compactMemory(projectId: string): Promise<JobStatus> {
  const r = await fetch(`${API}/projects/${projectId}/memory/compact`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getWikiTree(projectId: string): Promise<WikiNode> {
  const r = await fetch(`${API}/projects/${projectId}/wiki/tree`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getWikiFile(projectId: string, path: string): Promise<string> {
  const r = await fetch(`${API}/projects/${projectId}/wiki/file?path=${encodeURIComponent(path)}`);
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.content;
}

export function subscribeJob(
  projectId: string,
  jobId: string,
  onEvent: (data: { stage: string; message: string; progress: number }) => void,
  onDone: () => void
): () => void {
  const es = new EventSource(`${API}/projects/${projectId}/jobs/${jobId}/stream`);
  es.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onEvent(parsed);
      if (parsed.stage === "done" || parsed.stage === "error") {
        es.close();
        onDone();
      }
    } catch {
      /* ignore */
    }
  };
  es.onerror = () => {
    es.close();
    onDone();
  };
  return () => es.close();
}
