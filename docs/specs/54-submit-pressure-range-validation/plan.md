# 实施计划：提交审核压强区间校验与草稿保存语义修复

**GitHub Issue**：[#54](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/54)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

迁移 0016 放宽 `ck_material_states_pressure_range` 允许单臂区间（方案 A）；`_validate_draft` 增加双臂 min>max 的 400 校验并以 `partial` 参数分离 PUT（仅结构）与 submit（全集）两级校验；前端失败横幅展示后端 `detail.message`。

## 技术上下文

- 与 #52/#53 相同（Python 3.12 FastAPI/SQLAlchemy 2、React+MUI、MySQL 8.4、pytest/vitest）。
- 无新依赖；迁移沿用裸 op 模式。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| #51/#52 提交链路 | submit 严格校验全集不回退 | partial 仅作用于 PUT 路径，submit 两处调用保持默认 | 通过 |
| Overview pdf-ingestion | 失败语义明确、不假成功 | 400 带 code/message，前端展示 | 通过 |
| AGENTS.md | 最小改动 | 单参数分离校验，不拆函数不复制规则 | 通过 |

## 源代码结构

```text
alembic/versions/20260826_0016_relax_pressure_range.py  # 新增
backend/models.py                                       # 约束文本同步
backend/api/rag.py                                      # 压强校验 + partial 参数 + PUT/submit 调用点
backend/tests/test_upload_workflow.py                   # 5 个新用例
frontend/src/components/UploadTaskEditor.tsx            # backendErrorReason/failureMessage + 两处 catch
tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx          # 2 个新用例
tests/01_decentralized_uploading/upload-task-editor-classification.test.tsx  # flake 修复（testTimeout）
```

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001 / US1 | 迁移 0016 + models 约束 | dev MySQL upgrade/downgrade + 临时表插入实测 |
| FR-002 / US1 | `_validate_draft` 压强校验（rag.py:283-287） | pytest（单臂过、倒置 400） |
| FR-003 / US2 | `_validate_draft(partial=...)`（rag.py:220-228、:799） | pytest（PUT 半成品 200、submit 400） |
| FR-004 / US3 | `backendErrorReason`/`failureMessage`（UploadTaskEditor.tsx:118-134） | vitest（2 用例） |

## 阶段与依赖

1. 后端：迁移 → 校验与分离 → 测试（单 agent 串行完成）。
2. 前端：错误展示 + 测试（与后端并行）。
3. 回归、提交、Issue 回写；镜像重建后 quickstart 验收。
