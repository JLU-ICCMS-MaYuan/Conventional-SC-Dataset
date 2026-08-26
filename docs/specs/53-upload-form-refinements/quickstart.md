# 快速验证：校对表单迭代

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 前置条件

- 已执行 `alembic upgrade head`（含 `20260826_0015`）；服务已重启加载新代码。

## 自动化验证

```bash
DEBUG=false python -m pytest backend/tests/test_space_groups.py backend/tests/test_upload_jobs.py backend/tests/test_scientific_drafts.py -q
cd frontend && npm run test:upload-ui && npx tsc --noEmit
```

## 端到端场景

### 场景 1：AI 建议单行（US1）

1. 打开关键词/研究方法 AI 建议较长的校对任务 → 建议块仅一行、末尾截断，出现展开按钮。
2. 点击展开 → 全文显示；再点击收起 → 恢复单行；短建议无按钮。

### 场景 2：研究方法推导（US2）

1. 草稿研究方法含 `McMillan equation`，材料状态超导类型未知、存在 unknown 方法的理论 Tc → 保存/刷新后：类型为常规超导体，Tc 方法为 McMillan。
2. 研究方法同时含 `McMillan equation` 与 `numerical solution of the Eliashberg equations` → 类型照判常规，Tc 方法保持 unknown 待人工。

### 场景 3：晶系联动（US3）

1. 晶系选「四方」→ 空间群符号下拉仅 75–142 号。
2. 符号选 `I4/mmm` → 群号 139、晶系自动四方。
3. 群号输 227 → 符号自动 `Fd-3m`、晶系自动立方。
4. 符号选 `P6_3/mmc` → 群号 194、晶系六方。

### 场景 4：结构家族（US4）

1. 页面无「主结构家族」字段；标签显示「更多类型标签（可以填写不止一个类型）」。
2. 选两个类型标签提交 → 审核页两个标签均在。

### 场景 5：超导类型（US5）

1. 下拉仅「常规超导体（BCS超导体）」「非常规超导体」两项；未选时显示占位。
