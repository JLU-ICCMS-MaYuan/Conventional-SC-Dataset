# 快速验收：社区图表数据源、背景分区与家族筛选

**Feature**：[spec.md](spec.md)

本文件给出端到端验收路径。B 组为纯前端改动，无需重启后端；A 组验收涉及接口，需清缓存。

## 前置条件

本地开发栈已启动（宿主机，无 Docker）：

```bash
make status          # 确认 frontend / goserver / mysql 均在运行
make start           # 未启动时
```

数据前提：库中至少有一篇 `review_status = 'approved'` 且带 `tc_results` 的论文。本地已有 Hg 文献（`papers.id = 9`，1911 年，4.2 K，家族「单质超导体」）。

## 自动化门

```bash
# 类型
cd frontend && ./node_modules/.bin/tsc --noEmit -p tsconfig.json

# 前端行为测试
cd frontend && ./node_modules/.bin/vitest run --config ../vitest.config.ts

# 源码契约测试
source scripts/lib-local.sh && "$PY_BIN/python" -m pytest tests/07_researcher_community_forum -q

# 后端未回退
bash scripts/run-tests.sh go
bash scripts/run-tests.sh
```

预期：除 `tests/07_researcher_community_forum/news-feed.test.tsx` 的 1 项既有失败外全部通过。

## A 组接口验收

图表结果是永久缓存，改动查询逻辑后必须先清缓存：

```bash
source scripts/lib-local.sh
"$INFRA_BIN/redis-cli" --scan --pattern 'chart:*' | xargs -r "$INFRA_BIN/redis-cli" DEL
```

```bash
curl -s 'http://127.0.0.1:8080/api/papers/stats/tc-pressure?tc_field=experimental_tc'
curl -s 'http://127.0.0.1:8080/api/papers/stats/tc-year?tc_field=experimental_tc'
```

预期：各返回一个数据点，含 `family_id: 8`、`family_name: "单质超导体"`、`type: "experimental"`、`paper_id: 9`。

```bash
curl -s -w ' [%{http_code}]' 'http://127.0.0.1:8080/api/papers/stats/tc-pressure?tc_field=drop_table'
```

预期：`{"error":"不支持的 Tc 字段"} [400]`。

```bash
curl -s 'http://127.0.0.1:8080/api/papers/stats/tc-pressure?tc_field=allen_dynes_tc'
```

预期：`[]`（该方法当前无数据，属正常空结果，非错误）。

## B 组浏览器验收

打开 <http://127.0.0.1:5173/share>。

### 场景 1：两图对齐（FR-014、FR-015、FR-016、SC-001）

1. 左图「材料家族」下拉全选（默认「全部」），观察两图绘图区顶边是否等高。
2. 取消左图 3 个家族（显示应变为折叠摘要），再次观察顶边 —— 应仍等高。
3. 只保留左图 1 个家族，再观察 —— 应仍等高。
4. 全部取消（显示「未选择」），再观察 —— 应仍等高。
5. 检查两图纵轴上界均为 500 K，刻度一致。
6. 检查两张卡片底边是否对齐（图例区固定高度）。

判据：以上 4 种选择状态下，两图绘图区顶边、底边纵坐标不发生相对偏移。

### 场景 2：控件宽度固定（FR-017、FR-018、SC-002）

1. 依次在选中 1、3、6、9 项的状态下观察「材料家族」选择框宽度 —— 应完全一致。
2. 对比左右两图的选择框宽度 —— 应一致。
3. 选中项名称总长超出控件宽度时，应显示 `已选 N 项`，不换行、不撑开。
4. 全选显示「全部」；一个不选显示「未选择」。

### 场景 3：无组合选择器（FR-019、SC-003）

1. 页面上不应出现「组合」下拉，也不应出现编辑、复制、导出、+ 新建按钮。
2. 以管理员账号登录后再看 —— 仍不应出现（该入口已整体移除，不是按权限隐藏）。
3. 进入管理页确认 `ChartGroupEditor` 仍可正常打开（组合功能本身未被移除）。

### 场景 4：背景填充（FR-021、FR-022、FR-023、FR-024、SC-006）

1. 压力图：高品质因子区（左上）为暖色，低品质因子区（右下）为冷色。
2. 压力图：等值线为绿色虚线，`S=0.2`…`S=3` 标注沿曲线可见。
3. 压力图：下方有 S 区间色块图例（6 档）。
4. 年份图：低温区（下部）蓝色，高温区（上部）红色，连续渐变。
5. 年份图：下方有温度色条图例。
6. 两图：77 K 与 300 K 参考线为深红点划线，各显示一次。

### 场景 5：Tc 字段英文（FR-025、SC-005）

1. 打开任一图的「Tc 字段」下拉，五个选项应为：`Experimental Tc`、`Anisotropic Eliashberg Tc`、`Isotropic Eliashberg Tc`、`Allen-Dynes Tc`、`McMillan Tc`。
2. 图上方「当前纵轴」提示应为英文。

### 场景 6：数据点与筛选联动仍正常（回归）

1. Hg 数据点应出现在两张图上。
2. 取消「单质超导体」后该点消失，坐标系与背景填充仍在，图内出现无数据提示。
3. 点击数据点应打开右侧论文详情抽屉。
4. 点击图例中的家族应与下拉状态同步。

## 失败排查

| 现象 | 可能原因 |
|---|---|
| 接口返回 `[]` 但库里有数据 | `chart:*` 缓存未清 |
| 接口返回 503 | 查询失败，看 goserver 日志的 SQL 错误 |
| 参考线不显示 | `ReferenceLine` 被 Fragment 包裹（见 research.md R6） |
| 所有点归入「其他」 | 家族列放进了匿名嵌入结构体（见 research.md R4） |
| 测试中图表完全不渲染 | jsdom 下 `getBoundingClientRect` 返回 0，需 stub |
