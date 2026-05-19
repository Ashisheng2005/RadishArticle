# RadishArticle

基于 LangChain DeepAgents 的小说自动化工作流：本地 LLM Wiki、三层记忆、多 Agent 协作。

## 功能

- 从用户大纲/基调/背景生成并持久化世界观（LLM Wiki）
- 章节写作：情节规划 → 正文 → 连续性校验 → 语风润色 → Wiki 更新
- 科学记忆：Canon Wiki / Episodic / Working 三层
- CLI + FastAPI + React 全栈

## 快速开始

```bash
# 1. 激活虚拟环境
.\.venv\Scripts\activate

# 2. 安装依赖（若尚未安装）
pip install -e backend/

# 3. 配置环境变量
copy .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY

# 4. 启动 API
cd backend
uvicorn app.main:app --reload --port 8000

# 5. 启动前端（另开终端）
cd frontend
npm install
npm run dev
```

## CLI

```bash
# 从项目根目录
python -m cli.radish_article_cli projects list
python -m cli.radish_article_cli projects create --title "我的小说" --outline "..." 
python -m cli.radish_article_cli world-build <project_id>
python -m cli.radish_article_cli write-chapter <project_id> --outline "第一章梗概"
```

## 项目数据

运行时数据位于 `data/projects/{novel_id}/`，包含 `wiki/`、`chapters/`、`memory/` 等目录。
