# 契约：版本化 FormDefinition

## 读取

```http
GET /api/form-definitions/{definition_key}/current
GET /api/form-definitions/{definition_key}/versions/{version}
```

公开读取只返回已发布或用于历史记录解释的已停用版本。响应包含定义键、版本、目标类型、适用模块、
记录类型、可选方法、JSON Schema、UI Schema、组级规则、状态和校验和。目标类型为
`property_module`、`property_record`、`calculation_condition` 或 `experimental_condition`。

## 发布

```http
POST /api/admin/form-definitions/{definition_key}/versions
PUT /api/admin/form-definitions/{definition_key}/versions/{version}
POST /api/admin/form-definitions/{definition_key}/versions/{version}/publish
POST /api/admin/form-definitions/{definition_key}/versions/{version}/retire
```

只有超级管理员可调用。创建草稿时版本号由服务端分配；发布前必须验证：

- 版本连续且同键同版本不存在；
- Schema 只使用允许的声明式关键字；
- 目标类型、模块、记录类型和方法组合已经注册且互相匹配；
- UI Schema 引用的字段存在于核心字段或 JSON Schema；
- 组级规则使用受支持的规则类型；
- 内容校验和与保存内容一致。

`PUT` 只允许修改 `draft`。发布后定义内容不可修改；停用只改变是否可用于新建，不改变历史读取。
方法特有定义的 `definition_key` 必须包含方法代码，例如
`record.superconductive_properties.predicted_tc.allen_dynes`，版本号只表达该方法定义的演进。

## Conditions 身份规则

Conditions 定义使用 `identity_rules` 声明决定性输入和规范化方式：

```json
{
  "condition_fields": [
    {"path": "/calculation_code", "normalizer": "trimmed_string", "cardinality": "zero_or_one"},
    {"path": "/k_grid", "normalizer": "trimmed_string", "cardinality": "zero_or_one"}
  ],
  "record_properties": [
    {"property_code": "mu_star", "normalizer": "decimal", "cardinality": "zero_or_one"}
  ]
}
```

首批只允许 `trimmed_string`、`casefolded_code`、`decimal`、`boolean`、`ordered_list` normalizer，以及
`exactly_one`、`zero_or_one` cardinality。后端按规则验证同一 `condition_key` 的完整记录组；同一输入
形成两个规范值时返回 `conflicting_condition`。该规则不生成键，也不按内容合并两次独立运行。

初始定义的决定性字段集合如下；未报告的可选字段允许为空，不因分组而补造科学信息：

| 定义 | 决定性字段或输入 |
| --- | --- |
| 计算 Conditions | 结构键、电子方法、泛函、赝势类型及名称、SOC、声子方法和核处理、EPC 方法、k/q 网格、截断能及单位、软件、声明的扩展输入 |
| 实验 Conditions | 结构键、样品标识、制备方式、测量方法、外场、压力不确定度、声明的扩展输入 |
| 计算的关联物性输入 | `mu_star`、`lambda_ep`、`omega_log`；各自 `zero_or_one`，允许未报告，不能从 Tc 反推 |

规范化语义固定：字符串只去首尾空白；代码仅对注册的 ASCII 代码转小写；十进制使用精确十进制比较，
`0.10` 与 `0.1` 相等，不使用浮点容差；布尔只接受 JSON 布尔；有序列表逐项比较且不排序。空值与缺失
统一为未报告。数值必须同时比较规范单位，不执行自动单位换算；不同表达无法确认一致时拒绝合并并提示
选择独立 Conditions。同一输入的两条记录即使数值相同也违反 `zero_or_one`，返回 `condition_group_rule_failed`；
数值不同优先返回 `conflicting_condition`。其他互斥或必要配套规则仅允许 `mutually_exclusive` 与
`requires`，以 `property_code` 为选择器，不允许脚本和自由表达式。

`identity_rules` 和 `group_rules` 仅允许出现在 Conditions 定义。发布新方法之前，必须为其适用的
Conditions 定义补齐新增决定性输入并发布版本；不能声称自动推断论文未报告的全部计算输入。

JSON Schema 以 2020-12 为基准，首批允许对象、数组、字符串、有限数值、布尔、null、properties、required、
additionalProperties=false、items、enum、const、minimum/maximum、minItems/maxItems、minLength/maxLength、
if/then/else 和 allOf/anyOf/oneOf。拒绝远程引用、动态引用和自定义可执行关键字。UI Schema 仅包含字段
JSON Pointer、控件、顺序、标签及相同声明式条件，不携带独立校验规则。校验和使用 RFC 8785 规范 JSON
后的 SHA-256，覆盖目标身份、JSON/UI Schema、两类规则；状态和审计时间单独保存，停用不能改变内容校验和。

## 记录版本升级

```http
POST /api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/preview
POST /api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/apply
POST /api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/rollback
```

预览请求携带目标定义版本和预期论文 revision，返回字段转换、将清除的字段、校验问题、目标数据、
记录校验和与预览校验和。`apply` 必须携带两个校验和；记录或论文 revision 在预览后变化时返回冲突，
不得套用过期转换。

三个接口沿用论文编辑权限且限超级管理员，不能绕过论文审核和 revision 变更。目标必须是相同定义键的
更高已发布版本；本功能不提供跨方法自动转换。预览先保留仍被目标版本允许的原字段，列出待移除字段；
缺少新必填值时允许调用方提供显式目标 `payload` 再预览。类型转换不猜测，不运行转换脚本。核心科学值、
方法、Conditions 和 Evidence 保持不变，只转换扩展字段和定义版本。

预览校验和必须绑定论文 revision、记录完整快照、Conditions 定义与同组记录、源/目标定义校验和以及目标
payload。应用在锁定论文后重新计算并验证；客户端不能仅通过修改预览返回值绕过校验。

应用成功后返回不可变 `upgrade_event_id`。`rollback` 必须携带该事件 ID、当前论文 revision、当前记录
校验和和预期前序事件。服务在现有论文编辑事务中恢复事件保存的升级前定义版本、核心字段和 `payload`
快照，并新增反向审计事件。事件已回滚、记录已再次升级或发生其他编辑时返回冲突，不覆盖后续修改。

回滚可以恢复已停用源定义，因为这是已有记录的历史恢复，不是新建；仍须通过该源定义、当前同组
Conditions 和 Evidence 规则。应用与回滚均返回操作后 revision、记录校验和和事件 ID；立即回滚使用
操作后 revision，而非要求它等于升级前 revision。论文其他修改改变 revision 后必须拒绝旧回滚请求。

## 错误

| HTTP | 错误码 | 含义 |
| --- | --- | --- |
| 400 | `unsupported_schema_keyword` | 使用了不支持或可执行的 Schema 能力 |
| 403 | `definition_publish_forbidden` | 调用者不是超级管理员 |
| 404 | `unknown_definition_version` | 定义键或版本不存在 |
| 409 | `definition_version_conflict` | 版本重复、跳号或发布后修改 |
| 409 | `definition_upgrade_stale` | 记录在预览后已变化 |
| 409 | `definition_rollback_stale` | 升级事件不是当前记录的可回滚前序事件 |
| 422 | `definition_invalid` | Schema、UI Schema 或组级规则不一致 |

## 缓存

客户端和服务可以按 `definition_key + version + checksum` 缓存不可变定义。校验和不一致时丢弃缓存并
重新读取；定义服务不可用且没有可信缓存时，允许只读展示原始核心字段，但禁止无法校验的新写入。
