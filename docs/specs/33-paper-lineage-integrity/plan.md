# 实施计划：全新空库的单代论文文件、Chunk 与 Evidence

**GitHub Issue**：[#33](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/33)

**日期**：2026-08-21

**Spec**：[spec.md](spec.md)

## 摘要

修复 fresh Alembic 链中 `paper_chunks` 未创建却被 `0005` 修改的问题，并在 `0006` 之后新增
#33 空库 revision：建立论文 revision、唯一文件来源、最多一个 main、文件内 Chunk 唯一、
Evidence→Chunk 组合外键和 Review Event 论文外键。同步 SQLAlchemy/GORM，不迁移历史数据。

## 技术上下文

- **语言与版本**：Python 3.12、Go 1.25、MySQL 8.4
- **主要依赖**：SQLAlchemy 2、Alembic、GORM
- **数据存储**：隔离的全新空 MySQL；Qdrant 仅为后续索引投影
- **测试体系**：pytest、Go `testing`、Alembic 空库集成测试
- **目标平台**：Docker Compose 与未来 MySQL fresh install
- **性能目标**：文件、Chunk、Evidence 和审核事件主要关系均由复合索引支持
- **约束**：单代内容；一次论文审核；不连接现有数据库；双 ORM 一致
- **规模范围**：目标 Schema，不承担历史数据迁移

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| 用户确认 | RAG/搜索/审核同代 Chunk | 当前代唯一键 + revision 组合外键 | 通过 |
| 用户确认 | 不迁入两个数据库 | 空库 guard，无回填任务 | 通过 |
| #23/#26 | 三态审核、恰好一个 main | CHECK + 至多一个 DB 约束 + 审核门契约 | 通过 |
| #32 | 一次审核覆盖科学内容 | `content_revision/approved_revision` | 通过 |
| AGENTS.md | KISS、可验证 | 五表不合并，空 MySQL 验收 | 通过 |

## Feature 文档结构

```text
docs/specs/33-paper-lineage-integrity/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/migration-invariants.md
├── tasks.md
└── checklists/
    ├── requirements.md
    └── data-migration.md
```

## 源代码结构

```text
alembic/versions/20260609_0001_initial_mysql_schema.py
alembic/versions/20260820_0005_add_multifile_uploads.py
alembic/versions/20260821_0007_add_paper_lineage_schema.py
backend/models.py
goserver/models/models.go
tests/02_maintenance_and_verification/test_issue33_paper_lineage.py
tests/02_maintenance_and_verification/test_fresh_mysql_schema.py
goserver/models/paper_lineage_test.go
```

**结构选择**：修复基础 migration 只补足 `0005` 的前置表；`0007` 统一完成目标血缘约束；
#32 的 `0008` 依赖该 revision。当前不新增文件回填服务或 RAG 业务代码。

## 需求到设计的映射

| 来源 | 设计组件 | 验证方式 |
| --- | --- | --- |
| FR-001–FR-003 / US1 | 五表、文件角色和 main 生成列 | MySQL 唯一约束、模型测试 |
| FR-004–FR-009 / US2 | revision、Chunk 唯一、Evidence 组合外键 | 跨 revision 非法写入 |
| FR-010–FR-012 / US3 | 单代替换契约与公开门 | Schema 状态测试，后续集成 Issue |
| FR-013–FR-015 / US4 | Review Event 外键与 revision | FK、CHECK、幂等元数据测试 |
| FR-016–FR-018 / US5 | fresh 链、guard、双 ORM | 空 MySQL upgrade、pytest、Go test |

## 阶段与依赖

1. 修复基础 Alembic 对 `paper_chunks` 的缺失。
2. 先写 #33 Schema/ORM 失败测试。
3. 创建 `0007`，同步 SQLAlchemy 和 GORM。
4. 在隔离空 MySQL 验证 upgrade/downgrade/upgrade 和非法关系。
5. #32 基于 `0007` 创建科学表。
6. 后续 Issue 按单代契约实现 RAG/Qdrant 和审核业务切换。

## 回滚边界

- 测试库无业务数据，可销毁重建。
- downgrade 仅在隔离空库验证 migration 可逆性。
- 已有业务数据触发 guard 后必须停止，不能自动删除或回填。
- 本 Feature 不承诺现有库上的升级路径。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| main 生成列 | MySQL 不支持通用 partial unique index | 仅应用校验可被其他写入路径绕过 |
| revision 组合外键 | 防止 Evidence/Chunk 跨代串线 | 单列 ID 外键无法证明论文 revision 一致 |
| 单代显式替换 | 用户要求全系统只使用同一代 | 多版本表会增加存储和后台分支 |
