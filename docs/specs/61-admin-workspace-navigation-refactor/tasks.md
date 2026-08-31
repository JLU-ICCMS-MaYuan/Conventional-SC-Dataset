# 实施任务：管理员工作台导航改为卡片式入口

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

## 阶段 1：移除页签导航

- [x] T001 删除 `<Tabs>` / `<Tab>` 块 — `frontend/src/pages/AdminPage.tsx`
- [x] T002 清理 `Tabs`、`Tab`、`AdminIcon` import

## 阶段 2：卡片式入口

- [x] T003 定义 `WORKSPACE_CARDS` 常量（label、hint、accent、tab、metric、superOnly），
  五张可点击卡片的样式只写一处（DRY）
- [x] T004 定义 `cardMetric()`：`stats` 为空时返回占位符而非 `0`（FR-007）
- [x] T005 卡片区改为遍历渲染，用 `CardActionArea` 包裹以获得按钮语义与键盘可达（FR-005）
- [x] T006 「当前角色」保留为不可点击卡片（身份展示，无目标页面）

## 阶段 3：验证

- [x] T007 更新 `admin-paper-classification-review.test.tsx` 入口为卡片按钮
- [x] T008 新增 `tests/02_identity_governance/admin-workspace-cards.test.tsx`：
  无 tab、按角色区分卡片可见性、5 个入口可按 `role=button` 定位、点击进入列表、
  加载中显示占位符
- [x] T009 `npx tsc -b --force` 通过
- [x] T010 `npx vitest run` 全量通过（11 文件 83 用例）

## 阶段 4：文档

- [x] T011 回写 Overview：卡片式导航、按钮语义、占位符行为

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001 | T001、T002 | `queryAllByRole('tab')` 长度为 0 |
| FR-002 | T003、T005 | 点击卡片进入论文列表 |
| FR-003、FR-004 | T003（superOnly） | 按角色断言卡片可见性 |
| FR-005 | T005 | `getByRole('button', { name })` 可定位 |
| FR-006 | T003（label 统一） | Overview 与界面核对 |
| FR-007 | T004 | 加载中不渲染 `0` |

## 遗留

- 「快讯管理」卡片的计数来源未接入，显示 `-`（范围外事项）
- 「图表管理」计数取自 `chartGroups`，超管进入页面时即通过 `useEffect` 加载，
  显示的是真实值。当前环境显示 `0` 是因为 `chart_groups` 表在库中不存在
  （goserver 日志报 `Error 1146`），请求失败后置为空数组。这是既有的库表缺失问题，
  不由本 Feature 引入，也不在本轮范围内。
