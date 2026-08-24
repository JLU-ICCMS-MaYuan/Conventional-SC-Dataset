# 实施计划：删除 phase_label 并明确空间群与可扩展分类边界

**GitHub Issue**：[Issue #50](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/50)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

在新上传主链路中移除 `phase_label`，同步清理前端类型、AI prompt、归一化、Python/Go 模型、Alembic Schema 和测试。历史草稿在有界兼容窗口内忽略该字段，原始证据不做模糊迁移。空间群继续作为结构事实，未来分类词典不在本 Feature 实施。

## 技术上下文

- **语言与版本**：Python、TypeScript/React、Go；版本以仓库 lockfile 和运行配置为准。
- **主要依赖**：FastAPI/SQLAlchemy/Alembic、React/MUI、GORM、Vitest、Pytest。
- **数据存储**：Redis 临时上传草稿、MySQL fresh 目标科学模型、文件 Evidence/JSON 快照。
- **测试体系**：`tests/01_decentralized_uploading/`、`backend/tests/`、`tests/02_maintenance_and_verification/`、Go schema tests、Vitest。
- **目标平台**：Docker Compose 下的 Python API、Go API、React 前端和 MySQL。
- **约束**：两套 ORM 必须一致；fresh Schema guard 不得静默改动现有运行库；不得模糊迁移旧物相文本。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| AGENTS.md | docs 使用简体中文、保留并发修改 | Spec 中文；只修改本 Feature 文件和明确目标文件 | 通过 |
| Issue #50 | 完整删除结构化 `phase_label` | 前端、后端、迁移、测试和契约同步清理 | 通过 |
| Overview | 空间群为 reported 事实，结构文本单独建模 | 不用分类或 phase 字段替代空间群 | 通过 |
| 兼容边界 | 历史草稿可恢复且新契约不生成旧字段 | 读取忽略、写出剔除，并有退出条件 | 通过 |

## Feature 文档结构

```text
docs/specs/50-remove-phase-label/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/upload-draft.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

- `frontend/src/components/UploadTaskEditor.tsx`：编辑器字段和保存路径。
- `frontend/src/lib/paperProcessing.ts`：草稿类型和前端归一化。
- `backend/ingest/upload_jobs.py`：AI 输出模板、新旧草稿归一化和兼容边界。
- `backend/api/rag.py`：保存/提交校验。
- `backend/ingest/scientific_drafts.py`：科学实体持久化。
- `backend/models.py`、`goserver/models/models.go`：双 ORM 模型。
- `alembic/versions/`：fresh Schema 删除迁移。
- 相关测试和 `docs/overview/`：行为与稳定事实验证。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/SC-001 | 新草稿契约、编辑器、归一化、持久化 | 前端/API/持久化回归 |
| FR-002/SC-001 | SQLAlchemy、GORM、Alembic | Schema 测试与迁移检查 |
| FR-003/FR-005/SC-003 | reported space group 和状态分组 | 多空间群测试 |
| FR-004 | `state_kind` | 理论/实验回归 |
| FR-006/FR-007/SC-004 | 兼容读取与原始证据保留 | 旧草稿测试 |
| FR-008/SC-005 | 分类边界文档 | Spec/Overview 检查 |

## 阶段与依赖

1. 先补契约、Schema、旧草稿和双空间群失败测试。
2. 清理生产路径和模型字段。
3. 加入数据库迁移与文档同步。
4. 运行前端、后端、Go Schema 和 fresh 数据库验证。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|---|---|---|
| 双 ORM 与 fresh migration 同步 | Python 和 Go 同时暴露目标实体，Schema 是共享契约 | 只删 UI 会留下错误可写字段 |
| 有界旧草稿兼容 | 旧 Redis/文件草稿可能仍含字段 | 立即拒绝会中断正在处理的上传任务 |
| 多空间群不静默合并 | 删除 phase 后仍需保留结构差异 | 只按材料+压力合并会丢结构状态 |
