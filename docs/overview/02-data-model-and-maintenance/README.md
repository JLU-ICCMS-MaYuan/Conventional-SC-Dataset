# 数据模型与维护

## 功能边界

该功能负责主业务数据的结构定义、数据库连接、初始化、迁移、离线导入导出以及 Docker 部署中的数据依赖说明。它不负责在线审核决策、外部数据集科学校验或 RAG 问答质量。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [领域模型与数据库结构](domain-model-and-schema.md) | 定义元素、材料、论文、关键物性、记录、结构、图表组合和用户关系 | GORM、SQLAlchemy |
| [数据库初始化与迁移](database-initialization-and-migrations.md) | 建表、填充周期表并执行版本迁移 | Alembic、Docker Compose、启动脚本 |
| [数据导入与导出](data-import-and-export.md) | 离线交换用户、论文、记录和结构数据 | JSON、主业务数据库 |
| [部署与运行时](deployment-and-runtime.md) | Docker 服务编排、配置和运行时边界 | Docker Compose、Nginx、Go、Python |

## 功能组成

```text
数据模型与维护
├── 领域模型与数据库结构
├── 数据库初始化与迁移
├── 数据导入与导出
└── 部署与运行时
```

## 关联关系

领域模型是所有主业务 API 的共同数据契约。Go 服务通过 GORM 读取 MySQL 并提供主要公开 API；Python 服务通过 SQLAlchemy 承担 RAG、结构、Tc 估算和部分工具接口。Docker 部署要求显式配置 MySQL、Redis、Neo4j、Qdrant 与数据挂载。
