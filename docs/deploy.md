# SC-Wiki 部署指南

从 `git clone` 到生产环境运行的完整流程。

---

## 1. 环境要求

| 依赖 | 版本要求 | 验证方式 |
|------|---------|---------|
| Python | >= 3.10 | `python --version` |
| Node.js | >= 18 | `node --version` |
| npm | >= 9 | `npm --version` |
| MySQL | 5.7+ 或 8.0 | `mysql --version` |
| pip | 最新 | `pip install --upgrade pip` |

## 2. 克隆项目

```bash
git clone https://github.com/JLU-ICCMS-MaYuan/SC-Wiki.git
cd SC-Wiki
git checkout guoqiang  # 主开发分支
```

## 3. 安装后端依赖

```bash
pip install -r requirements.txt
```

## 4. 配置 .env

```bash
cp .env.example .env   # 没有 .env.example 时手动创建
```

编辑 `.env`，填入以下配置：

```env
# 数据库（MySQL 已配置好）
DATABASE_URL=mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4

# LLM（对话用 DeepSeek）
DEEPSEEK_API_KEY="sk-your-deepseek-key"
DEEPSEEK_BASE_URL="https://api.deepseek.com"
DEEPSEEK_MODEL="deepseek-chat"

# Embedding（向量化用，独立配置，回退到 OPENAI_*）
EMBEDDING_API_KEY="sk-your-embedding-key"
EMBEDDING_BASE_URL="https://api.openai.com/v1"

# ChromaDB
RAG_CHROMA_PATH="data/chroma_db"
```

> ⚠️ `EMBEDDING_API_KEY` 必须指向**真正支持 `/v1/embeddings` 端点**的服务。很多国产代理只支持 `/v1/chat/completions`，不支持 embedding。

## 5. ChromaDB 向量数据库

ChromaDB 包含 29,311 个论文文本块的向量索引，按 15 个文件夹 + 6 个标签组织为 21 个集合。

**方式一：复制已有数据**（推荐）

```bash
cp -r /path/to/existing/chroma_db data/
```

**方式二：引用外部路径**

```bash
# 在 .env 中
RAG_CHROMA_PATH="/path/to/chroma_db"
```

ChromaDB 数据目录约 1.2GB，必须与 `dev.db`（RAG SQLite 数据库，含 `paper_chunks` 表）配套使用。两者缺一不可。

> ⚠️ ChromaDB 集合是在部署前**预建好的**。如果从零开始建，需要先导入论文数据（`paper_chunks` 表），再运行 embedding 脚本——过程涉及数十万次 API 调用，不建议重建。

## 6. 数据库连接

MySQL 数据库需包含 `papers`、`superconductors`、`superconductor_records`、`paper_chunks` 等表，数据已预置。

```bash
# 测试连接
python -c "from backend.database import engine; engine.connect(); print('OK')"
```

如果只使用 RAG 功能（不需要主应用的用户/审核系统），可以跳过 `alembic upgrade head` 和 `init_db`。

## 7. 前端构建

```bash
cd frontend
npm install
npm run build        # 输出到 frontend/static/
cd ..
```

构建产物在 `frontend/static/`（index.html + JS/CSS/字体）。**不要在 `npm run build` 中途中断**。

## 8. 启动服务

```bash
# 开发（热重载 Python）
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 前端开发（热重载 React，端口 5173，/api 代理到 8000）
cd frontend && npx vite --port 5173
```

```bash
# 生产
./start.sh
# 或
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 9. 验证

```bash
# 首页
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
# → 200

# AI 文献助手
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/rag
# → 200

# RAG 健康检查
curl -s http://localhost:8000/api/rag/health
# → {"available": true, "message": "AI 文献助手已就绪"}
```

在浏览器打开 `http://localhost:8000`：
- `/` — 首页
- `/elements` — 周期表
- `/compound/La-H` — La-H 体系文献
- `/rag` — AI 文献助手（普通问答 + 🔬 探索模式）
- `/tc-pre` — Tc 预测
- `/admin/dashboard` — 管理员审核

## 10. 目录结构（部署后）

```
SC-Wiki/
├── .env                  # 环境配置（不提交）
├── backend/              # FastAPI 后端
│   ├── main.py           # 入口
│   ├── api/              # API 路由
│   ├── rag/              # RAG 引擎 + Inspiration Agent
│   └── ...
├── frontend/             # React 前端源码
│   ├── src/
│   ├── static/           # npm run build 产物
│   └── ...
├── data/
│   ├── chroma_db/        # ChromaDB 向量库（~1.2GB）
│   └── ...
├── requirements.txt
└── start.sh
```

## 常见问题

### ❌ `ModuleNotFoundError: No module named 'backend.init_db'`

工作树缺少 `init_db.py`。如果不需要用户/审核系统，直接跳过 init_db 步骤启动即可。不影响 RAG 功能。

### ❌ Embedding 返回 405 / 404

`.env` 中的 `EMBEDDING_BASE_URL` 指向的代理不支持 `/v1/embeddings` 端点。换用真正支持 embedding 的 API（如 OpenAI、Anthropic、或兼容代理）。

### ❌ 前端修改不生效

开发模式下 Vite 自动热重载。生产模式需重新执行 `npm run build` 后刷新浏览器。

### ❌ 页面打开白屏 / JS 报错

1. 删除 `frontend/static/` 后重新 `npm run build`
2. 清除浏览器 localStorage（F12 → Application → Local Storage → 删除 `rag_conversations` 和 `rag_meta_*`）
3. 硬刷新 `Ctrl+Shift+R`

### ❌ RAG 问答返回"AI 文献助手数据不可用"

ChromaDB 路径未配置或数据不存在。检查 `.env` 中 `RAG_CHROMA_PATH` 是否正确。

### ❌ LLM 返回"API key 未配置"

`.env` 中 `DEEPSEEK_API_KEY` 未设置。如果使用其他 OpenAI 兼容 API，修改 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。

### ❌ 两个端口？

开发时：5173（Vite React）+ 8000（FastAPI），Vite 代理 `/api` 到 8000。生产时只有一个 8000，前端构建到 `frontend/static/`，由 FastAPI 直接提供。
