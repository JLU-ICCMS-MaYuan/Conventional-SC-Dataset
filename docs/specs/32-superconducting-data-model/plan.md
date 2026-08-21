# 实施计划：全新空库的条件化超导数据模型

**GitHub Issue**：[#32](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/32)

**日期**：2026-08-21

**Spec**：[spec.md](spec.md)

## 摘要

在 #33 的论文 revision、文件、Chunk 和 Evidence 空库 Schema 之后，创建材料状态、结构模型、
理论/实验上下文、纵向 Tc、属性定义、`superconductor_properties` 及三类 Evidence 连接表。
同步 SQLAlchemy/GORM，并用隔离空 MySQL 验证约束。本次不接触现有数据库和历史数据。

## 技术上下文

- **语言与版本**：Python 3.12、Go 1.25、MySQL 8.4
- **主要依赖**：SQLAlchemy 2、Alembic、GORM
- **数据存储**：隔离的全新空 MySQL
- **测试体系**：pytest、Go `testing`、Alembic 空库集成测试
- **目标平台**：Docker Compose 与未来 MySQL fresh install
- **性能目标**：论文 revision、材料+压力、Tc 方法和属性代码查询均有复合索引
- **约束**：双 ORM 一致；不连接现有数据库；子实体无独立审核；原文保真
- **规模范围**：目标 Schema，不对历史数据量作迁移承诺

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| 用户确认 | 只审核论文一次 | revision 公开门，子实体无审核列 | 通过 |
| 用户确认 | 两个数据库均不迁入 | 空库 guard，无回填任务 | 通过 |
| 用户确认 | 普通物性改名 | `property_definitions` + `superconductor_properties` | 通过 |
| 用户确认 | 原文优先 | raw 字段必存，规范字段可选 | 通过 |
| #33 | 同代 Chunk/Evidence | 组合外键绑定同一 paper revision | 通过 |
| AGENTS.md | KISS、DRY、可验证 | 单一科学 Schema revision + 双 ORM 测试 | 通过 |

## Feature 文档结构

```text
docs/specs/32-superconducting-data-model/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/database-invariants.md
├── tasks.md
└── checklists/
    ├── requirements.md
    └── data-migration.md
```

## 源代码结构

```text
alembic/versions/20260609_0001_initial_mysql_schema.py
alembic/versions/20260821_0008_add_superconducting_data_model.py
backend/models.py
goserver/models/models.go
tests/02_maintenance_and_verification/test_issue32_schema.py
tests/02_maintenance_and_verification/test_fresh_mysql_schema.py
goserver/models/scientific_schema_test.go
```

**结构选择**：#33 revision 先建立论文血缘基础，#32 revision 后创建科学表；当前不新增历史
回填服务、兼容读模式或 API。

## 需求到设计的映射

| 来源 | 设计组件 | 验证方式 |
| --- | --- | --- |
| FR-001、FR-005–FR-008 | 组分、状态、结构和上下文 | Python/Go 元数据与 MySQL FK/CHECK |
| FR-002–FR-004 | 论文 revision 公开门 | #33 Schema + 子实体列检查 |
| FR-009–FR-011 | `tc_results` 与代表生成列 | 非法写入和唯一约束测试 |
| FR-012–FR-013、FR-017 | 属性定义与普通物性 raw 字段 | 表结构、命名和原文保留测试 |
| FR-014、FR-018 | 三类 Evidence 连接 | 跨论文/revision 拒绝测试 |
| FR-019–FR-020 | 空库 guard 与双 ORM | fresh MySQL、pytest、Go test |

## 阶段与依赖

1. #33 修复 fresh Alembic 链并建立论文单代血缘。
2. 先增加目标 Schema 元数据和约束失败测试。
3. 创建 #32 空库 revision，同步 SQLAlchemy 与 GORM。
4. 在隔离空 MySQL 执行 `upgrade head` 并验证非法写入。
5. 更新任务状态和 Overview；历史迁移、API、UI 与 GNN 投影保持后续 Issue。

## 回滚边界

- 本次没有业务数据回滚；测试库可直接销毁重建。
- downgrade 只用于隔离空库的迁移可逆性测试。
- revision 检测到现有业务数据必须停止，不能清表绕过。
- 正式旧库迁移方案必须在表结构稳定后另行设计和确认。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| revision 组合外键 | 一次审核必须精确覆盖同代内容 | 只看 `review_status` 会批准修改后内容 |
| 理论/实验上下文分表 | 必填关系与参数语义不同 | 单一 JSON 无法提供强约束 |
| 代表 Tc 生成列 | MySQL 没有通用 partial unique index | 只靠应用校验可被脚本绕过 |
