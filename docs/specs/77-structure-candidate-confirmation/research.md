# 技术研究：未分配结构候选的分配与确认交互

**GitHub Issue**：[#77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)

本文件只记录本 Feature 内的技术决策。

## R1：分配交互放在前端共享组件，后端不改动

**决策**：全部交互逻辑（未分配候选区、分配、确认、排除）放在 `MaterialStatesEditor.tsx`，候选状态经既有的 `structureCandidates` / `onStructureCandidatesChange` 受控传递。后端 `_confirmed_candidates_by_state` 契约不变。

**理由**：

- `_confirmed_candidates_by_state`（`backend/ingest/scientific_drafts.py:50`）已支持「`material_states[N]` + confirmed」的候选写 `structure_models`——缺的只是前端把 `unassigned:*` 候选改成这个形态的入口。
- 管理端与上传页已共用 `MaterialStatesEditor`（#76），放共享组件使两处同时获得能力，符合 DRY。
- 后端改动（如提交时自动分配）属于隐式行为，违背「候选需用户确认」的既有设计（后端注释与测试都期待确认步骤）。

**备选方案**：

- **提交时后端把 unassigned+confirmed 候选自动分配到唯一材料状态**：隐式猜测，多材料状态时语义不清，且绕过用户确认。已拒绝。
- **在校对页外另建独立页面管理候选**：与材料状态编辑脱节，交互割裂。已拒绝。

**证据**：`scientific_drafts.py:50-60`；`MaterialStatesEditor.tsx` 的 `structureCandidates` props（#76 已接线）。

## R2：分配不可逆回「未分配」，撤销只回到 unreviewed

**决策**：候选一旦分配到 `material_states[N]`，`material_state_ref` 不再回到 `unassigned`；撤销只把 `confirmation` 恢复为 `unreviewed`（候选仍显示在对应卡片的候选面板）。

**理由**：

- `_candidate_state_index` 只认 `material_states[N]`，回到 `unassigned` 会使候选再次不可见、不可确认，形成死循环。
- 分配的「目标」是用户明确选择的，来回搬移无实际价值；`unreviewed` 状态已表达「尚未最终确认」。
- 与 `StructureCandidatePanel` 既有的「恢复为待确认」交互（`confirmation='unreviewed'`）一致。

**证据**：`scientific_drafts.py:44-48`；`StructureCandidatePanel.tsx:159`。

## R3：存量数据修复用现有结构工具一次性执行，不保留脚本

**决策**：`papers.id=9` 的 Hg 结构用 `build_structure_candidate` 从磁盘 VASP 生成候选，取 conventional CIF 写 `structure_models`；一次性执行，脚本不留库。

**理由**：

- 复用 `build_structure_candidate` 保证规范表示（conventional CIF）与校验口径与正常链路一致，不手工拼结构文本。
- 一次性数据修复不留脚本，避免被误认为可反复运行的正式功能（沿用 #74 FR-017 先例）。

**证据**：`backend/services/structure_candidates.py:206`；#74 的一次性脚本先例。

## R4：只渲染非 excluded 的未分配候选

**决策**：未分配候选区过滤掉 `confirmation === 'excluded'` 的候选；排除后立即从区中消失。

**理由**：排除是「不参与提交」的显式意图，继续显示会误导用户以为还需处理。需要恢复时从对应卡片面板或重新上传。

**证据**：`StructureCandidatePanel.tsx:25` 的既有排除语义。
