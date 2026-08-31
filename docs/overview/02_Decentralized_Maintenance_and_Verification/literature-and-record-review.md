# 论文与记录审核

## 功能说明

通过分级工作台提供论文和关键物性的审核能力，并将图表、快讯和账号治理限制在超级管理员工作台。

## 当前行为

- 管理后台可按状态、关键词、材料和年份筛选论文列表，并分页展示。
- 管理员可编辑论文基础字段、摘要、LLM 富化字段和普通物性；物性支持新增、修改与标记删除。
- 物性写入只接受 `superconductor_properties` 的真实列（`material_raw`、`name_raw`、`value_raw`、`value_number`、`unit_raw`、`canonical_unit`、`value_min`、`value_max`、`condition_note`）。压强、温度、主记录标记、结构文本与结构格式没有对应列，因此不再被接受，而不是接受后静默丢弃——后者会让管理员以为改动已保存。条件字段属材料状态，不经物性接口修改，以免绕过材料状态自身的校验与审核语义。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 管理员可查看、编辑、单篇审核和批量审核论文；论文删除与批量删除只允许超级管理员，且为不可恢复的物理删除（详见下方“论文物理删除”）。
- 管理员在审核弹窗为每个材料状态确认材料家族、结构家族和材料维度；可认可建议、改选数据库已有项或输入新名称。分类变更随同一次审核请求提交，不额外调用目录治理 API。旧 `key_properties.superconductor_type` 不再参与管理员写入。
- 审核弹窗只保留判定所需内容：论文标题与 DOI、年份、记录数标签，材料状态分类确认区，审核结果选择器（通过、拒绝、退回待审核）和审核意见输入框。AI 与用户提交值的三列对照、原文证据引文、同 DOI 候选附件列表已移除——它们是纯阅读性内容，造成信息过载。分类确认区不属于被移除范围，它承载可编辑能力。（[Issue #62](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/62)）
- 目录不提供独立建议队列、重命名、停用、合并或超级管理员二次治理。新名称只在论文批准事务中创建，拒绝或退回不会污染正式目录。
- 批准论文前检查当前 revision 的材料家族、元素种类数、材料维度和主结构唯一性；不完整时返回 `409 classification_incomplete`，论文状态及目录均不改变。批准事件保存 AI 上下文与最终目录 ID 快照。
- 同一审核人每次实际提交单篇或批量论文审核都会写入一条不可变审核事件，即使论文状态和意见与上次相同；相同 `review_request_id` 的网络重试保持幂等，不重复计数。
- 批量接口不允许批准论文，避免绕过逐篇材料分类确认；批量拒绝和退回仍可使用。
- Go 统一承载 `/api/papers` 列表、`/api/papers/{id}` 详情和白名单 PATCH：匿名仅查看 approved；登录用户可查看 approved 与 pending；上传者额外可查看自己的 rejected 和 `review_comment`；管理员可查看全部及 `admin_internal_note`。
- 无权查看的已存在 rejected 论文返回 403，不再伪装成 404。普通用户不能修改审核状态、文件路径、上传者、审核者或内部备注。
- 工作台首页即导航：顶部页签已移除，功能入口以统计卡片呈现，点击卡片进入对应视图。卡片名称与目标视图名称一致（原“论文总数”改为“论文审核”）。可点击卡片用 `CardActionArea` 渲染，具备按钮语义、可聚焦、可用 Enter 激活；“当前角色”是身份展示，不做成入口。统计未加载完时显示占位符而非 `0`，避免被误读为真实值为零。（[Issue #61](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/61)）
- `/admin` 页面标题为“管理员工作台”，显示“论文审核”和“当前角色”两张卡片。
- `/superadmin` 页面标题为“超级管理员工作台”，复用同一 `AdminPage` 审核状态和业务逻辑，显示六张卡片：用户与权限、论文审核、待审批管理员、图表管理、快讯管理、当前角色；并额外组合图表管理、快讯管理、管理员申请、用户与权限、账号治理和三类审计面板。
- 图表组合和快讯公开读取保持不变，创建、修改、删除和公开状态切换只允许超级管理员。

## 论文物理删除

超级管理员通过 `DELETE /api/admin/papers/:id`（单篇）和 `POST /api/admin/papers/batch-delete`（批量）执行删除。删除是物理删除：论文行从 MySQL 移除，不写软删除标记，无法恢复。（[Issue #60](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/60)）

- 同一事务内级联清理 14 张关联表，顺序为：`tc_result_evidences`、`structure_model_evidences`、`superconductor_property_evidences`、`tc_results`、`superconductor_properties`、`calculation_contexts`、`experimental_contexts`、`structure_models`、`material_state_structure_families`、`material_states`、`paper_evidences`、`paper_chunks`、`paper_files`、`paper_review_events`，最后删除 `papers`。
- 删除顺序按 `information_schema` 实测的外键依赖拓扑逆序，不可随意调整：例如 `superconductor_properties` 引用 `calculation_contexts`，必须先删前者，否则 MySQL 抛 `Error 1451` 并回滚整个事务，表现为“提示删除成功但数据仍在”。`structure_models` 自引用 `parent_structure_id`，删除前先置空。`material_state_structure_families` 没有 `paper_id` 列，按本论文的 `material_states` 子查询删除。
- 跨论文共享的目录数据不删除：`superconductors`、`material_families`、`structure_families`、`property_definitions`。
- MySQL 事务提交后，Go 调用 Python 内部端点 `DELETE /api/internal/papers/{id}/vectors` 与 `DELETE /api/internal/papers/{id}/graph` 清理 Qdrant 向量与 Neo4j 节点。该清理是 best-effort：失败只写日志，不回滚、不改变 HTTP 结果——MySQL 行此时已不可恢复，强制回滚只会制造更严重的不一致。Go 通过 `PYTHON_BACKEND_URL` 定位 Python 服务。
- 批量删除逐篇独立处理，单篇失败不影响其余。存在失败时返回 `206` 与 `failed_ids`；`206` 落在 2xx 内不会触发前端的错误分支，因此前端按 `failed_ids` 判定并提示失败篇数与 ID，而非仅凭 HTTP 成功即报完成。
- 删除成功后清理 `chart:*`、`search:*`、`community:contributions:*` 缓存。

## 工作流程

管理员工作台只请求论文数据并完成筛选、编辑和审核。超级管理员工作台复用这些审核请求，再按所选卡片加载图表、快讯、申请、用户和审计数据；后端路由组独立校验各级权限。

## 约束

- 所有审核操作需要 active admin 或 active superadmin 身份。
- `review_comment` 在界面称为“审核意见”，用于向上传者反馈；`admin_internal_note` 只允许管理员读取和通过审核接口维护。
- 图表组合管理的前端存在搜索、导入、导出、复制等调用，但当前 Go 路由只注册列表、详情、创建、更新、删除和公开切换。
- 用户“删除”已替换为保留历史关系的账号注销；封禁、解封、注销和角色变更要求原因与确认。论文物理删除仍仅限超级管理员。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/handlers/paper_deletion.go`
- `goserver/handlers/paper_deletion_test.go`
- `goserver/handlers/stats.go`
- `backend/api/admin_internal.py`
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
- `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx`
- `tests/02_identity_governance/admin-workspace-cards.test.tsx`

## 相关变更记录

- [Epic #37：用户身份、账户安全与分级管理工作台](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/37)
- [Issue #57：物性写入收敛为真实列，不再接受无对应列的字段](../../specs/57-paper-detail-data-parity/spec.md)
- [Issue #60：论文删除改为按外键依赖级联的物理删除](../../specs/60-fix-paper-deletion-cascade/spec.md)
- [Issue #61：工作台导航由页签改为卡片式入口](../../specs/61-admin-workspace-navigation-refactor/spec.md)
- [Issue #62：审核弹窗移除纯阅读性展示内容](../../specs/62-simplify-paper-review/spec.md)

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约仍不完整；本次只收紧现有写接口权限。
- 论文删除对 Qdrant 与 Neo4j 的实际清理效果**待核验**：MySQL 级联删除已在真实库验证（删除后 14 张表清零、全库无 `paper_id` 残留、`superconductors` 保留），但用于验证的论文为 `pending` 状态、从未发布到向量库与图库，两库本就没有对应数据，因此目前只覆盖了“目标不存在时不误报失败”这一边界。需用一篇已 `approved` 且已发布的论文补验。
