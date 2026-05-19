import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { startWorldBuild, subscribeJob } from "../api/client";

export default function WorldBuild() {
  const { id } = useParams<{ id: string }>();
  const [extra, setExtra] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);

  const run = async () => {
    if (!id) return;
    setRunning(true);
    setDone(false);
    setLog([]);
    const job = await startWorldBuild(id, extra);
    subscribeJob(
      id,
      job.job_id,
      (ev) => {
        setProgress(ev.progress * 100);
        setLog((prev) => [...prev, `[${ev.stage}] ${ev.message}`]);
      },
      () => {
        setRunning(false);
        setDone(true);
        setProgress(100);
      }
    );
  };

  return (
    <div>
      <Link to="/" className="text-sm text-stone-500 hover:text-stone-300">
        ← 返回项目
      </Link>
      <h1 className="text-2xl font-bold mt-4 mb-2">世界观工作台</h1>
      <p className="text-stone-500 text-sm mb-6">项目 {id}</p>

      <textarea
        placeholder="额外说明（可选）"
        rows={3}
        className="w-full mb-4 px-3 py-2 bg-stone-900 border border-stone-700 rounded"
        value={extra}
        onChange={(e) => setExtra(e.target.value)}
      />

      <button
        type="button"
        disabled={running}
        onClick={run}
        className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg"
      >
        {running ? "构建中…" : "开始构建世界观"}
      </button>

      <div className="mt-6 h-2 bg-stone-800 rounded overflow-hidden">
        <div className="h-full bg-amber-500 transition-all" style={{ width: `${progress}%` }} />
      </div>

      {done && (
        <p className="mt-4 text-green-400 text-sm">
          完成。前往 <Link to={`/projects/${id}/wiki`} className="underline">Wiki 浏览器</Link> 查看。
        </p>
      )}

      <ul className="mt-6 space-y-1 text-sm text-stone-400 font-mono max-h-64 overflow-auto">
        {log.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
