# 快速验证：提交失败后任务状态回滚修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 自动化验证

```bash
DEBUG=false python -m pytest backend/tests/test_upload_workflow.py -q   # 含失败回滚用例
```

## 端到端场景

1. 打开任务 `6b5bf07cac944ed6acbaa6422bdbeee7`（状态已运维修复为 ready），确认表单可编辑、LaH10 等数据完整。
2. 点击「提交审核」→ 预期成功（#54 修复已生效），papers 表出现该论文。
3. （可选）人为断开 MySQL 后提交另一任务 → 返回错误后任务回到 ready 可编辑，恢复 MySQL 后重提成功。
