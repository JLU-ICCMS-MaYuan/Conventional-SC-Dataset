# RAG 数据库 MySQL 迁移设计

日期：2026-06-18
状态：待实现

## 目标

将 RAG 系统（摄入管线、知识图谱查询、SQL 搜索、问答引擎）从 SQLite 切换为 MySQL，统一使用主应用已有的 `superconductor_dataset` 数据库。

## 背景

当前 RAG 系统通过 SQLite 访问 `RAG_DATA_ROOT/dev.db` 中的 papers、superconductors、superconductor_records、paper_chunks 等表。主应用 SC-Wiki 已将相同数据迁移至 MySQL `superconductor_dataset`。唯一缺失的表是 `paper_chunks`（29369 行）。

## 不改的部分

- Chroma 向量库保持本地文件存储
- `RAG_DATA_ROOT` 环境变量保留（Chroma 路径仍需使用）
- RAG SQLAlchemy 模型定义不变（已兼容 MySQL）

## 改动详情

### 1. `backend/rag/config.py` — database_url 支持 MySQL

- `rag_database_url` 字段：env `RAG_DATABASE_URL` → `.env` 中的 `RAG_DATABASE_URL` → fallback SQLite
- 新增 health 属性 `database_available`：通过 `SELECT 1` 检测连接（替代文件存在检查）

### 2. `backend/rag/knowledge_graph.py` — raw sqlite3 → SQLAlchemy async

- 删除 `import sqlite3` 和 `_conn()` 函数
- `query()`、`get_all_properties()`、`delete_paper_triples()`、`stats()` 全部改为 async
- 使用 `async_session_factory` + SQLAlchemy `select()`

### 3. `backend/rag/service.py` — 健康检查改用 MySQL

- 删除 `_sqlite_path_from_url()` 和 `dev.db` 文件存在检查
- `health()` 调用 `config.database_available`

### 4. `backend/rag/rag/engine.py` — 调用方适配

- `knowledge_graph.query()` 从同步改为 `await`
- `get_all_properties()` 从同步改为 `await`

### 5. `backend/rag/database.py` — 保持不变

- 已有 MySQL 支持（pool_size/max_overflow 非 SQLite 自动启用）
- `init_db()` 用于自动建表

### 6. MySQL paper_chunks 表

- 使用 `init_db()` 自动创建
- 数据迁移脚本：从 SQLite 读取 29369 行写入 MySQL

## 环境变量

```bash
RAG_DATABASE_URL="mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4"
RAG_DATA_ROOT="/home/work/workshop/git/Conventional-SC-Dataset-talk"  # Chroma 仍需要
```

`.env` 示例：

```env
RAG_DATABASE_URL=mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4
DEEPSEEK_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.suchuang.vip/v1
```

## 测试

- `test_rag_service.py`：health 检查使用 MySQL 连接测试替代文件检查
- `test_knowledge_graph`：适配 async SQLAlchemy
- 所有已有测试保持通过
