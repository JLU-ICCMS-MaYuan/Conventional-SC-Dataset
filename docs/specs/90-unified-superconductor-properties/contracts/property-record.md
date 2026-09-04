# 契约：`SuperconductorPropertyRecord`

## 适用接口

本契约适用于：

- 上传任务草稿读取与保存；
- 上传任务正式提交；
- 管理员论文科学数据读取与整体重写；
- 论文详情及其探索页、社区页消费的物性投影。

所有接口在 `material_states[]` 下使用同一个字段：

```json
{
  "material_states": [
    {
      "material": "LaH10",
      "superconductor_properties": []
    }
  ]
}
```

新响应不得同时输出 `tc_results`、`calculation_contexts`、`experimental_contexts`、
`properties` 或顶层 `key_properties` 作为第二份科学事实。

## 完整记录结构

```json
{
  "record_key": "property-1",
  "property_code": "tc",
  "name_raw": "critical temperature",
  "value_kind": "number",
  "value_raw": "250 K",
  "value_number": 250,
  "value_min": null,
  "value_max": null,
  "uncertainty": 5,
  "unit_raw": "K",
  "canonical_unit": "K",
  "method_raw": "Allen-Dynes equation",
  "criterion": null,
  "condition_note": null,
  "structure_ref": "structure-1",
  "context": {
    "context_key": "calc-a",
    "kind": "calculation",
    "structure_ref": "structure-1",
    "missing_structure_reason": null,
    "calculation_details": {
      "electronic_method": "DFT",
      "exchange_correlation": "PBE",
      "pseudopotential_type": "PAW",
      "pseudopotential_name": null,
      "spin_orbit_coupling": false,
      "phonon_method": "DFPT",
      "phonon_nuclear_treatment": "harmonic",
      "epc_method": "isotropic",
      "k_grid": "24x24x24",
      "q_grid": "6x6x6",
      "energy_cutoff_value": 80,
      "energy_cutoff_unit": "Ry",
      "calculation_code": "Quantum ESPRESSO",
      "parameters": null
    },
    "experimental_details": null
  },
  "tc_method": "allen_dynes",
  "tc_method_custom": null,
  "result_kind": "theoretical",
  "is_representative": true,
  "evidences": [
    {
      "section": "Results",
      "page": 5,
      "quote": "Tc reaches 250 K for mu*=0.10."
    }
  ]
}
```

## 同一 Context 下的平级参数

λ、ωlog、μ* 各自是独立记录。它们可以携带与 Tc 完全相同的 Context：

```json
[
  {
    "record_key": "property-tc-a",
    "property_code": "tc",
    "name_raw": "Tc",
    "value_kind": "number",
    "value_raw": "250 K",
    "value_number": 250,
    "unit_raw": "K",
    "canonical_unit": "K",
    "context": { "context_key": "calc-a", "kind": "calculation" },
    "tc_method": "allen_dynes",
    "result_kind": "theoretical",
    "is_representative": true,
    "evidences": []
  },
  {
    "record_key": "property-lambda-a",
    "property_code": "lambda_ep",
    "name_raw": "electron-phonon coupling constant",
    "value_kind": "number",
    "value_raw": "2.2",
    "value_number": 2.2,
    "unit_raw": null,
    "canonical_unit": null,
    "context": { "context_key": "calc-a", "kind": "calculation" },
    "tc_method": null,
    "result_kind": null,
    "is_representative": null,
    "evidences": []
  },
  {
    "record_key": "property-mu-a",
    "property_code": "mu_star",
    "name_raw": "Coulomb pseudopotential",
    "value_kind": "number",
    "value_raw": "0.10",
    "value_number": 0.1,
    "unit_raw": null,
    "canonical_unit": null,
    "context": { "context_key": "calc-a", "kind": "calculation" },
    "tc_method": null,
    "result_kind": null,
    "is_representative": null,
    "evidences": []
  }
]
```

示例为突出关联而省略了值为 null 的公共字段及重复的 Context 详情。正式请求/响应必须使用
稳定字段集合；同一 `context_key` 在多条记录中出现时，重复的 Context 详情必须完全一致。
数组为空时返回 `[]`，可空对象返回 `null`。

## Context 复用规则

- `context_key` 是草稿/API 范围内的关联键，不是数据库主键。
- UI 可以自动生成和维护该键，不提供要求用户输入 ID 的控件。
- 相同 `context_key` 的 `kind`、结构和详情必须一致。
- 后端把相同键解析为同一个持久化 Context。
- Context 为空时 `context` 为 `null`，记录仍是合法的平级物性。
- `result_kind` 由 `tc_method` 推导并可在读取响应中返回；新请求即使携带该字段，也不能覆盖推导结果。
- `tc_method=unknown` 只允许兼容读取或未提交草稿，正式提交必须先选定方法。
- `method_raw` 与 `criterion` 描述当前结果本身；Context 中只保留可由多条结果共享的方法环境和实验条件。

## 校验错误

校验错误继续返回可定位字段路径，例如：

```json
{
  "detail": "科学数据校验失败",
  "issues": [
    {
      "field": "material_states[0].superconductor_properties[3].context",
      "code": "conflicting_context",
      "message": "context_key=calc-a 的内容与第 0 条物性不一致"
    }
  ]
}
```

至少覆盖以下错误代码：

| code | 条件 |
| --- | --- |
| `missing_property_code` | 缺少物性代码且无法由原始名称安全映射 |
| `invalid_property_value` | 值类型、数值或范围不满足规则 |
| `conflicting_context` | 同一 Context 键出现互相冲突的详情 |
| `cross_state_context` | Context 被跨材料状态复用 |
| `invalid_tc_method_context` | Tc 方法与计算/实验 Context 不一致 |
| `duplicate_representative_tc` | 同状态同方法出现多条代表 Tc |
| `cross_revision_evidence` | Evidence 不属于当前论文 revision |

## 兼容边界

旧字段只作为输入兼容：

```text
tc_results[]                  → property_code=tc
calculation_context.lambda_ep → property_code=lambda_ep
calculation_context.omega_log_k → property_code=omega_log
calculation_context.mu_star   → property_code=mu_star
properties[] / key_properties[] → 对应 property_code
```

如果新通用物性行已经表达某个 Context 下的 λ、ωlog 或 μ*，兼容器不得再从旧 Context 字段
产生重复记录。新保存结果只输出 `superconductor_properties[]`。
