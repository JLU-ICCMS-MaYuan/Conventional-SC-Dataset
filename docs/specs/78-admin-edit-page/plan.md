# 实施计划：管理端审核编辑页独立化并功能对齐提交页

**GitHub Issue**：[#78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)　**决策依据**：[research.md](research.md)

## 目标结构

```text
后端（Python）
  GET /api/rag/papers/{id}/structures/{structure_id}/representations   ← 新增
    从 structure_models 读取惯用胞 CIF → read_atoms + export_representations → 完整表示
    管理员鉴权；结构不存在 404；生成失败 400 structure_representation_failed

前端
  frontend/src/pages/AdminPaperEditPage.tsx          ← 新增：独立编辑页组件
    路由 /admin/papers/:id/edit（LazyRoutes + RoleRoute admin）
    迁移现编辑弹窗能力：论文级字段、MaterialStatesEditor（含结构区）、
    审核区、两段保存（C4）、升版警告与退回提示
    加载详情后：对每个已落库结构调用表示端点 → 合并进候选的 representations
  frontend/src/pages/AdminPage.tsx                  ← 修改：移除编辑弹窗，「编辑」按钮跳转 navigate(`/admin/papers/${id}/edit`)
  frontend/src/i18n/{zh,en}/admin.ts                ← 新增页面级文案（标题、返回、加载失败等）
```

## 实施步骤

### 步骤 1：后端结构表示端点

- `backend/api/rag.py` 新增 `GET /api/rag/papers/{paper_id}/structures/{structure_id}/representations`（`get_current_admin`）。
- 从 `structure_models` 读该结构行（`structure_id` + `paper_id`），取 `structure_text`（惯用胞 CIF）。
- `read_atoms("cif", structure_text)` → `export_representations(atoms)` → 返回 `{ok, data: {structure_id, structure_format, representations, validation}}`。
- 生成失败（解析异常）返回 400 `structure_representation_failed`（前端降级）。
- 抽内部函数便于测试（沿用 #76 先例）。

### 步骤 2：独立编辑页组件

- 新增 `frontend/src/pages/AdminPaperEditPage.tsx`：
  - `useParams` 取 `id`，`useAuth` 校验管理员（RoleRoute 已在路由层保护，页面内无需重复）。
  - 加载详情（`GET /api/admin/papers/:id`）、目录（`loadClassificationCatalogs`）、空间群表。
  - 迁移 `candidateFromStructureModel` 转换（含 `structure_models` → confirmed 候选）与 `materialStateFromDetail`。
  - 对每个已落库结构调用表示端点，把返回的 `representations` 合并进对应候选；失败时保留落库 CIF（降级）。
  - 论文级字段编辑表单、`MaterialStatesEditor`（可编辑，含未分配候选区与结构面板）、审核区、升版警告。
  - 两段保存（C4）：`PUT /api/admin/papers/:id` → `PUT /api/rag/papers/:id/scientific-draft`；失败语义与提示沿用 #76。
  - 保存成功提示、`revision_bumped` 退回提示、返回列表导航。
- 布局：页面级（`Box`/`Container` + 标题栏 + 返回按钮），非弹窗。

### 步骤 3：列表跳转与弹窗移除

- `AdminPage.tsx`：删除编辑弹窗的渲染与相关状态（`editPaper`/`editForm`/`handleEditSave` 等迁移到独立页面）；列表「编辑」按钮改为 `navigate(\`/admin/papers/${paper.id}/edit\`)`。
- `frontend/src/LazyRoutes.tsx`：注册 `/admin/papers/:id/edit`（`RoleRoute allow={['admin']}`）。

### 步骤 4：i18n

- `admin.ts` 新增：独立页标题、返回列表、加载失败、结构表示生成失败降级提示（若需）、页面保存成功/失败提示（复用现有键优先）。

### 步骤 5：测试

- `tests/02_identity_governance/admin-edit-page.test.tsx`（新增）：
  1. 渲染 `AdminPaperEditPage`（`/admin/papers/88/edit`），断言论文级字段、材料状态区、审核区、升版警告（approved 时）可见。
  2. 已落库结构调用表示端点后，结构区切换 cell/format 有预览内容（mock 端点返回完整 representations）。
  3. 表示端点失败时降级（仅落库 CIF 可用），不阻塞保存。
  4. 两段保存顺序（先论文级后科学数据）与 `revision_bumped` 提示。
- `tests/02_identity_governance/admin-edit-review.test.tsx` 与 `admin-scientific-data-edit.test.tsx`：**改造为独立页面语义**（点「编辑」后进入页面而非弹窗）；既有断言如适用则迁移。
- `upload-task-*` 等上传页测试不变（SC-005）。

### 步骤 6：验证

- `cd frontend && npx vitest run --config ../vitest.config.ts tests/02_identity_governance/ tests/01_decentralized_uploading/` 全绿。
- `cd frontend && npm run build`（tsc -b）无类型错误。
- `scripts/run-tests.sh go`、`backend` 无回归（后端新增端点用 pytest 覆盖）。
- 浏览器走查：列表「编辑」→ 独立页面；结构晶胞/格式切换与下载；保存与升版提示。

## 关键约束

- **结构表示按需生成**：不落库、不改 `structure_models`、不改提交契约。
- **弹窗移除**：独立页面上线后 `AdminPage` 不再有编辑弹窗。
- **行为对齐**：两段保存、升版警告、失败语义与 #76 弹窗完全一致，仅承载容器变化。
- **上传页零改动**。
