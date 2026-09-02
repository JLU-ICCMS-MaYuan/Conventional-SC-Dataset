# Tc 历史与压力图表

## 功能说明

从已审核的公开超导数据生成发现年份与 Tc、压力与 Tc 的统计数据，并在社区页绘制可按个人偏好查看的交互图表。

## 当前行为

- Go API `/api/papers/stats/tc-pressure` 与 `/api/papers/stats/tc-year` 查条件化模型：`tc_results` JOIN `material_states` JOIN `superconductors` JOIN `papers`，再用论文 revision 相关子查询读取 `paper_material_families`。只公开 `review_status = 'approved'` 且 `tc_results.paper_revision = papers.content_revision` 的数据，即审核通过的那一版内容；主查询不直接 JOIN 多标签表，因此一篇论文关联多个 family 不会把未筛选数据点重复展开。
- 两个 API 接受白名单 `tc_field`：`experimental_tc`、`anisotropic_eliashberg_tc`、`isotropic_eliashberg_tc`、`allen_dynes_tc`、`mcmillan_tc`；默认使用 `experimental_tc`，非法字段返回 HTTP 400。该字段现在映射到 `tc_results.tc_method` 的行过滤值（如 `experimental_tc` → `experimental`），而非旧模型的列名。
- Tc 取值为 `COALESCE(tc_value_k, (tc_min_k + tc_max_k) / 2)`，只登记区间的条目按中点上图。
- 实验/计算的判定来自 `tc_results.result_kind`；`experimental` 为实验，其余（含未知取值）按计算处理。
- 查询失败返回 HTTP 503 且不写缓存，不再返回空数组——静默空结果会把 schema 漂移伪装成「暂无数据」。
- 分类维度是论文级材料家族标签（`material_families` 目录），由 `/api/classification-catalogs` 动态提供，含用户自建家族；API 为每个数据点返回所属论文的 `family_ids[]`，没有论文级 family 时归入 ID 0 的「其他」。
- `/share` 页面在宽屏并排、窄屏单列显示 Tc-Pressure 与 Tc-Year；两张图可独立选择 Tc 字段与材料家族多选组合，并分别呈现加载失败状态。
- 两张图恒对齐：控件区与图例区高度固定，材料家族选择框宽度固定（190 px），因此选中项数量与文本长度不影响图表纵向位置。选中项名称过长时折叠为「已选 N 项」，全选显示「全部」，一个不选显示「未选择」。
- 每张图有独立的材料家族多选下拉，默认全选，与图例点击双向同步；多个家族可组合显示在同一张图里。筛选任一 family 时，命中论文的全部材料结果都纳入，单个数据点即使同时命中多个已选 family 也只绘制一次。社区页不再提供图表组合入口，材料家族多选已承担论文标签筛选职责。
- 登录用户的字段与家族偏好按 `user.id` 隔离保存在浏览器 `localStorage`（键名 `scwiki_chart_preferences:v2:<id>`），恢复默认只清除当前用户配置；匿名用户不持久化。家族选择存 `null` 表示「全部」，因此后续新增的家族自动可见。
- 没有数据点时仍渲染坐标系与背景分区，只在图内提示无数据点。压力图横轴固定 0–400 GPa，年份图横轴固定 1900–次年；纵轴由两图共用，固定 0–500 K，以便并排直接比对 Tc 高度。
- Tc-Pressure 图绘制 Pickard 品质因子 `S = Tc / sqrt(39² + P²)` 的动态等值线（绿色虚线），并在相邻档位之间填充色带形成区域划分（`<0.2 / 0.2–0.5 / 0.5–1 / 1–2 / 2–3 / >3`）。色带用 recharts `Customized` 在数据空间画多边形，因为 `ReferenceArea` 只能画轴对齐矩形，跟不了曲线。
- Tc-Year 图按纵轴温度填充蓝→红渐变（低温蓝、高温红）。边界只依赖 Tc（水平线），故用 SVG `linearGradient` 矩形而非逐段多边形。该图不画品质因子分区：S 依赖压强，在年份轴上无物理意义。
- 两图的背景色都统一为「暖色 = 高、冷色 = 低」，并各自提供说明其含义的图例（压力图为 S 区间色块，年份图为温度色条）。
- 两张图都绘制 77 K 与 300 K 参考线。这两条线曾因被 React Fragment 包裹而完全不显示——recharts 按子元素类型分派渲染，Fragment 内的 `ReferenceLine` 不被识别。
- 视觉编码分两个通道：材料家族定形状与描边色（7 种符号 × 8 色按目录顺序确定性分配），实验/计算定实心/空心。家族数量可由用户增长，配色必然循环撞色，因此形状承担区分职责。新增家族追加在目录末尾，不改变既有家族外观。
- 两个下拉都带 `labelId`，具备可访问名；材料家族下拉设 `displayEmpty`，否则值为空时 MUI 会跳过 `renderValue` 而显示空控件，「未选择」提示不会出现。
- `Tc 字段` 下拉的五个选项与图上方的纵轴提示均为英文（`Experimental Tc`、`Anisotropic Eliashberg Tc`、`Isotropic Eliashberg Tc`、`Allen-Dynes Tc`、`McMillan Tc`）；`tc_field` 键名属 API 契约，不随标签变化。
- 点击点后打开右侧论文详情抽屉。
- 图表组合（chart group）功能本身保留，但入口只在管理页（`AdminPage` 的 `ChartGroupEditor`）：组合 API 支持列表、详情、创建、更新、删除和公开状态切换；组合点可以引用物性记录或使用自定义点字段，压强取自所属材料状态，分类取材料家族 id（沿用既有 `custom_type` 列存储，不新增表结构）。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)、[Issue #72](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/72)）
- 未登录用户的本地图表组合（`scwiki_local_groups`）合并只发生在组合编辑器中，社区页不再读取该存储。

## 工作流程

`/share` 页面先加载材料家族目录确定图例与多选项，再按两张图各自的 `tc_field` 请求公共数据并渲染散点；压力图在同一坐标系计算品质因子等值线与色带，年份图渲染温度渐变。用户点击点后用 `paper_id` 请求 `/api/papers/:id` 并在抽屉中查看论文基础信息、关键物性和研究方法。社区页不再请求 `/api/chart-groups`。

## 约束

- 没有 Approved 论文关联、不属于已批准版本、或所选 Tc 方法无对应条目的数据不会进入公共图表。
- 个人偏好不写入 MySQL、Redis 或公共科研记录；清除站点数据、更换浏览器或设备后不会保留。
- 统计结果反映数据库当前收录范围，不代表完整学科历史。
- 图表组合编辑器前端调用了 `/api/chart-groups/search` 与 `/api/chart-groups/import`，但 Go 路由未注册这两个端点（`goserver/main.go` 的 `chart-groups` 组只注册了列表、详情、创建、更新、删除和公开状态切换）。原先社区页调用的 `/:id/copy` 与 `/:id/export` 随组合入口移除后已无调用方，后端同样没有对应 handler。
- Go 图表缓存按图表类型和 Tc 字段隔离；管理操作现有的 `chart:*` 刷新规则覆盖这些键。缓存为永久缓存，改动查询逻辑后需手动清 `chart:*` 才能看到新结果。

## 代码与测试

- `goserver/handlers/stats.go`
- `goserver/handlers/chart_groups.go`
- `frontend/src/pages/share.tsx`
- `frontend/src/components/ChartScatter.tsx`
- `frontend/src/components/ChartGroupEditor.tsx`
- `frontend/src/lib/scatterConfig.ts`
- `frontend/src/lib/chartPreferences.ts`
- `goserver/handlers/stats_test.go`
- `tests/07_researcher_community_forum/test_issue30_tc_chart_preferences.py`（源码契约断言）
- `tests/07_researcher_community_forum/community-charts.test.tsx`（渲染行为，含空数据背景、两图对齐、家族多选）

## 相关变更记录

- [Feature #30：社区 Tc 双图个人配置与品质因子](../../specs/30-community-tc-chart-preferences/spec.md)
- [Feature #72：图表数据源迁移到条件化模型并恢复背景分区与家族筛选](../../specs/72-chart-data-source-and-family-filter/spec.md)
- [Feature #79：论文级 Material family 多选分类](../../specs/79-paper-material-families/spec.md)

## 已知问题

- 图表组合的搜索与导入接口前后端契约不完整：编辑器会调用 `/api/chart-groups/search` 与 `/import`，但 Go 未注册这两个路由。
- 旧模型的 `show_in_chart` 策展开关随 `superconductor_records` 表一并删除，条件化模型没有替代列，策展人目前无法单独隐藏某条已审核数据。
- 纵轴统一为 0–500 K 后，压力图的低档位等值线（`S=0.2`）被压缩到图的下部，分辨率下降。这是为两图对齐主动接受的取舍。
- `tc_method` 的 `scdft`、`other`、`unknown` 三种取值没有对应的对外 `tc_field`，这些 Tc 条目不会出现在图表中。
