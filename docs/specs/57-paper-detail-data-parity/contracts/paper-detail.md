# 接口契约：论文详情与记录搜索

**Feature**：[spec.md](../spec.md)

**日期**：2026-08-27

## GET /api/papers/{id}

权限判定不变（#56 已确立）：匿名仅 `approved`；登录用户可看 `approved`/`pending`；上传者另可看自己的 `rejected` 与 `review_comment`；管理员可看全部及 `admin_internal_note`。

### 响应结构（本 Feature 影响的部分）

```json
{
  "id": 4,
  "title": "...",
  "key_properties": [
    {
      "id": 1,
      "paper_id": 4,
      "material": "LaH10",
      "name": "thermodynamic stability",
      "name_raw": "thermodynamic stability",
      "value_raw": "0",
      "value_number": 200,
      "value_min": null,
      "value_max": null,
      "unit": "meV/atom",
      "canonical_unit": "meV/atom",
      "condition_note": null
    }
  ],
  "material_states": [
    {
      "id": 1,
      "material": "LaH10",
      "material_family": { "id": 1, "name": "...", "status": "confirmed" },
      "structure_families": [],
      "element_count": 2,
      "material_dimensionality": "bulk",
      "superconductor_kind": "unknown",
      "crystal_system": "cubic",
      "state_kind": "theoretical",
      "pressure_value_gpa": 250,
      "pressure_min_gpa": 200,
      "pressure_max_gpa": null,
      "pressure_raw": "above 200 GPa",
      "pressure_unit_raw": null,
      "reported_space_group_symbol": "Fm-3m",
      "reported_space_group_number": 225,
      "temperature_value_k": null,
      "temperature_raw": null,
      "magnetic_field_t": null,
      "note": null,
      "tc_results": [
        {
          "id": 1,
          "result_kind": "theoretical",
          "tc_method": "unknown",
          "tc_method_custom": null,
          "tc_value_k": 274,
          "tc_min_k": null,
          "tc_max_k": null,
          "uncertainty_k": null,
          "value_raw": "274",
          "unit_raw": "K",
          "source_locator": null
        }
      ],
      "calculation_contexts": [
        { "id": 1, "lambda_ep": null, "mu_star": null, "omega_log_k": null },
        { "id": 2, "lambda_ep": 2.56, "mu_star": 0.1, "omega_log_k": null }
      ]
    }
  ]
}
```

### 契约规则

| 规则 | 说明 |
|---|---|
| 空集合而非缺失键 | 论文无 Tc 结果或计算上下文时，`tc_results`/`calculation_contexts` 为 `[]`，不省略键、不为 null。消费方无需区分两种「无数据」形态。 |
| NULL 原样透出 | 可选数值字段在库中为 NULL 时返回 `null`，不转 0、不转空字符串。使「无上限」与「上限为 0」可区分。 |
| 单臂区间保持 | `pressure_min_gpa` 与 `pressure_max_gpa` 只有一侧有值时，另一侧为 `null`。沿用 #54 入库语义，读取侧不补造边界。 |
| 多条计算上下文全返回 | 同一材料状态可有多条，含全为 NULL 的记录。读取侧不筛选、不合并，不擅自判定哪条有效。 |
| 物性名称非空 | `name` 取 `property_definitions.display_name`，缺失时回退 `name_raw`。两者皆空的记录在写入侧不应存在。 |
| 原文值与解析值并存 | `value_raw` 与 `value_number` 都返回，可能不一致（论文 4 为 `"0"` 与 200）。展示优先级由消费方决定，本接口不裁决。 |
| 已移除字段不得出现 | 响应中不含 `superconductor_id`、`name_note`、`pressure_gpa`、`temperature_k`、`condition_json`、`is_primary`、`superconductor_type`、`article_type`、`source_label`、`structure_text`、`structure_format`。 |

## POST /api/papers/search/records

### 修复前实测行为

```
请求：{"elements": [], "limit": 5}
响应：{"items": [], "total": 0}
日志：Error 1146 (42S02): Table 'scwiki.key_properties' doesn't exist
```

无论库中有多少已批准论文，结果恒为空。

### 修复后契约

记录主体为 Tc 结果，一行代表「一个材料在一组条件下的一个 Tc」，与修复前的用户可见语义一致，前端结果表结构无需改动。

| 请求字段 | 求值来源 |
|---|---|
| `elements`、`formula`、`mode` | `material_states.superconductor_id`（经 `superconductors` 元素匹配） |
| `keyword` | `papers.title` / `doi` / `journal`，或材料化学式 |
| `year_min`、`year_max` | `papers.year` |
| `tc_min`、`tc_max` | `tc_results.tc_value_k` |
| `pressure_min`、`pressure_max` | `material_states.pressure_value_gpa` |
| `superconductor_type` | `material_states.state_kind` |
| `chart_only` | 不再支持（新模型无主记录语义），传入时忽略 |

响应行字段来源：

| 字段 | 来源 |
|---|---|
| `record_id` | `tc_results.id` |
| `paper_id`、`year`、`doi`、`status` | `papers` |
| `formula` | 材料化学式 |
| `type` | `material_states.state_kind` |
| `pressure` | `material_states.pressure_value_gpa`，格式 `<值> GPa`，无值为 `-` |
| `tc` | `tc_results.tc_value_k`，有区间时 `<min>–<max> K`，无值为 `-` |
| `space_group` | `material_states.reported_space_group_symbol`，无值为 `-`（此前硬编码 `-`） |

**不变约束**：仅返回 `papers.review_status='approved'` 的记录。这是既有的公开数据边界，本 Feature 不放宽。

## 管理员物性写入

`PUT` 论文时 `key_properties[]` 的可接受字段收敛为真实列：

**接受**：`id`、`material`、`name_raw`、`value_raw`、`value_number`、`value_min`、`value_max`、`unit`、`canonical_unit`、`condition_note`、`_deleted`

**不再接受**：`name`、`name_note`、`pressure_gpa`、`temperature_k`、`is_primary`、`article_type`、`condition_json`、`structure_text`、`structure_format`

修复前这些字段被接受后静默丢弃（新建路径经 `gorm:"-"` 丢弃，更新路径会拼出不存在的列名）。修复后不接受，避免管理员误以为改动已保存。物性名称由 `name_raw` 承载；条件类字段属材料状态，不经物性接口修改。
