# 论文与物性结果

## 功能说明

把材料检索命中项组织为论文、超导体和物性记录结果，供详情展示、统计与审核功能复用。

## 当前行为

- 当前结果主链路为 `papers` 与 `key_properties`：论文保存 DOI、标题、作者、年份、摘要、审核状态和 LLM 富化字段；关键物性保存材料名、规范物性名、数值范围、单位、压强、温度、超导类型、文章类型、结构文本和主图标记。
- Go API `GET /api/papers/:id` 返回论文详情和 `key_properties`，并聚合论文中的最大临界温度为 `tc_max`。
- Go API `POST /api/papers/search/records` 返回扁平列表行，包含 `record_id`、`paper_id`、`year`、`formula`、`type`、`pressure`、`tc`、`source`、`status`、`doi` 等字段。
- `/search` 页面单击或选择记录后可显示详情；如果记录有 `paper_id`，会请求论文详情；若 `key_properties` 中存在结构文本，可调用结构接口或前端 3D 组件展示。

## 工作流程

材料检索先确定候选超导体；Go API 通过 `key_properties` 关联论文并生成扁平结果；前端把本地与外部来源适配为统一视图。详情阶段再按论文 ID 加载完整论文和关键物性列表，供详情卡片、结构预览、审核编辑和图表点击抽屉复用。

## 约束

- 结果准确性取决于 `key_properties`、`papers`、`superconductors` 的关联关系和审核状态。
- `superconductor_records` 模型仍存在，但当前 Go 搜索和图表主链路主要使用 `key_properties`。
- 外部来源详情字段不与本地论文字段完全等价，前端会按来源差异兜底显示缺失字段。

## 代码与测试

- `goserver/handlers/papers.go`
- `goserver/models/models.go`
- `backend/models.py`
- `frontend/src/pages/SearchPage.tsx`
- `frontend/src/components/StructureViewer3D.tsx`
- `tests/03_data_search_and_database_discovery/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 本地列表行的空间群字段当前为占位值，完整结构字段需要从详情或结构接口继续读取。
