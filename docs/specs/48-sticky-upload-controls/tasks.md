# 实施任务：固定主导航与上传解析收起操作

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[contracts/sticky-layout.md](contracts/sticky-layout.md)

**格式**：`- [ ] T### [P?] [US1?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：固定协作入口和文档门。

- [x] T001 创建并验证 GitHub Issue #48 的唯一 `type:bug` 标签及父 Epic #24 反向链接
- [x] T002 创建 `docs/specs/48-sticky-upload-controls/` 完整规划产物并通过需求质量检查

## 阶段 2：基础反馈环

**目的**：先让当前实现稳定复现两个不可达行为。

- [x] T003 [P] 在 `tests/02_identity_governance/identity_ui.test.tsx` 增加左侧主导航 sticky 契约失败测试
- [x] T004 [P] 在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加详情常驻收起入口及本地文件保留失败测试

## 阶段 3：用户故事 1——随时收起长解析详情（P1，MVP）

**目标**：解析详情展开期间，收起入口始终可达并复用现有关闭行为。

**独立验收**：真实 `UploadPage` 测试通过专用常驻按钮关闭详情，任务行恢复查看状态且本地文件仍在。

### 实施

- [x] T005 [US1] 在 `frontend/src/pages/UploadPage.tsx` 提取唯一的当前任务关闭函数并接管任务行收起路径
- [x] T006 [US1] 在 `frontend/src/pages/UploadPage.tsx` 为当前任务详情增加响应式 sticky 操作栏和常驻收起按钮

## 阶段 4：用户故事 2——滚动内容时保持主导航可达（P1）

**目标**：全站左侧 Navigation Rail 固定在顶部栏下方并处理自身高度溢出。

**独立验收**：真实 `AppShell` 测试验证导航语义和 sticky/高度契约，浏览器滚动后仍可见。

### 实施

- [x] T007 [US2] 在 `frontend/src/components/AppShell.tsx` 统一 App Bar 高度并实现 Navigation Rail sticky、高度与内部滚动约束

## 阶段 5：验证与文档

- [x] T008 按 `docs/specs/48-sticky-upload-controls/quickstart.md` 运行前端全量测试、生产构建和多视口界面检查
- [x] T009 使用 `big-project-overview-maintainer` 更新相关导航与 PDF 上传 Overview 当前事实
- [x] T010 核对 FR/SC、更新 Issue #48 实施证据并按仓库规则自动提交本任务文件

## 依赖与执行顺序

- T001–T002 完成后才能实施。
- T003 与 T004 修改不同测试文件，可并行编写；必须先观察失败。
- T004 阻断 T005–T006；T003 阻断 T007。
- T006 与 T007 修改不同生产文件，可分别实现，但最终统一验证。
- T008 阻断 T009–T010。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-003–005 / SC-002–003 / US1 | T004–T006、T008 | 常驻收起入口、共享行为和本地文件保留 |
| FR-001–002 / SC-001 / US2 | T003、T007–T008 | 主导航 sticky、高度和滚动 |
| FR-006–007 / SC-004 | T006–T008 | Material 层级、长文件名和响应式 |
| FR-008 / SC-005 | T003–T004、T008 | 确定性回归与完整前端验证 |
| Documentation Impact | T009–T010 | Overview、Issue 和提交证据 |

## MVP 与增量策略

1. 先完成 T003–T006，交付长解析详情随时可收起的直接价值。
2. 完成 T007，使全站主导航在长页面保持可达。
3. 完成全量测试、浏览器检查、Overview 和自动提交。
