# 接口契约：上传校对页布局重构与材料状态卡片完善

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 新增：GET /api/rag/space-groups

- **权限**：登录用户（与上传草稿接口一致）。
- **响应 200**：

```json
{
  "space_groups": [
    { "number": 1, "symbol": "P1" },
    { "number": 225, "symbol": "Fm-3m" }
  ]
}
```

- **语义**：恰好 230 条，按群号升序；符号为 spglib 国际符号（Hermann–Mauguin）。只读，无写入路径。
- **错误**：spglib 为声明依赖，模块导入失败属部署错误（fail-fast），正常部署下无运行时失败路径。

## 既有接口契约调整

### PUT /api/rag/upload-tasks/{task_id}/draft 与 GET .../draft

- 草稿 JSON 接受并返回 `material_states[].superconductor_kind`、`element_count_locked`、`tc_results[].calculation_context`、`tc_results[].tc_method_custom`（见 data-model.md）。
- `_validate_draft` 的非综述 `research_materials` 必填校验放宽为：草稿值与材料状态化学式汇总任一非空即通过；失败仍 400 `research_material_required`。

### POST /api/rag/upload-tasks/{task_id}/submit

- 请求体不变；服务端行为变化：
  - `research_materials` 由材料状态化学式去重汇总覆盖（汇总为空保留草稿原值）。
  - 常规 Tc 逐条创建 CalculationContext；`tc_method='other'` 时 `tc_method_custom` 入库。
  - `element_count` 优先草稿非空值。

### AI 汇总契约（SUMMARY_SYSTEM_PROMPT）

- `material_states[]` 新增 `"superconductor_kind": "conventional|unconventional|unknown"`（BCS/电声耦合机制判 conventional，无法判断 unknown）。
- `tc_results[].tc_method` 枚举扩为 `unknown|experimental|mcmillan|allen_dynes|isotropic_eliashberg|anisotropic_eliashberg|scdft|other`；`other` 时给 `tc_method_custom` 文本。
- `properties[]` 提取 energy above hull（单位 eV/atom）；论文明确 thermodynamically stable 时值为 0。
- CHUNK 契约与 `CHUNK_RESULT_SCHEMA_VERSION=5` 不变（D10）。

## 前端 UI 契约

- 空间群符号：MUI Autocomplete freeSolo；选中标准符号 → `reported_space_group_number` 自动填充；自由输入原样保存、群号可空。
- Tc 方法下拉：仅常规类型显示；「其他」出现文本框写 `tc_method_custom`；非常规/未知条目不显示方法与计算参数字段。
- 折叠状态仅存组件 state，不进入草稿 JSON。
