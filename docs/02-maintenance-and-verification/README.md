# 02 数据维护与审核当前规划

## 总体定位

负责权限、审核、维护、导入导出和数据可信治理。

## 当前状态

已部分落地。

## 文档导航

- [总体规划](README.md)
- [前端设计](frontend-design.md)
- [后端设计](backend-design.md)
- [API 设计](api-design.md)

## 核心建设内容

### 前端

- 后台页面集中展示待审核论文、结构、用户和批量维护任务。
- 逐条记录编辑、审核历史和批量操作 dry-run 区域右上角标注「有待建设」。
- 危险操作需要展示影响范围、确认信息和操作结果汇总。

### 后端

- 使用 `users.role`、`papers.review_status`、`superconductors_structures.review_status` 和 `show_in_chart` 控制状态。
- 规划增加审核日志，记录操作人、实体、动作、变更摘要和时间。
- 批量审核、批量图表可见性和导入导出应下沉为服务层。

### API

- `POST /api/admin/papers/{paper_id}/review`：论文审核。
- `POST /api/admin/papers/batch-review`：批量审核。
- `POST /api/admin/records/batch-chart-visibility`：批量控制图表显示。
- 未来新增审核历史查询和批量操作 dry-run 接口。

## 数据模型与数据流

维护数据流从用户提交进入待审核状态，经管理员审核后进入公开检索或图表展示。图表展示还需单独通过 `show_in_chart` 控制。

## 验收标准

- 不同角色权限隔离正确。
- 审核动作可追溯。
- 批量操作前能看到影响范围。
