# SC-Wiki 当前功能总览

## 项目说明

SC-Wiki 是面向超导材料研究的数据检索与知识服务应用。当前代码以 React/Vite 提供单页应用，以 Go Gin 服务作为主要公开 API 聚合层，并将未覆盖的接口反向代理到 Python FastAPI 服务；数据库侧同时使用 GORM 与 SQLAlchemy 模型访问 MySQL 中的用户、论文、材料、物性记录、晶体结构、外部数据和图表组合数据。

当前能力覆盖超导数据去中心化上传（PDF 解析管线）、数据维护与审核验证、本地与外部材料检索、知识图谱、RAG 文献问答、实验性 Tc 估算和研究者社区。部分能力依赖 Docker 部署中的 MySQL、Redis、Neo4j、Qdrant、外部数据文件和 LLM/Embedding 配置，具体边界见各功能文档。

## 大功能目录

| 大功能 | 职责 | 主要依赖 |
| --- | --- | --- |
| [超导快讯与最新论文](news.md) | 官方来源每日采集、稳定标识去重、独立资讯列表与来源状态 | Python、独立 RQ 队列、Redis、MySQL、Go API |
| [超导数据去中心化上传](01_Decentralized_Uploading_of_Superconductivity_Data/README.md) | PDF/TXT/MD 与结构附件的上传、五阶段 AI 解析、校对提交落库 | RQ Worker、Redis、LLM、MySQL、Qdrant |
| [去中心化维护与验证](02_Decentralized_Maintenance_and_Verification/README.md) | 领域模型、迁移、导入导出、部署，论文审核、管理员审批、结构校验 | GORM、SQLAlchemy、Alembic、MySQL |
| [超导数据搜索与数据库发现](03_Superconductivity_Data_Search_and_Database_Discovery/README.md) | 本地与外部材料检索、结果分享导出、代表结构下载、Tc 统计图表 | Go API、主业务数据库、外部数据表 |
| [超导发展知识图谱](04_Superconductivity_Development_Knowledge_Graph/README.md) | `graph.json` 快照展示与 Neo4j 多跳遍历 | Go API、Python KG API、Neo4j |
| [检索增强 AI 问答](05_Retrieval-Augmented_AI_Question_Answering/README.md) | 混合检索、流式问答、证据展示和灵感探索 | Python FastAPI、MySQL、Qdrant、LLM 配置 |
| [AI 辅助 Tc 估算](06_AI_Assisted_Tc_Estimation/README.md) | 根据 CONTCAR 与 PDOS 文件计算实验性 Tc 估算和解释特征 | pymatgen、NumPy、上传文件 |
| [研究者社区论坛](07_Researcher_Community_Forum/README.md) | 注册登录身份体系与研究者贡献排行 | Go API、JWT、Redis |

## 整体关系

```mermaid
flowchart LR
    U["用户与管理员"] --> FE["React/Vite 前端"]
    FE --> GO["Go Gin API"]
    GO --> DB["MySQL 主业务数据"]
    GO --> KGJSON["graph.json 知识图谱快照"]
    GO --> PY["Python FastAPI"]
    PY --> RAG["RAG 服务"]
    RAG --> QD["Qdrant 向量库"]
    RAG --> NEO["Neo4j 图数据库"]
    PY --> DB
    UP["01 上传解析管线"] --> DB
    DB --> RV["02 审核与维护"]
    RV --> Q["03 检索与发现"]
    RV --> PUB["发布向量索引"] --> QD
    DB --> V["07 社区贡献排行"]
    F["CONTCAR 与 PDOS"] --> T["06 Tc 估算"]
```

主业务数据库是上传、审核、检索、结构和统计能力的共同事实来源。Go 服务负责大部分用户可见 API、缓存和权限路由，未匹配请求转发到 Python 服务；Python 服务继续承担 RAG、结构 API、Tc 估算和 Neo4j 工具接口。Tc 估算只处理用户上传的计算文件，不会自动回写主业务数据。

## 当前边界

- Docker 部署入口使用 Nginx 前端、Go API、Python RAG、MySQL、Redis、Neo4j、Qdrant 七类服务；本地直接运行 Python FastAPI 时只包含 Python 注册的接口。
- `backend/main.py` 当前 include `tc_predict`、`structures`、`rag`、`upload_tasks`、`kg` 五类 Python 路由；canonical `/api/upload-tasks` 由 Go 未匹配路由转发到 Python。邮箱验证、用户中心、公开资料与管理员治理由 Go 直接承载；图表组合导入/导出/复制/搜索等前端调用仍需按实际部署链路继续核验。
- RAG 已从 Chroma 迁移到 Qdrant 封装，但部分兼容命名仍保留 `chroma` 字样。
- 晶体结构后端 API 已实现，前端在论文详情中按材料状态下的 `structures`（来自 `structure_models`）展示结构，完整结构审核工作台仍未从当前路由中确认。当前全库无结构模型记录，只验证过空态。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- “社区”当前是公共图表、图表组合、贡献榜单和论文详情抽屉，不包含帖子、评论或关注等论坛能力。
- Tc 估算由代码明确标记为实验页面，不构成模型科学有效性的保证。
- Neo4j 知识图谱同步不在上传链路中自动触发，需独立运行 `backend/ingest/sync_neo4j.py`；自动触发机制待核验。
- 账号身份与分级工作台变更已通过 Go 全量测试、Vitest、前端生产构建和 Alembic MySQL 离线迁移 SQL 生成；真实 SMTP、持久化 MySQL 与完整部署链路仍需在目标环境验收。

## 文档维护

本目录只记录当前代码、配置和测试文件能够支持的已落地事实。未来方案位于 `future-plan/`，不作为当前能力依据。无法从当前实现确认的内容在相应文档中标记为“待核验”。
