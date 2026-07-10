# 贡献、上传与审核

## 职责

该领域管理用户角色、账户审批、文献审核与公开图表可见性。管理员 API 位于
`/api/admin`，角色集合为 `user`、`admin` 和 `superadmin`。

## 当前行为

- 文献具有 `pending`、`approved`、`rejected`、`needs_revision` 审核状态。
- 管理员可审核单篇或批量审核文献，并批量调整文献关联记录的图表可见性。
- 管理端路由包括 `/admin/dashboard`、`/admin/papers`、`/admin/users`。
- RAG PDF 上传会写入独立 RAG 数据库并标记上传论文为待审核；它不是主库文献
  管理界面的等价入口。

## 证据

- `backend/api/admin.py`
- `backend/models.py`
- `frontend/src/pages/AdminPages.tsx`
- `backend/api/rag.py`

## 已知缺口

- `CompoundPage` 调用的 `POST /api/papers/` 没有对应已注册端点，普通页面文献上传
  不能视为闭环能力，应建立 `type:bug` 或 `type:doc-debt` Issue。
- RAG PDF 上传端点未在此文档中声明认证保证；其访问与审核衔接需单独核验。
