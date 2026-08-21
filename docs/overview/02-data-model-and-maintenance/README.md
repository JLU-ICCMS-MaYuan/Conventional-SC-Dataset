# 数据模型与维护

## 功能边界

该功能负责主业务数据的结构定义、数据库连接、初始化、迁移、离线导入导出以及 Docker 部署中的数据依赖说明。它不负责在线审核决策、外部数据集科学校验或 RAG 问答质量。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [领域模型与数据库结构](domain-model-and-schema.md) | 定义并区分已验证的 fresh 目标 Schema 与两个现有运行库 | GORM、SQLAlchemy、Alembic |
| [运行中 MySQL 表目录](mysql-schema-catalog.md) | 记录两个尚未迁移的现有 MySQL 旧 Schema、字段、关系和规模 | MySQL、Alembic |
| [数据库初始化与迁移](database-initialization-and-migrations.md) | 建表、填充周期表并执行版本迁移 | Alembic、Docker Compose、启动脚本 |
| [数据导入与导出](data-import-and-export.md) | 离线交换用户、论文、记录和结构数据 | JSON、主业务数据库 |
| [部署与运行时](deployment-and-runtime.md) | Docker 服务编排、配置和运行时边界 | Docker Compose、Nginx、Go、Python |

## 功能组成

```text
数据模型与维护
├── 领域模型与数据库结构
├── 运行中 MySQL 表目录
├── 数据库初始化与迁移
├── 数据导入与导出
└── 部署与运行时
```

## 关联关系

领域模型是所有主业务 API 的共同数据契约。Go 服务通过 GORM 读取 MySQL 并提供主要公开 API；Python 服务通过 SQLAlchemy 承担 RAG、结构、Tc 估算和部分工具接口。Docker 部署要求显式配置 MySQL、Redis、Neo4j、Qdrant 与数据挂载。

代码库已经为全新空 MySQL 落地 [Feature #32](../../specs/32-superconducting-data-model/spec.md)
和 [Feature #33](../../specs/33-paper-lineage-integrity/spec.md) 的 Alembic Schema、SQLAlchemy
模型与 GORM 模型，并通过隔离 MySQL 升降级和约束验证。该结果尚未部署到两个现有运行
数据库，也不读取、迁移或修改历史数据；现有库仍以 `key_properties`、
`superconductors_structures` 和旧论文血缘列为准。RAG/Qdrant、API、导入导出和网页切换
仍是后续工作，不能把 fresh Schema 就绪理解为业务链路已经切换。
