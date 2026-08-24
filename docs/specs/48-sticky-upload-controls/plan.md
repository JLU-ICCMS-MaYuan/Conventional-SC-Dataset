# 实施计划：固定主导航与上传解析收起操作

**GitHub Issue**：[#48](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/48)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

在现有 React + Material UI App Shell 中，把左侧导航改为受 72px 顶部栏约束的 sticky 网格项；在上传页当前解析详情卡片内增加 sticky 操作栏，并将现有内联收起逻辑提取为页面级函数供任务行和常驻按钮复用。全程不引入滚动监听、额外状态或后端变化。

## 技术上下文

- **语言与版本**：TypeScript 5.6、React 19
- **主要依赖**：Material UI 7、React Router 6
- **数据存储**：不涉及新增或迁移数据；继续使用现有 React state 和 localStorage 活动任务键
- **测试体系**：Vitest、React Testing Library、jsdom；生产构建使用 TypeScript project build 和 Vite
- **目标平台**：现代桌面与移动浏览器中的 SC-Wiki Web 前端
- **性能目标**：不增加滚动事件监听；sticky 定位由浏览器布局引擎处理
- **约束**：顶部 App Bar 高度 72px；不得混入现有用户工作树修改；不改变任务 API 和轮询
- **规模范围**：一个全局 App Shell、一个上传页面、两个前端测试文件

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | KISS、先读后写、测试后自动提交 | 使用 CSS sticky 和共享关闭函数，不增加状态或依赖 | 通过 |
| PRODUCT.md / design.md | 产品界面遵循 Material、导航熟悉可预测 | 复用现有 Navigation Rail、Button、Surface 和 z-index | 通过 |
| Spec FR-004–005 | 两个入口共享行为且不影响任务或本地文件 | 提取单一 `collapseActiveTask` 并由两个入口调用 | 通过 |
| Spec SC-004 | 窄屏不新增溢出 | 操作栏允许标题截断、按钮禁止收缩；不增加固定宽度 | 通过 |

## Feature 文档结构

```text
docs/specs/48-sticky-upload-controls/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   └── sticky-layout.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
frontend/src/components/AppShell.tsx
frontend/src/pages/UploadPage.tsx
tests/02_identity_governance/identity_ui.test.tsx
tests/01_decentralized_uploading/upload-task-workspace.test.tsx
docs/overview/04-authentication-and-review/roles-and-administrator-approval.md
docs/overview/06-rag-literature-assistant/pdf-ingestion.md
```

**结构选择**：全局导航行为留在 `AppShell`；当前任务及收起状态的唯一所有者仍是 `UploadPage`。不让 `UploadTaskCenter` 接管详情布局，避免组件职责扩张。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001–002 / US2 | `AppShell` sticky Navigation Rail | 身份导航组件测试 + 浏览器滚动检查 |
| FR-003–007 / US1 | `UploadPage` sticky 当前任务操作栏与共享关闭函数 | 上传工作区交互测试 + 响应式浏览器检查 |
| FR-008 / SC-005 | 两个现有 Vitest 测试文件、Vite 构建 | quickstart 命令 |

## 阶段与依赖

1. 建立两个能在当前代码上失败的前端回归断言。
2. 修改 App Shell 导航定位并独立转绿。
3. 提取关闭函数、增加详情 sticky 操作栏并转绿上传工作区测试。
4. 执行全量前端测试、生产构建和多视口界面检查。
5. 更新 Overview、Issue 证据并自动提交。
