# 实施任务：上传解析记录的英文输出与持久化语言一致性

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/language-contract.md](contracts/language-contract.md)

## 阶段 1：语言契约与测试

- [ ] T001 [US3] 在 `backend/tests/test_upload_workflow.py` 为分段候选、部分草稿、草稿保存和提交增加英文生成字段与中文拒绝测试。
- [ ] T002 [P] [US1] 在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加已验证分段记录与实时预览的英文显示测试。
- [ ] T003 [P] [US3] 在隔离 MySQL 提交测试中增加违规生成字段不得持久化的事务测试。

## 阶段 2：统一解析与写入规则

- [ ] T004 [US1] 在 `backend/ingest/` 新增共享的生成字段语言策略与结构化错误类型，明确 chunk/draft/submit 作用域。
- [ ] T005 [US1] 修改 `backend/ingest/upload_jobs.py` 的 `CHUNK_SYSTEM_PROMPT`、`SUMMARY_SYSTEM_PROMPT`、分段清单与部分草稿写入点，调用策略并在违规时走既有失败/重试语义。
- [ ] T006 [US2] 修改 `backend/api/rag.py` 的草稿保存、提交和管理员科学数据重写入口，在持久化前调用同一策略。
- [ ] T007 [US2] 修改 `backend/ingest/scientific_drafts.py` 或其调用边界，确保正式论文写入不会绕过验证。
- [ ] T008 [US1] 检查 `frontend/src/components/UploadParsingDetail.tsx`，只展示服务端已验证的分段与草稿，并补齐必要的错误呈现测试。

## 阶段 3：历史数据与收敛

- [ ] T009 [US3] 在 `backend/scripts/` 实现一次性、可审计的正式论文生成字段英文修复工具，并在隔离库验证已修复/跳过/失败报告。
- [ ] T010 [US3] 验证完成后删除 T009 的一次性脚本，保留测试或执行审计证据，确认 Redis 快照未迁移。
- [ ] T011 运行相关 pytest、Vitest、隔离 MySQL 测试以及 quickstart 的中英文原文样本走查。
- [ ] T012 使用 `big-project-overview-maintainer` 更新 PDF 解析、上传审核和格式存储 Overview 文档。

## 依赖与执行顺序

- T001 至 T003 先于 T004 至 T008。
- T004 是所有语言校验接入的阻断项。
- T009 在新数据路径通过后执行；T010 必须在 T009 验证后执行。
- T011 和 T012 位于收尾阶段。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 至 FR-002 | T004、T005 | prompt 和共享规则 |
| FR-003 至 FR-004 | T001、T003、T005–T007 | 三层写边界与失败语义 |
| FR-005 | T002、T008 | 解析记录与实时预览 |
| FR-006 | T001、T011 | 中文原文保留测试 |
| FR-007 | T009、T010 | 正式历史数据受控收敛 |
