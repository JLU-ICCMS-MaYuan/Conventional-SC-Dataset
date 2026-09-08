# 契约：模块化物性的持久化映射

## 目标表

| 领域实体 | 目标表 | 说明 |
| --- | --- | --- |
| 论文内化学体系 | `chemical_systems` | 增加论文 revision 归属，唯一键限定在论文 revision 内 |
| 论文内材料 | `superconductors` | 增加论文 revision 归属，不跨论文复用主键 |
| 模块实例 | `property_modules` | 每行是一个材料状态挂载的模块 |
| 物性记录 | `property_records` | 统一保存 Tc 和其他模块记录的核心字段与扩展 JSON |
| 表单定义 | `form_definitions` | 保存不可变版本化核心 Schema、JSON Schema 和 UI Schema |
| 定义升级事件 | `property_record_definition_events` | 保存记录定义升级与回滚的不可变前后快照 |
| 自定义性质提升事件 | `property_definition_promotion_events` | 保存管理员、来源快照、目标定义和幂等键 |
| 记录内 Conditions 与参数 | `property_records.payload_json` | 逐条内嵌保存，不新建共享条件表或输入关系表 |
| 证据连接 | `property_record_evidences` | 统一连接 PropertyRecord 与 PaperEvidence |

## 旧数据映射

| 旧来源 | 目标 |
| --- | --- |
| `tc_results` 理论行 | 超导模块中的 `predicted_tc` |
| `tc_results` 实验行 | 超导模块中的 `measured_tc` |
| `superconductor_properties` | 依据定义种子映射到目标模块的普通记录 |
| 旧计算/实验 Context | 按每条原使用记录复制到其 `payload.calculation_conditions` 或 `payload.experimental_conditions` |
| Context 中的 `lambda_ep`、`omega_log_k`、`mu_star` | 复制到每条原使用 Tc 的 `payload.parameters`，保留原值、单位和字段来源 |
| `tc_result_evidences` | `property_record_evidences` |
| `superconductor_property_evidences` | `property_record_evidences` |

迁移保存旧表名、旧 ID 与新 ID 的映射，供对账和可恢复切换使用。无法确定模块或定义版本的行进入
异常清单，不能自动归入一个含义模糊的兜底模块。

## 核心字段与 JSON

`property_modules` 和 `property_records` 各自绑定定义键与版本；条件和参数随记录版本解释。
`property_records` 的固定列至少包括归属、模块、记录类型、物性代码、定义键/版本、原始与规范值、
单位、不确定度、方法、判据、代表标记、结构外键、来源指纹和时间字段。

`payload_json` 保存 Schema 声明的本条 Conditions、参数和扩展分组；没有两个 Conditions 外键。
CHECK 验证 Tc 类型对应的 JSON 条件对象存在且另一类不存在；具体字段类型、单位与方法规则由后端
按记录定义校验。普通物性可按定义内嵌至多一种条件。

Tc 数值和方法等固定核心列不得在 JSON 再次保存为另一可写来源。需要常用查询的参数可建立 JSON
提取索引或只读投影；若未来提升为固定列，必须通过迁移维持唯一写入来源。

自定义性质仍写入 `property_records`，增加可空 `custom_property_key` 列，只在 `property_code=custom`
且 `record_type=property` 时非空；名称、四种类型的值及单位复用核心列，`core_schema` 校验它们。
初始定义种子包含四模块的已发布自定义模板，用户不发布 Schema 即可提交并随论文批准。

提升只写 `form_definitions` 和 `property_definition_promotion_events`，不更新源物性。所有全站普通性质
使用 `record.property.<property_code>` 定义键，v1 的唯一键防止并发代码注册，版本语义和模块不能改变代码
身份。提升事件按 operation_id 及来源论文/revision/模块/custom_property_key 分别设唯一约束。
事件存必要来源快照，源论文删除不会级联删除通用定义或事件；公开接口不输出审计内容。

## Tc 数据库约束

- `record_type=predicted_tc` 时必须为 `property_code=tc` 并包含计算 Conditions 对象。
- `record_type=measured_tc` 时必须为 `property_code=tc` 并包含实验 Conditions 对象。
- 其他记录不得填写 Tc 专用代表标记。
- Tc 规范值、范围和不确定度必须非负；规范单位必须为 `K`。
- 代表 Tc 唯一范围为论文、revision、材料状态、记录类型和方法。
- 为 Tc 图表建立 `record_type + method_code + value_number` 等实际查询需要的索引。

## 分阶段迁移

1. **Expand**：创建目标表、索引、定义种子和迁移映射表；材料使用 `issue90_chemical_systems` 与
   `issue90_superconductors` 影子表，直接建立论文 revision 内唯一键，旧材料表保持全局唯一约束。
2. **Copy**：分批复制材料、Tc、其他物性和 Evidence；按旧引用把 Conditions 和参数展开到每条记录内，每批记录进度。
3. **Reconcile**：按结果记录数、核心值、展开后的字段来源映射、证据和来源指纹对账；预期参数复制与意外重复分别核对，异常必须可定位。
4. **切换准备**：阻止上传提交、科学数据编辑、审核、升版、物理删除和后台科学数据写入，并等待在途
   事务完成。最终同步所有发生变化或已删除论文的完整 revision 图，不仅追加新增行；完成再次对账和备份。
5. **Read switch**：仍保持停写，将旧材料表更名为 `legacy_issue90_chemical_systems` 与
   `legacy_issue90_superconductors`，把影子表更名为目标表名，并依据映射重连 MaterialState。
   MySQL 表更名不会自动把指向旧表的外键转为新实体，因此必须显式重建材料及状态复合外键。
   对这段非事务 DDL 暂停科学数据读取并返回明确维护错误，不能返回不完整数据；完成后恢复目标读取并验收。
   若失败，仍保持停写，按记录的反向步骤或切换前备份恢复表名、ID 和外键，再恢复旧读取与旧写入。
6. **Write switch**：读取验收通过后让上传和管理端只写新模型，再解除停写；旧写入关闭。
7. **Observe**：验证搜索、图表、审核、升版、回滚和删除，无差异后进入退役。
8. **Contract**：删除旧业务表或旧列；该步骤使用独立迁移，不与复制步骤假定为同一事务。
9. **审计清理**：完整归档检查点、映射和异常清单并保存 SQL 备份后，执行 `issue90_audit_cleanup_v1`
   删除三张临时迁移表；检查点必须已完成 Contract，且不存在未解决异常。

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

### 条件和参数展开

旧 Context 表在观察结束前保留以支持旧读取；其内容按实际使用记录复制成独立 JSON 快照，不保留原条件
主键作为新写入权威。迁移映射记录旧表、旧 ID、论文 revision、目标 record_key 和目标字段路径；
同一旧条件服务多条 Tc 时，每条都获得自己的完整条件和参数。幂等依据来源与目标组合，不能把预期复制
误判为重复，也不能重跑后新增额外结果。

旧 Context 的结构引用转入所属记录的 `structure_key`；已有记录结构与它冲突时阻断并报告，不能丢弃其中一个。
其他旧条件字段均须有目标字段路径或明确归档位置，包括方法扩展和原文补充，不能仅复制当前表单已展示的字段。

仅按旧引用或明确的记录内来源映射输入，不按数值相近或材料同名猜测归属。若某条旧 Tc 具有明确的
记录级参数，则保留它的来源；与共享旧字段不一致时生成阻断异常，不能静默选择一个值。
原本独立报告的普通物性继续保留为记录，不因数值等同于某条 Tc 的参数而删除。

Evidence 逐项保留真实来源，可在参数值对象内保存字段证据；不能把 Tc 的证据伪装成参数证据。
迁移以旧字段到各目标记录字段的映射核对原值、单位、缺失状态和来源，不要求展开前后参数总数相等。

无人引用的旧条件、无法归属的参数或无法解析的证据进入逐项异常清单，阻断切换和退役，直到完成明确
归属或以带原内容、来源和处理决定的迁移归档保留。归档是历史异常留存，不作为新科研数据写入入口；
已保留在归档中的资料须能核验，不能随临时映射表一同删除。所有科学归属不得靠迁移程序猜测。

## Contract 后的迁移审计归档

三表仅服务迁移过程，清理完成后不保留在业务库中：

| 表 | 删除前归档内容 |
| --- | --- |
| `issue90_migration_checkpoint` | 最终阶段、读写切换、对账、观察结果和已删除旧表清单 |
| `issue90_property_migration_map` | 来源表、旧 ID、论文 revision、目标 ID/record_key、字段映射和校验和 |
| `issue90_migration_anomalies` | 迁移异常、原始详情和解决状态；空表也记录完整结构及空数组 |

归档包含表结构和全部记录，并保留 SQL 备份位置及 SHA-256。本地部署快照见
[迁移审计归档](../migration-audit-archive.md)。归档是删除前历史事实，业务数据后续变化不回写归档。

独立清理迁移先检查 Contract 完成标记和未解决异常，再按映射、异常、检查点的顺序删除；检查点最后删除，
支持 MySQL 非事务 DDL 中断后重试。正常业务仍保留迁移期间的停写检查，检查点表不存在时直接放行，
不再通过缺表异常走正常路径。ORM 元数据不声明三表，历史迁移仍按原顺序创建、使用并最终清理它们。
清理不可通过 downgrade 重建原记录；需要恢复审计内容时使用归档或 SQL 备份。

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
-> structure_models
-> material_states
-> superconductors
-> chemical_systems
```

只删除当前论文 revision 拥有的记录。Conditions 与参数随所属记录处理；同名材料和其他 Tc 的资料不受影响。
字段内 Evidence 引用须与记录 Evidence 一并验证并随论文升版重映射，删除不能反向删除证据正文。
