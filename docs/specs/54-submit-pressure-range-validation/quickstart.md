# 快速验证：提交审核压强区间校验与草稿保存语义修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 前置条件

- dev MySQL 已执行 `alembic upgrade head`（含 `20260826_0016`）。
- **dev 栈镜像已重建并重启**（compose 不挂源码，旧镜像不含本修复）：`cd docker && docker compose build python frontend && docker compose up -d`。

## 自动化验证（已完成于 commit 16298c9）

```bash
DEBUG=false python -m pytest backend/tests/test_upload_workflow.py -q   # 含 5 个新用例
cd frontend && npm run test:upload-ui                                    # 6 文件 45 用例
```

## 端到端场景

### 场景 1：原失败任务重新提交（US1，验收 SC-002）

1. 打开任务 `6b5bf07cac944ed6acbaa6422bdbeee7`（LaHn YHn，草稿仍在 Redis，含 LaH10 min=200/max=NULL）。
2. 点击「提交审核」→ 预期提交成功，任务进入 pending；`papers` 表出现 DOI 10.1073/pnas.1704505114。
3. 数据库抽查该材料状态：`pressure_min_gpa=200`、`pressure_max_gpa IS NULL` 保留。

### 场景 2：倒置区间明确 400（US1）

1. 任意草稿将某材料状态压强改为 min>max（可由后端直接构造草稿），提交 → 400。
2. 页面横幅显示「提交失败：第 N 个材料状态的压强区间 min 不能大于 max（invalid_pressure_range）」，不再 500。

### 场景 3：半成品自动保存不丢（US2）

1. 校对页添加一条 Tc 但不填数值，等待 5 秒 → 显示已保存（PUT 200）。
2. 刷新页面 → 该 Tc 行仍在。
3. 点击「提交审核」→ 400，横幅指出第 N 个材料状态第 M 条 Tc 缺少数值。

### 场景 4：错误原因可见（US3）

1. 触发任意保存失败 → 横幅为「保存失败：{后端 message}（{code}）」。
2. 触发无 detail 的 500 → 回退「提交审核失败」通用文案。
