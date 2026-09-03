# 实施计划：上传解析规范英文值与本地化 AI 建议

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

在 `backend/ingest/` 中抽取一套规范生成字段语言策略，改写分段与汇总 prompt，并在分段清单、草稿保存、提交及正式持久化前调用它。任务创建时固化界面语言；Worker 将英文 canonical draft 与按该快照本地化的 `ai_original` 建议副本分开。前端不翻译数据，只分别展示这两份已生成的值。

## 技术上下文

- **语言与版本**：Python/FastAPI/Redis/MySQL，TypeScript/React。
- **数据存储**：分段清单文件、Redis 任务草稿、MySQL `papers` 与科学实体。
- **测试体系**：pytest 上传流程测试、Vitest 上传工作区测试、隔离 MySQL 提交测试。
- **约束**：#74 单语英文 MySQL 存储；原文证据不可翻译；不新增正式 schema 列；`ai_original` 仅存在于 Redis 审核草稿与任务快照。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| #85 FR-001、FR-002 | 不同阶段不能漂移 | 共享字段策略模块 | 通过 |
| #85 FR-003、FR-004 | 不能静默持久化 | 所有写边界调用同一验证器 | 通过 |
| #85 FR-006 | 原文保持可核对 | 明确事实字段排除表 | 通过 |
| #74 | 不做双语列 | 只校验值，无迁移新列 | 通过 |

## 源代码结构

```text
backend/ingest/upload_jobs.py
backend/ingest/extractor.py
backend/ingest/upload_tasks.py
backend/api/rag.py
backend/ingest/scientific_drafts.py
backend/scripts/
backend/tests/test_upload_workflow.py
tests/01_decentralized_uploading/upload-task-workspace.test.tsx
frontend/src/components/UploadParsingDetail.tsx
```

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 至 FR-002 | prompt 与语言策略模块 | pytest prompt/规范化测试 |
| FR-003 至 FR-004 | 分段、草稿、提交写入边界 | pytest 失败且无写入测试 |
| FR-005 | `/parsing` 与 `UploadParsingDetail` | Vitest 预览测试 |
| FR-006 | 策略排除字段 | 中文原文样本测试 |
| FR-007 | 一次性修复命令 | 隔离 MySQL 审计测试 |
| FR-008 至 FR-009 | 语言快照、建议副本与 Pb 定向修复 | pytest + 审核草稿核验 |

## 阶段与依赖

1. 定义字段分类与失败语义，先写跨边界测试。
2. 统一 LLM prompt、候选规范化、Redis 草稿与提交验证。
3. 受控修复正式 MySQL 数据，完成端到端回归并删除一次性脚本。
