# 实施计划：论文上传科学数据结构化

**GitHub Issue**：[#46](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/46)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

升级分段与汇总提示词、草稿 DTO 和编辑页；在材料状态上保存论文报告空间群；新增确定性的
科学草稿持久化服务，把压力、结构、上下文、Tc、普通物性和 Evidence 写入 #32 目标实体。

## 技术上下文

- **语言与版本**：Python 3.12、TypeScript/React 18、Go 1.25、MySQL 8.4
- **主要依赖**：FastAPI、SQLAlchemy 2、Alembic、MUI、Vitest、pytest、GORM
- **数据存储**：Redis 临时草稿、MySQL 正式实体、文件系统论文与审核快照
- **测试体系**：pytest、Vitest/Testing Library、Go testing、隔离 MySQL Alembic
- **目标平台**：Docker Compose
- **性能目标**：单篇论文事务内线性处理草稿状态与结果，不新增外部网络请求
- **约束**：论文 revision 单一审核边界；原文优先；不迁移历史数据；不伪造结构
- **规模范围**：单次一篇论文、数十材料状态/结果

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| #32 | 状态、上下文、Tc、普通物性分表 | 新草稿直接映射目标实体 | 通过 |
| #33 | 全部内容同 paper revision | 单事务复制当前 revision | 通过 |
| 用户确认 | 空间群符号与群号独立 | reported 字段 + 应用校验 | 通过 |
| 科学真实性 | 无结构文本不得伪造结构 | reported 字段与 StructureModel 分开 | 通过 |
| Diagnose | 实际故障回归 | Li2MgH16 夹具覆盖 GET/PUT/提交 | 通过 |

## Feature 文档结构

```text
docs/specs/46-upload-scientific-data-pipeline/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/upload-draft-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
alembic/versions/20260824_0010_add_reported_space_group.py
backend/models.py
backend/ingest/upload_jobs.py
backend/ingest/scientific_drafts.py
backend/api/rag.py
frontend/src/lib/paperProcessing.ts
frontend/src/components/UploadTaskEditor.tsx
goserver/models/models.go
backend/tests/test_upload_jobs.py
tests/01_decentralized_uploading/
tests/02_maintenance_and_verification/
```

**结构选择**：提取归一化留在上传任务模块；实体图验证、指纹和持久化集中到
`scientific_drafts.py`；API 只编排事务、文件、Chunk 和 Evidence。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001–FR-004 / US1–US2 | 新草稿 normalize + DTO + 编辑器 | Python 单测、前端行为测试 |
| FR-005–FR-009 / US3 | scientific draft writer | 提交事务集成、隔离 MySQL |
| FR-010–FR-012 | UploadTaskEditor、缓存版本 | Vitest、缓存回归 |
| FR-013 | MaterialState reported fields | Alembic/双 ORM 测试 |
| FR-014 | IntegrityError 分类 | API 回归测试 |

## 阶段与依赖

1. 先建立失败测试与 reported space group Schema。
2. 实现草稿契约、归一化和验证。
3. 实现前端材料状态编辑。
4. 实现新模型事务持久化与 Evidence 连接。
5. 更新 Overview，执行全量相关测试和 quickstart。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 新草稿 DTO | 旧扁平行无法表达状态/上下文 | 给旧卡加字段仍会重复条件 |
| reported 空间群字段 | 原文可能无结构坐标 | 空结构记录会伪造科学事实 |
| 新持久化服务 | 七类实体有依赖和 revision 约束 | 在 API 中继续堆构造器不可测试 |
