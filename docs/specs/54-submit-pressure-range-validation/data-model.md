# 数据模型：提交审核压强区间校验与草稿保存语义修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 持久层变更（MySQL，alembic 迁移 `20260826_0016`）

### material_states.ck_material_states_pressure_range（约束替换）

| | 约束文本 | 语义 |
|---|---------|------|
| 修复前 | `(min IS NULL AND max IS NULL) OR (min IS NOT NULL AND max IS NOT NULL AND min <= max)` | 区间必须成对 |
| 修复后 | `min IS NULL OR max IS NULL OR min <= max` | 单臂合法；双臂要求 min≤max |

- 单臂语义约定：min-only =「≥min」（如 "above 200 GPa"），max-only =「≤max」。
- downgrade 恢复原成对约束；已在 dev MySQL 8.4 验证往返可逆。
- 无列变更、无数据回填：既有行全部满足新约束（旧约束是新约束的子集）。

## 消费方核查（方案 A 影响面）

| 消费方 | 是否消费 min/max | 证据 |
|--------|------------------|------|
| 搜索压力筛选 | 否（走 `key_properties.pressure_gpa`） | `goserver/handlers/papers.go:253-257` |
| 论文详情 API | 否（仅输出 `pressure_value_gpa`） | `goserver/handlers/papers.go:489-511` `materialStatesToDict` |
| 前端展示 | 否（仅 `pressure_value_gpa`/`pressure_raw`） | `AdminPage.tsx:876`、`UploadTaskEditor.tsx:981` |
| 后端计算 | 否（仅数值透传） | `upload_jobs.py:971-972`、`scientific_drafts.py:245-246` |
| goserver 模型 | 可空指针，NULL 安全 | `goserver/models/models.go:271-272` |

未来新增消费方（区间搜索、范围图）时必须兑现单臂 ≥/≤ 语义，并注意 SQL NULL 臂在比较运算中静默排除行的陷阱。

## 校验级别契约

| 级别 | 调用路径 | 内容 |
|------|----------|------|
| partial | PUT `/api/rag/upload-tasks/{id}/draft` | 仅结构性检查（`invalid_draft`） |
| strict | submit（`_create_pending_paper` 内两处） | 业务字段全集（含新增 FR-002 压强校验） |

分类目录解析（`_resolve_draft_classifications`）不属于两级校验，PUT 路径行为不变。
