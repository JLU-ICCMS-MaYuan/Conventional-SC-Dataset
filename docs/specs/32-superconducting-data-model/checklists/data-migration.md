# 空库 Schema 验收检查表：条件化超导数据模型

**目的**：约束空库建立、隔离测试和现有数据库保护

**创建日期**：2026-08-21

**Feature**：[spec.md](../spec.md)

## 环境隔离

- [ ] CHK001 `DATABASE_URL` 是否指向可销毁空 MySQL？[FR-019]
- [ ] CHK002 是否确认现有数据库、SQL dump 和历史文件均未作为输入？[范围外事项]
- [ ] CHK003 是否验证测试库初始业务记录数为 0？[T002]
- [ ] CHK004 空库 guard 是否在已有记录时于破坏性操作前中止？[SC-008]

## Schema

- [ ] CHK005 Alembic 是否单一 head 且 fresh `upgrade head` 成功？[SC-007]
- [ ] CHK006 目标科学表、三类 Evidence 连接和索引是否齐全？[FR-005–FR-018]
- [ ] CHK007 旧三类科学表是否不属于 head 目标 Schema？[FR-009、FR-013]
- [ ] CHK008 SQLAlchemy、GORM 和 MySQL 是否一致？[FR-020]

## 强约束

- [ ] CHK009 子实体审核字段是否为 0？[SC-001]
- [ ] CHK010 跨论文/revision 关系是否被拒绝？[SC-003]
- [ ] CHK011 理论/实验互斥和范围检查是否生效？[FR-010、FR-015]
- [ ] CHK012 代表 Tc 重复写入是否被拒绝？[SC-004]
- [ ] CHK013 同材料同压力多状态是否允许？[SC-002]
- [ ] CHK014 raw 字段是否保留且规范字段可空？[SC-006]

## 收尾

- [ ] CHK015 downgrade/upgrade 是否只在空测试库演练？[quickstart.md]
- [ ] CHK016 是否记录 MySQL、pytest、Go test 和 `git diff --check`？[T015]
- [ ] CHK017 是否未执行历史迁移、清表或旧库 DDL？[FR-019]
