# 社区散点图全面升级 — 设计文档

## 1. 概述

当前 `/share` 页面有两张基础散点图（Tc-Pressure / Tc-Year），仅区分实验/理论两个系列。本次升级全面改造：形状编码超导类型（7种）、颜色编码实验/理论、引入数据点组合管理系统、支持自定义标注点。

### 目标受众
研究者和材料科学家，用于快速浏览超导材料分布、对比预定义材料组合。

### 核心变化
- 散点图可视化升级（形状+颜色双通道编码）
- 组合管理系统（chart_groups）
- 自定义标注点
- 每张图独立组合选择

---

## 2. 数据模型

### 2.1 chart_groups

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| name | VARCHAR(255) | 组合名称 |
| description | TEXT | 描述 |
| is_preset | BOOLEAN | 系统预设，不可删除 |
| is_public | BOOLEAN | 公开可见 |
| created_by | INTEGER FK→users.id | 创建者 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 2.2 chart_group_items

| 列 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PK | |
| group_id | INTEGER FK→chart_groups.id | |
| key_property_id | INTEGER FK→key_properties.id | 数据库数据点（可空） |
| sort_order | INTEGER | 排序 |
| custom_label | VARCHAR(255) | 自定义点标签（kp_id 为空时） |
| custom_tc | FLOAT | 自定义 Tc |
| custom_pressure | FLOAT | 自定义压强 |
| custom_type | VARCHAR(20) | 自定义超导类型 |
| custom_year | INT | 自定义年份 |

**约束**: `key_property_id` 和 `custom_label` 互斥 —— 要么关联数据库点，要么是自定义点。

---

## 3. 可视化编码

### 3.1 散点图编码

**形状 → 超导类型**（7 种）：

| sc_type | 形状 | Recharts 映射 |
|---------|------|-------------|
| hydride | ▲ 三角 | `triangle` |
| cuprate | ■ 方块 | `square` |
| iron_based | ◆ 菱形 | `diamond` |
| nickel_based | ● 圆点 | `circle` |
| carbon | ▼ 倒三角 | 自定义 path |
| organic | ⬢ 六边形 | 自定义 path |
| others | ✚ 十字 | 自定义 path |

**颜色 → 实验/理论**：

| article_type | 颜色 | hex |
|-------------|------|-----|
| 实验 (e) | 深色, 不透明 0.9 | 同 sc_type 主色 |
| 理论 (t) | 浅色, 半透明 0.5 | 同 sc_type 浅色 |

### 3.2 图例

图上方一行，左侧 7 个类型形状+名称（可点击切换显隐该类型），右侧实验/理论双色块说明。

### 3.3 背景点

当前组合的数据点 → 实心高亮。非当前组合的数据点 → 灰色半透明（opacity 0.15），可切换显隐。

### 3.4 自定义标注点

在图表上以特殊标记（★ 或中空形状 + 文字标签）显示。

---

## 4. 页面布局

```
┌─────────────────────────────────────────────────────────┐
│ Community                                                │
├─────────────────────────────────────────────────────────┤
│ ▸ 全局筛选（可折叠）                                       │
│   类型: ☑h ☑cu ☑fe ☑ni ☑cb ☑org ☑oth                  │
│   实验/理论: ☑实验 ☑理论                                   │
│   年份: [1900 ─── 2026]  压强: [0 ─── 400]              │
├─────────────────────────────────────────────────────────┤
│  ▮▮ Tc-Pressure 散点图                                    │
│  组合: [高压氢化物 ▼]  [编辑] [复制] [导出] [+新建]        │
│  图例: ▲h ■cu ◆fe ●ni ▼cb ⬢org ✚oth  实验深 理论浅     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  灰色背景点 + 当前组合实心点 + 标注标签              │  │
│  │  Hover: tooltip (材料/Tc/压强/年/DOI/组合)         │  │
│  │  点击数据点 → 加入/移出当前组合                      │  │
│  └────────────────────────────────────────────────────┘  │
│  自定义标注: LaH10@250K,200GPa | YH6@220K,180GPa | ...  │
├─────────────────────────────────────────────────────────┤
│  ▮▮ Tc-Year 散点图                                       │
│  组合: [2020后铁基 ▼]  [编辑] [复制] [导出] [+新建]       │
│  图例: ▲h ■cu ◆fe ●ni ▼cb ⬢org ✚oth  实验深 理论浅     │
│  ┌────────────────────────────────────────────────────┐  │
│  │  同上                                               │  │
│  └────────────────────────────────────────────────────┘  │
│  自定义标注: FeSe@65K,2023 | ...                         │
└─────────────────────────────────────────────────────────┘
```

两张图上下排列，各自独立组合，共享全局筛选。

---

## 5. 组合编辑 Dialog

点击「编辑」→ 弹出 Dialog：

```
┌─ 编辑组合: 高压氢化物 ────────────────────────────────┐
│ 名称: [高压氢化物                    ]                  │
│ 描述: [Tc > 150K 的高压氢化物        ]                  │
│ ☑ 公开                                                 │
├───────────────────────────────────────────────────────┤
│ #  │ 材料       │ Tc(K) │ P(GPa) │ 类型   │ 来源   │ ✕│
│ 1  │ CaYH12     │ 194   │ 180    │ hydride│ kp_636 │🗑│
│ 2  │ LaH10      │ 250   │ 200    │ hydride│ kp_201 │🗑│
│ 3  │ 预测LaH12  │ 280   │ 160    │ hydride│ 自定义 │🗑│
├───────────────────────────────────────────────────────┤
│ [+ 从数据库添加]   [+ 添加自定义点]                     │
└───────────────────────────────────────────────────────┘
```

**从数据库添加** — 弹出子 Dialog：
- 搜索框（材料名模糊搜索 key_properties）
- 多选列表 + 确认添加按钮

**添加自定义点** — 弹出子 Dialog：
- label (文本) / Tc (数字) / pressure (数字) / type (下拉)

**删除** — 每行右侧 🗑 按钮，直接删除。

---

## 6. 权限模型

| 操作 | 普通用户 | 管理员 | 超管 |
|------|---------|--------|------|
| 创建组合 | ✅ | ✅ | ✅ |
| 编辑自己的组合 | ✅ | ✅ | ✅ |
| 删除自己的组合 | ✅ | ✅ | ✅ |
| 编辑他人组合 | ❌ | ❌ | ✅ |
| 删除他人组合 | ❌ | ❌ | ✅ |
| 设公开 | ❌ | ✅ | ✅ |
| 创建预设 | ❌ | ❌ | ✅ |
| 查看公开/预设 | ✅ | ✅ | ✅ |

---

## 7. API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/chart-groups` | 列表（公开+预设+自己的） |
| POST | `/api/chart-groups` | 创建组合 |
| GET | `/api/chart-groups/{id}` | 详情（含 items） |
| PUT | `/api/chart-groups/{id}` | 更新组合+items |
| DELETE | `/api/chart-groups/{id}` | 删除组合 |
| POST | `/api/chart-groups/{id}/copy` | 复制组合 |
| GET | `/api/chart-groups/{id}/export` | 导出 JSON |
| POST | `/api/chart-groups/import` | 从 JSON 导入 |
| PATCH | `/api/chart-groups/{id}/public` | 管理员设公开 |

---

## 8. 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/models.py` | 修改 | 新增 ChartGroup / ChartGroupItem 模型 |
| `backend/api/chart_groups.py` | 新建 | 组合 CRUD API |
| `backend/main.py` | 修改 | 注册 router |
| `frontend/src/pages/share.tsx` | 重写 | 全面升级散点图 |
| `frontend/src/components/ChartGroupEditor.tsx` | 新建 | 组合编辑 Dialog |
| `frontend/src/components/ChartGroupScatter.tsx` | 新建 | 散点图组件（含图例/筛选） |
| `backend/scripts/migrate_chart_groups.py` | 新建 | 建表+预设数据 |

---

## 9. 技术选型

- 散点图：**Recharts**（已使用，保持一致性）
- 自定义形状：用 Recharts 的 `shape` prop 传入自定义 SVG
- 数据点点击交互：Recharts `onClick` + Scatter
- 组合编辑：MUI Dialog + Table

---

## 10. 预设组合

系统预装的基础组合（`is_preset=true`）：

| 名称 | 说明 |
|------|------|
| 高压氢化物 Tc>200K | 所有 Tc>200K 的 hydride 数据点 |
| 铜基超导 Tc>100K | 所有 cuprate Tc>100K |
| 铁基超导 | 所有 iron_based 数据点 |
| 近室温超导体 | Tc>200K 的任意类型 |
| 常压超导体 | P<1GPa 的任意类型 |

---

## 11. 自检

- [x] 无 TBD/占位符
- [x] 数据模型与 API 一致
- [x] 权限模型完整
- [x] 视觉编码无歧义
- [x] 组合与数据点关系明确
- [x] 预设组合有具体筛选条件
