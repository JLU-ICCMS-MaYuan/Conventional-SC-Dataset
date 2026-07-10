# 数据与 RAG 资产

## 三类持久化资产

- 主应用数据库：由 `DATABASE_URL` 指定；本地启动脚本默认使用
  `data/local_dev.db`。
- RAG 关系数据库：由 `RAG_DATABASE_URL` 或 `RAG_DATA_ROOT` 派生，独立于主库。
- Chroma 向量资产：由 `RAG_CHROMA_PATH` 或 RAG 数据根目录定位。

`data/`、`.env` 和 `frontend_build/` 被 Git 忽略。部署环境必须提供持久化卷、受管
密钥和前端构建产物，不能把本地未跟踪文件当作可用资产。

## 配置风险

- `backend/database.py` 的默认主库路径与 `start.sh` 的默认路径不同；部署必须显式
  设定 `DATABASE_URL`，避免直接 Uvicorn 与脚本启动连接不同数据库。
- RAG 默认依赖相邻数据根目录时，部署必须显式确认该目录及 Chroma 卷存在。

## 证据

- `backend/database.py`
- `backend/rag/config.py`
- `backend/rag/database.py`
- `backend/rag/vectordb.py`
- `.gitignore`
