# Tc 历史与压力图表

## 功能说明

从已审核的公开超导记录生成发现年份与 Tc、压力与 Tc 的统计数据，并在社区页绘制可按个人偏好查看的交互图表。

## 当前行为

- Go API `/api/papers/stats/tc-pressure` 与 `/api/papers/stats/tc-year` 从 `superconductor_records` 读取 `show_in_chart = true` 且关联论文已审核通过的记录。
- 两个 API 接受白名单 `tc_field`：`experimental_tc`、`anisotropic_eliashberg_tc`、`isotropic_eliashberg_tc`、`allen_dynes_tc`、`mcmillan_tc`；默认使用 `experimental_tc`，非法字段返回 HTTP 400，字段为空的记录不回退。
- `/share` 页面在宽屏并排、窄屏单列显示 Tc-Pressure 与 Tc-Year；两张图可独立选择 Tc 字段，并分别呈现加载失败和空数据状态。
- 登录用户的两图字段偏好按 `user.id` 隔离保存在浏览器 `localStorage`，恢复默认只清除当前用户配置；匿名用户不持久化该偏好。
- Tc-Pressure 图绘制 Pickard 品质因子 `S = Tc / sqrt(39² + P²)` 的动态等值线，以及 77 K 和 300 K 参考线；实验点使用实心样式，计算点使用空心样式。
- 图表仍可按超导类型切换可见性，点击点后打开右侧论文详情抽屉。
- 图表组合 API 支持列表、详情、创建、更新、删除和公开状态切换；组合点可以引用 `key_properties` 或使用自定义点字段。
- 图表页面支持从本地浏览器存储合并未登录用户的本地图表组合。

## 工作流程

`/share` 页面按两张图各自的 `tc_field` 请求公共数据，并与当前图表组合合成散点；压力图在同一坐标系计算品质因子等值线。用户点击点后用 `paper_id` 请求 `/api/papers/:id` 并在抽屉中查看论文基础信息、关键物性和研究方法。

## 约束

- 未标记为 `show_in_chart`、没有 Approved 论文关联或所选 Tc 字段为空的记录不会进入公共图表数据。
- 个人偏好不写入 MySQL、Redis 或公共科研记录；清除站点数据、更换浏览器或设备后不会保留。
- 统计结果反映数据库当前收录范围，不代表完整学科历史。
- 图表组合编辑器前端调用了 `/api/chart-groups/search`、`/api/chart-groups/import`、`/api/chart-groups/:id/copy` 和 `/api/chart-groups/:id/export`，但当前 Go 路由未注册这些端点。
- Go 图表缓存按图表类型和 Tc 字段隔离；管理操作现有的 `chart:*` 刷新规则覆盖这些键。

## 代码与测试

- `goserver/handlers/stats.go`
- `goserver/handlers/chart_groups.go`
- `frontend/src/pages/share.tsx`
- `frontend/src/components/ChartScatter.tsx`
- `frontend/src/components/ChartGroupEditor.tsx`
- `frontend/src/lib/chartPreferences.ts`
- `goserver/handlers/stats_test.go`
- `tests/07_researcher_community_forum/`

## 相关变更记录

- [Feature #30：社区 Tc 双图个人配置与品质因子](../../specs/30-community-tc-chart-preferences/spec.md)

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约不完整。
