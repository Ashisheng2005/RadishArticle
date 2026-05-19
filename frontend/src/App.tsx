import { Link, Route, Routes } from "react-router-dom";
import ChapterEditor from "./pages/ChapterEditor";
import ProjectList from "./pages/ProjectList";
import WikiBrowser from "./pages/WikiBrowser";
import WorldBuild from "./pages/WorldBuild";

export default function App() {
  return (
    <div className="min-h-screen">
      <nav className="border-b border-stone-800 bg-stone-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-3 flex gap-6 items-center">
          <Link to="/" className="font-semibold text-amber-400">
            RadishArticle
          </Link>
          <Link to="/" className="text-stone-400 hover:text-stone-200 text-sm">
            项目
          </Link>
        </div>
      </nav>
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/projects/:id/world" element={<WorldBuild />} />
          <Route path="/projects/:id/chapter" element={<ChapterEditor />} />
          <Route path="/projects/:id/wiki" element={<WikiBrowser />} />
        </Routes>
      </main>
    </div>
  );
}
