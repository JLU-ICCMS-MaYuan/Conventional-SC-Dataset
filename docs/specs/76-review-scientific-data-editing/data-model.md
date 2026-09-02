# 数据模型：审核编辑页补齐超导性质并支持完全编辑

**GitHub Issue**：[#76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76)

**日期**：2026-09-01（2026-09-01 修订：升版方案改为外键级联，新增一次迁移）

**Spec**：[spec.md](spec.md)　**Plan**：[plan.md](plan.md)　**决策依据**：[research.md](research.md)

**本 Feature 不新增表、不新增列、不改唯一约束与检查约束。** 唯一的 Schema 改动是一次外键规则调整（见「外键迁移」），用于支撑 Issue #33 已建立但从未执行过的论文版本递增语义。

## 涉及的既有实体

| 实体 | 表 | 本 Feature 的操作 |
| --- | --- | --- |
| 论文 | `papers` | 更新 `content_revision`、`approved_revision`、`review_status`（仅已批准论文升版时） |
| 材料状态 | `material_states` | 删除后重建；其 `paper_revision` 受级联 |
| Tc 结果 | `tc_results` | 删除后重建 |
| 普通物性 | `superconductor_properties` | 删除后重建 |
| 结构模型 | `structure_models` | 删除后重建 |
| 计算上下文 | `calculation_contexts` | 删除后重建 |
| 实验上下文 | `experimental_contexts` | 删除后重建 |
| 材料状态与结构家族关联 | `material_state_structure_families` | 删除后重建 |
| 三类证据关联 | `tc_result_evidences`、`structure_model_evidences`、`superconductor_property_evidences` | 删除后重建 |
| 正文文件 | `paper_files` | **不触碰**；`paper_revision` 由级联自动更新 |
| 文本切片 | `paper_chunks` | **不触碰**；同上 |
| 证据锚点 | `paper_evidences` | **不触碰**；同上 |
| 审核事件 | `paper_review_events` | 新增一条升版记录 |
| 跨论文共享目录 | `superconductors`、`material_families`、`structure_families`、`property_definitions` | **不动** |

共享目录不删除是既有约束（见[文献与记录审核](../../overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md)），本 Feature 沿用。

## 外键迁移

### 迁移前的实测现状

5 条复合外键全部引用 `papers(id, content_revision)`，`UPDATE_RULE` 全部为 `NO ACTION`（立即检查的 RESTRICT）：

| 外键 | 子表 | 子列 | 父表 | UPDATE | DELETE |
| --- | --- | --- | --- | --- | --- |
| `fk_paper_files_paper_revision` | `paper_files` | `paper_id, paper_revision` | `papers` | NO ACTION | RESTRICT |
| `fk_paper_chunks_paper_revision` | `paper_chunks` | `paper_id, paper_revision` | `papers` | NO ACTION | RESTRICT |
| `fk_paper_chunks_file_revision` | `paper_chunks` | `paper_file_id, paper_id, paper_revision` | `paper_files` | NO ACTION | RESTRICT |
| `fk_paper_evidences_paper_revision` | `paper_evidences` | `paper_id, paper_revision` | `papers` | NO ACTION | RESTRICT |
| `fk_paper_evidences_chunk_revision` | `paper_evidences` | `paper_chunk_id, paper_id, paper_revision` | `paper_chunks` | NO ACTION | RESTRICT |
| `fk_material_states_paper_revision` | `material_states` | `paper_id, paper_revision` | `papers` | NO ACTION | RESTRICT |

因此任何 `papers.content_revision` 的更新都会被立即拒绝——这是原「手工迁移子表」方案不可执行的根因。

### 迁移目标结构

```text
papers ─┬─ON UPDATE CASCADE→ paper_files ─CASCADE→ paper_chunks ─CASCADE→ paper_evidences
        └─ON UPDATE CASCADE→ material_states
```

| 操作 | 外键 | 说明 |
| --- | --- | --- |
| 改为 `ON UPDATE CASCADE` | `fk_paper_files_paper_revision` | 文件链首层 |
| 改为 `ON UPDATE CASCADE` | `fk_paper_chunks_file_revision` | 经 files 到达 papers |
| 改为 `ON UPDATE CASCADE` | `fk_paper_evidences_chunk_revision` | 经 chunks 到达 papers |
| 改为 `ON UPDATE CASCADE` | `fk_material_states_paper_revision` | 平行分支 |
| **删除** | `fk_paper_chunks_paper_revision` | 冗余直连 |
| **删除** | `fk_paper_evidences_paper_revision` | 冗余直连 |

`ON DELETE` 全部保持 `RESTRICT`，不改动。

### 为何必须删除两条直连外键

MySQL 不允许多条 `ON UPDATE CASCADE` 作用于同一子表的同一列。`paper_chunks.paper_revision` 若同时被 `fk_paper_chunks_file_revision` 与 `fk_paper_chunks_paper_revision` 两条 CASCADE 覆盖，则级联更新时报 `ERROR 1452`。

**实测发现的危险特性**：这种冲突在 `CREATE TABLE` / `ADD CONSTRAINT` 阶段**不报错**，只在实际执行级联更新时才失败。因此不能依赖迁移成功来判断结构正确，必须有运行时的级联测试覆盖。

### 删除直连外键不放松完整性（实测验证）

| 违规操作 | 是否仍被拦截 | 拦截者 |
| --- | --- | --- |
| 插入 `paper_id` 不存在的 chunk | 是 | `fk_paper_chunks_file_revision` 的复合键含 `paper_id`，必须匹配已有 file 行 |
| 删除仍被引用的 paper | 是 | `ON DELETE RESTRICT` 经 files 层传递 |
| 删除仍被 chunk 引用的 file | 是 | `fk_paper_chunks_file_revision` 的 RESTRICT |

完整性经链条传递，直连外键确属冗余。

### 迁移的可逆性

`downgrade` 恢复原状：4 条外键改回 `ON UPDATE NO ACTION`，重建 2 条直连外键。

**注意**：`downgrade` 前必须确认库中不存在 `content_revision > 1` 的论文——恢复 RESTRICT 后这些论文的血缘数据虽然一致，但后续无法再升版。迁移脚本的 `downgrade` 应在检测到升版论文时报错而非静默执行。

### 迁移风险

改外键需要 `DROP` 再 `ADD`，MySQL 在此期间对表加元数据锁。当前三张表的数据量为 `paper_files` 约 0 条、`paper_chunks` 约 2.8 万条、`paper_evidences` 少量，锁持有时间可忽略。

## 论文版本字段的状态转换

`papers` 的三个字段受检查约束 `ck_papers_review_revision` 联合约束：

```text
content_revision >= 1
AND (
  (review_status = 'approved' AND approved_revision = content_revision)
  OR
  (review_status IN ('pending', 'rejected') AND approved_revision IS NULL)
)
```

公开条件为 `review_status = 'approved' AND approved_revision = content_revision`。

### 待审核论文保存科学数据

| 字段 | 保存前 | 保存后 |
| --- | --- | --- |
| `content_revision` | N | N（不变） |
| `approved_revision` | NULL | NULL |
| `review_status` | `pending` | `pending` |

科学实体在同一版本号 N 下被删除重建。不触发级联（版本号未变）。约束始终成立。

### 已批准论文保存科学数据（升版）

| 字段 | 保存前 | 保存后 |
| --- | --- | --- |
| `content_revision` | N | N+1 |
| `approved_revision` | N | NULL |
| `review_status` | `approved` | `pending` |

**三个字段必须在同一条 UPDATE 中一起写入**。分多条语句会产生违约的中间状态——例如只递增 `content_revision` 时，`approved_revision(N) != content_revision(N+1)` 且状态仍为 `approved`，违反约束（[research.md](research.md) R7）。

这条 UPDATE 同时触发外键级联，把 `paper_files`、`paper_chunks`、`paper_evidences`、`material_states` 的 `paper_revision` 全部更新为 N+1。

升版后公开条件不再成立（`approved_revision` 为 NULL），论文自动下架。

### 升版后重新批准

走既有审核流程，`applyPaperReview` 在批准时设置 `approved_revision = content_revision`（`goserver/handlers/admin.go:379-381` 的既有逻辑），公开条件重新成立。

## 升版的写库次序

```text
1. 按依赖逆序删除科学实体（6 步，见下）
2. UPDATE papers SET content_revision = N+1,
                     approved_revision = NULL,
                     review_status = 'pending'
   WHERE id = ? AND content_revision = N
   → MySQL 级联更新 paper_files / paper_chunks / paper_evidences / material_states
3. 按新 revision 重建科学实体（persist_scientific_draft）
4. 写入 paper_review_events 升版记录
```

全部步骤在单一事务内。实测确认级联更新与主表更新一同回滚，任一步失败不留中间态。

**为何先删除再升版**：`material_states` 已受级联，若先升版则待删除的旧材料状态会被一并带到新 revision。删除按 `paper_id` 执行（不含 revision 条件），两种次序结果等价，但先删后升版的中间态更少、更直白。

## 科学实体的删除顺序

复用 `goserver/handlers/paper_deletion.go` 已验证的依赖逆序，共 6 步：

```text
1. tc_result_evidences, structure_model_evidences, superconductor_property_evidences
2. tc_results, superconductor_properties
3. calculation_contexts, experimental_contexts
4. structure_models：
   4a. UPDATE structure_models SET parent_structure_id = NULL
       WHERE paper_id = ? AND parent_structure_id IS NOT NULL
   4b. DELETE FROM structure_models WHERE paper_id = ?
5. DELETE FROM material_state_structure_families
   WHERE material_state_id IN (SELECT id FROM material_states WHERE paper_id = ?)
6. DELETE FROM material_states WHERE paper_id = ?
```

**第 4 步的自引用处理是必需的**：`structure_models.parent_structure_id` 自引用同表，同论文内父子结构的删除先后顺序不确定，不先置空会触发外键错误（`paper_deletion.go` 第 68–70 行注释已记录此坑）。

**第 5 步用子查询**：`material_state_structure_families` 无 `paper_id` 列，只能通过材料状态定位。

**删除范围按 `paper_id` 而非 `(paper_id, paper_revision)`**：科学实体在同一论文下只存在当前版本一份（升版是级联迁移而非分叉），按 `paper_id` 删除即可。这与 `paper_deletion.go` 的既有做法一致。

**与 `paper_deletion.go` 的差异**：该文件在第 6 步后还会清空 `paper_evidences`、`paper_chunks`、`paper_files`；本 Feature 完全不触碰这三张表。

## 校验规则

科学数据保存复用上传提交的既有校验（`backend/api/rag.py` 的 `_validate_draft`），不另立规则：

| 规则 | 来源 | 违反时 |
| --- | --- | --- |
| 非综述论文至少一个材料状态 | `_validate_draft` | 400 拒绝 |
| 每个材料状态必须有化学式 | `_validate_draft` | 400 拒绝，错误含材料状态序号 |
| 非综述论文每个材料状态必须有材料家族 | `_validate_draft` | 400 拒绝 |
| 材料维度必须为合法枚举 | `persist_scientific_draft` | 抛错回滚 |
| 压强区间 min 不大于 max | `_validate_draft` | 400 拒绝 |
| 超导类型、晶系非法值回退 unknown | `persist_scientific_draft` | 静默回退（既有行为） |

**综述论文可以没有材料状态**：管理员把材料状态全部删除后保存，若论文类型为综述则合法（Spec 边界场景）。

## 事务边界

单一事务覆盖：删除科学实体 → 更新论文版本字段（触发级联）→ 重建科学实体 → 写审核事件。

任一步失败则整体回滚，论文保持原版本号、原审核状态、原科学数据，血缘数据的 `paper_revision` 也一同回滚，且论文仍然对外公开（FR-018、US4 场景 7）。

**不跨服务**：论文级字段的保存走 Go 的独立接口与独立事务，两者不构成分布式事务（[research.md](research.md) R2）。

## 不涉及的变更

- 不新增表、列。
- 不改唯一约束（`uq_paper_files_main`、`uq_paper_files_path`、`uq_paper_files_order` 等全部保持原样）。
- 不改检查约束（含 `ck_papers_review_revision`）。
- 不改 ORM 模型字段——外键规则不体现在 SQLAlchemy 与 GORM 的字段声明中。
- 不改动 `superconductors`、`material_families`、`structure_families`、`property_definitions` 的任何行。
