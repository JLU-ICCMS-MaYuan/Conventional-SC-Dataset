# 实施计划：论文级 Material family 多选分类

**GitHub Issue**：[#79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)

## 摘要

新增论文版本到 Material family 的多对多关联表，将草稿和 API 契约统一为论文级 `material_families[]`。上传与管理员编辑页在 Paper type 附近使用现有分类自动完成组件的多选模式；材料状态编辑器删除 family 控件但保留 `structure_families[]`。迁移先聚合旧状态关联，再删除状态外键。Python 负责草稿校验与科学数据持久化，Go 负责批准事务和详情序列化，两端共享相同所有权。

## 技术上下文

- **语言与版本**：Python 3、Go（仓库当前 toolchain）、TypeScript 5.6、React 19
- **主要依赖**：FastAPI、SQLAlchemy、Alembic、GORM、MUI、Vitest、Testing Library
- **数据存储**：MySQL；Redis 保存未提交草稿；审核快照为 JSON
- **测试体系**：pytest、Go test、Vitest、TypeScript/Vite production build
- **目标平台**：现有 Docker Compose Web/API/Go 服务
- **性能目标**：论文详情仅增加一次预加载；family 列表去重，无逐状态额外查询
- **约束**：批准与科学数据重写保持单事务；已有审核状态不得被迁移改变；README 禁止编辑
- **规模范围**：单篇论文通常少量 family；迁移覆盖全部现有论文和材料状态

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | 简体中文文档、合理验证、仅提交本任务文件 | 全部 Spec/Overview 使用简体中文并按路径暂存 | 通过 |
| Overview / #51 | 目录项只在批准事务正式创建 | 草稿保留 pending，Go 批准统一解析并写关联 | 通过 |
| #76 / #78 | 科学数据整体替换、升版和失败回滚 | 已有正式 family 关联随版本外键级联保留，最终选择仍由批准事务替换 | 通过 |
| Spec FR-006 | More type labels 不变 | 保留状态结构家族 schema、关联表和共享控件 | 通过 |
| Spec FR-010 | 历史多 family 无损迁移 | `SELECT DISTINCT` 汇总后再删除旧外键 | 通过 |

## Feature 文档结构

```text
docs/specs/79-paper-material-families/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── paper-material-families-api.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
alembic/versions/                       # 多对多表与数据迁移
backend/models.py                      # Python ORM
backend/api/rag.py                     # 草稿校验、分类解析、科学数据接口
backend/ingest/{upload_jobs,scientific_drafts}.py
goserver/models/models.go              # Go ORM
goserver/handlers/{classifications,admin,papers,stats}.go
frontend/src/lib/paperProcessing.ts
frontend/src/components/{UploadTaskEditor,MaterialStatesEditor,PaperEditView}.tsx
frontend/src/pages/AdminPaperEditPage.tsx
tests/                                 # Python、Go、Vitest 契约与回归
docs/overview/                         # 落地后的当前事实
```

**结构选择**：复用现有 Material family 目录和 `ClassificationAutocomplete`，只改变归属与集合基数；不增加第二套分类组件或服务。论文—family 关联独立成表，避免在 `papers` JSON 中复制目录数据。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001–FR-004 / US1 | `UploadTaskEditor`、草稿校验 | Vitest + pytest 草稿/提交测试 |
| FR-005–FR-008 / US1 | 共享类型、`MaterialStatesEditor`、管理员编辑页 | 前端分类与管理编辑测试 |
| FR-009–FR-011 / US3 | Alembic + Python/Go ORM | schema 与迁移测试 |
| FR-012 / US2 | Go 批准分类事务 | Go 审核 API 测试 |
| FR-013 | 上传汇总归一化 | Python 上传任务测试 |
| FR-014 / US2 | Go 详情序列化 + `PaperEditView` | Go/前端详情测试 |
| FR-015 | Go 社区统计查询 | Go/契约测试验证筛选命中与总计不重复 |

## 阶段与依赖

1. 建立迁移、ORM 和共享草稿数据结构。
2. 修改 Python 提取、校验和落库主路径。
3. 修改 Go 审核、详情、统计消费路径。
4. 修改上传和管理员前端。
5. 执行迁移、后端、Go、前端测试和构建。
6. 同步 Overview、Issue Documentation Impact 并关闭 Issue。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 版本化多对多关联表 | 一篇论文多个目录项，且分类必须随内容 revision 一致 | `papers` JSON 会失去外键、目录一致性和查询能力 |
| Python 与 Go 双端同步 | 上传持久化由 Python 执行，批准和详情由 Go 执行 | 只改一端会造成保存与发布契约分裂 |
| 条件式 downgrade | 旧模型不能表达一篇论文多个 family | 任意挑一个回填会静默损坏科研分类 |
