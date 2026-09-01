# 实施计划：社区图表数据源迁移到条件化模型，并恢复背景分区与家族筛选

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

**Research**：[research.md](research.md)

**Quickstart**：[quickstart.md](quickstart.md)

## 摘要

**A 组（已实现）**：社区页两张 Tc 图恒空 —— Go 查询仍指向已删除的 `superconductor_records` 表，GORM 未检查错误导致静默返回 `[]`，前端又用空数组早退渲染 Alert，连坐标系都不画。把查询迁到条件化模型（`tc_results` + `material_states`），让错误浮出来；把分类维度从硬编码 7 类改为动态 `material_families` 目录并加多选组合；补上品质因子区域填充，且空数据时也渲染背景。

**B 组（本轮）**：纯前端布局与视觉改版 —— 固定控件区/图例区高度与控件宽度使两图恒对齐；移除社区页的组合选择器并收敛数据点样式；品质因子填充定为红→黄→绿（高 S 暖色）；Tc 字段标签英文化；年份图加温度渐变；两图纵轴统一 0–500 K。

两组均不改数据库 schema。B 组不触碰后端。

## 技术上下文

- **后端**：Go 1.25 + Gin + GORM，MySQL 8.0（本地 3307）
- **前端**：React + TypeScript + MUI + recharts 2.15
- **测试**：Go `go test`、pytest（源码契约断言）、vitest + Testing Library
- **约束**：
  - 对外 `tc_field` 白名单与错误码不变（`tests/07` 已锁定，前端偏好无需迁移）
  - 不新增数据库列（组合点家族 id 沿用 `custom_type`）
  - 可访问性不回退：实验/计算不依赖颜色单一通道（形状 + 实心/空心双通道）
  - B 组不改动 `/api/chart-groups` 接口与 `AdminPage` 的 `ChartGroupEditor` 入口

## 源代码结构

### A 组（已完成）

```text
goserver/handlers/stats.go                     [重写] 两个图表查询迁到条件化模型
goserver/handlers/stats_test.go                [扩充] 映射、家族回落、嵌入结构体约束
frontend/src/lib/scatterConfig.ts              [重写] 动态家族样式 + 品质因子分区常量
frontend/src/components/ChartScatter.tsx       [重写] 家族编码、色带、空数据渲染
frontend/src/lib/chartPreferences.ts           [修改] v2 纳入家族选择
frontend/src/pages/share.tsx                   [修改] 目录加载、多选、去掉空数据早退
frontend/src/components/ChartGroupEditor.tsx   [修改] 硬编码 7 类 → 动态家族目录
tests/07_researcher_community_forum/
  test_issue30_tc_chart_preferences.py         [修改] 旧表断言 → 新模型断言
  community-charts.test.tsx                    [新增] 空数据背景 + 家族多选
vitest.config.ts                               [修改] include 加入 tests/07
tests/test_chart_rules.py                      [删除] 依赖已删除的 backend.services.chart_rules
docs/overview/03_.../tc-history-and-pressure-charts.md  [重写] 仍在描述旧表
```

### B 组（本轮）

```text
frontend/src/lib/scatterConfig.ts              [修改] 配色改版、纵轴 500 K、温度渐变常量
frontend/src/lib/chartPreferences.ts           [修改] TC_FIELD_LABELS 英文化
frontend/src/components/ChartScatter.tsx       [修改] 固定图例区高度、温度渐变、
                                                      收敛 showBackground/isInGroup、英文纵轴提示
frontend/src/pages/share.tsx                   [修改] 移除组合选择器、固定控件区高宽
tests/07_researcher_community_forum/
  community-charts.test.tsx                    [扩充] 对齐、固定宽度、无组合、渐变、英文标签
  test_issue30_tc_chart_preferences.py         [修改] 同步标签、纵轴域、组合移除相关断言
docs/overview/03_.../tc-history-and-pressure-charts.md  [修改] 回写 B 组行为
```

不涉及后端文件：B 组无 Go、Python、SQL 改动。

## A 组实施阶段（已完成）

### 阶段 1：后端数据源

把 SQL 从 `superconductor_records` 迁到 `tc_results` JOIN 链；`tc_field` 从选列改为按 `tc_method` 过滤行；Tc 取 `COALESCE(tc_value_k, 区间中点)`；实验/计算改判 `result_kind`；加 `paper_revision = content_revision` 版本约束；输出家族三元组；`.Scan().Error` 检查后返回 503。

### 阶段 2：前端视觉编码

`scatterConfig.ts` 改为按目录顺序确定性分配「7 符号 × 8 色」，家族定形状与描边色、实验/计算定实心/空心。品质因子公式与档位下沉到此文件，等值线与色带共用。

### 阶段 3：背景分区与空数据

`Customized` 组件取 recharts 比例尺，在相邻等值线间画多边形色带（`ReferenceArea` 画不了曲线）。去掉 `share.tsx` 的空数据早退，改用固定坐标域 + 图内提示。

### 阶段 4：家族多选

`share.tsx` 加载 `/api/classification-catalogs`，每张图一个 MUI 多选（带勾选框），与图例共享状态。偏好提到 v2，全选存 `null`。

### 阶段 5：测试与文档

改写 `tests/07` 中锁定旧表的断言；新增前端测试覆盖空数据背景与家族多选；补 Go 单测；删除孤儿测试；更新 overview 文档。

## B 组实施阶段（本轮）

### 阶段 6：常量与标签（无 UI 依赖，可先行）

`scatterConfig.ts`：`EMPTY_TC_DOMAIN` 改 `[0, 500]`（R11）；`QUALITY_FACTOR_BAND_COLORS` 定为高 S 暖色的 6 档红→黄→绿色阶（R9）；新增年份图温度渐变的起止色常量。
`chartPreferences.ts`：`TC_FIELD_LABELS` 五个值改英文（R13），键名不动。

### 阶段 7：布局对齐

`share.tsx`：控件区容器设固定高度，家族选择框由 `minWidth: 220` 改为固定 `width`（≤ 200 px），`renderValue` 在文本过长时降级为 `已选 N 项`（R8）。
`ChartScatter.tsx`：图例区容器设固定高度（R7），「当前纵轴」前缀改英文。

两处高度需按实际渲染量取值，避免固定值过小导致内容被裁切 —— 这是 R7 与 R8 必须配套的原因。

### 阶段 8：移除组合选择器

`share.tsx`：删除 `renderGroupSelector`、`groups` / `chart1` / `chart2` / `editorOpen` / `editingGroupId` 状态、`loadAllGroups`、`refreshGroups`、`buildGroupPoints`、`isAdmin`、`ChartGroupEditor` 引用及 `Edit`/`ContentCopy`/`FileDownload` 图标导入。
`ChartScatter.tsx`：`showBackground` 与 `isInGroup` 分支收敛为单一前景样式（R12）；`DataPoint` 的 `isInGroup`/`isCustom` 字段随之移除。

保留 `/api/chart-groups`、`ChartGroupEditor` 组件与 `AdminPage` 入口不动。

### 阶段 9：背景填充

压力图沿用 `QualityFactorBands` 多边形，仅换配色。
年份图新增 `TemperatureBands`：在 `Customized` 内声明 `<defs><linearGradient>`，画一个覆盖绘图区的矩形，沿 Y 轴由蓝（低温）渐变到红（高温）（R10）。
两图各加背景色图例（FR-024）：压力图为 S 区间色块，年份图为温度色条。

### 阶段 10：测试与文档

扩充 `community-charts.test.tsx`：两图对齐（绘图区顶边坐标相等）、选择框宽度不随选中数变化、无组合选择器、年份图渐变存在、Tc 标签为英文、纵轴上界 500。
同步 `test_issue30_tc_chart_preferences.py` 中被 B 组改动影响的断言。
回写 overview 文档。

## 复杂度说明

B 组唯一非平凡处是「固定高度」与「固定宽度」的耦合：单独固定高度会让长文本被裁切，单独固定宽度不解决图例区换行。两者必须一起做，因此阶段 7 不再细分。

年份图渐变与压力图色带用了两种不同几何（矩形渐变 vs 多边形），这是边界形状本质不同导致的，不是可以统一掉的重复（R10）。

## A 组过程中发现的额外问题

1. **77 K / 300 K 参考线一直不显示**：`ChartScatter` 把两条 `ReferenceLine` 包在 React Fragment 里，recharts 按子元素类型分派渲染，Fragment 内的元素不被识别。改为并列条件渲染后恢复。这是独立于主故障的既有 bug。

2. **GORM 不填充嵌入结构体**：初版把家族两列放进匿名嵌入的 `chartFamilyRow`，`Raw().Scan()` 按列名匹配时跳过嵌入字段，家族恒为 NULL，所有点归入「其他」。改为直接声明并加测试固化。

3. **永久缓存掩盖修复效果**：`chart:*` 是永久缓存，重启 goserver 后仍返回旧的空数组，需手动清缓存。已写入文档约束。

4. **`tests/test_chart_rules.py` 是孤儿**：其依赖的 `backend/services/chart_rules.py` 在 `4e04034`（Go 网关接管 API）中已删除，该测试 import 即失败。随旧表逻辑一并删除。

## 质量门

| 门 | 判据 | 命令 |
|---|---|---|
| 类型 | 无 TS 错误 | `cd frontend && ./node_modules/.bin/tsc --noEmit -p tsconfig.json` |
| 前端行为 | `community-charts.test.tsx` 全通过 | `cd frontend && ./node_modules/.bin/vitest run --config ../vitest.config.ts` |
| 源码契约 | `tests/07` 全通过 | `source scripts/lib-local.sh && "$PY_BIN/python" -m pytest tests/07_researcher_community_forum -q` |
| 后端未回退 | Go 与 pytest 全通过 | `bash scripts/run-tests.sh go && bash scripts/run-tests.sh` |
| 人工验收 | 见 [quickstart.md](quickstart.md) | 浏览器 |

已知例外：`tests/07_researcher_community_forum/news-feed.test.tsx` 有 1 项既有失败，与本 Feature 无关，不计入门。

详细验证路径见 [quickstart.md](quickstart.md)。
