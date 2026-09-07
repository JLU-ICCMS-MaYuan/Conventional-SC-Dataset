# 数据模型：MaterialState 模块化物性

## 1. 领域结构

```text
PaperRevision
└── ChemicalSystems[]
    └── ChemicalSystem
        └── Superconductors[]
            └── Superconductor
                └── MaterialStates[]
                    └── MaterialState
                        ├── StructureModels[]
                        └── PropertyModules[]
                            └── PropertyModule
                                └── PropertyRecords[]
                                    └── PropertyRecord
                                        ├── 结果、方法、判据和证据
                                        └── payload：本条 Conditions、参数及预设扩展分组
```

这棵树表示论文科研数据的所有权。同名材料不跨论文共享：论文 A 与论文 B 的 LaH10 是两条
`Superconductor` 记录。规范化学式用于检索，不作为全库共享身份。

## 2. PropertyModule

| 字段 | 必填 | 含义 |
| --- | --- | --- |
| `module_key` | 是 | 当前材料状态中的稳定键，由系统生成 |
| `module_code` | 是 | 模块代码 |
| `definition_key` / `definition_version` | 是 | 模块自身使用的不可变定义版本 |
| `display_order` | 是 | 当前状态中的展示顺序 |
| `records[]` | 是 | 模块内平级记录，允许空数组 |

首批 `module_code`：

| 代码 | 中文含义 | 首批典型记录 |
| --- | --- | --- |
| `superconductive_properties` | 超导性质 | `predicted_tc`、`measured_tc`、Hc1/Hc2、能隙、临界电流、穿透深度、相干长度 |
| `dynamical_properties` | 动力学性质 | 声子稳定性、虚频、声子相关结果 |
| `thermodynamical_properties` | 热力学性质 | energy above hull、形成能、热容等 |
| `electronic_properties` | 电子性质 | DOS、费米能级附近电子结构等 |

模块是页面组织和扩展边界。每条 `PropertyRecord` 只属于一个模块；本 Feature 不建立跨模块记录引用。
删除空模块不影响其他模块，非空模块必须先显式处理其中记录。

## 3. PropertyRecord

### 3.1 固定核心字段

| 字段 | 必填 | 含义与约束 |
| --- | --- | --- |
| `record_key` | 是 | 请求和响应内稳定键；不暴露数据库主键 |
| `module_code` | 是 | 所属模块，必须与模块实例一致 |
| `record_type` | 是 | 例如 `predicted_tc`、`measured_tc`、`property` |
| `property_code` | 是 | 规范科学量代码，例如 `tc`、`lambda_ep`、`omega_log`、`mu_star`、`hc2` |
| `custom_property_key` | 条件必填 | `property_code=custom` 时必填的论文 revision 内性质键；通用性质记录为空 |
| `definition_key` | 是 | 使用的表单定义键 |
| `definition_version` | 是 | 使用的不可变定义版本 |
| `name_raw` | 是 | 论文原文名称 |
| `value_kind` | 是 | `number`、`range`、`text` 或 `boolean` |
| `value_raw` | 是 | 论文原始值文本 |
| `value_number` | 条件必填 | 单一规范数值 |
| `value_min` / `value_max` | 条件必填 | 完整规范范围 |
| `value_text` / `value_boolean` | 条件必填 | 文本或布尔规范值；与 `value_kind` 对应，其他类型置空 |
| `uncertainty` | 否 | 非负不确定度，与规范单位一致 |
| `unit_raw` / `canonical_unit` | 否 | 原文单位和规范单位 |
| `method_code` | 否 | 规范方法代码；Tc 必填 |
| `method_raw` | 否 | 论文中的原始方法文本 |
| `criterion_code` / `criterion_raw` | 否 | 规范判据及原文判据 |
| `is_representative` | 条件必填 | Tc 必填，其他记录默认空 |
| `structure_key` | 否 | 关联本论文 revision 当前材料状态中的结构 |
| `payload` | 是 | 符合定义版本的扩展 JSON；默认 `{}` |
| `evidences[]` | 是 | 当前论文 revision 的 Evidence；草稿可为空 |

固定列负责搜索、统计、关联、唯一约束和审计。`payload` 保存本条条件和参数，不得再次保存 Tc 数值、方法等固定列事实。若某扩展字段后来成为核心查询条件，需要用迁移提升为固定列，不能同时保留两个
可写来源。

### 3.2 Tc 记录

Tc 使用 `property_code=tc`，并按 `record_type` 分为：

| 记录类型 | Conditions | 方法示例 |
| --- | --- | --- |
| `predicted_tc` | 必须包含 `payload.calculation_conditions` | Allen-Dynes、McMillan、Eliashberg、SCDFT、自定义理论方法 |
| `measured_tc` | 必须包含 `payload.experimental_conditions` | 电阻、磁化率、比热或自定义实验方法 |

`method_code` 是具体方法权威，`record_type` 是预测/测量性质权威。二者必须匹配。`result_kind`
不再作为独立可写字段；兼容读取时由旧值映射到 `record_type`。

代表 Tc 唯一范围为：

```text
paper_id + paper_revision + material_state_id + record_type + method_code
```

同一范围最多一条 `is_representative=true`。

### 3.3 自定义性质

自定义性质仍为 `PropertyRecord`，固定使用 `record_type=property`、`property_code=custom`，按模块绑定
已发布的 `record.<module_code>.custom` 定义。性质名称保存在 `name_raw`，值和单位仍使用固定核心字段；
不把用户名称当作任意 JSON 键。`custom_property_key` 由系统生成，身份范围是论文 revision 和模块，
同一性质的多条测量可以共享该键；同键名称、值类型和单位语义必须一致，跨论文不按名称自动合并。
论文升版复制该键随其他科学事实一起归入新 revision。自定义记录没有独立审核状态，公开资格继承论文。

### 3.4 PropertyDefinitionPromotionEvent

全站提升不修改源记录，仅新增已发布 `FormDefinition` 和不可变提升事件。事件保存 operation_id、管理员、
时间、源论文 revision、源记录稳定键及快照、目标定义键/版本/校验和；operation_id 唯一。同一来源
论文/revision/模块/custom_property_key 最多成功提升一次；并发不同来源提升同一目标代码由全局唯一约束拒绝。
全站普通性质代码用定义键 `record.property.<property_code>` 定位，模块作为定义适用字段，不能通过换模块
重复注册同一代码。服务在单个事务内注册代码、
发布 v1 和保存事件。事件来源以快照留存，不建立阻止源论文升版或删除的强外键；目标定义不依赖源记录生存。

## 4. 记录内 Conditions 与参数

Conditions 和参数都是当前 `PropertyRecord.payload` 的组成部分，与结果在同一表单填写和保存。
记录定义的 `json_schema` 同时校验它们，不另建 Conditions 实例表、条件键或输入关系表。

| 路径 | 内容 |
| --- | --- |
| `payload.calculation_conditions` | 软件、电子方法、泛函、赝势、SOC、声子/EPC 方法、k/q 网格、k/q 各自展宽与单位、截断能及其他适用计算条件 |
| `payload.experimental_conditions` | 样品、制备方式、测量装置、外场、压力不确定度等实验条件 |
| `payload.parameters` | 当前预测 Tc 使用的 λ、ωlog、μ* 等结构化输入，保留原值、规范值、单位及可选字段证据 |
| 各定义预留的 `extensions[]` | 当前分组内用户新增字段的名称、类型、单位、值和证据 |

预测 Tc 必须具有计算 Conditions 对象，不得有实验 Conditions 对象；测量 Tc 反之。
普通物性可按定义携带至多一种条件。对象中未报告的可选字段允许缺失，不从结果反推。
状态压力、温度和结构归 MaterialState；当前计算的网格和展宽归该条记录。记录的可选 `structure_key`
只指向同状态结构，不在条件内再保存一个可冲突的结构引用。

一条预测 Tc 的 `parameters` 每个规范输入只有一个值或一个明确范围，不保存两个无法配对的候选值。
不同输入得到的多个 Tc 分别建立记录。不同记录参数可以完全相同；复制后修改一条不影响其他记录。
λ 等也可以作为独立报告的普通物性录入，但与任何 Tc 没有自动输入关系，不用其值回填或同步 Tc。

字段的预留分组和审核规则见[记录契约](contracts/property-record.md#预设分组内新增字段)。

## 5. FormDefinition

| 字段 | 含义 |
| --- | --- |
| `definition_key` | 完整目标的稳定键，例如 `record.superconductive_properties.predicted_tc.allen_dynes` |
| `version` | 从 1 开始单调递增；与键组成唯一标识 |
| `target_kind` | `property_module` 或 `property_record` |
| `module_code` | 模块或记录定义的适用模块 |
| `record_type` | 记录定义的适用记录类型；其他目标类型为空 |
| `method_code` | 可选；为空表示通用定义，非空表示方法扩展 |
| `property_code` | 记录定义适用的性质代码；其他目标类型为空；`custom` 是保留的论文内性质类型 |
| `core_schema` | 校验固定核心字段的声明式 Schema；与扩展 JSON 的 Schema 分开，二者共同绑定版本 |
| `json_schema` | 扩展字段的数据结构、类型、枚举和条件必填规则 |
| `ui_schema` | 控件、顺序、分组、标签键和单位提示；不拥有数据校验权威 |
| `status` | `draft`、`published`、`retired` |
| `checksum` | 定义内容校验和 |
| `created_by` / `created_at` | 创建审计信息 |
| `published_by` / `published_at` | 发布审计信息 |

状态规则：

```text
draft -> published -> retired
```

- `draft` 可修改，但不能用于正式记录。
- `published` 不可修改；修订必须创建下一版本。
- `retired` 可继续解释历史记录，但不用于新建记录。
- 新建模块或记录选择对应定义键最新的 `published` 版本，内嵌条件和参数随记录版本解释。
- 记录升级版本是显式操作，必须预览转换、重新验证并保留审计记录。

方法特有记录使用包含 `method_code` 的完整 `definition_key`，不把不同方法放在同一键的不同版本中。
版本只表达同一目标定义的演进，不能用版本号区分 Allen-Dynes、Eliashberg 等不同方法。

### 5.1 PropertyRecordDefinitionEvent

每次定义升级和回滚都记录不可变审计事件，至少包含论文与 revision、记录稳定键、操作类型、操作者、
操作时间、升级前后定义键与版本、升级前后核心字段及 `payload` 快照、请求校验和和前序事件 ID。
回滚不是修改历史事件，而是在当前论文编辑事务中创建反向事件；只有记录仍处于该事件产生的版本和
校验和时才允许执行。

JSON Schema 只允许声明式、安全的受限关键字；定义不能包含或执行脚本。后端校验是最终权威，
前端显示规则不能替代后端校验。

## 6. 物理表设计

目标核心表：

| 表 | 每行含义 |
| --- | --- |
| `chemical_systems` | 一篇论文 revision 中的一个元素体系 |
| `superconductors` | 一篇论文 revision 中的一种材料 |
| `material_states` | 该论文材料的一种研究状态 |
| `property_modules` | 状态中挂载的一个物性模块 |
| `property_records` | 模块中的一条科学事实 |
| `form_definitions` | 一份不可变版本化表单定义 |
| `property_record_definition_events` | 记录定义升级与回滚的不可变审计事件 |
| `property_definition_promotion_events` | 管理员把论文内自定义性质提升为全站定义的来源与操作快照 |
| `property_record_evidences` | 记录与 Evidence 的多对多连接 |

`property_records` 统一接收旧 `tc_results` 与 `superconductor_properties`。Tc 核心列保持专用 CHECK、
生成列、唯一索引和统计索引；不同记录类型不适用的专用列必须为空。旧表完成对账和观察期后退役。

持久化层把 Conditions、参数和分组扩展保存在当前记录的 `payload_json`。
CHECK 验证预测/测量对应的 JSON 条件对象存在且另一类不存在；类型、单位、适用性和必填字段由
记录绑定的 Schema 校验。Tc 的数值、方法和代表标记仍使用固定列。没有 Tc 输入关联表或 Conditions 外键。

`chemical_systems` 和 `superconductors` 增加 `paper_id + paper_revision` 归属，唯一键从全库唯一调整为：

```text
chemical_systems: paper_id + paper_revision + system_key
superconductors:   paper_id + paper_revision + composition_key
```

所有从 `Superconductor` 到 `MaterialState` 的关系使用同论文 revision 复合外键，禁止跨论文引用。

## 7. API 结构示例

以下 LaH10 数据仅示意归属，不代表论文实测数据或 Allen-Dynes 公式验算；完整核心字段见记录契约。

```json
{
  "material_states": [
    {
      "state_key": "state-1",
      "property_modules": [
        {
          "module_code": "superconductive_properties",
          "records": [
            {
              "record_key": "tc-a",
              "record_type": "predicted_tc",
              "property_code": "tc",
              "definition_key": "record.superconductive_properties.predicted_tc.allen_dynes",
              "definition_version": 1,
              "value_kind": "number",
              "value_raw": "250 K",
              "value_number": 250,
              "canonical_unit": "K",
              "method_code": "allen_dynes",
              "payload": {
                "calculation_conditions": {
                  "calculation_code": "Quantum ESPRESSO",
                  "k_grid": [24, 24, 24],
                  "q_grid": [6, 6, 6],
                  "k_broadening": {"value_number": 0.02, "unit": "Ry"},
                  "q_broadening": {"value_number": 0.01, "unit": "Ry"}
                },
                "parameters": {
                  "lambda_ep": {"value_raw": "2.2", "value_number": 2.2, "unit": "1"},
                  "omega_log": {"value_raw": "1100 K", "value_number": 1100, "unit": "K"},
                  "mu_star": {"value_raw": "0.10", "value_number": 0.1, "unit": "1"}
                }
              },
              "evidences": []
            }
          ]
        }
      ]
    }
  ]
}
```

每条记录直接包含自己的条件和参数；增加 Tc-B 时复制所需资料并独立保存。
网格、展宽的具体含义和单位必须由方法定义说明；不同程序的展宽不自动视为同一物理量。

MaterialState 导出在单个包中包含材料身份、状态、结构、全部模块记录、证据和定义版本内容。
内部稳定键可保留用于追溯，但包内必须能解析全部科学引用，不要求用户下载关系表后自行拼接。


## 8. 迁移与生命周期

迁移顺序、停写边界、唯一约束替换及恢复路径统一以
[持久化迁移契约](contracts/persistence-mapping.md#分阶段迁移) 为准，不在本文件维护另一套步骤。
缺失 Evidence 的历史记录保留事实并生成报告，不伪造来源；这些记录后续编辑并重新批准时执行当前证据规则。

## 9. 数据库不变量

统一见 [数据库不变量](contracts/database-invariants.md)。实体章节说明字段含义，跨实体约束仅在该契约维护。
