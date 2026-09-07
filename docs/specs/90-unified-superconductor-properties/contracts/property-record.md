# 契约：模块化物性记录

## 接口范围

上传草稿、正式提交、管理员编辑和论文详情统一使用：

```text
material_states[].property_modules[].records[]
```

Conditions 与输入参数直接内嵌在当前记录：

```text
material_states[].property_modules[].records[].payload.calculation_conditions
material_states[].property_modules[].records[].payload.experimental_conditions
material_states[].property_modules[].records[].payload.parameters
```

两类 Conditions 对象互斥。每条 Tc 自带资料，没有 `condition_key` 或 Tc 输入关联表。

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
每条记录只属于一个模块。空模块可以删除；保存请求若删除了已有的非空模块，却没有逐条提交其记录的
显式删除操作，则返回 `nonempty_module_delete`。

完整材料状态更新使用显式删除列表：

```json
{
  "deleted_record_keys": ["record-dos-1"],
  "deleted_module_keys": ["module-electronic-1"]
}
```

服务端先应用 `deleted_record_keys`，再验证 `deleted_module_keys` 对应模块已经为空。仅从提交数组中省略
已有记录或模块不表示删除，避免旧客户端或部分保存静默丢失数据。

## 记录结构

```json
{
  "record_key": "record-tc-1",
  "module_code": "superconductive_properties",
  "record_type": "predicted_tc",
  "property_code": "tc",
  "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
  "definition_version": 2,
  "name_raw": "critical temperature",
  "value_kind": "number",
  "value_raw": "250 K",
  "value_number": 250,
  "value_min": null,
  "value_max": null,
  "value_text": null,
  "value_boolean": null,
  "uncertainty": 5,
  "unit_raw": "K",
  "canonical_unit": "K",
  "method_code": "allen_dynes",
  "method_raw": "Allen-Dynes equation",
  "criterion_code": null,
  "criterion_raw": null,
  "is_representative": true,
  "structure_key": null,
  "payload": {
    "calculation_conditions": {"calculation_code": "Quantum ESPRESSO"},
    "parameters": {"mu_star": {"value_raw": "0.10", "value_number": 0.1, "unit": "1"}},
    "solver_tolerance": "1e-8"
  },
  "evidences": []
}
```

## 自定义性质与审核

已有模块的定义选择器提供已发布 `record.<module_code>.custom` 定义，允许用户显式选择自定义性质。
以下为突出新增字段而省略其他可空核心字段的示例，批准时 Evidence 必须解析为同 revision 的有效证据：

```json
{
  "record_key": "record-custom-1",
  "module_code": "electronic_properties",
  "record_type": "property",
  "property_code": "custom",
  "custom_property_key": "custom-opaque-1",
  "definition_key": "record.electronic_properties.custom",
  "definition_version": 1,
  "name_raw": "论文报告的新性质",
  "value_kind": "number",
  "value_raw": "1.25 eV",
  "value_number": 1.25,
  "unit_raw": "eV",
  "canonical_unit": null,
  "payload": {},
  "evidences": []
}
```

通用模板只接受已声明的核心字段和类型；数值原始单位可以保留为文本，不擅自换算或推断规范单位。
`name_raw` 必填且去首尾空白后非空，同键在同论文 revision/模块内必须具有一致性质含义和类型，
有冲突返回 `custom_property_conflict`。不同论文同名性质不共享身份。审核不要求生成全站定义；管理员
批准论文后自定义记录按原文展示，详情和搜索投影不得因其 `property_code=custom` 而遗漏。

用户选择已注册 Tc 或其他规范性质时仍使用专用定义，不允许以保留代码（例如 `tc`）配自定义定义绕过
约束。自定义同名科学语义由管理员审查，不宣称系统能自动判定。未提升的自定义记录不作为已规范化
Tc 图表点或跨论文同性质聚合依据。提升后的历史记录仍保持原自定义绑定，后续新记录可选择新定义。

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
4. 本条 Conditions、参数和预留扩展分组的类型、单位、条件必填及归属是否符合该记录版本；
5. 定义是否允许新建或仅允许历史读取。

前端使用 `ui_schema` 决定控件和顺序，但后端不信任前端校验结果。

## 记录内资料

- 计算或实验条件对象仅属于当前记录，随记录在同一事务保存、升版和删除。
- 当前 Tc 使用的 λ、ωlog、μ* 在 `payload.parameters` 中保存；已知参数用稳定代码，值为带类型和单位的对象。
- 复制记录必须复制内部资料，产生新 `record_key`，不能共享可变对象；修改、删除副本不改变原记录。
- 其他独立物性可保存自己的 Conditions；不从同名物性记录自动读取、配对或同步参数。
- 已报告的参数需保留原值及适用单位，未报告时留缺失；证据可精确到字段路径，不要求编造论文未提供的来源。
- 字段内 `evidences[]` 引用同 revision 的有效 Evidence，并纳入记录的证据集合；字段路径说明证据支持哪个参数，
  不把记录级 Tc 证据自动视为所有参数的证据。升版时一并重映射，导出时一并解析。

## 预设分组内新增字段

记录定义的 Schema 只在预设路径开放 `extensions[]`，例如 `payload.parameters.extensions`、
`payload.calculation_conditions.extensions`、`payload.experimental_conditions.extensions` 和
`payload.extensions`。方法定义决定哪些分组可用，前端不能任意创建新的分组路径。

用户在参数区点击新增，字段就属于该条记录的参数区；后端根据嵌套位置确认归属，不信任客户端另报的
分组名称。新增项使用已发布的通用字段结构：

```json
{
  "field_key": "field-local-1",
  "name_raw": "论文补充的计算参数",
  "value_kind": "number",
  "value_raw": "0.03 Ry",
  "value_number": 0.03,
  "unit_raw": "Ry",
  "evidences": []
}
```

`field_key` 由系统生成，在当前记录和分组内稳定唯一；`name_raw` 必须非空。同记录跨组移动必须显式
编辑并重新审核。支持 number/range/text/boolean 的互斥值字段及单位，不允许覆盖已注册系统字段、
借扩展伪装 Tc 核心值或绕过类型校验。记录内系统字段与新增项出现同名歧义时提示人工处理。

这些字段随论文审核，批准后按原分组永久保留在该 revision 的数据中，后续版本不得静默丢弃；
无需为每次提案发布新 Schema，也无需专门的字段关系表。审核退回允许修订；删除与修改遵守论文生命周期。
全站推广仍需显式发布新定义版本，不自动改变其他记录。模块级自定义性质提升继续按既有独立流程执行。

## 完整 MaterialState 导出

`GET /api/papers/{paper_id}/material-states/{state_key}/export` 返回带 `export_version=1` 的 JSON 数据包；
权限沿用论文读取，公开用户只能导出已批准内容，管理员审计信息不公开。

包内含论文来源与 revision、所属 ChemicalSystem/Superconductor 的材料资料、MaterialState 全部状态字段、
结构内容、全部物性模块及记录、每条记录内部 Conditions 和参数、Evidence 原文及定位、所有绑定的
FormDefinition 完整版本及校验和。记录/字段证据和结构引用必须能在包内解析；结构原文件采用带文件名、
媒体类型和校验和的内嵌内容表示，不能只输出本地路径或需联网下载的 URL。论文 PDF 本体不属于此数据导出。

导出使用同一 revision 快照读取；过程中 revision 变化则重试或返回冲突，不输出混合版本。
缺失本应存在的结构、证据、定义或文件时返回可定位的错误；历史未报告字段保留缺失及说明，不伪造资料。
下载得到完整数据包，用户无需另导关系表或访问在线定义服务。

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
| `invalid_extension_group` | 字段不在定义预留分组中 |
| `extension_field_conflict` | 扩展键重复或覆盖系统字段 |
| `export_incomplete` | 导出所需的已有资料无法解析 |
| `export_revision_conflict` | 导出过程中论文版本改变 |
| `duplicate_representative_tc` | 同范围存在多条代表 Tc |
| `nonempty_module_delete` | 未显式处理记录就删除非空模块 |
| `custom_property_conflict` | 同论文内自定义性质键的名称、类型或单位语义冲突 |
| `cross_revision_reference` | 结构或 Evidence 跨 revision |

## 兼容边界

旧输入只在边界转换：

```text
tc_results[] -> superconductive_properties / predicted_tc 或 measured_tc
properties[] -> 定义映射后的目标模块 / property
calculation_contexts[] -> 逐条复制到原使用记录的 payload.calculation_conditions
experimental_contexts[] -> 逐条复制到原使用记录的 payload.experimental_conditions
旧 Context 的 lambda/omega_log/mu_star -> 原使用 Tc 的 payload.parameters
```

新响应不输出旧字段作为第二份科学事实。无法确定目标模块或定义版本时进入明确的迁移异常报告，
不能静默归入“其他”。

旧共享条件按使用记录展开；无引用条件、来源不明或无法判定的参数必须进入可追溯保留/异常流程，禁止静默丢弃。
