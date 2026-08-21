# 空库 Schema 验收检查表：单代论文血缘

**目的**：约束 fresh migration、隔离测试和现有数据库保护

**创建日期**：2026-08-21

**Feature**：[spec.md](../spec.md)

## 环境隔离

- [ ] CHK001 `DATABASE_URL` 是否指向可销毁的空 MySQL？[FR-017]
- [ ] CHK002 是否确认未读取两个现有数据库和历史文件？[范围外事项]
- [ ] CHK003 是否验证业务表初始记录数为 0？[T002]
- [ ] CHK004 空库 guard 是否在已有记录时于重构 DDL 前中止？[SC-008]

## Fresh Alembic

- [ ] CHK005 `paper_chunks` 是否在 `0005` 修改前已经创建？[T003、FR-016]
- [ ] CHK006 Alembic 是否只有一个 head 且 `upgrade head` 成功？[SC-008]
- [ ] CHK007 `papers.source_file_path` 是否不在目标 Schema？[SC-001]
- [ ] CHK008 SQLAlchemy、GORM 与 MySQL 是否一致？[FR-018]

## 文件、Chunk 与 Evidence

- [ ] CHK009 role CHECK 与每论文最多一个 main 是否生效？[SC-002]
- [ ] CHK010 `(paper_file_id, chunk_index)` 唯一约束是否生效？[SC-004]
- [ ] CHK011 File/Chunk/Evidence 的 revision 组合外键是否拒绝串线？[SC-003]
- [ ] CHK012 Evidence 是否只保存 Chunk 外键和原文快照？[FR-007–FR-008]

## 审核事件与收尾

- [ ] CHK013 Review Event 论文/用户外键和 `ON DELETE RESTRICT` 是否生效？[SC-007]
- [ ] CHK014 Review Event 是否记录被审核 revision 且 request 幂等？[FR-014]
- [ ] CHK015 downgrade/upgrade 是否只在空测试库执行？[quickstart.md]
- [ ] CHK016 是否记录 MySQL、pytest、Go test 和 `git diff --check` 结果？[T017]
- [ ] CHK017 是否未执行历史回填、兼容读取或旧库 DDL？[FR-017]
