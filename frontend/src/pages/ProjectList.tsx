import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects, type ProjectInfo } from "../api/client";

export default function ProjectList() {
  const [projects, setProjects] = useState<ProjectInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "",
    genre: "fiction",
    tone: "",
    outline: "",
    background: "",
    character_notes: "",
  });

  const load = () => {
    setLoading(true);
    listProjects()
      .then(setProjects)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await createProject(form);
    setShowForm(false);
    setForm({ title: "", genre: "fiction", tone: "", outline: "", background: "", character_notes: "" });
    load();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">小说项目</h1>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-amber-600 hover:bg-amber-500 rounded-lg text-sm font-medium"
        >
          新建项目
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="mb-8 p-6 bg-stone-900 rounded-xl border border-stone-800 space-y-3">
          <input
            required
            placeholder="标题"
            className="w-full px-3 py-2 bg-stone-950 border border-stone-700 rounded"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
          <textarea
            placeholder="大纲"
            rows={3}
            className="w-full px-3 py-2 bg-stone-950 border border-stone-700 rounded"
            value={form.outline}
            onChange={(e) => setForm({ ...form, outline: e.target.value })}
          />
          <textarea
            placeholder="基调"
            rows={2}
            className="w-full px-3 py-2 bg-stone-950 border border-stone-700 rounded"
            value={form.tone}
            onChange={(e) => setForm({ ...form, tone: e.target.value })}
          />
          <textarea
            placeholder="背景设定"
            rows={3}
            className="w-full px-3 py-2 bg-stone-950 border border-stone-700 rounded"
            value={form.background}
            onChange={(e) => setForm({ ...form, background: e.target.value })}
          />
          <textarea
            placeholder="人设片段"
            rows={2}
            className="w-full px-3 py-2 bg-stone-950 border border-stone-700 rounded"
            value={form.character_notes}
            onChange={(e) => setForm({ ...form, character_notes: e.target.value })}
          />
          <button type="submit" className="px-4 py-2 bg-amber-600 rounded-lg text-sm">
            创建
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-stone-500">加载中…</p>
      ) : projects.length === 0 ? (
        <p className="text-stone-500">暂无项目，点击「新建项目」开始。</p>
      ) : (
        <ul className="space-y-3">
          {projects.map((p) => (
            <li key={p.id} className="p-4 bg-stone-900 rounded-xl border border-stone-800 flex justify-between items-center">
              <div>
                <h2 className="font-semibold">{p.title}</h2>
                <p className="text-sm text-stone-500">
                  {p.id} · {p.chapter_count} 章
                </p>
              </div>
              <div className="flex gap-2 text-sm">
                <Link to={`/projects/${p.id}/world`} className="px-3 py-1.5 bg-stone-800 rounded hover:bg-stone-700">
                  世界观
                </Link>
                <Link to={`/projects/${p.id}/chapter`} className="px-3 py-1.5 bg-stone-800 rounded hover:bg-stone-700">
                  写章
                </Link>
                <Link to={`/projects/${p.id}/wiki`} className="px-3 py-1.5 bg-stone-800 rounded hover:bg-stone-700">
                  Wiki
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
