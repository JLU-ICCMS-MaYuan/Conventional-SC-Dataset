# API 契约：论文物理删除与外部清理

## 公开端点（Go）

- `DELETE /api/admin/papers/{id}`：物理删除单篇论文。要求 `superadmin`。
  - `200 {"message":"已删除"}`
  - `400 {"error":"无效的论文 ID"}`：id 非数字
  - `404 {"error":"论文不存在"}`：由哨兵错误 `ErrPaperNotFound` 判定，不做文案匹配
  - `500 {"error":"删除失败，请重试"}`：数据库错误。原始 error 只写服务端日志，
    不进响应体——它含表名、约束名与驱动细节（参见 `backend/main.py` 同类处置）。

- `POST /api/admin/papers/batch-delete`：批量物理删除。要求 `superadmin`。
  - 请求 `{"paper_ids":[1,2,3]}`
  - `200 {"message":"批量删除完成"}`：全部成功
  - `206 {"message":"部分删除失败","failed_ids":[...]}`：逐篇独立处理，
    单篇失败不影响其余；失败原因写日志
  - `400 {"error":"参数错误"}`

**注意**：`206` 落在 2xx 内，`fetch` 的 `response.ok` 为 `true` 不会抛错，
前端必须按 `failed_ids` 判定。历史事故：前端仅凭 `response.ok` 就显示
「批量删除完成」，而删除实际因外键错误全部回滚。

## 内部端点（Python，供 Go 调用）

不面向前端，仅在 MySQL 事务提交后由 Go 调用。路径自带 `/api` 前缀，
`main.py` 中 `include_router` 不得再加 `prefix`，否则拼成 `/api/api/internal/...`。

- `DELETE /api/internal/papers/{paper_id}/vectors`：清理 Qdrant 向量
- `DELETE /api/internal/papers/{paper_id}/graph`：清理 Neo4j 节点及关系
  - `200 {"message":str,"deleted_count":int}`
  - `401`：缺少或无效的管理员 token
  - `503 {"detail":{"code":"qdrant_cleanup_failed"|"neo4j_cleanup_failed","message":str}}`

目标本就不存在时返回 `200`（幂等），不视为错误。

## 一致性边界

MySQL 删除在事务内保证原子性；Qdrant/Neo4j 清理在事务提交**之后**执行，属
best-effort：MySQL 行已物理删除且不可恢复，此时强制回滚只会制造更严重的不一致。
外部清理失败仅记日志，不改变 HTTP 结果，需要时由人工或后台任务补偿。

Go 通过 `PYTHON_BACKEND_URL` 定位 Python 服务（dev 与生产 compose 均设为
`http://python:8000`）。未设置时回落 `127.0.0.1:8000`，该默认值在多容器部署下
不可用，必须显式配置。
