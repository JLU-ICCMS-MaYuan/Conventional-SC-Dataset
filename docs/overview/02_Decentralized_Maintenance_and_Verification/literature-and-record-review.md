# 论文与记录审核

## 功能说明

通过分级工作台提供论文和关键物性的审核能力，并将图表、快讯和账号治理限制在超级管理员工作台。

## 当前行为

- 管理后台可按状态、关键词、材料和年份筛选论文列表，并分页展示。
- 管理员可编辑论文基础字段、摘要、LLM 富化字段和普通物性；物性支持新增、修改与标记删除。
- 管理员和超级管理员的论文编辑页将 Authors 显示为可增删的姓名标签，输入姓名后按 Enter 或离开输入框确认，直接点击保存也会带上待确认姓名；重复新增不会产生重复标签。关键词与研究方法采用每行一项的多行输入，窄屏上下排列。三个字段不再展示 JSON 列表包装，姓名及描述内部的逗号、引号、括号仍保留。编辑后保存为 JSON 文本列表，清空后重开保持空态；未经编辑的原字符串或空值保持不变，保存失败保留输入以便重试。（[Issue #95](../../specs/95-admin-paper-list-fields/spec.md)）
- 编辑入口为独立页面（`/admin/papers/:id/edit`，`admin` 与 `superadmin` 角色保护），不再是列表页上的弹窗；页面在论文基础信息区维护多个 Material family 和单选 Superconductor type，并接入共享的材料状态编辑组件（`MaterialStatesEditor`，与上传校对页同一实现）：管理员可查看并修改全部材料状态的化学式、维度、`More type labels`、晶系、空间群、压强，及其下的 Tc 列表、普通物性列表与结构附件。任务解析产生的未分配结构候选也在该编辑页中支持分配、确认和排除；#77 Spec 中的“编辑弹窗”表述由 #78 的独立页面实现替代。承载化学式的输入框标签为「化学式」（上传页）/「化学式 (material)」（管理端物性行）。（[Issue #75](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/75)、[Issue #76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)、[Issue #77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)、[Issue #78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)、[Issue #79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)、[Issue #80](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/80)）
- 已落库结构的晶胞表示（惯用胞/原胞）与格式（CIF/POSCAR）按需从落库 CIF 实时生成（`GET /api/rag/papers/{id}/structures/{sid}/representations`），管理端编辑页可自由切换预览并下载对应文件（[Issue #78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)）。
- 科学数据编辑走 Python 端点 `PUT /api/rag/papers/{id}/scientific-draft`（管理员鉴权），语义是整体替换：单事务内按依赖逆序删除该论文当前科学实体后按请求体重建，复用上传提交的校验规则。`pending` 论文原地重建（版本号不变）；`approved` 论文升版重审——`content_revision` 递增、`approved_revision` 清空、状态回到 `pending`，期间不对外公开，重新批准后走既有 publish 链路重建索引。升版由外键级联链支撑：`paper_files` / `paper_chunks` / `paper_evidences` / `material_states` 的 `paper_revision` 随单条 `UPDATE papers` 由 MySQL 级联迁移（[Issue #76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)）。结构附件补传走 `POST /api/rag/papers/{id}/structure-candidates`，只产出候选不写库，随保存一并提交。
- 物性写入只接受 `superconductor_properties` 的真实列（`material_raw`、`name_raw`、`value_raw`、`value_number`、`unit_raw`、`canonical_unit`、`value_min`、`value_max`、`condition_note`）。压强、温度、主记录标记、结构文本与结构格式没有对应列，因此不再被接受，而不是接受后静默丢弃——后者会让管理员以为改动已保存。条件字段属材料状态，不经物性接口修改，以免绕过材料状态自身的校验与审核语义。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 管理员可查看、编辑、单篇审核和批量审核论文；论文删除与批量删除只允许超级管理员，且为不可恢复的物理删除（详见下方“论文物理删除”）。
- 管理员和超级管理员的科学数据编辑复用共享记录表单：同一材料状态下的测量 Tc、预测 Tc 和自定义性质均可独立折叠，默认展开；收起时保留结果摘要及服务端校验或定义加载错误提示。记录标题和添加选项隐藏模板版本，测量 Tc 的实验 Conditions 使用一个多行文本框，计算 Conditions 保持结构化输入。旧条件及 Evidence 的保留规则见[上传数据结构与表单映射](../01_Decentralized_Uploading_of_Superconductivity_Data/data-structure-and-form-mapping.md)。（[Issue #94](../../specs/94-property-record-editor/spec.md)）
- 管理员在独立编辑页确认论文级 Material family、论文级单选 Superconductor type、状态级结构家族和材料维度；可认可建议、改选数据库已有项或输入新名称。待审正式关联为空时，页面从审核产物回填上传者确认的多个 family、Superconductor type 与 `More type labels`。分类变更随同一次批准请求提交，不额外调用目录治理 API。旧 `key_properties.superconductor_type` 与状态级 `superconductor_kind` 都不再参与管理员写入。
- 独立编辑页顶部有固定的审核区域，可一边修改字段和分类一边提交审核；元数据区显示论文 ID 和创建时间，不显示物性记录数量。管理工作台论文列表每行操作区域显示可点击进入 `/users/:username` 的上传者，并提供仅显示历史图标的入口；只有管理员和超级管理员可从此读取按时间排序的上传、修改、审核记录。审核事件保留当时操作者和每次审核意见，历史导入论文显示“历史导入，上传者未知”。审核结果统一提供「通过」「拒绝」「↩️ 退回待审核」三个状态。选择「通过」时，页面会把当前论文级 family、Superconductor type 和材料状态分类随审核请求提交，无需先单独保存，后端继续执行分类完整性校验。审核请求成功后立即返回当前角色工作台：管理员回 `/admin`，超级管理员回 `/superadmin`。（[Issue #87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)）
- 论文列表和快速审核弹窗不展示物性记录数量；快速审核只提供「拒绝」与「退回待审核」，以及论文标题、DOI、年份和审核意见。批准必须进入独立编辑页完成论文级 family 与状态标签确认。AI 与用户提交值的三列对照、原文证据引文、同 DOI 候选附件列表已移除。（[Issue #62](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/62)、[Issue #78](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/78)、[Issue #79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)、[Issue #87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)）
- 目录不提供独立建议队列、重命名、停用、合并或超级管理员二次治理。新名称只在论文批准事务中创建，拒绝或退回不会污染正式目录。
- 批准论文前检查当前 revision 至少有一个论文级 Material family，并校验各材料状态的元素种类数与主结构唯一性；不完整时返回 `409 classification_incomplete`。批准事务还逐条检查 `property_records` 是否关联当前论文 revision 内可解析的 Evidence，缺失时返回 `409 evidence_incomplete` 和对应 `record_keys`。任一检查失败时论文状态及目录均不改变。批准事件保存 AI 上下文、全部论文 family 与状态级标签的最终目录 ID 快照。历史迁移中已经批准且缺少 Evidence 的记录不被自动改写，但编辑升版后必须补齐 Evidence 才能重新批准。
- `paper_history_events` 是上传、修改和审核的唯一追加式历史来源：新上传与论文创建同事务写入 `uploaded`；有实际业务变化的保存写入一条 `modified`；每次实际审核写入 `reviewed` 并保留审核意见。同一次编辑页保存的 Go/Python 两段请求共享 `history_operation_id`，同值保存和同一操作重试不产生重复事件；审核贡献统计仅计 `reviewed`。
- 论文历史弹窗为每条事件显示 `YYYY-MM-DD-HH-mm-vN-审核人-审核简介` 格式的名称。时间沿用浏览器本地时区、精确到分钟；审核人和意见来自该事件快照，空意见显示“未填写审核意见”。上传和修改条目对应位置使用实际操作者及事件类型，历史导入保留上传者未知提示。长意见在名称中合并连续空白并自动换行，原评论正文保留。名称只用于展示，不作为唯一版本标识，也不写回数据库。前端工作台守卫及 `GET /api/admin/papers/:id/history` 均限制管理员和超级管理员，普通用户为 403、未登录 API 请求为 401。（[Issue #93](../../specs/93-paper-version-visibility-and-naming/spec.md)）
- 批量接口不允许批准论文，避免绕过逐篇材料分类确认；批量拒绝和退回仍可使用。
- Go 统一承载 `/api/papers` 列表、`/api/papers/{id}` 详情和白名单 PATCH：匿名仅查看 approved；登录用户可查看 approved 与 pending；上传者额外可查看自己的 rejected 和 `review_comment`；管理员可查看全部及 `admin_internal_note`。
- 无权查看的已存在 rejected 论文返回 403，不再伪装成 404。普通用户不能修改审核状态、文件路径、上传者、审核者或内部备注。
- 工作台首页即导航：顶部页签已移除，功能入口以统计卡片呈现，点击卡片进入对应视图。卡片名称与目标视图名称一致（原“论文总数”改为“论文审核”）。可点击卡片用 `CardActionArea` 渲染，具备按钮语义、可聚焦、可用 Enter 激活；“当前角色”是身份展示，不做成入口。统计未加载完时显示占位符而非 `0`，避免被误读为真实值为零。（[Issue #61](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/61)）
- `/admin` 页面标题为“管理员工作台”，显示“论文审核”和“当前角色”两张卡片。
- `/superadmin` 页面标题为“超级管理员工作台”，复用同一 `AdminPage` 审核状态和业务逻辑，显示六张卡片：用户与权限、论文审核、待审批管理员、图表管理、快讯管理、当前角色；并额外组合图表管理、快讯管理、管理员申请、用户与权限、账号治理和三类审计面板。
- 图表组合和快讯公开读取保持不变，创建、修改、删除和公开状态切换只允许超级管理员。

## 论文物理删除

超级管理员通过 `DELETE /api/admin/papers/:id`（单篇）和 `POST /api/admin/papers/batch-delete`（批量）执行删除。删除是物理删除：论文行从 MySQL 移除，不写软删除标记，无法恢复。（[Issue #60](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/60)）

- 同一事务内级联清理 15 张关联表，顺序为：`tc_result_evidences`、`structure_model_evidences`、`superconductor_property_evidences`、`tc_results`、`superconductor_properties`、`calculation_contexts`、`experimental_contexts`、`structure_models`、`material_state_structure_families`、`material_states`、`paper_material_families`、`paper_evidences`、`paper_chunks`、`paper_files`、`paper_history_events`，最后删除 `papers`。
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
- `chart_groups` 与 `chart_group_items` 两表此前从未有迁移创建，图表组合功能整体不可用（goserver 持续报 `Error 1146`）；迁移 `20260831_0065` 已补齐建表，功能恢复可用。图表数据点的 `custom_year` 与 `custom_article_type` 此前在创建与更新接口中被静默丢弃，现已收取。
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
- `frontend/src/pages/AdminPaperEditPage.tsx`
- `frontend/src/lib/paperTextLists.ts`
- `frontend/src/LazyRoutes.tsx`
- `frontend/src/components/PaperEditView.tsx`
- `frontend/src/components/NewsManager.tsx`
- `frontend/src/components/SuperAdminGovernance.tsx`
- `goserver/handlers/admin_review_event_test.go`
- `goserver/handlers/paper_history_test.go`
- `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx`
- `tests/02_identity_governance/admin-edit-page.test.tsx`
- `tests/02_identity_governance/admin-paper-list-fields.test.tsx`
- `goserver/handlers/admin_paper_list_fields_test.go`
- `tests/02_identity_governance/identity_ui.test.tsx`
- `tests/02_identity_governance/admin-workspace-cards.test.tsx`

## 相关变更记录

- [Epic #37：用户身份、账户安全与分级管理工作台](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/37)
- [Issue #57：物性写入收敛为真实列，不再接受无对应列的字段](../../specs/57-paper-detail-data-parity/spec.md)
- [Issue #60：论文删除改为按外键依赖级联的物理删除](../../specs/60-fix-paper-deletion-cascade/spec.md)
- [Issue #61：工作台导航由页签改为卡片式入口](../../specs/61-admin-workspace-navigation-refactor/spec.md)
- [Issue #62：审核弹窗移除纯阅读性展示内容](../../specs/62-simplify-paper-review/spec.md)
- [Issue #78：管理端审核编辑页独立化并功能对齐提交页](../../specs/78-admin-edit-page/spec.md)
- [Issue #94：物性记录标题、实验条件文本与独立折叠](../../specs/94-property-record-editor/spec.md)
- [Issue #95：管理端论文作者、关键词与研究方法的可读编辑](../../specs/95-admin-paper-list-fields/spec.md)

## 已知问题

- 图表组合的搜索、导入、导出和复制接口前后端契约仍不完整；本次只收紧现有写接口权限。
- 论文删除对 Qdrant 与 Neo4j 的实际清理效果**待核验**：MySQL 级联删除已在真实库验证（删除后 14 张表清零、全库无 `paper_id` 残留、`superconductors` 保留），但用于验证的论文为 `pending` 状态、从未发布到向量库与图库，两库本就没有对应数据，因此目前只覆盖了“目标不存在时不误报失败”这一边界。需用一篇已 `approved` 且已发布的论文补验。
