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
                        ├── CalculationConditions[]
                        ├── ExperimentalConditions[]
                        └── PropertyModules[]
                            └── PropertyModule
                                └── PropertyRecords[]
                                    └── PropertyRecord
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

模块是页面组织和扩展边界，不改变记录的唯一权威。一个性质若与多个领域有关，只保存一条
`PropertyRecord`；其他模块通过记录引用或筛选展示，不能复制一份独立可编辑值。

## 3. PropertyRecord

### 3.1 固定核心字段

| 字段 | 必填 | 含义与约束 |
| --- | --- | --- |
| `record_key` | 是 | 请求和响应内稳定键；不暴露数据库主键 |
| `module_code` | 是 | 所属模块，必须与模块实例一致 |
| `record_type` | 是 | 例如 `predicted_tc`、`measured_tc`、`property` |
| `property_code` | 是 | 规范科学量代码，例如 `tc`、`lambda_ep`、`omega_log`、`mu_star`、`hc2` |
| `definition_key` | 是 | 使用的表单定义键 |
| `definition_version` | 是 | 使用的不可变定义版本 |
| `name_raw` | 是 | 论文原文名称 |
| `value_kind` | 是 | `number`、`range`、`text` 或 `boolean` |
| `value_raw` | 是 | 论文原始值文本 |
| `value_number` | 条件必填 | 单一规范数值 |
| `value_min` / `value_max` | 条件必填 | 完整规范范围 |
| `uncertainty` | 否 | 非负不确定度，与规范单位一致 |
| `unit_raw` / `canonical_unit` | 否 | 原文单位和规范单位 |
| `method_code` | 否 | 规范方法代码；Tc 必填 |
| `method_raw` | 否 | 论文中的原始方法文本 |
| `criterion_code` / `criterion_raw` | 否 | 规范判据及原文判据 |
| `is_representative` | 条件必填 | Tc 必填，其他记录默认空 |
| `condition_key` | 否 | 关联一次确定的计算或实验 Conditions |
| `structure_key` | 否 | 关联本论文 revision 当前材料状态中的结构 |
| `payload` | 是 | 符合定义版本的扩展 JSON；默认 `{}` |
| `evidences[]` | 是 | 当前论文 revision 的 Evidence；草稿可为空 |

固定列负责搜索、统计、关联、唯一约束和审计。`payload` 不得再次保存 Tc 数值、方法、Conditions
引用等核心事实。若某扩展字段后来成为核心查询条件，需要用迁移提升为固定列，不能同时保留两个
可写来源。

### 3.2 Tc 记录

Tc 使用 `property_code=tc`，并按 `record_type` 分为：

| 记录类型 | Conditions | 方法示例 |
| --- | --- | --- |
| `predicted_tc` | 必须关联 `CalculationCondition` | Allen-Dynes、McMillan、Eliashberg、SCDFT、自定义理论方法 |
| `measured_tc` | 必须关联 `ExperimentalCondition` | 电阻、磁化率、比热或自定义实验方法 |

`method_code` 是具体方法权威，`record_type` 是预测/测量性质权威。二者必须匹配。`result_kind`
不再作为独立可写字段；兼容读取时由旧值映射到 `record_type`。

代表 Tc 唯一范围为：

```text
paper_id + paper_revision + material_state_id + record_type + method_code
```

同一范围最多一条 `is_representative=true`。

## 4. Conditions

Conditions 表示一次确定的运行或测量，不是物性模块，也不保存物性结果。

### 4.1 CalculationCondition

固定字段保存常用配置，例如电子方法、交换关联泛函、赝势、SOC、声子方法、EPC 方法、k/q 网格、
截断能和计算软件。方法特有配置可以使用同样版本化定义管理扩展 JSON。

### 4.2 ExperimentalCondition

固定字段保存样品标识、制备方式、测量方法、外场、压力不确定度等共享实验条件。单条结果自己的
判据仍属于 `PropertyRecord`。

### 4.3 归组规则

一个 `condition_key` 表示一次确定执行。以下例子必须建立两组 Conditions：

```text
calc-a: mu_star=0.10, Tc=250 K
calc-b: mu_star=0.15, Tc=220 K
```

即使两次计算的软件、结构、网格相同，只要决定性输入不同，就不是同一次执行。`mu_star` 仍作为
独立 PropertyRecord 保存，并与对应 Tc 共享 `condition_key`。定义可以声明“同一 Conditions 下某
输入 `property_code` 最多一条”等组级规则，后端必须在整组记录上校验。

## 5. FormDefinition

| 字段 | 含义 |
| --- | --- |
| `definition_key` | 稳定键，例如 `superconductive_properties.predicted_tc` |
| `version` | 从 1 开始单调递增；与键组成唯一标识 |
| `target_kind` | `property_module`、`property_record`、`calculation_condition` 或 `experimental_condition` |
| `module_code` | 模块或记录定义的适用模块；Conditions 定义为空 |
| `record_type` | 记录定义的适用记录类型；其他目标类型为空 |
| `method_code` | 可选；为空表示通用定义，非空表示方法扩展 |
| `json_schema` | 扩展字段的数据结构、类型、枚举和条件必填规则 |
| `ui_schema` | 控件、顺序、分组、标签键和单位提示；不拥有数据校验权威 |
| `group_rules` | 需要观察同一 Conditions 多条记录的规则 |
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
- 新建模块、记录或 Conditions 选择对应定义键最新的 `published` 版本。
- 记录升级版本是显式操作，必须预览转换、重新验证并保留审计记录。

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
| `calculation_conditions` | 一次计算运行 |
| `experimental_conditions` | 一次实验测量 |
| `property_record_evidences` | 记录与 Evidence 的多对多连接 |

`property_records` 统一接收旧 `tc_results` 与 `superconductor_properties`。Tc 核心列保持专用 CHECK、
生成列、唯一索引和统计索引；不同记录类型不适用的专用列必须为空。旧表完成对账和观察期后退役。

`chemical_systems` 和 `superconductors` 增加 `paper_id + paper_revision` 归属，唯一键从全库唯一调整为：

```text
chemical_systems: paper_id + paper_revision + system_key
superconductors:   paper_id + paper_revision + composition_key
```

所有从 `Superconductor` 到 `MaterialState` 的关系使用同论文 revision 复合外键，禁止跨论文引用。

## 7. API 结构示例

```json
{
  "material_states": [
    {
      "state_key": "state-1",
      "calculation_conditions": [
        {"condition_key": "calc-a", "calculation_code": "Quantum ESPRESSO"}
      ],
      "experimental_conditions": [],
      "property_modules": [
        {
          "module_code": "superconductive_properties",
          "records": [
            {
              "record_key": "tc-a",
              "record_type": "predicted_tc",
              "property_code": "tc",
              "definition_key": "superconductive_properties.predicted_tc",
              "definition_version": 2,
              "value_kind": "number",
              "value_raw": "250 K",
              "value_number": 250,
              "canonical_unit": "K",
              "method_code": "allen_dynes",
              "condition_key": "calc-a",
              "payload": {"solver_tolerance": "1e-8"},
              "evidences": []
            }
          ]
        }
      ]
    }
  ]
}
```

数组不存在时返回 `[]`，可空引用返回 `null`。API 不重复嵌入 Conditions 详情到每条记录；记录使用
`condition_key` 引用同一材料状态顶层的 Conditions，避免同一内容被重复编辑。

## 8. 迁移与生命周期

迁移按阶段执行：

1. 创建新表、定义种子和目标索引，不改旧读取。
2. 复制旧材料、Tc、普通物性、Conditions 和 Evidence，保存旧 ID 到新 ID 的迁移映射。
3. 按论文、revision、状态、记录类型、方法、值、单位和关联逐项对账。
4. 应用先切换读取并观察差异，再切换写入。
5. 停止旧写入，保留可回退读取窗口。
6. 验证图表、搜索、审核、升版和删除后再退役旧表及旧字段。

迁移不能假定 MySQL DDL 可以和数据回填一起事务回滚。每一步必须可重复、记录进度，并提供从最近
稳定阶段恢复的办法。缺失 Evidence 的历史记录保留事实并生成报告，不伪造来源；这些记录后续编辑并
重新批准时执行当前证据规则。

## 9. 数据库不变量

1. 模块、记录、Conditions、结构和 Evidence 必须与 `MaterialState` 属于同一论文 revision。
2. 预测 Tc 只关联计算 Conditions；测量 Tc 只关联实验 Conditions。
3. 核心字段与 `payload` 不得出现两个可写权威。
4. 定义键和版本必须指向已存在且内容校验和一致的定义。
5. 已发布定义不可修改；历史记录不得在读取时自动升级。
6. 同一科学事实不得因跨模块展示而复制。
7. 论文拥有的材料不得被另一论文 revision 引用。
8. 新批准记录必须满足对应定义版本、组级规则和 Evidence 门槛。
