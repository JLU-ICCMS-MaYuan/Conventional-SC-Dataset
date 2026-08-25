# 实施计划：材料状态多维分类与论文审核内确认

## 技术目标

保留数据库驱动的材料家族、结构家族、不同元素种类数、压力和材料维度，删除独立分类建议与目录治理工作流。最终分类只在论文批准事务中写入，并把 AI 建议与最终选择保存到 revision 级审核事件。

## 约束映射

| 需求 | 设计 |
| --- | --- |
| FR-008～010 | `GET /api/classification-catalogs` 返回规范中文目录及 seed 别名 |
| FR-011～014 | 临时 review artifact 保存建议；`paper_review_events.classification_snapshot` 保存批准快照 |
| FR-019～021 | Go 单篇审核事务负责解析/创建目录、写分类、校验、批准和幂等 |
| FR-023 | 删除 proposal、evidence、audit、merge/deactivate API 和治理面板 |
| SC-007 | `0012` 修复 MySQL 兼容；`0013` 收敛最终 Schema；真实 MySQL 回归 |

## 数据库

1. 保留历史 revision `20260825_0012`，只修复 MySQL 8.4 不接受自增列 CHECK 和 `STORED` 生成列的问题。
2. 新增 `20260825_0013`：
   - 删除 `classification_evidences`、`classification_proposals`、`classification_audit_events`；
   - 删除两类目录的 `merged_into_id` 和 `is_active`；
   - 将 `name_en` 改为可空；
   - 为 `paper_review_events` 增加 `classification_snapshot JSON NULL`。
3. 保留目录、seed 别名、材料状态外键、多结构关系和唯一主结构约束。

不直接重写 `0012` 为最终结构，因为其他开发环境可能已执行该 revision；`0013` 负责让新旧环境收敛。

## Python 提交链路

- review artifact 继续保存 AI 值、贡献者值、证据和 `current_paper|referenced_work`。
- `persist_scientific_draft` 只为 `current_paper` 建立材料状态并计算元素种类数。
- 提交阶段不创建 proposal/evidence，也不把草稿分类写成最终目录关系。
- `referenced_work` 不建立材料状态。

## Go 审核事务

批准请求携带当前 revision 的材料状态选择：材料家族 `{id,name}`、材料维度、结构家族 `{id,name,is_primary}` 以及内部审核上下文。

事务顺序：

1. 检查 `review_request_id` 幂等。
2. 锁定论文当前 revision 的材料状态。
3. 对已有 ID 做归属验证；对名称先匹配规范名、英文名、编码和 seed 别名。
4. 未匹配名称以自动内部编码创建正式项。
5. 替换材料状态最终分类和结构关系。
6. 执行批准完整性校验。
7. 更新论文状态并写入含最终数据库名称的 `classification_snapshot`。

任一步失败回滚。拒绝和退回不执行第 2～5 步。批量批准返回 400，要求逐篇确认。

## 前端

- 删除管理员“分类建议/分类目录”页签和 `ClassificationGovernancePanel`。
- 审核弹窗同时展示 AI 建议、贡献者提交和证据作用域。
- 每个材料状态提供材料家族、结构家族和材料维度控件；自由输入表示审核通过时创建新项。
- `handleReview` 只调用一次审核 API，不再先调用独立分类更新 API。
- 审核成功后刷新目录缓存，使新项立即可选。

## 验证

- Python：提交不写旧治理实体，正文/引用作用域边界保持。
- Go：认可已有、别名匹配、改选、内联创建、回滚、拒绝不创建、旧 revision、幂等和审核快照。
- 前端：无治理页签、一次审核请求、已有/新名称和结构主项 payload。
- 迁移：真实 fresh MySQL 8.4 执行 `alembic upgrade head`，检查最终表和列。
- 全量：后端相关测试、`go test ./...`、Vitest、TypeScript 和生产构建。

## 文档影响

实现验证后增量更新 `docs/overview/02-data-model-and-maintenance/`、`docs/overview/05-administration-and-governance/` 和 `docs/overview/06-rag-literature-assistant/` 中受影响的当前事实。
