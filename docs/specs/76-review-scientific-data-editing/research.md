# 技术研究：审核编辑页补齐超导性质并支持完全编辑

**GitHub Issue**：[#76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

本文件只记录本 Feature 内的技术决策。

## R1：科学数据重写放 Python 侧，不在 Go 侧重写一份

**决策**：新增 Python 端点 `PUT /api/rag/papers/{paper_id}/scientific-draft`，在单事务内删除该论文当前版本的科学实体，再调用现成的 `persist_scientific_draft` 重建。Go 侧不实现等价逻辑。

**理由**：

- `backend/ingest/scientific_drafts.py` 的 `persist_scientific_draft` 已经承担「从草稿结构建立完整科学实体图」的职责，含材料状态、Tc、物性、结构、计算上下文、实验上下文与证据关联的全部写入顺序与校验。在 Go 侧重写是 1:1 逻辑重复。
- 两套 ORM（GORM 与 SQLAlchemy）维护同一套外键顺序与校验规则，任一侧修改后另一侧漂移的风险高，且漂移只在特定数据形态下暴露。
- 提交链路（`backend/api/rag.py` 的 `_create_pending_paper`）已在用该函数，审核编辑走同一实现可保证两条路径产出的数据结构完全一致。

**备选方案**：

- **Go 侧实现完整重写**：需复制约 250 行写入逻辑与校验，且 Go 侧无 `_validate_draft` 等价实现。已拒绝。
- **前端逐字段调用细粒度接口**：需为材料状态、Tc、物性、结构各设增删改端点（约 12 个），且无法保证跨实体一致性。已拒绝。

**证据**：`backend/ingest/scientific_drafts.py:211-460` 的 `persist_scientific_draft`；`backend/api/rag.py:1083` 的既有调用。

## R2：论文级字段与科学数据分两次保存，不引入分布式事务

**决策**：论文级字段继续走 Go 的 `PUT /api/admin/papers/:id`，科学数据走新增的 Python 端点。前端分别发起、分别反馈。

**理由**：

- 两者分属不同服务与不同数据库连接，跨服务原子性需引入两阶段提交或 Saga，复杂度远超收益。
- 失败语义可以做到清晰：论文级成功而科学数据失败时，论文级改动保留，错误提示明确指出科学数据部分失败，管理员只需重试科学数据（FR-019）。
- 前端已有直接调用 Python 端点的先例：`frontend/src/pages/AdminPage.tsx:238` 调用 `/api/rag/papers/${paper.id}/review-artifact`，不经 Go 转发。

**备选方案**：

- **Go 转发到 Python 并包裹事务**：Go 无法参与 Python 的数据库事务，包裹只是形式上的。已拒绝。
- **把论文级字段也移到 Python 端点**：会改动 Go 的既有编辑契约，波及未纳入本 Feature 范围的字段。已拒绝。

**证据**：`frontend/src/pages/AdminPage.tsx:238`、`goserver/handlers/admin.go:587` 的 `publishApprovedPaperAt`（Go 已在通过 HTTP 调用 Python，非共享事务）。
## R3：升版依靠单向外键级联链，不手工迁移子表

**决策**：新增一次 Alembic 外键迁移，建立单向级联链，升版时只更新一次 `papers` 的三个版本字段，由 MySQL 在同一事务内级联更新全部血缘数据。

```text
papers ─┬─ON UPDATE CASCADE→ paper_files ─CASCADE→ paper_chunks ─CASCADE→ paper_evidences
        └─ON UPDATE CASCADE→ material_states
删除：fk_paper_chunks_paper_revision、fk_paper_evidences_paper_revision（两条冗余直连）
ON DELETE 全部保持 RESTRICT
```

**理由**：

原设计「先 UPDATE `papers` 再逐表迁移 `paper_revision`」在当前结构下**根本不可执行**。5 条复合外键全部是 `ON UPDATE NO ACTION`（即立即检查的 RESTRICT）：先改父表则子行悬空、先改子表则指向不存在的父行，两个方向都在第一条语句就失败。

而简单地给所有外键加 `ON UPDATE CASCADE` 也不行——MySQL 不允许多条 CASCADE 作用于同一子表的同一列。实测确认这个限制比文档描述更危险：

```text
CREATE TABLE 阶段不报错 → 级联更新时才抛 ERROR 1452
```

即盲目加级联会让故障潜伏到运行时。因此必须保留单一路径：`paper_chunks` 与 `paper_evidences` 删除直连 `papers` 的外键，只经文件链到达。

**为何删除直连外键不放松完整性**（实测验证）：

| 违规操作 | 删除直连后是否仍被拦截 | 拦截者 |
| --- | --- | --- |
| 插入 `paper_id` 不存在的 chunk | 是 | `fk_paper_chunks_file_revision` 的复合键含 `paper_id`，必须匹配已有 file 行 |
| 删除仍被引用的 paper | 是 | `ON DELETE RESTRICT` 经 files 层传递 |
| 删除仍被 chunk 引用的 file | 是 | `fk_paper_chunks_file_revision` 的 RESTRICT |

完整性经链条传递，直连外键确属冗余。

**`material_states` 必须一并纳入**：它同样直接引用 `papers(id, content_revision)`（共 5 条复合外键，不是 4 条），不加 CASCADE 会成为新的阻塞点。实测确认它与文件链可共存——限制只针对「同一子表的同一列被多条 CASCADE 覆盖」，`material_states` 与 `paper_files` 是 `papers` 的两个平行分支，各自作用于不同表。

**端到端验证结果**（按真实表结构复刻，含生成列与全部唯一约束）：

```text
单条 UPDATE papers SET content_revision=2, approved_revision=NULL, review_status='pending'
  → paper_files      revision=[2] 行数不变
  → material_states  revision=[2] 行数不变
  → paper_chunks     revision=[2] 行数不变
  → paper_evidences  revision=[2] 行数不变
事务内抛异常后回滚 → 主表与全部子表一同回到原版本，无中间态残留
```

**复杂度净下降**：

| | 原设计 | 本方案 |
| --- | --- | --- |
| 迁移 | 无 | 1 次外键调整 |
| 升版写库 | 4 条 UPDATE，顺序敏感 | **1 条** UPDATE |
| 顺序推理 | 需保证外键在每步都满足——实际不可能 | 无需，由 MySQL 保证 |
| `material_states` | 遗漏 | 纳入链条 |
| 失败模式 | 运行时外键错误 | 无 |

原设计中「迁移顺序必须在 `papers` 更新之后」的整段推理随之删除，`scientific_draft_rewrite.py` 的编排逻辑显著简化。

**代价**：`ON UPDATE CASCADE` 意味着此后任何 `papers.content_revision` 的更新都会静默带走全部血缘数据。在升版场景这正是所需行为，但误改 revision 的后果从「外键报错拦住」变为「静默级联」。`ON DELETE` 保持 RESTRICT，删除路径仍由 `paper_deletion.go` 显式控制，不受影响。

**为何不改唯一约束后复制行**：`paper_files` 有三个不含 `paper_revision` 的唯一约束（`uq_paper_files_main`、`uq_paper_files_path`、`uq_paper_files_order`），复制必然违约；扩展它们会改动 Issue #33 已确立的约束语义，且 `paper_chunks` 会随版本数线性膨胀（当前已 2.8 万条）。级联迁移不复制数据，无此问题。

**旧版本不再持有血缘数据**：级联是「迁移」而非「分叉」，升版后旧 revision 下无文件与切片。该代价与 Spec 范围外事项一致——不提供历史版本浏览与回滚。

**证据**：实测导出的 5 条复合外键定义（全部 `UPDATE_RULE=NO ACTION`）；`paper_files` 的三个唯一约束；MySQL 多 CASCADE 限制的实测复现；单向链方案的端到端验证与回滚验证。

## R4：科学实体删除必须按既有依赖顺序，含自引用解开

**决策**：重建前的删除严格复用 `goserver/handlers/paper_deletion.go` 记录的依赖逆序，共 6 步，其中 `structure_models` 的自引用须先置空再删。

**理由**：

该顺序已在论文删除功能中验证过，直接复用可避免重新推导外键依赖：

1. 证据连接表（`tc_result_evidences`、`structure_model_evidences`、`superconductor_property_evidences`）
2. 叶子业务表（`tc_results`、`superconductor_properties`）
3. 上下文表（`calculation_contexts`、`experimental_contexts`）
4. `structure_models`——先 `UPDATE parent_structure_id = NULL` 再删除
5. `material_state_structure_families`（无 `paper_id`，按材料状态子查询删除）
6. `material_states`

第 4 步的自引用处理是必需的：`paper_deletion.go` 的注释明确写出「同论文内父子结构的删除先后顺序不定，可能触发 Error 1451」。

**与删除功能的差异**：`paper_deletion.go` 在第 6 步之后还会清空 `paper_evidences`、`paper_chunks`、`paper_files`；本 Feature **完全不触碰**这三张表——它们的 `paper_revision` 由 R3 的外键级联自动更新，无需删除也无需手工迁移。

**升版时的执行次序**：先执行上述 6 步删除科学实体，**再**更新 `papers` 的三个版本字段触发级联。理由是 `material_states` 已受 `ON UPDATE CASCADE`——若先升版，级联会把待删除的旧材料状态一并带到新 revision，随后的删除仍能按 `paper_id` 正确清除，但中间态多余。先删后升版的次序更直白，且删除按 `paper_id` 不含 revision 条件，两种次序结果等价。

跨论文共享的目录表（`superconductors`、`material_families`、`structure_families`、`property_definitions`）两者都不动。

**证据**：`goserver/handlers/paper_deletion.go:40-95`；`docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md:33`（共享目录不删除的既有约束）。

## R5：材料状态编辑区抽成共享受控组件

**决策**：把 `frontend/src/components/UploadTaskEditor.tsx` 的材料状态编辑区（约 1020–1284 行）抽成 `frontend/src/components/MaterialStatesEditor.tsx`，props 为 `states / onChange / catalogs / readOnly / issues`，由上传校对页与管理员编辑弹窗共同消费。

**理由**：

- 该区域约 265 行，含化学式、家族选择、维度、超导类型、晶系与空间群联动、压强、Tc 列表、物性列表、结构候选面板。在管理端复制一份必然漂移——两处对同一数据的校验与联动规则会逐渐不一致。
- 受控组件（值与回调都由父级提供）使两个消费方各自管理自己的保存逻辑：上传页存草稿，管理端调科学数据端点。
- `readOnly` prop 使详情只读展示也可复用，替代 `PaperEditView` 中的部分重复展示逻辑（本 Feature 不强制改造该处）。

**风险与对策**：重构触碰上传主路径。对策是 US5 列为 P1，并要求既有 vitest 全部通过（SC-008）——`tests/01_decentralized_uploading/` 下已有 upload-task-editor-classification、upload-task-editor-layout、submit-validation-feedback 等多个用例覆盖该区域行为。

**备选方案**：管理端另写一份简化编辑界面。会导致校验规则与联动逻辑两地维护，违反 DRY。已拒绝。

**证据**：`frontend/src/components/UploadTaskEditor.tsx:1020-1284`；`tests/01_decentralized_uploading/` 下的既有测试文件。

## R6：结构附件补传复用既有候选机制

**决策**：新增 `POST /api/rag/papers/{paper_id}/structure-candidates`，复用 `backend/services/structure_candidates.py` 的 `build_structure_candidate` 做校验与多表示生成。

**理由**：上传链路已有 `POST /api/rag/upload-tasks/{task_id}/structure-candidates`（`backend/api/rag.py:815`），其校验、格式识别与原胞/惯用胞表示生成逻辑可直接复用，只是宿主从上传任务改为论文。前端 `StructureCandidatePanel` 亦可原样复用。

**证据**：`backend/api/rag.py:815-826` 的既有端点；`backend/services/structure_candidates.py`。

## R7：升版必须满足既有版本一致性约束

**决策**：升版事务内的写入顺序须保证 `ck_papers_review_revision` 检查约束在事务提交时成立。

**理由**：该约束要求：

```text
content_revision >= 1
AND (
  (review_status = 'approved' AND approved_revision = content_revision)
  OR
  (review_status IN ('pending', 'rejected') AND approved_revision IS NULL)
)
```

已批准论文升版需同时满足三个变更：`content_revision + 1`、`approved_revision = NULL`、`review_status = 'pending'`。若分多条语句且中间状态被检查，会违约（例如只递增版本号而未清空 `approved_revision`，则 `approved_revision != content_revision` 且状态仍为 approved）。因此三个字段必须在同一条 UPDATE 中一起写入。

**证据**：`alembic/versions/20260821_0007_add_paper_lineage_schema.py:102-113` 的约束定义；`docs/specs/33-paper-lineage-integrity/data-model.md:39-45`。

## R8：升版记录审核事件

**决策**：升版时写入一条 `paper_review_events` 记录，`status` 为 `pending`，注明版本变更来源。

**理由**：`PaperReviewEvent` 已是审核动作的溯源载体（`goserver/handlers/admin.go:365-374` 的既有写入），升版是一次实质的状态变更（已公开 → 待审核），不留记录则无法回答「这篇论文为何从公开变回待审核」。

**证据**：`goserver/models/models.go` 的 `PaperReviewEvent`；`goserver/handlers/admin.go:344-385` 的 `applyPaperReview`。

## R9：重新批准后的索引重建走既有 publish 链路

**决策**：升版后重新批准时，不新增索引重建逻辑，沿用 Go 批准流程中已有的对 Python `publish` 端点的调用。

**理由**：`goserver/handlers/admin.go:577` 在批准成功后已调用 `publishApprovedPaperAt`，后者请求 Python 的 `POST /api/rag/papers/{id}/publish`，该端点重建 Qdrant 向量索引并同步 Neo4j（`backend/api/rag.py:1395-1483`）。升版重新批准走同一路径，天然覆盖 SC-005 的索引重建要求。

**注意**：`publish` 端点读取 `paper_chunks` 时按 `paper_id` 过滤而不带版本条件（`backend/api/rag.py:1409-1412`）。因 R3 采用迁移而非复制，同一 `paper_id` 下的切片只存在一个版本，该查询仍然正确。若当初选择复制方案，此处会索引到多版本重复切片——这是迁移方案的一个附带好处。

**证据**：`goserver/handlers/admin.go:577`、`587-590`；`backend/api/rag.py:1395-1483`。

## R10：只在 `pending` 与 `approved` 两种状态下允许编辑

**决策**：`rejected` 论文不提供科学数据编辑入口。

**理由**：被拒绝的论文不对外公开也不在审核队列中，编辑它没有明确的工作流意义；若需重新处理，应先退回 `pending`。限制状态可减少需要验证的状态转换组合。

**备选方案**：允许编辑 `rejected` 论文。无明确用例支撑，且会引入「rejected 论文编辑后是否也升版」的额外判断。已拒绝。

## 未决事项

无。唯一阻塞点（升版时三张表的唯一约束冲突）已在 `plan` 前解决，记入 Spec 澄清记录与 R3。
