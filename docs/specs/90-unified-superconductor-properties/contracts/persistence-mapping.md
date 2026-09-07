# 契约：模块化物性的持久化映射

## 目标表

| 领域实体 | 目标表 | 说明 |
| --- | --- | --- |
| 论文内化学体系 | `chemical_systems` | 增加论文 revision 归属，唯一键限定在论文 revision 内 |
| 论文内材料 | `superconductors` | 增加论文 revision 归属，不跨论文复用主键 |
| 模块实例 | `property_modules` | 每行是一个材料状态挂载的模块 |
| 物性记录 | `property_records` | 统一保存 Tc 和其他模块记录的核心字段与扩展 JSON |
| 表单定义 | `form_definitions` | 保存不可变版本化 JSON Schema、UI Schema 和组级规则 |
| 定义升级事件 | `property_record_definition_events` | 保存记录定义升级与回滚的不可变前后快照 |
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
单位、不确定度、方法、判据、代表标记、两个互斥的 Conditions 外键、结构外键、来源指纹和时间字段。
计算与实验 Conditions 分别使用复合外键约束材料状态和论文 revision；CHECK 保证一条记录最多关联一种
Conditions，并强制预测/测量 Tc 使用正确类型。

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

1. **Expand**：创建目标表、索引、定义种子和迁移映射表；材料使用 `issue90_chemical_systems` 与
   `issue90_superconductors` 影子表，直接建立论文 revision 内唯一键，旧材料表保持全局唯一约束。
2. **Copy**：分批复制材料、Conditions、Tc、其他物性和 Evidence；每批记录进度。
3. **Reconcile**：按记录数、核心值、关联和来源指纹对账；异常必须可定位。
4. **切换准备**：阻止上传提交、科学数据编辑、审核、升版、物理删除和后台科学数据写入，并等待在途
   事务完成。最终同步所有发生变化或已删除论文的完整 revision 图，不仅追加新增行；完成再次对账和备份。
5. **Read switch**：仍保持停写，将旧材料表更名为 `legacy_issue90_chemical_systems` 与
   `legacy_issue90_superconductors`，把影子表更名为目标表名，并依据映射重连 MaterialState。
   MySQL 表更名不会自动把指向旧表的外键转为新实体，因此必须显式重建材料及状态复合外键。
   对这段非事务 DDL 暂停科学数据读取并返回明确维护错误，不能返回不完整数据；完成后恢复目标读取并验收。
   若失败，仍保持停写，按记录的反向步骤或切换前备份恢复表名、ID 和外键，再恢复旧读取与旧写入。
6. **Write switch**：读取验收通过后让上传和管理端只写新模型，再解除停写；旧写入关闭。
7. **Observe**：验证搜索、图表、审核、升版、回滚和删除，无差异后进入退役。
8. **Contract**：删除旧表或旧列；该步骤使用独立迁移，不与复制步骤假定为同一事务。

任一步失败时从最近完成且已记录的阶段恢复。DDL 的可恢复性必须使用隔离 MySQL 实测，不能用
“事务整体回滚”作为唯一方案。

解除停写后旧表已不再完整，不允许直接切回旧读路径。该阶段采用修复目标版本后恢复服务，或先停止所有
科学写入、备份目标完整状态，并在同一目标 Schema 上恢复最近检查点和重放后续事务日志；必须验证无
已提交事务丢失后才解除维护。Contract 前后均演练这条目标模型恢复路径，旧表只用于切写前恢复和对账。

## 论文内材料迁移

旧模型可能由多篇论文共享同一个 `superconductors.id`。Copy 在影子表中为每个实际引用该材料的论文
revision 建立目标材料记录；旧 MaterialState 外键在停写切换前不变，目标关联先保存在映射表。
这样既不触发旧全局唯一键，也不让未切换的旧写入误选论文内副本。Read switch 才重连状态。

`ChemicalSystem` 同样按论文 revision 复制。旧 ID 到新 ID 映射必须包含论文和 revision，避免把
两篇论文的 LaH10 再次合并。

两类 Conditions 同样在新表中复制，保留旧主键和状态/revision；旧 Context 表在观察结束前保留，
不以改名或兼容视图破坏旧读取。所有临时表名和映射表均限定在本次迁移，Contract 后退役。

## 定义版本

- 初始迁移为每类旧记录绑定确定的定义键和 v1。
- 已发布定义内容由校验和保护，不允许 UPDATE 改写语义。
- 新建记录解析当前发布版本后，将具体版本写入记录；后续读取不重新解析为最新版。
- 停用定义不影响历史读取。
- 显式升级记录时，在同一业务事务内写入新版本、转换后的 `payload` 和审计事件。
- 回滚根据升级事件的旧快照创建反向审计事件；论文 revision、记录校验和或前序事件不匹配时拒绝。

## 删除顺序

```text
property_record_evidences
-> property_record_definition_events
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
