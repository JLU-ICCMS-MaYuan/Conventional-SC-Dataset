# 领域模型与数据库结构

## 功能说明

定义 SC-Wiki 主业务数据的实体、字段和关联关系，为 API、审核、检索和维护工具提供共同契约。

## 当前行为

- `PeriodicTableElement` 保存元素基础信息。
- `ChemicalSystem` 和 `Superconductor` 表达元素体系与具体超导材料。
- `Paper` 保存 DOI、标题、作者、年份、摘要、审核状态、上传者和 LLM 富化字段。
- `KeyProperty` 是当前 Go 搜索、上传富化和图表的主要物性记录表，保存规范物性名、原始名称、数值范围、单位、压强、温度、超导类型、文章类型、结构文本和 `is_primary`。
- `SuperconductorRecord` 仍定义实验/理论 Tc、压力、空间群、计算参数和图表可见性等字段，但当前部分新 Go API 不以它作为主查询入口。
- `SuperconductorStructure` 保存结构内容、解析元数据和审核状态。
- `User` 保存身份、角色、审批和邮箱验证信息。
- `ChartGroup` 与 `ChartGroupItem` 保存可视化图表组合，支持引用 `key_properties` 或自定义点。
- `AlexandriaEntry`、`AlexandriaElementIdx` 和 `HTSCMaterial` 保存外部数据集查询所需字段。
- `PaperChunk` 保存 RAG 文本块元数据，向量本体写入 Qdrant。

## 工作流程

Go API 通过 GORM 结构体访问 MySQL，Python API 和离线工具通过 SQLAlchemy 会话访问同一业务库或 RAG 配置库。关系字段连接材料、论文、关键物性、记录、结构、图表组合和用户；Alembic 以 SQLAlchemy 模型元数据为迁移参照。

## 约束

- 当前 Docker 部署要求 `DATABASE_URL` 指向 MySQL；Python 仍保留 SQLite fallback 逻辑，但 Go 服务要求可解析的 MySQL DSN。
- GORM 与 SQLAlchemy 两套模型需要保持字段一致，否则会出现接口可读写范围不一致。
- RAG 向量数据位于 Qdrant，Neo4j 图数据由同步工具或 `graph.json` 快照支撑，不属于普通关系表字段。
- 当前模型是事实来源；历史迁移只说明演进过程。

## 代码与测试

- `backend/models.py`
- `goserver/models/models.go`
- `backend/database.py`
- `goserver/database/db.go`
- `goserver/config/config.go`
- `alembic/versions/`
- `tests/02_maintenance_and_verification/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- `superconductor_records` 与 `key_properties` 的职责边界仍需在后续实现中统一；当前 Overview 只记录两者并存事实。
