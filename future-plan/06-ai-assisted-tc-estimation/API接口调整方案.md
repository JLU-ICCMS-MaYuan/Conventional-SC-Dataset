# 06 AI 辅助 Tc 估算：API 接口调整方案

## 规划接口

- `POST /api/tc-predict/`：保留当前即时预测接口。
- `POST /api/tc-prediction-jobs`：创建预测任务。
- `GET /api/tc-prediction-jobs`：查询用户预测历史。
- `POST /api/tc-prediction-jobs/{job_id}/submit-review`：提交审核。

## 验收标准

- 响应保留 predicted Tc 和解释字段。
- 历史接口只返回当前用户有权限查看的数据。
- 提交审核后状态可追踪。
