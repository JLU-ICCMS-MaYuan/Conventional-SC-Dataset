# 实施计划：简化论文审核弹窗

**GitHub Issue**：[#62](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/62)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

只改前端一个文件：从审核弹窗移除三块纯阅读性内容，保留分类编辑控件与审核控件。
后端不变。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library，`npx vitest run --config ../vitest.config.ts`
- **约束**：
  - 不修改后端审核 API 与状态枚举
  - 不得移除「确认材料状态分类」控件（FR-006）
  - 不得删除 `openReview` 对 detail 与 review-artifact 的拉取（FR-007）

## 源代码结构

```text
frontend/src/pages/AdminPage.tsx        [修改] 审核弹窗
tests/01_decentralized_uploading/
  admin-paper-classification-review.test.tsx  [修改] 入口改为卡片按钮
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | 删除「AI 建议、用户提交与原文证据」与「同 DOI 候选附件」两个区块 | grep 确认区块标题不存在；手动打开弹窗核对 |
| FR-002 | 保留既有 `Select`，三个 `MenuItem` | Vitest 用例选中「✅ 通过」并提交 |
| FR-003 | 保留既有 `TextField multiline` | 手动测试 |
| FR-006 | 保留 `ClassificationAutocomplete` 与「确认材料状态分类」区块 | Vitest 2 个用例断言下拉框与提交载荷 |
| FR-007 | `openReview` 继续并发拉取 detail 与 review-artifact | Vitest 断言 body 含 classification_context |
| FR-008 | 删除 candidateAttachments、reviewArtifactLoading、downloadCandidateAttachment 及相关 import | `tsc -b --force` 无未使用告警 |

## 实施步骤

1. 删除弹窗中的 AI 三列对照与原文证据引文区块
2. 删除同 DOI 候选附件区块及 `downloadCandidateAttachment`
3. 清理失效状态：`candidateAttachments`、`reviewArtifactLoading`、`CandidateAttachment`
   接口、`DownloadIcon` import
4. 保留 `reviewDetail` 与 `reviewArtifact`——`handleReview` 依赖它们构造提交载荷
5. 更新受影响测试的入口操作（因 Issue #61 同时移除了 Tabs）
6. 验证：`tsc -b --force`、`vitest run`

## 技术决策

### 决策1：保留 openReview 的两个并发请求

删除 UI 后，`reviewArtifact` 不再用于展示，但 `handleReview` 仍用它构造
`classification_reason`、`classification_scope`、`ai_material_states`、
`user_material_states`。若一并删除，审核请求将丢失分类上下文，破坏 Issue #51 契约。
因此只删展示，不删数据来源。

### 决策2：不把审核控件提取为独立组件

本轮只有弹窗一个使用场景，提取组件属过度设计（YAGNI）。若后续实施 US2（编辑页
审核入口），届时按实际重复情况再提取。

## 事故记录

初稿把「确认材料状态分类」误判为 AI 展示内容一并删除，导致：
- Issue #51/#53 的分类编辑能力回退
- `admin-paper-classification-review.test.tsx` 2 个用例失败

经与用户确认后已移回弹窗。教训：判断「是否为纯展示」不能只看区块位置与标题，
需确认其中是否含可编辑控件与提交路径。
