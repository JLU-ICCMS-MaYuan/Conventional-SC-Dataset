# 接口契约：提交审核压强区间校验与草稿保存语义修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## 校验行为矩阵（PUT draft vs submit）

| 校验码 | 触发 | PUT（partial） | submit（strict） |
|--------|------|----------------|------------------|
| `invalid_draft` | 草稿 JSON 结构损坏 | 400 | 400 |
| `title_required`、`invalid_doi`、`paper_type_required`、`theoretical_subtype_required` | 论文级字段缺失/非法 | 放行 | 400 |
| `research_material_required`、`material_state_required`、`state_material_required` | 材料缺失 | 放行 | 400 |
| `invalid_material_family`、`multiple_primary_structure_families` | 分类非法 | 放行 | 400 |
| `invalid_space_group_number` | 群号非 1–230 | 放行 | 400 |
| `invalid_calculation_parameter` | λ/ωlog/μ\* 为负 | 放行 | 400 |
| **`invalid_pressure_range`（新增）** | 双臂 min>max | 放行 | **400** |
| `invalid_tc_result_kind`、`tc_value_required` | Tc 半成品 | 放行 | 400 |
| `property_name_required`、`dedicated_property_required`、`property_value_required` | 物性半成品 | 放行 | 400 |
| `structure_representation_missing` | 结构候选缺惯用胞 CIF | 放行 | 400 |

## 错误响应体

- 结构：`{"detail": {"code": "...", "message": "..."}}`（`_upload_error` 产生）；裸字符串 detail 也可能出现（其他 HTTPException）。
- 新增 `invalid_pressure_range` message 格式：「第 N 个材料状态的压强区间 min 不能大于 max」。
- 前端契约：横幅显示 `detail.message`（对象形态附 code），区分「保存失败/提交失败」前缀；无 detail 回退通用文案。

## 入库契约

- `material_states.pressure_min_gpa/max_gpa`：单臂（恰一臂为 NULL）合法入库，语义 min-only=≥、max-only=≤。
- 数值解析：校验与入库共用 `_number` 语义（先 float 再正则提取），保证「校验放行即可入库」。
