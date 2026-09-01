# 技术研究：社区图表数据源、背景分区与家族筛选

**Feature**：[spec.md](spec.md)

**日期**：2026-09-01

本文件记录本 Feature 内的技术决策。A 组决策已随实现验证；B 组决策为本轮新增。

## A 组

### R1：图表数据源改查 `tc_results` JOIN 链

- **决策**：查询主体改为 `tc_results`，JOIN `material_states` / `superconductors` / `papers`，左连 `material_families`；加 `t.paper_revision = p.content_revision`。
- **理由**：`superconductor_records` 已在 `alembic/versions/20260821_0008_add_superconducting_data_model.py:83` 被 `drop_table`；条件化模型中 Tc 是 `tc_results` 的行，条件字段上提到 `material_states`。加版本约束才能保证图上点与点击后的详情一致。
- **备选方案**：恢复旧表或建兼容视图 —— 会让已退役的数据模型重新成为读取依赖，违反迁移方向。
- **证据**：`SHOW TABLES` 确认 `superconductor_records` 不存在；迁移脚本第 83 行有 `drop_table`。

### R2：`tc_field` 从「选列」改为「按 `tc_method` 过滤行」

- **决策**：`chartTcColumns` 的值从列名改为 `tc_method` 取值，对外白名单与默认值不变。
- **理由**：旧模型每种 Tc 是一列；新模型中方法存在 `tc_method` 列，不同方法是不同行。保持对外契约不变可让前端偏好免于迁移，且 `tests/07` 已锁定该契约。
- **备选方案**：改造对外字段名 —— 会破坏已存的用户偏好与既有契约测试。
- **证据**：`ck_tc_results_method` CHECK 约束允许 8 个取值，其中 5 个有对应 `tc_field`。

### R3：查询错误必须外显

- **决策**：`Raw().Scan()` 后检查 `.Error`，失败返回 HTTP 503 且不写缓存。
- **理由**：静默返回空数组正是本故障潜伏的直接原因 —— schema 漂移被伪装成「暂无数据」。
- **证据**：修复前 `curl` 两个接口均返回 `[]`，日志无任何异常。

### R4：家族列不能放在匿名嵌入结构体

- **决策**：`family_id` / `family_name` 直接声明在各 row 结构体上。
- **理由**：GORM 的 `Raw().Scan()` 按原始列名匹配，不填充匿名嵌入字段。初版用嵌入导致家族恒为 NULL，所有点归入「其他」。
- **证据**：SQL 直查返回 `material_family_id = 8`，但接口输出 `family_id = 0`；改为直接声明后输出 `family_id = 8`。

### R5：品质因子色带用 `Customized` 画多边形

- **决策**：用 `Customized` 取 recharts 内部比例尺，在数据空间采样 64 点画 `<polygon>`。
- **理由**：`ReferenceArea` 只能画轴对齐矩形，无法贴合 `Tc = S×sqrt(39²+P²)` 曲线。
- **证据**：`recharts/types/index.d.ts` 导出 `Customized`；`generateCategoricalChart.js:1471` 的 `renderCustomized` 把 `props` 与 `state`（含 `xAxisMap`/`yAxisMap`）注入子组件。

### R6：`ReferenceLine` 不能包在 Fragment 里

- **决策**：两条参考线并列条件渲染，不用 `<>` 包裹。
- **理由**：recharts 按子元素类型分派渲染，`renderMap` 只识别直接子元素类型；Fragment 内的 `ReferenceLine` 被跳过，参考线静默消失。
- **证据**：最小复现对比 —— Fragment 包裹时 `.recharts-reference-line` 计数为 0，改为并列后为 4。

## B 组

### R7：对齐用固定高度容器，而非同步两图内容

- **决策**：控件区与图例区使用固定高度容器，内容变化被容器吸收。
- **理由**：错位根因是控件文本长度影响布局高度。「同步两图内容」要求两图选择状态一致，与「两图独立选择」的既有设计（US3）冲突。固定高度不触碰选择语义。
- **备选方案**：
  - CSS Grid `subgrid` 让两卡片行高联动 —— 浏览器支持面窄，且卡片是独立 `Card`，需重构 DOM 层级。
  - 用 `ResizeObserver` 测量后同步高度 —— 引入运行时测量与重排，复杂度远高于固定高度。
- **配套约束**：必须同时固定控件宽度（R8），否则长文本在固定高度容器内会被裁切。

### R8：宽度固定 + `renderValue` 折叠摘要

- **决策**：`FormControl` 用固定 `width`（而非 `minWidth`），`renderValue` 在选中项文本过长时返回 `已选 N 项`。
- **理由**：MUI `Select` 的显示宽度由 `renderValue` 结果撑开；只设 `minWidth` 无上限时文本越长控件越宽。改为固定 `width` 并让 `renderValue` 自行降级，宽度就与选择内容解耦。
- **备选方案**：保留全名并用 `noWrap` + `ellipsis` 截断 —— 用户无法得知选了几项，信息量低于「已选 N 项」。
- **证据**：`@mui/material/Select/Select.d.ts:128` 的 `renderValue?: (value) => React.ReactNode` 完全由调用方决定显示内容。

### R9：品质因子配色定为红→黄→绿，冷暖统一「暖 = 高」

- **决策**：高 S 用暖色、低 S 用冷色，色阶取 A 组的 `#eef2f6 → #dcece4 → #c8e6c9 → #ffe8a3 → #ffc9a3 → #ffb0a3`。
- **理由**：参考图蓝色在左上（低压高 Tc）即高 S 区；年份图按需求蓝色代表低温。两图并排时同色异义会误读，故冷暖方向必须统一为「暖 = 高、冷 = 低」。
- **过程**：曾按参考图质感改用淡粉紫→深暖色（`#f7f4f6 → #b5623f`），用户实际观感比对后要求回退到 A 组的红→黄→绿。冷暖方向在两版之间未变，仅色相不同。
- **备选方案**：忠实照搬参考图的冷暖朝向 —— 与年份图冲突，须靠图例文字补救，可读性更差。
- **确认**：配色与冷暖方向均已与用户确认（见 spec 澄清记录）。

### R10：年份图渐变用 SVG `linearGradient`，压力图仍用多边形

- **决策**：年份图在 `Customized` 内画单个覆盖绘图区的矩形，填充 `linearGradient` 沿 Y 轴由蓝到红；压力图沿用 R5 的多边形逐段拟合。
- **理由**：年份图的温度分区边界只依赖 Tc，是水平线，单个渐变矩形即可，无需采样；压力图边界是曲线，必须逐段拟合。两者共用同一挂载点与比例尺读取方式，仅填充几何不同。
- **备选方案**：年份图也用多段多边形 —— 能实现但把连续渐变离散化，且代码量更大而无收益。
- **注意**：`linearGradient` 需要 `<defs>`；在 `Customized` 返回的 `<g>` 内声明 `<defs>` 是合法 SVG，recharts 自身也在 `generateCategoricalChart.js:1802` 用 `<defs>` 定义 clipPath。

### R11：纵轴统一 0–500 K

- **决策**：`EMPTY_TC_DOMAIN` 改为 `[0, 500]`，两图共用。
- **理由**：用户要求年份图 0–500 K，同时要求两图对齐；纵轴不一致会让「对齐」只剩几何意义而失去比对价值。
- **代价**：压力图低档位等值线（`S=0.2`）被压缩到图的下部，分辨率下降。已在 spec 的「边界与已知缺口」显式承认。
- **确认**：用户已确认接受该取舍。

### R12：移除组合选择器后收敛数据点样式

- **决策**：删除 `renderGroupSelector` 及组合相关状态；`ChartScatter` 的 `showBackground` / `isInGroup` 分支收敛为单一前景样式。
- **理由**：`isInGroup` 的存在意义是区分「组合内点（前景）」与「其他公共数据（半透明背景）」。组合入口移除后社区页不再产生组合点，两条分支恒等价，保留只会留下永不执行的代码路径（违反 YAGNI）。
- **保留边界**：`/api/chart-groups` 接口、`ChartGroupEditor` 组件、`AdminPage` 入口均不动 —— 组合功能本身未被废弃，只是不再从社区页进入。
- **影响面**：`share.tsx` 可移除 `Edit`/`ContentCopy`/`FileDownload` 图标导入、`groups` 状态、`loadAllGroups`、`refreshGroups`、`editorOpen`、`editingGroupId`、`isAdmin`、`buildGroupPoints` 及 `ChartGroupEditor` 引用。

### R13：Tc 字段英文化的影响面

- **决策**：只改 `TC_FIELD_LABELS` 的五个值与 `ChartScatter` 的「当前纵轴」前缀，不动 `TC_FIELDS` 键名。
- **理由**：键名是 API 契约的一部分（`tc_field` 查询参数），改键名会破坏后端白名单与已存偏好；标签仅用于展示。
- **需同步**：`tests/07_researcher_community_forum/test_issue30_tc_chart_preferences.py` 断言了标签相关文本，改动后须同步；`community-charts.test.tsx` 断言了「当前 Tc 字段暂无可公开数据点」等中文提示，需确认哪些属 Tc 字段标签、哪些属独立提示语。
