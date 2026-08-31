# 实施计划：管理员工作台导航改为卡片式入口

**GitHub Issue**：[#61](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/61)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

移除 `AdminPage.tsx` 的 Tabs 组件，把原「概览」页的统计卡片改造成功能入口。
卡片配置数据化，避免五张卡片重复同一段样式。后端不变。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library
- **约束**：
  - 工作台内部仍以视图索引切换，不引入路由级拆分
  - 卡片必须对键盘与读屏可达（FR-005）

## 源代码结构

```text
frontend/src/pages/AdminPage.tsx        [修改] 移除 Tabs，卡片改为入口
tests/01_decentralized_uploading/
  admin-paper-classification-review.test.tsx  [修改] 入口由 tab 改为卡片按钮
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | 删除 `<Tabs>` 与 `<Tab>` 及其 import | grep 确认无 `<Tabs` |
| FR-002 / FR-003 / FR-004 | `WORKSPACE_CARDS` 常量驱动渲染，`superOnly` 控制可见性 | Vitest 按角色断言卡片数 |
| FR-005 | 用 `CardActionArea` 包裹卡片内容 | Vitest `getByRole('button', { name })` 可定位 |
| FR-006 | 卡片 label 与目标视图名称统一为「论文审核」等 | 界面核对 |
| FR-007 | `cardMetric()` 在 `stats` 为空时返回占位符 | 界面核对 |

## 技术决策

### 决策1：用 CardActionArea 而非给 Card 加 onClick

带 `onClick` 的 `Card` 渲染为 `div`，没有按钮语义：键盘无法聚焦、读屏不播报可操作性、
`getByRole('button')` 也查不到。`CardActionArea` 是 MUI 为此提供的标准封装，一次同时
解决无障碍与可测试性。

### 决策2：卡片配置数据化

五张可点击卡片原本各自重写一遍相同的 `sx`（边框、指针、hover、位移、阴影），属重复
代码。抽为 `WORKSPACE_CARDS` 数组后，样式只写一处，增删卡片只改数据（DRY）。

### 决策3：统计未加载显示占位符

`stats` 为 `null` 时若渲染 `0`，管理员会把「尚未加载」误读为「确实是 0」。
`cardMetric()` 对未加载返回占位符，只有确有数值才显示数字。

## 实施步骤

1. 删除 `<Tabs>` 块及 `Tabs`、`Tab`、`AdminIcon` import
2. 定义 `WORKSPACE_CARDS` 常量（label、hint、accent、tab、metric、superOnly）
3. 定义 `cardMetric()` 处理取值与占位符
4. 卡片区改为遍历渲染，用 `CardActionArea` 包裹；「当前角色」单独保留为不可点击卡片
5. 更新受影响测试的入口操作
6. 验证：`tsc -b --force`、`vitest run`
