# 接口框架搭建描述

本说明由 Understand-Anything 的 `understand` 知识图谱格式整理，聚焦当前项目的 FastAPI 接口框架、数据接口、前端调用和运维支撑关系。

## 总体结构

- 后端入口：`backend/main.py` 创建 FastAPI 应用，注册 API router，挂载 `/static`，并返回首页、组合页、登录页、后台页和 Tc 预测页模板。
- API 路由：`backend/api/*.py` 按业务模块拆分接口，包括元素、化合物、文献、认证、管理员、AI 文献库、Alexandria、HTSC-2025 和 Tc 预测。
- 数据接口：`backend/schemas.py` 定义 Pydantic 请求/响应模型；`backend/models.py` 定义 SQLAlchemy ORM 表；`backend/crud.py` 承担主要查询、创建和响应转换。
- 数据库：`backend/database.py` 暴露主元数据 DB、图片 DB、AI 元数据 DB、AI 图片 DB 四套 session，供路由通过 Depends 注入。
- 前端消费：`frontend/static/js/*.js` 通过 fetch 调用 API，HTML 模板由页面路由直接返回。

## 架构层

- **FastAPI 应用入口与页面路由**：应用启动、路由注册、静态资源挂载和页面模板返回。（10 个文件级节点）
- **HTTP API 接口层**：所有 /api 路由模块，负责请求参数、权限依赖和业务编排。（10 个文件级节点）
- **认证与权限层**：JWT、密码哈希、邮箱验证码和权限依赖。（2 个文件级节点）
- **数据模型与持久化层**：数据库连接、ORM 模型、CRUD、初始化、迁移和导入导出。（12 个文件级节点）
- **前端接口消费层**：前端脚本、样式和状态辅助代码，调用后端 API 并渲染页面。（9 个文件级节点）
- **Schema 与工具层**：Pydantic schema、引用生成、DOI 解析、图片处理和预测辅助工具。（5 个文件级节点）
- **运行配置与运维脚本**：部署入口、依赖、备份脚本、数据文件和运行配置。（19 个文件级节点）
- **文档与论文材料**：业务文档、运维文档、论文原始材料和 PaperSpine 写作产物。（60 个文件级节点）
- **包初始化与其他辅助文件**：包初始化和未归入主要接口框架的辅助文件。（13 个文件级节点）

## API 模块分布

- `backend/api/admin.py`：19 个接口
  - `DELETE /api/admin/papers/{paper_id}`
  - `DELETE /api/admin/papers/{paper_id}/images/{image_id}`
  - `DELETE /api/admin/users/{user_id}`
  - `GET /api/admin/all-admins`
  - `GET /api/admin/all-users`
  - `GET /api/admin/my-reviews`
  - `GET /api/admin/papers/all`
  - `GET /api/admin/papers/unreviewed`
  - `GET /api/admin/papers/{paper_id}`
  - `GET /api/admin/papers/{paper_id}/images`
  - `GET /api/admin/pending-approvals`
  - `GET /api/admin/users/{user_id}/submitted-papers`
  - `POST /api/admin/approve-user`
  - `POST /api/admin/papers/batch-chart-visibility`
  - `POST /api/admin/papers/batch-delete`
  - `POST /api/admin/papers/batch-review`
  - `POST /api/admin/papers/{paper_id}/review`
  - `PUT /api/admin/papers/{paper_id}`
  - `PUT /api/admin/users/{user_id}/permissions`
- `backend/api/ai_papers.py`：5 个接口
  - `GET /api/ai/compounds/{element_symbols}`
  - `GET /api/ai/papers/compound/{element_symbols}`
  - `GET /api/ai/papers/crystal-structures`
  - `GET /api/ai/papers/{paper_id}/images/{image_order}`
  - `POST /api/ai/papers/search-by-mode`
- `backend/api/alexandria.py`：5 个接口
  - `GET /api/alexandria/elements`
  - `GET /api/alexandria/material/{mat_id}`
  - `GET /api/alexandria/material/{mat_id}/download`
  - `GET /api/alexandria/stats`
  - `POST /api/alexandria/search`
- `backend/api/auth_routes.py`：4 个接口
  - `GET /api/auth/me`
  - `POST /api/auth/login`
  - `POST /api/auth/register`
  - `POST /api/auth/verify-email`
- `backend/api/compounds.py`：3 个接口
  - `GET /api/compounds/{element_symbols}`
  - `POST /api/compounds/check`
  - `POST /api/compounds/search`
- `backend/api/elements.py`：2 个接口
  - `GET /api/elements/`
  - `GET /api/elements/{symbol}`
- `backend/api/htsc2025.py`：3 个接口
  - `GET /api/htsc2025/detail/{name}`
  - `GET /api/htsc2025/stats`
  - `POST /api/htsc2025/search`
- `backend/api/papers.py`：12 个接口
  - `GET /api/papers/batch-upload-example`
  - `GET /api/papers/compound/{element_symbols}`
  - `GET /api/papers/crystal-structures`
  - `GET /api/papers/images/{image_id}`
  - `GET /api/papers/stats/chart-data`
  - `GET /api/papers/stats/user-ranking`
  - `GET /api/papers/{paper_id}`
  - `GET /api/papers/{paper_id}/images/{image_order}`
  - `POST /api/papers/`
  - `POST /api/papers/batch-upload`
  - `POST /api/papers/export`
  - `POST /api/papers/search-by-mode`
- `backend/api/tc_predict.py`：1 个接口
  - `POST /api/tc-predict/`
- `backend/main.py`：13 个接口
  - `GET /`
  - `GET /admin/dashboard`
  - `GET /admin/login`
  - `GET /admin/my-reviews`
  - `GET /admin/papers`
  - `GET /admin/register`
  - `GET /admin/superadmin`
  - `GET /compound/{element_symbols}`
  - `GET /health`
  - `GET /login`
  - `GET /periodic-table`
  - `GET /register`
  - `GET /tc-pre`

## 关键接口链路

- **元素检索链路**：周期表前端选择元素 -> `/api/elements` 和 `/api/compounds` 校验/检索 -> `/compound/{element_symbols}` 页面 -> `/api/papers/compound/{element_symbols}` 加载文献。
- **文献上传链路**：登录用户调用 `POST /api/papers/` -> DOI 校验和元数据解析 -> `get_or_create_compound` -> 写入 `papers`、`paper_data` -> 图片写入独立图片库。
- **后台治理链路**：管理员通过 `/api/admin/papers/*` 查看、审核、编辑、批量操作文献；超级管理员额外管理用户权限和删除文献。
- **图表链路**：后台设置 `show_in_chart` -> `/api/papers/stats/chart-data` 读取可展示 PaperData -> `frontend/static/js/chart.js` 渲染 P-Tc 图表。
- **外部数据链路**：Alexandria、HTSC-2025、AI 文献库复用元素检索语义，但分别读取独立 JSON/SQLite 数据源。
- **预测实验链路**：`/tc-pre` 页面上传 CONTCAR 和 PDOS -> `/api/tc-predict/` 解析 H 结构和 PDOS_H -> 返回预测结果，不写入数据库。

## 数据表接口

- `elements`：ORM 表 `elements` 由 `Element` 模型定义，是接口数据读写的持久化结构。
- `compounds`：ORM 表 `compounds` 由 `Compound` 模型定义，是接口数据读写的持久化结构。
- `users`：ORM 表 `users` 由 `User` 模型定义，是接口数据读写的持久化结构。
- `papers`：ORM 表 `papers` 由 `Paper` 模型定义，是接口数据读写的持久化结构。
- `paper_data`：ORM 表 `paper_data` 由 `PaperData` 模型定义，是接口数据读写的持久化结构。
- `paper_images`：ORM 表 `paper_images` 由 `PaperImage` 模型定义，是接口数据读写的持久化结构。

## 图谱产物

- 知识图谱：`.understand-anything/knowledge-graph.json`
- 扫描结果：`.understand-anything/intermediate/scan-result.json`
- 本说明：`.understand-anything/interface-framework.md`
