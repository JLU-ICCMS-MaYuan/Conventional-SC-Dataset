# 契约：模块化物性记录

## 接口范围

上传草稿、正式提交、管理员编辑和论文详情统一使用：

```text
material_states[].property_modules[].records[]
```

Conditions 位于同一材料状态下：

```text
material_states[].calculation_conditions[]
material_states[].experimental_conditions[]
```

记录使用 `condition_key` 引用 Conditions，不在每条记录中复制整份条件。

## 模块结构

```json
{
  "module_key": "module-superconductive-1",
  "module_code": "superconductive_properties",
  "definition_key": "module.superconductive_properties",
  "definition_version": 1,
  "display_order": 0,
  "records": []
}
```

允许的首批模块代码为 `superconductive_properties`、`dynamical_properties`、
`thermodynamical_properties` 和 `electronic_properties`。未添加的模块不输出空占位对象。

## 记录结构

```json
{
  "record_key": "record-tc-1",
  "module_code": "superconductive_properties",
  "record_type": "predicted_tc",
  "property_code": "tc",
  "definition_key": "superconductive_properties.predicted_tc",
  "definition_version": 2,
  "name_raw": "critical temperature",
  "value_kind": "number",
  "value_raw": "250 K",
  "value_number": 250,
  "value_min": null,
  "value_max": null,
  "uncertainty": 5,
  "unit_raw": "K",
  "canonical_unit": "K",
  "method_code": "allen_dynes",
  "method_raw": "Allen-Dynes equation",
  "criterion_code": null,
  "criterion_raw": null,
  "is_representative": true,
  "condition_key": "calc-a",
  "structure_key": null,
  "payload": {
    "solver_tolerance": "1e-8"
  },
  "evidences": []
}
```

## Tc 规则

- `predicted_tc` 必须满足 `property_code=tc`、理论 `method_code`、计算 Conditions。
- `measured_tc` 必须满足 `property_code=tc`、实验 `method_code`、实验 Conditions。
- 记录类型、方法和 Conditions 类型任一不匹配时拒绝正式提交。
- 切换记录类型或方法后，旧定义不允许的扩展字段必须显式转换、清除或返回错误。
- 同一论文 revision、材料状态、记录类型和方法最多一条代表 Tc。

## Schema 绑定

客户端读取定义：

```http
GET /api/form-definitions/{definition_key}/versions/{version}
GET /api/form-definitions/{definition_key}/current
```

记录必须携带 `definition_key` 和 `definition_version`。后端按该版本校验：

1. 定义目标类型、模块代码和记录类型是否匹配；
2. 固定字段的类型、单位和条件规则；
3. `payload` 是否符合 `json_schema`；
4. 同一 Conditions 下的记录是否符合 `group_rules`；
5. 定义是否允许新建或仅允许历史读取。

前端使用 `ui_schema` 决定控件和顺序，但后端不信任前端校验结果。

## Conditions 归组

```json
{
  "condition_key": "calc-a",
  "definition_key": "conditions.calculation",
  "definition_version": 1,
  "calculation_code": "Quantum ESPRESSO",
  "k_grid": "24x24x24",
  "payload": {}
}
```

- 一个 Conditions 对象表示一次确定的运行或测量。
- `condition_key` 在一个材料状态内唯一，由系统生成。
- 多条记录可共享该键；跨材料状态或跨 revision 引用无效。
- 决定性输入不同必须建立不同 Conditions。

## 错误格式

```json
{
  "detail": "科学数据校验失败",
  "issues": [
    {
      "field": "material_states[0].property_modules[0].records[2].payload.solver_tolerance",
      "code": "schema_validation_failed",
      "message": "字段不符合定义版本 2"
    }
  ]
}
```

稳定错误码至少包括：

| 错误码 | 含义 |
| --- | --- |
| `unknown_module` | 模块未注册 |
| `unknown_definition_version` | 定义键或版本不存在 |
| `definition_not_available` | 定义状态不允许新建 |
| `schema_checksum_mismatch` | 定义内容与校验和不一致 |
| `schema_validation_failed` | 固定字段或 `payload` 不符合定义 |
| `invalid_condition_type` | 记录类型与 Conditions 类型不匹配 |
| `conflicting_condition` | 同一条件键的内容冲突 |
| `condition_group_rule_failed` | 同一 Conditions 下的记录组合非法 |
| `duplicate_representative_tc` | 同范围存在多条代表 Tc |
| `cross_revision_reference` | Conditions、结构或 Evidence 跨 revision |

## 兼容边界

旧输入只在边界转换：

```text
tc_results[] -> superconductive_properties / predicted_tc 或 measured_tc
properties[] -> 定义映射后的目标模块 / property
calculation_contexts[] -> calculation_conditions[]
experimental_contexts[] -> experimental_conditions[]
```

新响应不输出旧字段作为第二份科学事实。无法确定目标模块或定义版本时进入明确的迁移异常报告，
不能静默归入“其他”。
