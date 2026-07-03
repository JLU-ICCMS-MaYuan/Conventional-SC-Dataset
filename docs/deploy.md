# SC-Wiki 部署指南

## 1. 环境准备

```bash
# Python 3.10+
python --version

# 虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 2. 配置 .env

```bash
cp .env.example .env   # 编辑 .env，填入实际值
```

关键配置项：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 主应用数据库 | `mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4` |
| `DEEPSEEK_API_KEY` | LLM 对话 API Key | — |
| `DEEPSEEK_BASE_URL` | LLM 对话 Base URL | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | LLM 模型名 | `deepseek-chat` |
| `EMBEDDING_API_KEY` | Embedding API Key | 回退到 `OPENAI_API_KEY` |
| `EMBEDDING_BASE_URL` | Embedding Base URL | 回退到 `OPENAI_BASE_URL` |
| `RAG_CHROMA_PATH` | ChromaDB 路径 | `data/chroma_db` |
| `JWT_SECRET_KEY` | JWT 签名密钥 | — |
| `PORT` | 服务端口 | `8000` |

## 3. 数据库初始化

```bash
# 创建迁移
python -m alembic upgrade head

# 初始化基础数据
python -m backend.init_db

# 创建管理员
python -m backend.create_superadmin
```

## 4. ChromaDB 数据准备

ChromaDB 集合需要预先建好。如果已有数据库备份：

```bash
# 复制 ChromaDB 到项目目录
cp -r /path/to/chroma_db data/

# 或设置环境变量指向已有路径
export RAG_CHROMA_PATH="/path/to/chroma_db"
```

如果需要新建（拆分文件夹集合）：

```bash
python backend/rag/ingest/ingest_split_collections.py   # 15 个文件夹集合
python backend/rag/ingest/ingest_tag_collections.py      # 6 个标签集合
```

## 5. 前端构建

```bash
cd frontend_test
npm install
npm run build        # 产物输出到 ../frontend/static/
cd ..
```

## 6. 启动服务

```bash
# 开发环境（热重载）
DATABASE_URL="mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4" \
  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境
./start.sh
```

## 7. 验证

```bash
# 首页
curl http://localhost:8000/

# AI 文献助手
curl http://localhost:8000/rag

# 健康检查
curl http://localhost:8000/api/rag/health
```

## 常见问题

**启动报 `ModuleNotFoundError: No module named 'backend.init_db'`**

工作树缺少 `init_db.py`，跳过该步骤直接启动：
```bash
DATABASE_URL="mysql+pymysql://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4" \
  uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Embedding 报 405 Not Allowed**

`EMBEDDING_BASE_URL` 指向的代理不支持 embedding，需单独设置：
```bash
EMBEDDING_API_KEY="sk-xxx"
EMBEDDING_BASE_URL="https://api.openai.com/v1"
```

**前端修改后不生效**

执行 `npm run build` 后刷新浏览器（`Ctrl+Shift+R`）。
