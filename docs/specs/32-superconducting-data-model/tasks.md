# 实施任务：全新空库的条件化超导数据模型

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 核对 `alembic/versions/` 单一 head，确定 #33 `0007` 后由 #32 `0008` 建立科学表。
- [x] T002 在 `tests/02_maintenance_and_verification/test_fresh_mysql_schema.py` 建立隔离空 MySQL 和现有数据 guard 测试入口。

## 阶段 2：基础 Schema

- [x] T003 [P] 在 `tests/02_maintenance_and_verification/test_issue32_schema.py` 编写实体、精度、外键、CHECK、索引和旧表缺失测试。
- [x] T004 [P] 在 `goserver/models/scientific_schema_test.go` 编写 GORM 表名、字段和关联测试。
- [x] T005 在 `alembic/versions/20260821_0008_add_superconducting_data_model.py` 创建目标科学表并移除空库临时旧表。
- [x] T006 在 `backend/models.py` 用目标模型替换 `KeyProperty`、横向记录和旧结构模型。
- [x] T007 在 `goserver/models/models.go` 增加目标 GORM 模型并将 `KeyProperty` 改为 `SuperconductorProperty`。

## 阶段 3：用户故事 1——一次论文审核（P1，MVP）

**独立验收**：科学子实体无审核列，全部记录携带论文 revision。

- [x] T008 [US1] 验证子实体审核列为零及 revision 组合外键。
- [x] T009 [US1] 建立科学记录到论文 revision 的约束和公开查询索引。

## 阶段 4：用户故事 2——多状态、多结构和纵向 Tc（P1）

**独立验收**：同材料同压力可保存多相、多结构和同方法多 Tc，非法上下文被拒绝。

- [x] T010 [US2] 覆盖相同压力、多结构、父子结构、理论/实验互斥和数值范围。
- [x] T011 [US2] 建立代表生成列与唯一约束，验证每组最多一条代表 Tc。

## 阶段 5：用户故事 3——普通物性与原文优先（P1）

**独立验收**：`superconductor_properties` 同时保存 raw 与 canonical 字段，Tc 被排除。

- [x] T012 [US3] 建立属性定义、普通物性和普通物性 Evidence 连接。
- [x] T013 [US3] 验证目标表不含 `key_properties`，raw 字段必填且规范字段可空。

## 阶段 6：用户故事 4——空库验收（P1）

- [x] T014 [US4] 执行空 MySQL upgrade/downgrade/upgrade，检查表和全部强约束。
- [x] T015 [US4] 运行 pytest、Go 模型测试和 `git diff --check`。

## 最终阶段：完善与收敛

- [x] T016 对照 FR、SC、#33 和实现执行跨 Spec analyze，修复 CRITICAL/HIGH 问题。
- [x] T017 使用 `big-project-overview-maintainer` 仅在 Schema/ORM 落地后更新 Overview。
- [x] T018 使用 `big-project-issue-manager` 同步 #32、#12 取代关系和 #13 GNN 投影边界。

## 依赖与执行顺序

- T001–T002 阻断实现；T003–T004 可并行；T005–T007 串行核对 Schema。
- US1 是 US2、US3 的 revision 基础；#33 完成后才能执行 T005。
- T014–T018 依赖全部 Schema 任务。

## 需求覆盖

| 来源 | 任务 |
| --- | --- |
| FR-001–FR-008 / US1–US2 | T003–T010 |
| FR-009–FR-011 / US2 | T005–T011 |
| FR-012–FR-017 / US3 | T003、T005–T007、T012–T013 |
| FR-018–FR-020 / US4 | T002–T007、T014–T016 |
| SC-001–SC-008 | T008、T010–T016 |

## MVP 与增量策略

1. 完成 #33 和 T001–T009，得到一次审核与 revision 基础。
2. 完成 T010–T013，得到完整科学目标 Schema。
3. 完成空 MySQL 验收和文档/Issue 收敛。
