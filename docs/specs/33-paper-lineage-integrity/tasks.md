# 实施任务：全新空库的单代论文血缘

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：建立可执行的 fresh migration 前提。

- [x] T001 核对 `alembic/versions/` 当前 head，确认 `0006` 已由用户名 Feature 占用且 #33 使用 `0007`。
- [x] T002 在 `tests/02_maintenance_and_verification/test_fresh_mysql_schema.py` 建立隔离空 MySQL 与现有数据 guard 测试入口。
- [x] T003 修复 `alembic/versions/20260609_0001_initial_mysql_schema.py`，在 `0005` 前创建 `paper_chunks` 及目标基础列。

## 阶段 2：基础 Schema

**目的**：先写失败测试，再实现 Alembic 和双 ORM。

- [x] T004 [P] 在 `tests/02_maintenance_and_verification/test_issue33_paper_lineage.py` 编写论文 revision、文件、Chunk、Evidence、Review Event 约束测试。
- [x] T005 [P] 在 `goserver/models/paper_lineage_test.go` 编写 GORM 表名、字段和外键元数据测试。
- [x] T006 在 `alembic/versions/20260821_0007_add_paper_lineage_schema.py` 建立目标论文血缘 Schema 和空库 guard。
- [x] T007 在 `backend/models.py` 同步 Paper/File/Chunk/Evidence/Review Event SQLAlchemy 模型。
- [x] T008 在 `goserver/models/models.go` 同步对应 GORM 模型。

## 阶段 3：用户故事 1——唯一文件来源（P1，MVP）

**独立验收**：目标 Paper 无旧路径列，同论文最多一个 main。

- [x] T009 [US1] 验证 `papers.source_file_path` 不存在，文件 role CHECK、路径和顺序唯一约束生效。
- [x] T010 [US1] 验证第二个 main 被数据库拒绝，并在契约中保留提交/审核“恰好一个”门。

## 阶段 4：用户故事 2——单代 Chunk 与 Evidence（P1）

**独立验收**：每文件 Chunk 编号唯一，Evidence 必须引用同论文 revision Chunk。

- [x] T011 [US2] 验证相同文件重复编号拒绝、不同文件同编号允许。
- [x] T012 [US2] 验证 Evidence Chunk FK 非空及跨论文/跨 revision 写入拒绝。
- [x] T013 [US2] 验证 Evidence 只保留 Chunk ID 与快照，不重复 File/Chunk index 归属列。

## 阶段 5：用户故事 3/4——复审边界与审核事件（P1）

**独立验收**：论文公开门可表达；审核事件记录 revision 并限制删除论文。

- [x] T014 [US3] 验证 `content_revision/approved_revision/review_status` CHECK 和公开索引。
- [x] T015 [US4] 验证 Review Event 论文/用户 FK、revision、状态 CHECK 和 request 幂等唯一约束。

## 阶段 6：用户故事 5——空库验收（P1）

- [x] T016 [US5] 在隔离空 MySQL 执行 `upgrade head`，确认 `0005` 不再因缺少 `paper_chunks` 失败。
- [x] T017 [US5] 执行空库 downgrade/upgrade、Python 测试、Go 测试和 `git diff --check`。
- [x] T018 [US5] 验证已有业务数据的测试库在目标 revision 前被 guard 拒绝。

## 最终阶段：完善与收敛

- [x] T019 与 #32 执行实体、revision、Evidence、迁移编号和任务覆盖的跨 Spec analyze。
- [x] T020 使用 `big-project-overview-maintainer` 仅在 Schema/ORM 落地后更新当前数据模型事实。
- [x] T021 使用 `big-project-issue-manager` 同步 #33，并为 RAG/Qdrant 单代事务编排保留后续集成工作。

## 依赖与执行顺序

- T001–T003 阻断 `0007`。
- T004–T005 可并行；T006–T008 串行核对同一 Schema。
- US1 是 US2 的文件身份前提，US2 是 #32 Evidence 连接前提。
- T016–T021 依赖全部 Schema 任务。

## 需求覆盖

| 来源 | 任务 |
| --- | --- |
| FR-001–FR-003 / US1 | T003–T010 |
| FR-004–FR-009 / US2 | T004–T008、T011–T013 |
| FR-010–FR-012 / US3 | T014、T019、T021 |
| FR-013–FR-015 / US4 | T004–T008、T015 |
| FR-016–FR-018 / US5 | T001–T008、T016–T019 |
| SC-001–SC-008 | T009–T19 |

## MVP 与增量策略

1. 完成 T001–T010，得到可审核论文的唯一文件来源。
2. 完成 T011–T015，得到单代 Chunk/Evidence 与审核 revision。
3. 完成空 MySQL 验收后由 #32 建立科学表。
4. RAG/Qdrant 和审核 API 编排在后续 Issue 实现。
