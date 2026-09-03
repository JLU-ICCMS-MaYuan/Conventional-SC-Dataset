# 实施计划：上传解析英文规范值与无建议审核表单

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

分段和汇总只生成、校验并保存英文 canonical draft。前端审核表单直接使用这份值，证据组件只展示原文 `quote`。删除任务创建、Redis、Worker、草稿 API、审核快照及前端类型中的建议副本字段；读取旧草稿时忽略它们。

## 技术上下文

- **语言与版本**：Python/FastAPI/Redis/MySQL，TypeScript/React。
- **数据存储**：分段清单、Redis 任务草稿、`review_artifacts` 快照、MySQL `papers` 与科学实体。
- **约束**：英文 canonical 值是唯一生成值；原文证据不可翻译；不新增正式 schema 列；不再发起建议本地化模型调用。

## 设计与验证映射

| 来源 | 设计组件 | 验证方式 |
| --- | --- | --- |
| FR-001 至 FR-003 | 既有 prompt 与共享英文验证器 | pytest 分段、草稿与提交测试 |
| FR-004 | `EvidenceNotes`、`UploadTaskEditor`、`MaterialStatesEditor` | Vitest 不渲染建议测试 |
| FR-005 | `upload_tasks.py`、`upload_jobs.py`、`rag.py` | 状态与 `result.json` 字段断言 |
| FR-006 | 字段分类表 | 中文原文证据样本 |
| FR-007 | 定向 Redis/产物清理 | Pb 活动任务读回核验 |

## 执行顺序

1. 删除建议副本生成、传输、类型和界面展示路径。
2. 将旧字段限定为读取兼容输入，并在新保存/提交快照中剔除。
3. 更新测试、Spec、Issue 与 Overview，清理 Pb 活动任务。
4. 运行后端测试、前端 Vitest 和生产构建。
