# 实施计划：AI 临时表单字段卡片渐进展开

**GitHub Issue**：[#47](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/47)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

在现有 `UploadParsingDetail` 临时表单字段渲染路径中增加局部的可折叠字段卡片。卡片使用真实渲染高度判断内容是否超过统一收起高度；只有溢出时显示文字化展开控制。展开状态按 `taskId + field.path` 隔离，并在解析轮询追加内容时保持。实现复用现有 MUI 组件和响应式 Grid，不改 API、数据契约或最终草稿编辑器。

## 技术上下文

- **语言与版本**：TypeScript 5.6、React 19.2。
- **主要依赖**：MUI 7.3、Emotion、React Router 6、Vite 5。
- **数据存储**：不新增持久化；展开状态仅存在于当前组件生命周期。
- **测试体系**：Vitest 2、jsdom、Testing Library；测试位于 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx`。
- **目标平台**：现代桌面和移动浏览器中的 `/upload` 页面。
- **性能目标**：只观察当前可见字段内容尺寸；轮询更新不新增网络请求，不对整页执行持续扫描。
- **约束**：保持现有解析 DTO、冲突语义、ready 后编辑器切换和响应式双列/单列结构；正文必须可选择复制。
- **规模范围**：单个已展开上传任务中的临时表单字段，通常为数十张卡片。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| `AGENTS.md` | KISS、复用现有组件、文档与代码验证后提交 | 在目标组件内建立单一局部卡片组件，不增加依赖和跨模块状态 | 通过 |
| PDF 摄入 Overview | 候选值、冲突和来源证据持续可见且不静默覆盖 | 折叠只改变视觉高度，底层候选顺序和内容保持不变 | 通过 |
| Spec FR-001～FR-010 | 稳定列宽、真实溢出判断、独立状态和动态更新 | Grid 顶部对齐；内容内层测量；状态由任务与字段身份隔离 | 通过 |
| Spec FR-011～FR-014 | 键盘、ARIA、文字状态、减少动效和安全换行 | 使用标准 Button、展开语义、可见焦点、短动效及 reduced-motion 分支 | 通过 |
| TDD 测试边界 | 只通过 `UploadParsingDetail` 的用户可见 UI 验证 | 仅在 API 边界提供响应，使用角色、名称和状态断言 | 通过 |
| Requirements Checklist | 全部需求质量项已完成 | 15/15 项为 `[x]` | 通过 |

## Feature 文档结构

```text
docs/specs/47-collapsible-preview-cards/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
└── checklists/
    └── requirements.md
```

本 Feature 不涉及持久数据、外部 API、CLI 或事件契约，因此不创建 `data-model.md` 与 `contracts/`。

## 源代码结构

```text
frontend/src/components/UploadParsingDetail.tsx
tests/01_decentralized_uploading/upload-task-workspace.test.tsx
docs/overview/06-rag-literature-assistant/pdf-ingestion.md
docs/specs/47-collapsible-preview-cards/
```

**结构选择**：字段折叠只服务于临时解析详情，保持为 `UploadParsingDetail.tsx` 内部局部组件，避免为单一使用点增加公共抽象。测试继续通过现有上传工作区集成测试文件覆盖公开 UI。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| US1、FR-001～FR-004、FR-014、SC-001、SC-003 | 响应式字段 Grid、统一收起高度和溢出判断 | 短/长字段 UI 测试、窄屏人工检查、前端构建 |
| US2、FR-005～FR-008、FR-015、SC-002、SC-005 | 独立字段状态、展开控制和原内容渲染 | 多卡片展开/收起测试、冲突来源回归测试 |
| US3、FR-006、FR-009～FR-013、SC-004 | 任务字段身份、尺寸观察、ARIA 和减少动效 | 动态轮询、任务切换、键盘与语义测试 |

## 阶段与依赖

1. 记录技术决策并建立 TDD 任务与验证路径。
2. 先交付 US1：短字段不出现控制，长字段默认收起。
3. 再交付 US2：独立展开、再次收起、正文选择不误触。
4. 最后交付 US3：动态追加、任务隔离、键盘/ARIA、响应式和减少动效。
5. 运行定向测试、上传模块回归和生产构建，更新 Overview 并收敛任务。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 真实 DOM 溢出测量 | 相同字符数在不同列宽、语言和来源结构下高度不同 | 按字符数或字段类型判断会在移动端、长 DOI 和多来源场景误判 |
| 尺寸变化监听 | 解析轮询和响应式换行会在首次渲染后改变内容高度 | 只在首次挂载测量会产生失效控制或漏掉新溢出 |
