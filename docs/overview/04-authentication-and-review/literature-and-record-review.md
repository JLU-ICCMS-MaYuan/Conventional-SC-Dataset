# 论文与记录审核

## 功能说明

通过分级工作台提供论文和关键物性的审核能力，并将图表、快讯和账号治理限制在超级管理员工作台。

## 当前行为

- 管理后台可按状态、关键词、材料和年份筛选论文列表，并分页展示。
- 管理员可编辑论文基础字段、摘要、LLM 富化字段和 `key_properties`；关键物性支持新增、修改、标记删除、主记录标记、结构文本和结构格式编辑。
- 管理员可查看、编辑、单篇审核和批量审核论文；论文删除与批量删除只允许超级管理员。
- 管理员审核材料状态时从数据库目录选择规范中文材料家族，可把待审核建议映射到已有项；旧 `key_properties.superconductor_type` 不再参与管理员写入。
- 超级管理员可以创建、重命名、停用和合并材料/结构家族目录；治理原因和前后快照写入分类审计。
- 批准论文前检查当前 revision 的材料家族、元素种类数和未解决材料家族建议；不完整时返回 `409 classification_incomplete`，论文状态不改变。
- 同一审核人每次实际提交单篇或批量论文审核都会写入一条不可变审核事件，即使论文状态和意见与上次相同；相同 `review_request_id` 的网络重试保持幂等，不重复计数。
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

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约仍不完整；本次只收紧现有写接口权限。
