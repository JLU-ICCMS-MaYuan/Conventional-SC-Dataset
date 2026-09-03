# 技术研究：审核编辑页元数据与成功返回工作台

**GitHub Issue**：[#87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## R1：不改后端详情契约

**决策**：前端直接使用详情对象的 `uploader_name` 与 `record_count`，不新增 API 字段或后端查询。

**理由**：测试夹具与审核列表契约均已使用这两个字段，问题是编辑页未渲染上传者，且记录数误用了不匹配的翻译键。

**备选方案**：新增专用审核元数据接口。该方案增加网络请求与契约维护成本，没有当前需求所需价值，拒绝。

**证据**：`tests/02_identity_governance/admin-edit-page.test.tsx` 的 `paper` 夹具；`frontend/src/i18n/zh/admin.ts` 的 `thUploader` 和 `recordsChip`。

## R2：成功后复用 workspacePath 导航

**决策**：`handleEditReview` 成功后调用 `navigate(workspacePath)`。

**理由**：`workspacePath` 已按当前用户角色返回 `/superadmin` 或 `/admin`。复用它能让标题栏返回按钮和审核成功行为保持同一规则。

**备选方案**：在成功分支再次判断角色。会复制角色规则，未来新增角色时容易漂移，拒绝。

**证据**：`frontend/src/pages/AdminPaperEditPage.tsx` 现有 `workspacePath` 与返回按钮实现。
