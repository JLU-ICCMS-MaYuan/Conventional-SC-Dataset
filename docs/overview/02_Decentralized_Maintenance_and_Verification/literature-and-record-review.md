# 论文与记录审核

## 功能说明

通过分级工作台提供论文和关键物性的审核能力，并将图表、快讯和账号治理限制在超级管理员工作台。

## 当前行为

- 管理后台可按状态、关键词、材料和年份筛选论文列表，并分页展示。
- 管理员可编辑论文基础字段、摘要、LLM 富化字段和普通物性；物性支持新增、修改与标记删除。
- 物性写入只接受 `superconductor_properties` 的真实列（`material_raw`、`name_raw`、`value_raw`、`value_number`、`unit_raw`、`canonical_unit`、`value_min`、`value_max`、`condition_note`）。压强、温度、主记录标记、结构文本与结构格式没有对应列，因此不再被接受，而不是接受后静默丢弃——后者会让管理员以为改动已保存。条件字段属材料状态，不经物性接口修改，以免绕过材料状态自身的校验与审核语义。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 管理员可查看、编辑、单篇审核和批量审核论文；论文删除与批量删除只允许超级管理员。
- 管理员在论文审核页对照 AI 建议、用户提交值和原文证据，为每个材料状态确认材料家族、结构家族和材料维度；可认可建议、改选数据库已有项或输入新名称。旧 `key_properties.superconductor_type` 不再参与管理员写入。
- 目录不提供独立建议队列、重命名、停用、合并或超级管理员二次治理。新名称只在论文批准事务中创建，拒绝或退回不会污染正式目录。
- 批准论文前检查当前 revision 的材料家族、元素种类数、材料维度和主结构唯一性；不完整时返回 `409 classification_incomplete`，论文状态及目录均不改变。批准事件保存 AI 上下文与最终目录 ID 快照。
- 同一审核人每次实际提交单篇或批量论文审核都会写入一条不可变审核事件，即使论文状态和意见与上次相同；相同 `review_request_id` 的网络重试保持幂等，不重复计数。
- 批量接口不允许批准论文，避免绕过逐篇材料分类确认；批量拒绝和退回仍可使用。
- Go 统一承载 `/api/papers` 列表、`/api/papers/{id}` 详情和白名单 PATCH：匿名仅查看 approved；登录用户可查看 approved 与 pending；上传者额外可查看自己的 rejected 和 `review_comment`；管理员可查看全部及 `admin_internal_note`。
- 无权查看的已存在 rejected 论文返回 403，不再伪装成 404。普通用户不能修改审核状态、文件路径、上传者、审核者或内部备注。
- `/admin` 页面标题为“管理员工作台”，只加载审核概览和论文审核。
- `/superadmin` 页面标题为“超级管理员工作台”，复用同一 `AdminPage` 审核状态和业务逻辑，并额外组合图表管理、快讯管理、管理员申请、用户与权限、账号治理和三类审计面板。
- 图表组合和快讯公开读取保持不变，创建、修改、删除和公开状态切换只允许超级管理员。

## 工作流程

管理员工作台只请求论文数据并完成筛选、编辑和审核。超级管理员工作台复用这些审核请求，再按页签加载图表、快讯、申请、用户和审计数据；后端路由组独立校验各级权限。

## 约束

- 所有审核操作需要 active admin 或 active superadmin 身份。
- `review_comment` 在界面称为“审核意见”，用于向上传者反馈；`admin_internal_note` 只允许管理员读取和通过审核接口维护。
- 图表组合管理的前端存在搜索、导入、导出、复制等调用，但当前 Go 路由只注册列表、详情、创建、更新、删除和公开切换。
- 用户“删除”已替换为保留历史关系的账号注销；封禁、解封、注销和角色变更要求原因与确认。论文物理删除仍仅限超级管理员。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/handlers/papers.go`
- `goserver/handlers/classifications.go`
- `goserver/handlers/news.go`
- `goserver/handlers/chart_groups.go`
- `backend/models.py`
- `frontend/src/pages/AdminPage.tsx`
- `frontend/src/components/PaperEditView.tsx`
- `frontend/src/components/NewsManager.tsx`
- `frontend/src/components/SuperAdminGovernance.tsx`
- `goserver/handlers/admin_review_event_test.go`

## 相关变更记录

- [Epic #37：用户身份、账户安全与分级管理工作台](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/37)
- [Issue #57：物性写入收敛为真实列，不再接受无对应列的字段](../../specs/57-paper-detail-data-parity/spec.md)

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约仍不完整；本次只收紧现有写接口权限。
