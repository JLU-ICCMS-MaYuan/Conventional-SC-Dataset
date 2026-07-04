# 02 数据维护与审核：API 接口调整方案

## 规划接口

- `GET /api/admin/review-queue`：统一待审核队列。
- `GET /api/admin/audit-logs`：查询审核和维护日志。
- `POST /api/admin/batch/dry-run`：批量操作影响范围预览。
- `POST /api/admin/records/{record_id}/review`：逐条超导记录审核。

## 兼容接口

现有论文审核、用户管理、结构审核和批量图表显示控制接口继续保留。

## 验收标准

- 未授权用户访问返回 403。
- 批量操作接口返回成功、失败和跳过数量。
- 审核日志可按实体和操作人查询。
