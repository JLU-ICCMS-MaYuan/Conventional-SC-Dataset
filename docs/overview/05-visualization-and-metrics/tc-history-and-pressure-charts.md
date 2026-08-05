# Tc 历史与压力图表

## 功能说明

从公开超导记录生成发现年份与 Tc、压力与 Tc 的统计数据，并在首页绘制交互图表。

## 当前行为

- Go API `/api/papers/stats/tc-pressure` 从 `key_properties` 选取 `name = critical_temperature`、`value_max` 非空、`pressure_gpa` 非空且 `is_primary = true` 的记录，返回 Pressure-Tc 散点数据。
- Go API `/api/papers/stats/tc-year` 从 `key_properties` JOIN `papers`，选取有年份且 `is_primary = true` 的临界温度记录，返回 Year-Tc 散点数据。
- `/share` 页面使用 Recharts 绘制 Tc-Pressure 与 Tc-Year 两张图，可按超导类型切换可见性，点击点后打开右侧论文详情抽屉。
- 图表组合 API 支持列表、详情、创建、更新、删除和公开状态切换；组合点可以引用 `key_properties` 或使用自定义点字段。
- 图表页面支持从本地浏览器存储合并未登录用户的本地图表组合。

## 工作流程

`/share` 页面请求公共图表数据和图表组合列表；前端先构造半透明背景点，再按所选组合叠加重点点；用户点击点后用 `paper_id` 请求 `/api/papers/:id` 并在抽屉中查看论文基础信息、关键物性和研究方法。

## 约束

- 未标记为 `is_primary` 的关键物性不会进入公共图表数据。
- 统计结果反映数据库当前收录范围，不代表完整学科历史。
- 图表组合编辑器前端调用了 `/api/chart-groups/search`、`/api/chart-groups/import`、`/api/chart-groups/:id/copy` 和 `/api/chart-groups/:id/export`，但当前 Go 路由未注册这些端点。
- Go 图表缓存使用固定 key，数据变更后的缓存刷新只在部分管理操作中出现，完整失效策略需核验。

## 代码与测试

- `goserver/handlers/stats.go`
- `goserver/handlers/chart_groups.go`
- `frontend/src/pages/share.tsx`
- `frontend/src/components/ChartScatter.tsx`
- `frontend/src/components/ChartGroupEditor.tsx`
- `tests/07_researcher_community_forum/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约不完整。
