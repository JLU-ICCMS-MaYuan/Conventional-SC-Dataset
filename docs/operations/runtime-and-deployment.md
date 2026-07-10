# 运行与部署

## 启动入口

`start.sh` 是完整启动编排：它确定本地 SQLite 默认位置、执行 Alembic 迁移、运行
`backend.init_db`，然后启动 `backend.main:app`。`Procfile` 只直接启动 Uvicorn，
不会执行迁移或种子初始化，不能视为等价生产入口。

## 前端与健康检查

- FastAPI 从 `frontend_build/` 提供 SPA、`assets/` 和 `img/`；部署前必须生成该目录。
- `/health` 返回主服务状态；`/api/rag/health` 检查 RAG 服务状态。
- 当前测试基线显示 `frontend_build/index.html` 缺失会使 SPA 路由返回错误 JSON；此
  部署前置条件必须满足。

## 安全前置条件

- 生产环境必须显式设置 `DATABASE_URL` 和 `JWT_SECRET_KEY`，不依赖开发默认值。
- LLM 与 embedding 凭据应由受管环境变量提供，不写入仓库或文档。
- CORS 当前允许所有来源；生产限制策略需作为独立安全决策记录。

## 证据

- `start.sh`
- `Procfile`
- `backend/main.py`
- `backend/database.py`
- `alembic/env.py`
