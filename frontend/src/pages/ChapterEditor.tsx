import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { startChapterWrite, subscribeJob } from "../api/client";

export default function ChapterEditor() {
  const { id } = useParams<{ id: string }>();
  const [outline, setOutline] = useState("");
  const [autoPlot, setAutoPlot] = useState(false);
  const [title, setTitle] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [preview, setPreview] = useState("");

  const run = async () => {
    if (!id) return;
    setRunning(true);
    setPreview("");
    setLog([]);
    const job = await startChapterWrite(id, { outline: outline || undefined, auto_plot: autoPlot, title });
    subscribeJob(
      id,
      job.job_id,
      (ev) => {
        setProgress(ev.progress * 100);
        setLog((prev) => [...prev, `[${ev.stage}] ${ev.message}`]);
      },
      async () => {
        setRunning(false);
        setProgress(100);
        try {
          const r = await fetch(`/api/projects/${id}/wiki/file?path=${encodeURIComponent("wiki/plot_state.md")}`);
          if (r.ok) {
            const d = await r.json();
            setPreview(d.content?.slice(0, 800) || "");
          }
        } catch {
          /* ignore */
        }
      }
    );
  };

  return (
    <div>
      <Link to="/" className="text-sm text-stone-500 hover:text-stone-300">
        ← 返回项目
      </Link>
      <h1 className="text-2xl font-bold mt-4 mb-6">章节编辑器</h1>

      <div className="space-y-4 mb-6">
        <input
          placeholder="章节标题（可选）"
          className="w-full px-3 py-2 bg-stone-900 border border-stone-700 rounded"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          placeholder="本章梗概（留空且勾选全自动则由 AI 构想）"
          rows={4}
          className="w-full px-3 py-2 bg-stone-900 border border-stone-700 rounded"
          value={outline}
          onChange={(e) => setOutline(e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-stone-400">
          <input type="checkbox" checked={autoPlot} onChange={(e) => setAutoPlot(e.target.checked)} />
          全自动构想情节
        </label>
      </div>

      <button
        type="button"
        disabled={running}
        onClick={run}
        className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg"
      >
        {running ? "写作中…" : "开始写作"}
      </button>

      <div className="mt-6 h-2 bg-stone-800 rounded overflow-hidden">
        <div className="h-full bg-amber-500 transition-all" style={{ width: `${progress}%` }} />
      </div>

      <ul className="mt-6 space-y-1 text-sm text-stone-400 font-mono max-h-48 overflow-auto">
        {log.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>

      {preview && (
        <pre className="mt-6 p-4 bg-stone-900 rounded-xl border border-stone-800 text-sm whitespace-pre-wrap overflow-auto max-h-96">
          {preview}
        </pre>
      )}
    </div>
  );
}
