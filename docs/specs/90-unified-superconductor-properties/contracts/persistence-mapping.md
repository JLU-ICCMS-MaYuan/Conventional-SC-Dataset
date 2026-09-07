# 契约：模块化物性的持久化映射

## 目标表

| 领域实体 | 目标表 | 说明 |
| --- | --- | --- |
| 论文内化学体系 | `chemical_systems` | 增加论文 revision 归属，唯一键限定在论文 revision 内 |
| 论文内材料 | `superconductors` | 增加论文 revision 归属，不跨论文复用主键 |
| 模块实例 | `property_modules` | 每行是一个材料状态挂载的模块 |
| 物性记录 | `property_records` | 统一保存 Tc 和其他模块记录的核心字段与扩展 JSON |
| 表单定义 | `form_definitions` | 保存不可变版本化 JSON Schema、UI Schema 和组级规则 |
| 计算 Conditions | `calculation_conditions` | 由旧 `calculation_contexts` 迁移并改名 |
| 实验 Conditions | `experimental_conditions` | 由旧 `experimental_contexts` 迁移并改名 |
| 证据连接 | `property_record_evidences` | 统一连接 PropertyRecord 与 PaperEvidence |

## 旧数据映射

| 旧来源 | 目标 |
| --- | --- |
| `tc_results` 理论行 | 超导模块中的 `predicted_tc` |
| `tc_results` 实验行 | 超导模块中的 `measured_tc` |
| `superconductor_properties` | 依据定义种子映射到目标模块的普通记录 |
| Conditions 中的 `lambda_ep`、`omega_log_k`、`mu_star` | 独立 PropertyRecord，并保留原 Conditions 关联 |
| `tc_result_evidences` | `property_record_evidences` |
| `superconductor_property_evidences` | `property_record_evidences` |

迁移保存旧表名、旧 ID 与新 ID 的映射，供对账和可恢复切换使用。无法确定模块或定义版本的行进入
异常清单，不能自动归入一个含义模糊的兜底模块。

## 核心字段与 JSON

`property_modules`、两类 Conditions 和 `property_records` 都绑定各自目标类型的定义键与版本。
`property_records` 的固定列至少包括归属、模块、记录类型、物性代码、定义键/版本、原始与规范值、
单位、不确定度、方法、判据、代表标记、Conditions 外键、结构外键、来源指纹和时间字段。

`payload_json` 只保存 `FormDefinition.json_schema` 声明的扩展字段。核心列与 JSON 同名或表达同一
事实时拒绝写入。需要数据库筛选、排序、唯一约束或跨记录关联的扩展字段，必须先通过后续迁移提升
为固定列。

## Tc 数据库约束

- `record_type=predicted_tc` 时必须为 `property_code=tc` 并关联计算 Conditions。
- `record_type=measured_tc` 时必须为 `property_code=tc` 并关联实验 Conditions。
- 其他记录不得填写 Tc 专用代表标记。
- Tc 规范值、范围和不确定度必须非负；规范单位必须为 `K`。
- 代表 Tc 唯一范围为论文、revision、材料状态、记录类型和方法。
- 为 Tc 图表建立 `record_type + method_code + value_number` 等实际查询需要的索引。

## 分阶段迁移

1. **Expand**：创建目标表、索引、定义种子和迁移映射表。
2. **Copy**：分批复制材料、Conditions、Tc、其他物性和 Evidence；每批记录进度。
3. **Reconcile**：按记录数、核心值、关联和来源指纹对账；异常必须可定位。
4. **Read switch**：详情和校验读取新模型，对比旧查询结果。
5. **Write switch**：上传和管理端只写新模型；旧写入关闭。
6. **Observe**：验证搜索、图表、审核、升版和删除，无差异后进入退役。
7. **Contract**：删除旧表或旧列；该步骤使用独立迁移，不与复制步骤假定为同一事务。

任一步失败时从最近完成且已记录的阶段恢复。DDL 的可恢复性必须使用隔离 MySQL 实测，不能用
“事务整体回滚”作为唯一方案。

## 论文内材料迁移

旧模型可能由多篇论文共享同一个 `superconductors.id`。迁移为每个实际引用该材料的论文 revision
建立一条目标材料记录，并重连相应 `MaterialState`。删除或修改任一论文拥有的材料不会级联影响
另一论文。

`ChemicalSystem` 同样按论文 revision 复制。旧 ID 到新 ID 映射必须包含论文和 revision，避免把
两篇论文的 LaH10 再次合并。

## 定义版本

- 初始迁移为每类旧记录绑定确定的定义键和 v1。
- 已发布定义内容由校验和保护，不允许 UPDATE 改写语义。
- 新建记录解析当前发布版本后，将具体版本写入记录；后续读取不重新解析为最新版。
- 停用定义不影响历史读取。
- 显式升级记录时，在同一业务事务内写入新版本、转换后的 `payload` 和审计事件。

## 删除顺序

```text
property_record_evidences
-> property_records
-> property_modules
-> calculation_conditions / experimental_conditions
-> structure_models
-> material_states
-> superconductors
-> chemical_systems
```

只删除当前论文 revision 拥有的记录。Conditions 仍被记录引用时不得删除；同名材料属于另一论文时
不受影响。
