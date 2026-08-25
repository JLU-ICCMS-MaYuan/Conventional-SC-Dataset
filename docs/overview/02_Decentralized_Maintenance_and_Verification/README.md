# 去中心化维护与验证

## 功能边界

该功能负责平台数据的结构化维护与验证治理：主业务数据的模型定义、初始化、迁移、导入导出与部署运行时，论文与记录的审核决策，管理员资格审批，以及晶体结构文本的格式校验与存储。它不负责检索算法、问答质量或社区互动。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [领域模型与数据库结构](domain-model-and-schema.md) | 定义并区分已验证的 fresh 目标 Schema 与两个现有运行库 | GORM、SQLAlchemy、Alembic |
| [运行中 MySQL 表目录](mysql-schema-catalog.md) | 记录两个尚未迁移的现有 MySQL 旧 Schema、字段、关系和规模 | MySQL、Alembic |
| [数据库初始化与迁移](database-initialization-and-migrations.md) | 建表、填充周期表并执行版本迁移 | Alembic、Docker Compose、启动脚本 |
| [数据导入与导出](data-import-and-export.md) | 离线交换用户、论文、记录和结构数据 | JSON、主业务数据库 |
| [部署与运行时](deployment-and-runtime.md) | Docker 服务编排、配置和运行时边界 | Docker Compose、Nginx、Go、Python |
| [论文与记录审核](literature-and-record-review.md) | 管理员论文审核与超级管理员的图表、快讯和治理工作台 | 分级权限、论文与关键物性模型 |
| [角色与管理员审批](roles-and-administrator-approval.md) | 用户中心、公开资料、管理员资格申请和账号治理 | 账户 API、超级管理员 API、审计模型 |
| [格式校验与存储](format-validation-and-storage.md) | 解析结构文本、计算摘要并保存元数据 | pymatgen、结构模型 |

## 功能组成

```text
去中心化维护与验证
├── 数据模型与 Schema 维护（模型、迁移、导入导出、部署）
├── 论文与记录审核（验证决策）
├── 角色与管理员审批（资格治理）
└── 结构格式校验与存储（数据验证）
```

## 关联关系

领域模型是所有主业务 API 的共同数据契约。01 上传提交的论文在此完成审核决策；审核通过的论文经发布后进入 03 检索与 05 问答。Go 服务通过 GORM 读取 MySQL 并提供主要公开 API；Python 服务通过 SQLAlchemy 承担 RAG、结构、Tc 估算和部分工具接口。
