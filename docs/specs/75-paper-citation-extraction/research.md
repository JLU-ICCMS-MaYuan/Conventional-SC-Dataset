# 技术研究：材料状态「材料」字段改名为「化学式」

**GitHub Issue**：[#75](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/75)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md)

本文件只记录本 Feature 内的技术决策。

## R1：只改展示标签，不改字段名与列名

**决策**：改动界面标签与校验文案；`material` 字段名、`superconductors.chemical_formula`、`superconductor_properties.material_raw` 列名全部保持不变。

**理由**：

- 改 JSON 字段名需同步前端组件、Go 白名单与序列化、Python 校验与落库、LLM prompt 返回结构，以及 `data/review_artifacts/` 下已存在的草稿快照（`ai_values`、`user_values` 结构含 `material` 键）。旧快照无法回溯改名，会造成审核页读不到值。
- 改列名需要 Alembic 迁移，且 `material_raw` 的语义确实是「原文材料名」而非化学式——它保存论文里对材料的原始称法（如 `lead wire`），与 `chemical_formula` 是两个不同的量。改名反而会引入错误语义。
- 用户诉求是「界面标签让人知道该填什么」，标签层改动即完全满足，收益与风险比最优。

**备选方案**：

- **同步改字段名为 `chemical_formula`**：波及 5 类代码与历史快照，且需处理新旧键兼容期。已拒绝。
- **改列名**：迁移风险大，且 `material_raw` 语义本就不是化学式。已拒绝。

**证据**：`backend/ingest/scientific_drafts.py:220` 的 `state_data.get("material")` → `_get_or_create_superconductor`；`goserver/models/models.go:425` 的 `Material string gorm:"column:material_raw"`；`backend/api/rag.py` 的 review artifact 快照结构。

## R2：排除图表组合编辑器的「材料名」标签

**决策**：`frontend/src/components/ChartGroupEditor.tsx:490` 的「材料名」标签不改动。

**理由**：

该输入框绑定 `customLabel` 状态，提交时同时写入两个字段：

```ts
// ChartGroupEditor.tsx:230-235
material: customLabel.trim(),
custom_label: customLabel.trim(),
```

它的用途是「图表上自定义数据点的显示标签」，读取时也按 `it.material ?? it.custom_label ?? ''` 回退（第 113、151 行）。用户在此填 `LaH10 @ 200GPa`、`Nb3Sn (bulk)` 这类带条件说明的标签是合理用法，该值不经过 `_get_or_create_superconductor`，不落 `superconductors.chemical_formula`。

改名为「化学式」会错误地暗示只能填纯化学式，缩小合法输入范围，属于需求理解偏差而非改进。

**备选方案**：一并改为「化学式」（Issue #75 正文的原始描述）。经代码核查后拒绝，理由如上，已记入 Spec 澄清记录与范围外事项。

**证据**：`frontend/src/components/ChartGroupEditor.tsx:113`、`151`、`222`、`230-235`、`269`、`490`；`goserver/models/models.go:492` 的 `CustomLabel *string`。

## R3：校验文案只改后半句，保留序号前缀

**决策**：`backend/api/rag.py:254` 的文案由「第 N 个材料状态缺少材料」改为「第 N 个材料状态缺少化学式」，前缀「第 N 个材料状态」原样保留。

**理由**：

前端靠该前缀定位出错卡片：

```ts
// UploadTaskEditor.tsx:147-152
const stateIndexFromMessage = (message: string): number | undefined => {
  const matched = /第\s*(\d+)\s*个材料状态/.exec(message)
  ...
}
```

该函数的注释已明确写出这是「依赖后端文案」的耦合，且「由测试固定，文案变更时测试会立即失败」。改前缀会使定位静默失效——错误横幅仍显示，但不再滚动定位到出错卡片，用户在多材料状态的长表单中难以找到问题所在。

**同文件的相邻文案**：第 262 行「第 N 个材料状态缺少材料家族」不改动——「材料家族」语义正确（FR-008）。

**备选方案**：

- **改为结构化错误码 + 前端组装文案**：能彻底解除文案耦合，是更好的长期设计，但属于独立重构，超出本 Feature 范围。可作为后续 Issue 候选。
- **前端改用字段路径而非文案定位**：后端已在部分错误中返回字段路径，但 `state_material_required` 当前不返回。同上，属独立改动。

**证据**：`backend/api/rag.py:254`、`262`；`frontend/src/components/UploadTaskEditor.tsx:144-152`（含耦合说明注释）。

## R4：受影响的测试断言需同步

**决策**：改文案的同时更新 `tests/01_decentralized_uploading/submit-validation-feedback.test.tsx` 中的相关断言。

**理由**：该测试有 3 处断言直接匹配「第 N 个材料状态缺少材料」这类文案，用于验证横幅内容与定位锚点。文案改动后断言必然失败——这正是 R3 所说的「测试会立即失败」的保护机制在起作用，属预期行为，需同步更新而非绕过。

**注意**：更新断言时只改「材料」→「化学式」部分，序号前缀的断言必须保留，否则失去对 R3 耦合的保护。

**证据**：`tests/01_decentralized_uploading/submit-validation-feedback.test.tsx` 中含「第 3 个材料状态」「第 1 个材料状态」的断言。

## R5：新标签直接以双语字典编写

**决策**：两处标签改名直接写入 Issue #74 建立的 `frontend/src/i18n/{zh,en}/upload.ts` 与 `admin.ts` 字典，不先写中文硬编码。

**理由**：#74 的 i18n 基建先行落地是既定顺序（Spec 假设与依赖）。若本 Feature 先写中文硬编码，#74 的文案替换会再改一遍同一处，产生无谓返工。

**依赖前提**：#74 的阶段 2（基础能力）与涉及 `upload.ts`、`admin.ts` 的文案替换任务需先完成。

**证据**：`docs/specs/74-site-wide-i18n/tasks.md` 的 T017、T018、T019 覆盖这两个字典文件。

## 未决事项

无。Spec 的唯一前提纠正（排除第三处标签）已完成代码核查并记入澄清记录。
