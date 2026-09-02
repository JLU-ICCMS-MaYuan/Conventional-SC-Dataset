# 实施任务：管理端审核编辑页独立化并功能对齐提交页

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认共享组件、两段保存与路由基建就位，记录基线。

- [x] T001 确认 `frontend/src/components/MaterialStatesEditor.tsx` 与 `frontend/src/pages/AdminPage.tsx` 的两段保存/升版逻辑就位（#76），`frontend/src/LazyRoutes.tsx` 路由模式可复用
- [x] T002 确认 `backend/services/structure_candidates.py::read_atoms/export_representations` 可用于表示生成（R1）
- [x] T003 执行 `scripts/run-tests.sh frontend` 记录基线，确认 `tests/07_researcher_community_forum/news-feed.test.tsx` 既有失败不计入回归

## 阶段 2：用户故事 2——结构表示生成（P1，前置）

**目标**：已落库结构获得完整表示，晶胞/格式切换与下载可用。

### 测试

- [x] T004 [P] [US2] 在 `backend/tests/test_paper_structure_candidates.py` 新增测试：`GET /api/rag/papers/:id/structures/:sid/representations` 返回完整 representations（primitive/conventional × cif/poscar）（FR-004、R1）
- [x] T005 [P] [US2] 在同一文件新增测试：结构不存在返回 404；生成失败返回 400（FR-007 降级前提）

### 实施

- [x] T006 [US2] 修改 `backend/api/rag.py`：新增 `GET /api/rag/papers/{paper_id}/structures/{structure_id}/representations`（`get_current_admin`），`read_atoms` + `export_representations` 生成，抽内部函数便于测试（FR-004、R1）

## 阶段 3：用户故事 1——独立编辑页（P1）

**目标**：编辑从弹窗变为独立页面路由。

**独立验收**：列表「编辑」跳转 `/admin/papers/:id/edit`，页面承载全部编辑能力。

### 测试

- [x] T007 [P] [US1] 新增 `tests/02_identity_governance/admin-edit-page.test.tsx`：渲染 `/admin/papers/88/edit`，断言论文级字段、材料状态区、审核区可见；`approved` 论文显示升版警告（FR-003、FR-009）
- [x] T008 [P] [US1] 同一文件：已落库结构调用表示端点后，结构区切换 cell/format 有预览内容；表示端点失败时降级不阻塞（FR-005、FR-007、SC-002）
- [x] T009 [P] [US1] 同一文件：两段保存顺序与 `revision_bumped` 提示（FR-008、FR-009、SC-004）
- [x] T010 [US1] 迁移 `admin-edit-review.test.tsx` / `admin-scientific-data-edit.test.tsx` 的编辑弹窗断言为独立页面语义（点「编辑」进入页面），保留其余断言（FR-010）

### 实施

- [x] T011 [US1] 新增 `frontend/src/pages/AdminPaperEditPage.tsx`：迁移 `materialStateFromDetail`/`candidateFromStructureModel`、两段保存、升版警告、审核区、结构表示加载与合并（FR-001–FR-009）
- [x] T012 [US1] 修改 `frontend/src/LazyRoutes.tsx`：注册 `/admin/papers/:id/edit`（`RoleRoute allow={['admin']}`）（FR-002）
- [x] T013 [US1] 修改 `frontend/src/pages/AdminPage.tsx`：移除编辑弹窗与相关状态，「编辑」按钮 `navigate(\`/admin/papers/${paper.id}/edit\`)`（FR-001）
- [x] T014 [US1] 修改 `frontend/src/i18n/{zh,en}/admin.ts`：独立页标题、返回、加载失败、表示降级提示等文案（FR-011）

## 最终阶段：完善与跨故事事项

- [x] T015 执行 `scripts/run-tests.sh frontend`、`go`、`backend`，与 T003 基线比对确认无新增失败（SC-005）
- [x] T016 执行 `cd frontend && npm run build`，确认 `tsc -b` 无类型错误
- [x] T017 按 [quickstart.md](quickstart.md) 场景 1–3 手工走查（跳转独立页、结构转换与下载、保存与升版提示）
- [x] T018 更新 Issue #78 正文：实现完成结论与验证结果，使 Issue 与 Spec 一致

## 依赖与执行顺序

- **阶段 1** 阻断全部；T001、T002 是硬阻塞（共享组件与表示生成能力未就位则不得开始）。
- **阶段 2** 依赖阶段 1；T006 阻断 T008（表示端点先存在）。
- **阶段 3** 依赖阶段 2；T011 阻断 T012/T013（页面组件先建）。
- **最终阶段** 依赖全部前置。

**串行触点（同文件任务必须串行）**：

| 文件 | 涉及任务 |
| --- | --- |
| `backend/api/rag.py` | T006 |
| `frontend/src/pages/AdminPaperEditPage.tsx` | T011（本 Feature 新增） |
| `frontend/src/pages/AdminPage.tsx` | T013 |
| `frontend/src/LazyRoutes.tsx` | T012 |
| `frontend/src/i18n/{zh,en}/admin.ts` | T014 |
| `tests/02_identity_governance/admin-edit-page.test.tsx` | T007–T009 |

**并行机会**：T004/T005（后端测试）与 T007–T009（前端测试）可并行编写；阶段 2 与阶段 3 的实施任务串行（T006 → T011）。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 / US1 | T011、T013 | 列表跳转独立页、移除弹窗 |
| FR-002 / US1 | T012 | RoleRoute 保护 |
| FR-003 / US1 | T007、T011 | 页面承载全部编辑能力 |
| FR-004 / US2 | T004、T006 | 完整表示生成 |
| FR-005 / US2 | T008、T011 | 晶胞/格式切换预览 |
| FR-006 / US2 | T011 | 结构下载（StructureCandidatePanel 现有交互） |
| FR-007 / US2 | T005、T008、T011 | 表示失败降级 |
| FR-008 / US3 | T009、T011 | 两段保存 |
| FR-009 / US3 | T007、T009、T011 | 升版警告与退回提示 |
| FR-010 | T010、T015 | 上传页不回退 |
| FR-011 | T014 | i18n |
| SC-001 | T013 | 弹窗移除 |
| SC-002 | T008 | 表示切换正确 |
| SC-003 | T011、T017 | 下载可用 |
| SC-004 | T009 | 保存行为一致 |
| SC-005 | T015 | 上传测试全绿 |

## MVP 与增量策略

1. 完成阶段 1：确认共享组件与表示生成能力。
2. 完成阶段 2（P1）：结构表示端点——独立页面的结构功能前提。
3. 完成阶段 3（P1）：独立编辑页 + 功能迁移——本 Feature 的最小可用交付。
4. 最终阶段收尾验证，并把 Issue 正文与实现对齐（T018）。
