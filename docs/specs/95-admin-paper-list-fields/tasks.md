# 实施任务：管理端论文列表字段可读编辑

输入：[规格](spec.md)、[计划](plan.md)、[研究](research.md)、[数据模型](data-model.md)、[接口](contracts/paper-metadata.md)。

## 阶段一：准备与基础

- [x] T001 核查 docs/specs/95-admin-paper-list-fields/ 文档、需求覆盖和接口事实来源，完成实施前质量门。
- [x] T002 [US1] [US2] 在 tests/02_identity_governance/admin-paper-list-fields.test.tsx 与 goserver/handlers/admin_paper_list_fields_test.go 编写显示、编辑、保存、清空与持久化回归测试。
- [x] T003 提取 frontend/src/lib/paperTextLists.ts 的共用解析，并让 frontend/src/components/PaperEditView.tsx 复用。

## 阶段二：用户故事实现（P1）

- [x] T004 [US1] [US2] 更新 frontend/src/pages/AdminPaperEditPage.tsx 与 frontend/src/i18n/zh/admin.ts、frontend/src/i18n/en/admin.ts：作者标签、每行文本、保存编码和失败输入保留。

独立验收：US1 验证作者增删与直接保存；US2 验证多行编辑、清空与标点保留。MVP 为两个故事共同完成。

## 阶段三：验证与文档

- [x] T005 运行 docs/specs/95-admin-paper-list-fields/quickstart.md 的前端、Go 测试与类型检查，执行已有管理页及详情回归，记录结果。
- [x] T006 使用 Overview Skill 回写 docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md，核验链接，并同步 Issue #95 验证证据。

## 依赖与覆盖

T001 → T002 → T003 → T004 → T005 → T006。同一页面串行；测试和实现由本任务连续完成，不引入代理并行。
FR-001、FR-002、FR-005 对应 T002/T004；FR-003 对应 T002/T003/T004；
FR-004 对应 T002/T004/T005；SC-001/SC-002 对应 T005，SC-003 对应 T005/T006。
