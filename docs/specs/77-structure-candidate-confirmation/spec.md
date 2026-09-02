# Feature 规格：未分配结构候选的分配与确认交互

**GitHub Issue**：[#77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)

**创建日期**：2026-09-02

**状态**：草稿

## 背景与目标

随上传任务附带的结构文件（CIF/POSCAR/VASP）在解析阶段会生成结构候选，`material_state_ref` 为 `unassigned:<file_id>`（`backend/ingest/upload_jobs.py:1349`、`backend/ingest/structure_extractor.py`）。后端测试 `test_normalize_draft_preserves_structure_candidates_for_user_confirmation` 明确期待这些候选「保留给用户确认」。

但前端从未实现这一确认入口：`MaterialStatesEditor` 与 `StructureCandidatePanel` 只按 `material_state_ref === "material_states[N]"` 过滤候选，`unassigned:*` 候选从不显示，用户无法「采用」；提交时 `_confirmed_candidates_by_state`（`backend/ingest/scientific_drafts.py:50`）只接受 `material_state_ref` 为 `material_states[N]` 且 `confirmation=confirmed` 的候选写 `structure_models`。

**实证后果**：全库 `structure_models` 0 条。已审核通过的 Hg 论文（`papers.id=9`）的 `Hg-R-3m.vasp` 附件存在于 `paper_files` 与磁盘，但从未落库，详情页 3D 结构展示永远为空。

本 Feature 在共享组件 `MaterialStatesEditor` 中补齐「未分配结构候选」的展示、分配与确认交互，使随任务上传的结构可被正常采用落库；并把已审核论文的存量结构数据恢复，使详情页 3D 展示生效。

## 用户场景与验收

### 用户故事 1：上传者确认随任务上传的结构（优先级：P1）

上传者在校对页看到随任务上传的结构附件生成的候选，把它分配到对应材料状态并确认，提交后结构落库、详情页可 3D 展示。

**优先级理由**：这是本 Feature 的核心价值。随任务上传结构是当前唯一的上传路径（校对页单传是 #76 的补传能力），缺确认入口则结构永远进不了 `structure_models`。

**独立验收**：上传一篇带 VASP 附件的任务，解析完成后校对页出现「未分配结构候选」区；把候选分配到材料状态并确认后，提交落库，详情页 3D 渲染该结构。

**验收场景**：

1. **假如** 任务解析完成且存在 `unassigned:*` 结构候选，**当** 打开校对页，**那么** 出现「未分配结构候选」区域，候选可见（文件名、校验状态）。
2. **假如** 论文有至少一个材料状态，**当** 选择目标材料状态并点击「采用」，**那么** 候选的 `material_state_ref` 变为 `material_states[N]`、`confirmation/status` 变为 `confirmed`，并出现在对应材料状态的候选面板中。
3. **假如** 论文没有材料状态（如综述论文），**当** 尝试分配，**那么** 提示先创建材料状态，禁止分配。
4. **假如** 候选校验失败（`status=blocked`），**当** 尝试采用，**那么** 「采用」不可用并提示校验失败原因。
5. **假如** 用户不想保留某候选，**当** 点击「排除」，**那么** 该候选不再参与提交。
6. **假如** 提交草稿，**当** 落库，**那么** `structure_models` 写入对应记录（沿用 `_confirmed_candidates_by_state`），详情页 3D 结构可见。

### 用户故事 2：管理员在校对/编辑中确认结构（优先级：P2）

管理员在编辑弹窗（管理端）看到同一批未分配候选，可同样分配确认。

**优先级理由**：管理端与上传页共用 `MaterialStatesEditor`，交互随共享组件自然获得；单独价值低于上传路径，故排 P2。

**独立验收**：管理端编辑弹窗出现「未分配结构候选」区，可分配到材料状态并确认，保存后随 C1 提交落库。

**验收场景**：

1. **假如** 管理员打开编辑弹窗且论文存在未分配候选，**当** 查看，**那么** 出现与上传页一致的未分配候选区。
2. **假如** 管理员分配并确认候选后保存，**当** 请求发出，**那么** C1 body 的 `structure_candidates` 含该候选（`material_states[N]` + confirmed），落库后详情页可见。

### 用户故事 3：存量结构数据恢复（优先级：P2）

已审核论文（`papers.id=9`）的 Hg 结构附件恢复为 `structure_models` 记录，详情页 3D 展示生效。

**优先级理由**：存量数据修复，用于验收与说明本 Feature 的价值；不阻塞新上传链路。

**独立验收**：`papers.id=9` 的详情页展示 Hg 的 3D 结构。

**验收场景**：

1. **假如** 查看已审核的 Hg 论文详情，**当** 打开材料状态结构区，**那么** 3D 结构可见（来自恢复后的 `structure_models`）。

### 边界与异常场景

- 多个未分配候选：逐条分配，互不影响；候选 id 唯一。
- 分配后撤销：候选可从对应材料状态面板「恢复为待确认」（现有 `confirmation='unreviewed'` 交互），但 `material_state_ref` 保持 `material_states[N]`（不再回到 `unassigned`，避免来回搬移）。
- `readOnly` 模式：不渲染分配控件（只读详情不涉及确认）。
- 材料状态被删除后，其已分配候选的 `material_state_ref` 指向不存在的下标：提交时 `_confirmed_candidates_by_state` 找不到对应 state_index 会忽略该候选——沿用现有语义，不额外处理。
- 结构与正文混合的 PDF（`structure_extractor` 提取的候选同样为 `unassigned`）：同一交互覆盖。

## 需求

### 功能需求

- **FR-001**：上传校对页必须展示 `material_state_ref` 以 `unassigned:` 开头的结构候选。
- **FR-002**：上传者必须能把未分配候选分配到指定材料状态并确认（`material_state_ref` → `material_states[N]`、`confirmation/status` → `confirmed`）。
- **FR-003**：论文没有材料状态时，分配必须被禁止并提示先创建材料状态。
- **FR-004**：校验失败的候选（`status=blocked`）不得被确认，须展示失败原因。
- **FR-005**：候选可被「排除」（`confirmation=excluded`），不参与提交。
- **FR-006**：分配确认后的候选必须进入对应材料状态的候选面板，沿用既有预览/排除交互。
- **FR-007**：提交落库必须沿用 `_confirmed_candidates_by_state` 契约，后端不做改动。
- **FR-008**：管理端编辑弹窗必须与上传页共用同一分配交互（`MaterialStatesEditor`）。
- **FR-009**：`readOnly` 模式不得渲染分配控件。
- **FR-010**：存量论文 `papers.id=9` 的 Hg 结构必须恢复为 `structure_models` 记录并可在详情页展示。
- **FR-011**：既有上传校对页行为不得回退。

### 关键实体

- **未分配结构候选**：`material_state_ref` 为 `unassigned:<file_id>` 的结构候选，由任务解析生成，等待用户分配与确认。分配后变为「已确认结构候选」（`material_states[N]` + confirmed）。
- **已确认结构候选**：`material_state_ref` 为 `material_states[N]` 且 `confirmation/status` 为 `confirmed` 的候选；提交时由 `_confirmed_candidates_by_state` 写入 `structure_models`。

## 成功标准

- **SC-001**：随任务上传的结构附件经「分配 + 确认 + 提交」后 `structure_models` 出现对应记录。
- **SC-002**：详情页（上传者/管理员）用 3Dmol 渲染已落库的结构。
- **SC-003**：管理端编辑保存后结构不丢失（`candidateFromStructureModel` 与未分配候选分配交互共同保证）。
- **SC-004**：`papers.id=9` 恢复后详情页展示 Hg 3D 结构。
- **SC-005**：既有上传校对页自动化测试全部通过，无行为回归。

## 假设与依赖

- 依赖 [Issue #76](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/76) 已落地的共享组件 `MaterialStatesEditor`（上传页与管理端已共用）。
- 与 [Issue #49](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/49)（解析论文附件中的晶体结构并生成 CIF/POSCAR）衔接：#49 生成候选，本 Feature 提供候选的确认落库入口。
- 依赖 [Issue #74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74) 的 i18n 基建，新增文案走双语字典。
- 存量数据修复为一次性操作，不保留迁移脚本（沿用 #74 的 FR-017 先例）。
- `_confirmed_candidates_by_state` 的提交契约稳定，后端不改动。

## 范围外事项

- 修改结构解析/候选生成逻辑（`upload_jobs.py`、`structure_extractor.py` 的 `unassigned` 语义）。
- 自动分配（多材料状态时不做隐式猜测）。
- 修改 `structure_models` 表结构、详情接口契约或 `_confirmed_candidates_by_state`。
- 历史版本结构的浏览与回滚。
- 结构家族与分类批准工作流（仍走 #51 的审核确认）。

## 澄清记录

### 2026-09-02

- 问：分配后能否撤销回「未分配」？ → 答：不能。分配后 `material_state_ref` 保持 `material_states[N]`，撤销只把 `confirmation` 恢复为 `unreviewed`（候选仍在对应卡片的面板里，可重新确认或排除）。理由：候选的分配目标是明确的，来回搬移只会增加交互复杂度；后端 `_candidate_state_index` 也只认 `material_states[N]`。
- 问：`readOnly` 模式（详情只读展示）下未分配候选怎么处理？ → 答：不渲染分配控件。只读详情不涉及确认动作，且 `PaperDetailPage` 的只读路径不携带 `structureCandidates`（已落库结构走 `material_states[].structures`）。
- 问：存量数据恢复是否写脚本入库？ → 答：一次性数据修复，用现有结构工具（`build_structure_candidate`）生成候选并写 `structure_models`，不保留脚本（沿用 #74 先例）。
