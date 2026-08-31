# 实施任务：简化论文审核弹窗

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

## 阶段 1：移除纯阅读性展示

- [x] T001 [US1] 删除审核弹窗中「AI 建议、用户提交与原文证据」区块（AI 与提交值三列
  对照、原文引文）— `frontend/src/pages/AdminPage.tsx`
- [x] T002 [US1] 删除「同 DOI 候选附件」区块及 `downloadCandidateAttachment` 函数
- [x] T003 [US1] 清理失效状态与 import：`candidateAttachments`、`reviewArtifactLoading`、
  `CandidateAttachment` 接口、`DownloadIcon`

## 阶段 2：保住不可回退的能力

- [x] T004 [US1] 保留「确认材料状态分类」区块与 `ClassificationAutocomplete`（FR-006）
- [x] T005 [US1] 保留 `openReview` 对 `/api/admin/papers/{id}` 与
  `/api/rag/papers/{id}/review-artifact` 的并发拉取（FR-007）——`handleReview` 依赖
  其构造 `material_states` 与 `classification_context`

## 阶段 3：验证

- [x] T006 更新 `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx`
  入口操作：因 Issue #61 移除 Tabs，`getByRole('tab')` 改为 `getByRole('button')`
- [x] T007 移除该测试中对已删引文展示的可见性断言；保留提交载荷断言（后者才是契约保障）
- [x] T008 `npx tsc -b --force` 通过
- [x] T009 `npx vitest run` 全量通过（11 文件 83 用例）

## 阶段 4：文档

- [x] T010 回写 Overview：审核弹窗保留范围与移除范围
- [ ] T011 [US2] 编辑页面审核控件区域 —— **本轮推迟**，见 spec.md US2

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001 | T001、T002 | grep 确认两个区块标题不存在 |
| FR-002、FR-003 | 沿用既有控件 | Vitest 选中「✅ 通过」并提交 |
| FR-006 | T004 | `admin-paper-classification-review.test.tsx` 2 个用例 |
| FR-007 | T005 | 上述用例断言 body 含 classification_context |
| FR-008 | T003 | tsc 无未使用告警 |
| FR-004、FR-005 | T011 | 推迟 |
