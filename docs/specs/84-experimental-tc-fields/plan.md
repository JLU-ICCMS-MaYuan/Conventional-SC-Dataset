# 实施计划：实验 Tc 的条件字段与计算上下文一致性

**GitHub Issue**：[#84](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/84)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

将 `MaterialStatesEditor` 的 Tc 编辑改为先选方法、再派生字段；在 `backend/api/rag.py` 统一校验草稿和科学数据重写请求；在 `scientific_drafts.py` 按方法创建关联；以 MySQL 迁移替换现有上下文约束并清理历史错误关联。

## 技术上下文

- **语言与版本**：TypeScript/React、Python/FastAPI/SQLAlchemy、MySQL、Go 只读服务。
- **数据存储**：MySQL 的 `tc_results`、`calculation_contexts`、`experimental_contexts`；Redis 暂存草稿。
- **测试体系**：Vitest、pytest、隔离 MySQL 科学数据重写测试。
- **约束**：共享编辑器必须保持上传与管理端一致；迁移必须可在真实 MySQL 上验证。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| #84 FR-001 至 FR-003 | 三个入口一致 | 只修改共享 `MaterialStatesEditor.tsx` | 通过 |
| #84 FR-004 至 FR-007 | 不能绕过数据不变量 | API 校验、持久化校验、MySQL 约束和迁移 | 通过 |
| AGENTS.md | KISS、无永久兼容分支 | 一次性迁移，不改变读取路径 | 通过 |

## 源代码结构

```text
frontend/src/components/MaterialStatesEditor.tsx
backend/api/rag.py
backend/ingest/scientific_drafts.py
backend/models.py
backend/scripts/run_migrations.py
backend/tests/test_upload_workflow.py
backend/tests/test_scientific_drafts.py
backend/tests/test_scientific_draft_rewrite.py
tests/01_decentralized_uploading/
```

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 至 FR-003 | `MaterialStatesEditor.tsx` | Vitest 交互测试 |
| FR-004 | `_validate_draft` 与科学数据重写入口 | pytest API 契约测试 |
| FR-005 | `persist_scientific_draft` | pytest 持久化对象测试 |
| FR-006 至 FR-007 | 迁移与模型约束 | 隔离 MySQL 迁移/约束测试 |

## 阶段与依赖

1. 先定义和测试方法驱动的草稿转换与 API 拒绝规则。
2. 实现共享前端和后端持久化规则。
3. 执行并验证数据库迁移，再跑跨入口回归。
