# 实施计划：提交失败后任务状态回滚修复

**GitHub Issue**：[#55](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/55)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## 摘要

`backend/api/rag.py:1312-1317` 异常路径的 `update_state` 调用补上 `status="ready"`；在 `backend/tests/test_upload_workflow.py` 追加失败回滚用例。

## 技术上下文

- 与 #54 相同链路（FastAPI、Redis state、pytest）。无新依赖、无迁移。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| Overview | 失败语义明确、不假成功 | 回滚保留 submission_status=failed 事实 | 通过 |
| KISS | 最小改动 | 单行参数补齐 + 1 个测试 | 通过 |

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001~003 / US1 | rag.py 异常路径 + pytest 用例 | 模拟抛错后断言 state 字段与草稿保留 |

## 阶段与依赖

单阶段：改代码 → 写测试 → 回归 → 提交。
