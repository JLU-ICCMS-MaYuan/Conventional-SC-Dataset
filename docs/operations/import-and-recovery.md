# 导入与恢复

## 主数据导入

`backend/import_data.py` 可将 JSON 载荷导入主库；使用 `--clear` 会先删除既有业务
数据，且该过程不是原子回滚操作。执行前必须备份目标数据库、校验载荷完整性，并
准备恢复路径。

## RAG 集合重建

文件夹集合、标签集合和综述集合重建脚本会删除原有 Chroma 集合后再生成。运行前必须
备份 Chroma 卷并确认外部 embedding API 的密钥、配额、预计耗时和重跑方式。

## 初始化顺序

1. 设置明确的数据库与 RAG 数据路径。
2. 执行 Alembic 迁移。
3. 运行 `backend.init_db` 初始化 SQLite 基础数据；周期表种子可重复执行。
4. 按需导入主数据或重建 RAG 集合。
5. 启动服务后检查 `/health` 和 `/api/rag/health`。

## 证据

- `backend/import_data.py`
- `backend/init_db.py`
- `backend/rag/ingest/ingest_split_collections.py`
- `backend/rag/ingest/ingest_tag_collections.py`
- `backend/rag/ingest/ingest_reviews.py`
