import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getWikiFile, getWikiTree, type WikiNode } from "../api/client";

function TreeItem({
  node,
  selected,
  onSelect,
}: {
  node: WikiNode;
  selected: string;
  onSelect: (path: string) => void;
}) {
  if (node.is_dir) {
    return (
      <div className="ml-2">
        <div className="text-stone-500 text-sm py-0.5">{node.name}/</div>
        {node.children.map((c) => (
          <TreeItem key={c.path} node={c} selected={selected} onSelect={onSelect} />
        ))}
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onSelect(node.path)}
      className={`block w-full text-left text-sm py-0.5 px-2 rounded ${
        selected === node.path ? "bg-amber-900/50 text-amber-200" : "hover:bg-stone-800"
      }`}
    >
      {node.name}
    </button>
  );
}

export default function WikiBrowser() {
  const { id } = useParams<{ id: string }>();
  const [tree, setTree] = useState<WikiNode | null>(null);
  const [selected, setSelected] = useState("wiki/plot_state.md");
  const [content, setContent] = useState("");

  useEffect(() => {
    if (!id) return;
    getWikiTree(id).then(setTree).catch(console.error);
  }, [id]);

  useEffect(() => {
    if (!id || !selected) return;
    getWikiFile(id, selected)
      .then(setContent)
      .catch(() => setContent("无法加载文件"));
  }, [id, selected]);

  return (
    <div>
      <Link to="/" className="text-sm text-stone-500 hover:text-stone-300">
        ← 返回项目
      </Link>
      <h1 className="text-2xl font-bold mt-4 mb-6">Wiki 浏览器</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <aside className="md:col-span-1 p-4 bg-stone-900 rounded-xl border border-stone-800 max-h-[70vh] overflow-auto">
          {tree ? (
            <TreeItem node={tree} selected={selected} onSelect={setSelected} />
          ) : (
            <p className="text-stone-500 text-sm">加载中…</p>
          )}
        </aside>
        <article className="md:col-span-2 p-4 bg-stone-900 rounded-xl border border-stone-800">
          <p className="text-xs text-stone-500 mb-3">{selected}</p>
          <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">{content}</pre>
        </article>
      </div>
    </div>
  );
}
