# 需求质量检查表：全新空库的单代论文血缘

**目的**：检查需求完整性、清晰度、可测性和跨文档一致性

**创建日期**：2026-08-21

**Feature**：[spec.md](../spec.md)

## 完整性

- [x] CHK001 是否明确五表保持独立？[FR-001]
- [x] CHK002 是否明确唯一文件路径来源和 main 规则？[FR-002–FR-003、US1]
- [x] CHK003 是否覆盖论文 revision、单代 Chunk 和 Evidence？[FR-004–FR-009、US2]
- [x] CHK004 是否定义重新分块、Qdrant 同代和重新审核？[FR-010–FR-012、US3]
- [x] CHK005 是否定义 Review Event 论文 FK、revision 和删除语义？[FR-013–FR-014、US4]
- [x] CHK006 是否明确空库边界且无历史迁移？[FR-016–FR-018、US5]

## 清晰度与可度量性

- [x] CHK007 “当前代”是否明确为唯一内容而非多版本键？[FR-009]
- [x] CHK008 是否区分数据库“至多一个 main”和审核门“恰好一个 main”？[FR-003]
- [x] CHK009 Evidence 是否明确直接引用 Chunk 且保留快照？[FR-007–FR-008]
- [x] CHK010 是否量化跨 revision、重复编号和孤立事件的拒绝结果？[SC-003、SC-004、SC-007]
- [x] CHK011 是否明确 MySQL/Qdrant 失败时论文保持 pending？[US3、FR-012]

## 一致性与覆盖

- [x] CHK012 Spec、Data Model、Contract 和 Tasks 的列与删除语义是否一致？[FR-002–FR-015]
- [x] CHK013 是否删除兼容读取、历史回填、多代 Evidence 和收缩迁移？[范围外事项]
- [x] CHK014 是否与 #32 的一次论文审核和 revision 依赖一致？[假设与依赖]
- [x] CHK015 每个 FR、SC 和用户故事是否有任务与验证映射？[tasks.md]

## 备注

- 本检查表检查需求文本质量，不测试实现行为。
- 当前无待澄清项；不可恢复的 Q13/Q14 题干不再向用户重复询问。
