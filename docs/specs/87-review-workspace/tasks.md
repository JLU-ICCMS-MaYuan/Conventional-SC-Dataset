# 实施任务：审核编辑页元数据与成功返回工作台

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

## 阶段 1：用户故事 1——核对审核元数据（P1）

**目标**：审核编辑页可见上传者和记录数。

**独立验收**：详情夹具中的上传者与记录数显示在页面中，空上传者与零记录有稳定回退。

- [x] T001 [US1] 在 `tests/02_identity_governance/admin-edit-page.test.tsx` 增加上传者、记录数和空值回退的失败回归测试。
- [x] T002 [US1] 在 `frontend/src/pages/AdminPaperEditPage.tsx` 的非编辑元数据区渲染上传者并复用 `admin.recordsChip` 显示记录数。

## 阶段 2：用户故事 2——成功后返回工作台（P1）

**目标**：审核成功后立即回到当前角色工作台。

**独立验收**：超级管理员进入 `/superadmin`，管理员进入 `/admin`，失败时不导航。

- [x] T003 [US2] 在 `tests/02_identity_governance/admin-edit-page.test.tsx` 增加管理员、超级管理员成功导航及失败停留的失败回归测试。
- [x] T004 [US2] 在 `frontend/src/pages/AdminPaperEditPage.tsx` 的 `handleEditReview` 成功分支调用 `navigate(workspacePath)`。

## 最终阶段：验证与文档

- [x] T005 运行 `tests/02_identity_governance/admin-edit-page.test.tsx` 和前端生产构建，并记录结果。
- [x] T006 使用 `big-project-overview-maintainer` 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md` 的已实现审核行为。

## 依赖与执行顺序

- T001 在 T002 前执行；T003 在 T004 前执行。
- T002 与 T004 修改同一页面文件，串行执行。
- T005 依赖 T001 至 T004；T006 依赖真实实现与验证结果。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001/FR-002 / US1 | T001-T002 | 元数据展示与空值边界 |
| FR-003/FR-004 / US2 | T003-T004 | 按角色导航与失败不跳转 |
| SC-004 | T005 | 前端生产构建 |
