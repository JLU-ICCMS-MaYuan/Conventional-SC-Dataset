# 技术研究：管理端审核编辑页独立化并功能对齐提交页

**GitHub Issue**：[#78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)

本文件只记录本 Feature 内的技术决策。

## R1：结构表示按需生成，不落库

**决策**：`structure_models` 只存惯用胞 CIF（提交链路契约不变），原胞/POSCAR 等表示由新端点从落库 CIF 实时生成（`read_atoms` + `export_representations`）。

**理由**：

- 提交链路 `persist_scientific_draft` 只把常规晶胞 CIF 作为规范表示落库（`scientific_drafts.py` 注释明确）。改落库全部表示需要改提交契约与表结构，且原胞/POSCAR 可从 CIF 无损推导——落库是冗余。
- `export_representations(atoms)`（`structure_candidates.py:177`）已生成 primitive/conventional × cif/poscar 的完整表示，直接复用。
- 按需生成保证落库数据与展示数据始终一致（同一 CIF 实时推导），不会出现落库表示与展示表示漂移。

**备选方案**：

- **落库全部表示**：改 `structure_models` 加列 + 改提交契约，破坏 #76 已稳定的数据模型。已拒绝。
- **前端本地转换**：前端无 pymatgen/ASE 等价能力，不可行。

**证据**：`structure_candidates.py:177-192`；`scientific_drafts.py:305-330`（只写惯用胞 CIF）。

## R2：独立页面用 SPA 路由而非强制新标签

**决策**：`/admin/papers/:id/edit` 是 SPA 路由（`LazyRoutes` + `RoleRoute`），「新标签页」指页面级视图（非弹窗），浏览器新标签打开同一 URL 同样成立；不引入 `window.open`。

**理由**：

- SPA 路由天然支持后退/前进、深链分享、`RoleRoute` 权限保护与 Lazy 加载。
- 弹窗的问题是「堆叠在列表页上、空间局促」，独立路由解决的是视图容器问题；强制新标签反而破坏 SPA 导航一致性。

**证据**：`frontend/src/LazyRoutes.tsx` 的既有路由模式（`/admin` 已用 `RoleRoute allow={['admin']}`）。

## R3：编辑能力从弹窗迁移为页面组件，逻辑不重写

**决策**：把 `AdminPage.tsx` 编辑弹窗的**逻辑**（`materialStateFromDetail`、`candidateFromStructureModel`、两段保存、升版警告）迁移到新组件 `AdminPaperEditPage.tsx`，不重写业务逻辑。

**理由**：

- 两段保存（C4）、升版、`revision_bumped` 提示在 #76 已实现并测试，重写会引入行为差异。
- 迁移 = 把弹窗内容从 Dialog 容器换成页面容器 + 补齐结构表示，KISS。

**证据**：`AdminPage.tsx` 的 `handleEditSave`/`handleEditOpen`/`handleUploadStructure`（#76 实现）。
