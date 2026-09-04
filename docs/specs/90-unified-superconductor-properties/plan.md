# 实施计划：统一材料状态的超导物性记录

**GitHub Issue**：[#90](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/90)

**日期**：2026-09-04

**Spec**：[spec.md](spec.md)

## 摘要

建立统一 `SuperconductorPropertyRecord` 契约，将 Tc、λ、ωlog、μ* 和其余物性作为材料状态
下的平级记录。新增共享规范化与持久化映射：Tc 继续使用专用表，非 Tc 记录使用通用物性
表，计算/实验 Context 只保存方法和条件并可被多条记录共享。上传、管理、详情和展示一次性
切换到统一契约，旧结构只在边界兼容。通过 Alembic 将 Context 中已有 λ、ωlog、μ* 回填为
通用物性行，并为通用物性增加实验 Context 关系。

## 技术上下文

- **语言与版本**：Python 3、Go 1.25、TypeScript 5.6、React 19。
- **主要依赖**：FastAPI、SQLAlchemy、Alembic、GORM、Gin、Vite 5、Vitest 2。
- **数据存储**：MySQL 保存权威科学实体；Redis 保存上传任务草稿；Qdrant/Neo4j 不属于本次权威物性存储改造。
- **测试体系**：pytest、Go test、Vitest、TypeScript/前端生产构建、隔离 MySQL Alembic upgrade/downgrade。
- **目标平台**：本地开发与 Docker 部署使用的 Linux/WSL + MySQL 环境。
- **性能目标**：单篇详情用批量预加载完成映射，不因每条物性引入 N+1 查询；Tc 图表继续走专用 SQL。
- **约束**：保留 revision/Evidence 血缘、#84 Tc Context 互斥、代表 Tc 唯一、共享编辑器和升版重审事务。
- **规模范围**：单篇论文若干材料状态、每状态通常数十条物性；历史运行库存在少量条件化科学数据，需要可核对迁移。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | KISS/YAGNI，不建立无需求的分类树 | 一个平级记录契约；只保留 Tc 已存在的专用校验 | 通过 |
| AGENTS.md | DRY，共享上传与管理编辑能力 | 改造现有 `MaterialStatesEditor` 和统一后端规范化入口 | 通过 |
| #33 / Overview | 所有科学实体与 Evidence 同 revision | Context、Structure、记录和 Evidence 在映射前统一校验 | 通过 |
| #84 | `tc_method` 是理论/实验规则唯一权威 | Tc 映射保留现有应用层与数据库约束 | 通过 |
| #57/#59/#65 | 详情完整，编辑和只读展示一致 | Go 统一映射 + 前端直接消费，不再三来源拼装 | 通过 |
| #72 | Tc 图表数据不可回退 | 保留 `tc_results` 专用查询并做投影一致性测试 | 通过 |
| Issue #90 | 物性平级且保留 Context 关联 | `SuperconductorProperties[]` + 共享 `context_key` | 通过 |
| Overview 维护规则 | 未实现设计不得写入当前事实 | 实施前只新增 Spec；Overview 任务位于最终阶段 | 通过 |

## Feature 文档结构

```text
docs/specs/90-unified-superconductor-properties/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── property-record.md
│   ├── persistence-mapping.md
│   └── database-invariants.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
alembic/versions/
└── 20260904_0001_unified_superconductor_properties.py

backend/
├── models.py
├── api/rag.py
├── ingest/
│   ├── upload_contracts.py
│   ├── upload_jobs.py
│   ├── scientific_drafts.py
│   └── superconductor_properties.py        # 新增：统一记录规范化与兼容转换
├── services/scientific_draft_rewrite.py
└── tests/
    ├── test_superconductor_properties.py   # 新增
    ├── test_upload_jobs.py
    ├── test_scientific_drafts.py
    └── test_scientific_draft_rewrite.py

goserver/
├── models/models.go
└── handlers/
    ├── superconductor_properties.go        # 新增：统一详情投影
    ├── papers.go
    ├── paper_detail_test.go
    ├── stats.go
    ├── stats_test.go
    ├── paper_deletion.go
    └── paper_deletion_test.go

frontend/src/
├── lib/
│   ├── paperProcessing.ts
│   ├── superconductorProperties.ts         # 新增：统一类型与兼容转换
│   └── paperDetailView.ts
├── components/MaterialStatesEditor.tsx
└── pages/
    ├── AdminPaperEditPage.tsx
    ├── SearchPage.tsx
    └── share.tsx

tests/
├── 01_decentralized_uploading/
│   ├── material-states-editor.test.tsx
│   ├── upload-task-editor-classification.test.tsx
│   └── paper-detail-form-parity.test.tsx
├── 02_identity_governance/
│   ├── admin-scientific-data-edit.test.tsx
│   └── admin-scientific-data-view.test.tsx
├── 02_maintenance_and_verification/
│   └── test_issue90_property_migration.py  # 新增
└── 03_data_search_and_database_discovery/
    └── paper-detail-view-sources.test.tsx
```

**结构选择**：Python 负责草稿规范化和权威写入，Go 负责公开详情和专用查询，前端共享一个
类型/兼容模块和一个编辑组件。三层都以 `contracts/property-record.md` 为准，各自只实现一次
映射；不引入新的跨服务协议框架，也不复制第二套材料状态编辑器。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001–FR-005 / US1 | 统一 TypeScript/Python 记录、平级编辑器、参数迁移 | 规范化测试、编辑器 Vitest、MySQL 行数对账 |
| FR-006–FR-011 / US2 | 嵌入 Context、`context_key` 去重和一致性校验 | 两组 μ*—Tc 往返与冲突测试 |
| FR-012–FR-016 / US3 | Tc 专用映射、#84 约束、Evidence 连接 | Python/MySQL 非法组合与代表唯一测试 |
| FR-017–FR-20 / US1/US4 | 原文/规范值保留、共享编辑器、Go 统一详情 | 上传—管理—详情契约对账 |
| FR-021–FR-025 / US4 | 旧输入适配、schema version、Alembic 回填 | 旧 fixture 转换、upgrade/downgrade、迁移报告 |
| FR-026–FR-030 / US4 | 专用 Tc 查询回归、删除/审核、Overview 回写 | Go/Python/Vitest 全量专项和 quickstart |
| FR-031 / US1–US3 | 结果级方法/判据与共享 Context 职责分离 | 迁移、统一记录和 Tc/实验回归测试 |

## 阶段与依赖

1. 固化统一契约和失败测试，建立共享测试 fixture。
2. 增加 Schema 关系、参数和实验判据回填、旧 Context 结果列移除迁移，以及 Python 规范化/持久化基础能力。
3. 切换上传草稿和共享编辑器，实现平级新增、编辑和 Context 关联。
4. 切换管理员科学数据读取/重写和 Go 详情统一投影。
5. 删除内部旧契约依赖，保留单向边界兼容并回归搜索、图表、审核和删除。
6. 完成隔离 MySQL、前后端测试、quickstart 和 Overview 回写。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 统一映射层 | 领域集合与 Tc/通用物性专用表不是一一对应 | 让每个调用方分别拼装会继续造成契约漂移 |
| `context_key` | 平级记录仍需表达同一次计算/实验 | 完全扁平且无关联会丢失 μ*—Tc 对应关系 |
| Alembic 参数回填 | λ、ωlog、μ* 必须成为真实记录和 Evidence 目标 | 只做前端虚拟行不能满足写入和证据要求 |
| 边界兼容 | Redis 旧草稿和当前详情结构已经存在 | 直接拒绝旧数据会让进行中的上传任务不可恢复 |
