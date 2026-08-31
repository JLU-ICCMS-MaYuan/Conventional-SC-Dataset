# 实施计划：简化论文审核功能

**GitHub Issue**：[#62](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/62)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

简化审核弹窗，移除**纯阅读性**的 AI 解析展示，保留基础信息、分类编辑控件、审核状态选择器和批注输入框。

**技术方案**：
1. 修改前端 `AdminPage.tsx` 中的审核弹窗，删除纯展示内容
2. 保持现有审核 API 契约不变（后端无需修改）

### 已删除内容（限于纯阅读性展示）

- AI 建议与用户提交的三列对照（论文类型、理论二级类型、分类理由）
- 原文证据引文（Abstract、Computational Methodology 等页码引用）
- 同 DOI 候选附件列表及其下载入口

### 明确保留：「确认材料状态分类」可编辑控件

材料家族 / 结构家族下拉框承载 Issue #51/#53 交付的能力——管理员在审核时修改分类，
并在同一次审核请求中提交，不额外调用目录治理 API。它不是 AI 信息展示，删除会造成
功能回退，并使 `admin-paper-classification-review.test.tsx` 的 2 个用例失效。

初稿曾把它误判为 AI 展示内容一并删除，经确认后已移回弹窗。

### 本轮不做

编辑页面（铅笔图标）的审核控件区域推迟到后续迭代，本轮只交付弹窗简化。

## 技术上下文

- **语言与版本**：TypeScript 5.x + React 18 + Material-UI 5
- **主要依赖**：`@mui/material`、`react`
- **测试体系**：Vitest + React Testing Library
- **目标平台**：现代浏览器（Chrome、Firefox、Safari）
- **约束**：
  - 不修改后端审核API
  - 保持现有审核状态枚举（pending、approved、rejected）
  - 编辑页面的审核控件不影响现有表单布局

## 源代码结构

```text
frontend/src/
├── pages/
│   └── AdminPage.tsx    [修改] 审核弹窗和编辑页面
└── components/
    └── (暂无新增组件)
```

## 需求到设计的映射

| 来源 | 设计组件 | 验证方式 |
|------|----------|----------|
| FR-001（移除纯展示内容） | 删除弹窗中的 AI 对照、原文引文、候选附件区块 | Vitest：`admin-paper-classification-review.test.tsx` 全通过 |
| FR-002（审核状态选择器） | 保留现有 `<Select>` | Vitest：用例选中「✅ 通过」并提交成功 |
| FR-003（批注输入框） | 保留现有 `<TextField multiline>` | 手动测试：验证可输入多行文本 |
| FR-006（分类能力不回退） | 保留「确认材料状态分类」控件 | Vitest：2 个用例断言分类下拉框与提交载荷 |

## 实施步骤

### 步骤1：简化审核弹窗

**目标**：移除纯阅读性展示，保留分类编辑控件与审核控件。

**操作**：
1. 定位 `AdminPage.tsx` 中的审核弹窗（`<Dialog open={reviewDlg.open}>`）
2. 删除「AI 建议、用户提交与原文证据」区块
3. 删除「同 DOI 候选附件」区块及 `downloadCandidateAttachment` 死代码
4. 保留「确认材料状态分类」控件、DOI/年份/记录数标签、状态选择器、批注输入框
5. 清理因此产生的未使用状态与 import（`candidateAttachments`、`reviewArtifactLoading` 等）

**注意**：`openReview` 仍需拉取 `detail` 与 `review-artifact`——`handleReview` 依赖它们
构造 `material_states` 与 `classification_context` 载荷，不可一并删除。

### 步骤2：测试与验证

1. `npx tsc -b --force`：类型检查
2. `npx vitest run --config ../vitest.config.ts`：前端 75 个用例
3. `vite build`：生产构建
4. 手动测试：打开弹窗确认无 AI 对照与引文，分类下拉框可改，提交后状态更新

## 技术决策

### 决策1：不提取审核控件为独立组件

**理由**：
- 审核控件逻辑简单（状态选择器 + 批注输入框）
- 本轮只有弹窗一个使用场景，提取组件属过度设计（YAGNI）
- 若后续加入编辑页审核入口，届时再按实际重复情况提取

### 决策2：编辑页面审核控件使用 sticky 定位

**理由**：
- `position: sticky` 可以在滚动时保持控件可见
- 不需要额外的滚动监听逻辑
- 兼容性好（现代浏览器全支持）
- 比 `position: fixed` 更符合页面流

### 决策3：保持现有审核API契约不变

**理由**：
- 后端已支持所需的审核功能
- 不需要新增或修改审核状态枚举
- 批注字段已存在（`review_comment`）
- 审核记录已自动保存到 `paper_review_events` 表

## MVP 交付

完成以下内容即可交付：
1. 审核弹窗简化（移除AI内容）
2. 编辑页面添加审核控件
3. 手动测试验证两个入口的审核功能正常
