# 领域模型与数据库结构

## 功能说明

定义 SC-Wiki 主业务数据的实体、字段和关联关系，为 API、审核、检索和维护工具提供共同契约。

## 当前行为

- `PeriodicTableElement` 保存元素基础信息。
- `ChemicalSystem` 和 `Superconductor` 表达元素体系与具体超导材料。
- `Paper` 与 `SuperconductorRecord` 表达论文及其中的实验/理论物性记录。
- `SuperconductorStructure` 保存结构内容、解析元数据和审核状态。
- `User` 保存身份、角色、审批和邮箱验证信息。

## 工作流程

API 或离线工具通过 SQLAlchemy 会话读写实体；关系字段连接材料、论文、记录、结构和用户；Alembic 以模型元数据为迁移参照。

## 约束

- 主业务访问使用同步 SQLAlchemy；RAG 使用另一套异步模型和数据库配置。
- SQLite 与 MySQL 均被依赖声明支持，具体生产数据库类型由 `DATABASE_URL` 决定。
- 当前模型是事实来源；历史迁移只说明演进过程。

## 代码与测试

- `backend/models.py`
- `backend/database.py`
- `alembic/versions/`
- `tests/02_maintenance_and_verification/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 旧 `crud.py` 和部分旧 schema 命名仍与重构后的模型并存，残留范围待核验。
