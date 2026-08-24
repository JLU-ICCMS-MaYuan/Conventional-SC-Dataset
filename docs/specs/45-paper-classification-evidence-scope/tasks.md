# 实施任务：论文分类证据作用域与汇总前状态

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：固定 Issue、文档门和真实故障边界。

- [x] T001 创建并验证 GitHub Issue #45 的唯一 `type:bug` 标签及父 Epic #24 双向链接
- [x] T002 创建 `docs/specs/45-paper-classification-evidence-scope/` 完整规划产物并通过需求质量检查

## 阶段 2：基础能力

**目的**：先以确定性测试复现真实分段产物到公开 DTO 和汇总输入的故障。

- [x] T003 [P] 在 `tests/01_decentralized_uploading/test_issue24_persistence_and_ui.py` 增加 Li–Mg–H 作用域、`unknown` 与元数据冲突回归测试
- [x] T004 [P] 在 `tests/01_decentralized_uploading/test_issue23_upload_lifecycle.py` 增加全文汇总输入作用域筛选回归测试
- [x] T005 [P] 在 `backend/tests/test_upload_jobs.py` 增加分段契约版本与旧缓存重读回归测试
- [x] T006 [P] 在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加分类候选状态与自由材料文本回归测试

## 阶段 3：用户故事 1——引用背景不污染本文分类（P1，MVP）

**目标**：分段证据区分本文和引用工作，后端只提升本文证据。

**独立验收**：Li–Mg–H 固定产物通过公开解析详情和全文汇总输入测试。

### 实施

- [x] T007 [US1] 在 `backend/ingest/upload_jobs.py` 扩展分段提示词和结构化结果契约，要求论文类型及材料类型证据输出作用域
- [x] T008 [US1] 在 `backend/ingest/upload_jobs.py` 实现本文候选筛选并保留引用工作原始分段证据
- [x] T009 [US1] 在 `backend/ingest/upload_jobs.py` 净化全文汇总输入，仅让本文有效分类候选参与最终建议

## 阶段 4：用户故事 2——汇总前不显示正式分类冲突（P1）

**目标**：分类候选和元数据冲突采用不同状态语义。

**独立验收**：同一解析详情中分类字段显示“候选尚未汇总”，标题字段仍显示“有冲突”。

### 实施

- [x] T010 [US2] 在 `backend/ingest/upload_jobs.py` 为解析中的分类字段生成 `pending_summary`，并将 `unknown` 作为无判断处理
- [x] T011 [US2] 在 `frontend/src/components/UploadParsingDetail.tsx` 展示“候选尚未汇总”和无判断提示，保留非分类冲突样式

## 阶段 5：用户故事 3——自由材料类型继续进入人工审核（P2）

**目标**：只筛选材料证据作用域，不限制候选文本。

**独立验收**：测试中的“高压三元氢化物超导体”原样进入候选和最终草稿路径。

### 实施

- [x] T012 [US3] 在 `backend/ingest/upload_jobs.py` 保持 `sc_type_candidates.value` 自由文本透传且不执行枚举或同义词映射

## 阶段 6：兼容、验证与文档

- [x] T013 在 `backend/ingest/upload_jobs.py` 增加分段结果契约版本，旧缓存恢复时定向重读且公开预览安全降级
- [x] T014 按 `docs/specs/45-paper-classification-evidence-scope/quickstart.md` 运行后端、前端、真实产物回放和生产构建验证
- [x] T015 使用 `big-project-overview-maintainer` 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md` 的作用域和汇总前状态事实
- [x] T016 核对 FR/SC、清理调试产物、更新 Issue #45 实施证据并按仓库规则自动提交本任务文件

## 依赖与执行顺序

- T001–T002 完成后才能进入实施。
- T003–T006 可并行编写，但必须先观察失败再执行 T007–T013。
- T007 阻断 T008–T009 和 T013；T008 阻断 T010；T010 阻断 T011。
- T012 与 T010–T011 可并行，但同一后端文件上的修改保持串行。
- T014 阻断 T015–T016。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001–003 / SC-001 / US1 | T003、T007–T009、T014 | 作用域生产、筛选、证据保留和回放 |
| FR-004–006 / SC-002–003 / US2 | T003、T006、T010–T011、T014 | `unknown` 语义、候选状态和元数据冲突回归 |
| FR-007 / SC-004 / US3 | T006、T012、T014 | 自由材料类型透传 |
| FR-008 / SC-005 | T005、T013–T014 | 旧缓存版本化兼容 |
| FR-009 | T004、T009、T014 | 全文汇总输入边界 |
| FR-010 / SC-006 | T003–T006、T014、T016 | 确定性测试和完整验证 |

## MVP 与增量策略

1. 先完成 T003–T010，阻止引用背景污染本文分类并修复后端状态。
2. 完成 T011–T013，交付用户可见状态、自由类型和旧缓存兼容。
3. 完成完整回归、Overview 回写、Issue 证据和 Git 提交。
