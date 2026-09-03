# 实施计划：建立管理员文献处理历史并修复审核页元数据

**GitHub Issue**：[#87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)　**研究记录**：[research.md](research.md)

## 摘要

本 Feature 将现有审核专用事件演进为文献处理历史，并在管理端编辑页增加真实元数据和
时间线入口。上传、审核和修改各在其真实写入事务中追加历史；编辑页两段保存通过统一 UUID
去重。实现不记录字段差异，也不向普通用户公开内部审核过程。

## 技术上下文

- **语言与版本**：Go、Python、TypeScript、React、SQLAlchemy、GORM、Alembic。
- **主要依赖**：Gin、FastAPI、React Router、Material UI、Vitest、pytest、Go test。
- **数据存储**：MySQL；`papers`、`superconductor_properties`、`paper_history_events`。
- **测试体系**：Go handler/迁移测试、Python 上传与科学数据重写测试、Vitest 页面测试。
- **目标平台**：Docker Compose 和宿主机本地开发。
- **性能目标**：编辑页首次详情只增加常数次聚合；打开处理记录时按需加载单篇时间线。
- **约束**：历史接口仅管理员；事件不可变；不删除既有审核意见；不创建字段级快照。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| Spec FR-001/FR-002 | 真实元数据与明确入口 | 管理端详情 DTO 计算用户名和当前版本物性数；页面分离物性记录与处理记录 | 已实现，Go/Vitest 定向回归通过 |
| Spec FR-003/FR-004 | 仅管理员读取时间线 | 新增管理端专用 GET 路由与权限测试 | 已实现，Go/Vitest 定向回归通过 |
| Spec FR-005 至 FR-009 | 单一、可信、可回填历史 | 表迁移、操作标识唯一约束、写入事务与不伪造修改规则 | 已实现；真实 MySQL 迁移与回填待验 |
| Spec FR-010/FR-011 | 统计与删除一致 | 审核榜筛选 `reviewed`；删除拓扑加入新表 | 已实现，Go 定向回归通过 |
| AGENTS.md | 中文文档与独立变更 | 文档已中文；实现后仅暂存 #87 文件 | 通过 |

## 源代码结构

```text
alembic/versions/20260903_0002_paper_history_events.py
backend/models.py
backend/api/rag.py
backend/services/scientific_draft_rewrite.py
goserver/models/models.go
goserver/handlers/admin.go
goserver/handlers/stats.go
goserver/handlers/paper_deletion.go
frontend/src/pages/AdminPaperEditPage.tsx
frontend/src/i18n/{zh,en}/admin.ts
backend/tests/test_upload_workflow.py
backend/tests/test_scientific_draft_rewrite.py
goserver/handlers/{admin_review_event_test.go,paper_deletion_test.go,contribution_ranking_test.go}
tests/02_identity_governance/admin-edit-page.test.tsx
```

## 设计

### 1. 单一历史表

通过 Alembic 重命名 `paper_review_events` 为 `paper_history_events`，并迁移模型字段：
审核人改为操作者、审核时间改为发生时间、审核状态变为仅审核事件拥有的可选字段；新增
`event_type`、用户名快照与通用 `operation_id`。遗留分类快照只为兼容保留，不进入新 API，
也不为新事件写入。

迁移先将旧行标为 `reviewed`，再为每篇论文补一条 `uploaded`。这不依赖 `updated_at` 推导
修改，因此不会编造历史。迁移完成后 Go、Python 和统计查询均只使用新表。

### 2. 元数据与时间线读模型

`GetPaperDetail` 预加载上传者并按当前 `content_revision` 聚合
`superconductor_properties`，组装明确的管理端详情响应。新增 `GetPaperHistory` 使用同一角色
权限，关联操作者用户名快照并按事件时间升序返回最小 DTO。

前端将物性数量 Chip 更名为“物性记录”，新增“处理记录”按钮。点击后按需请求历史并在
页面内 `Dialog` 展示紧凑时间线；加载或接口失败不影响编辑和审核。

### 3. 写入与去重

新上传在 `_create_pending_paper` 的同一事务创建 `uploaded` 事件。审核将现有
`applyPaperReview` 的写入迁为 `reviewed` 事件，继续使用请求 UUID 幂等。

编辑页在一次保存开始生成 `history_operation_id`。Go 论文级保存与 Python 科学数据保存各自
先判断是否有语义变化；若有，在本次变更所在事务内尝试插入 `modified`。表上的唯一
`operation_id` 使两段成功保存只能保留一条。若第一段已成功而第二段失败，历史忠实保留
第一段实际变更，页面仍显示原有失败提示。

### 4. 横向行为

贡献审核榜只查询 `event_type = 'reviewed'`。物理删除的依赖逆序中以
`paper_history_events` 替换旧表。论文当前 `review_status` 和最新 `review_comment` 的可见性
规则不变。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001/FR-002 | `GetPaperDetail`、`AdminPaperEditPage` | Go API 测试、Vitest |
| FR-003/FR-004 | `GET /api/admin/papers/:id/history`、历史 Dialog | 权限/API/页面测试 |
| FR-005/FR-006 | 上传创建、`applyPaperReview` | Python 上传测试、Go 审核测试 |
| FR-007 | `history_operation_id`、语义差异判断 | 跨端保存与重复保存测试 |
| FR-008/FR-009 | Alembic、Go/Python 模型 | 新库迁移与回填验证 |
| FR-010/FR-011 | `stats.go`、`paper_deletion.go` | Go 统计和删除测试 |
| FR-012 | `handleEditReview` | Vitest 路由测试 |

## 阶段与依赖

1. 建立迁移、模型和历史写入辅助能力。
2. 接入上传、审核、编辑、统计和删除路径。
3. 增加详情/历史读取 API 与编辑页时间线。
4. 完成迁移、后端、前端和构建验证。

## 必要复杂度

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 通用历史表与迁移 | 上传、修改和审核需要一个可信来源，且审核统计不得混入其他动作 | 直接复用审核专用字段会让上传者成为“审核人”，语义与统计错误 |
| 操作标识去重 | 一次页面保存实际会触发两个服务请求 | 按 HTTP 请求直接记事件会把一次修改重复显示 |
