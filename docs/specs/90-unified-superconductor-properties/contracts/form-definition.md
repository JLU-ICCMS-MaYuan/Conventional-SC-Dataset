# 契约：版本化 FormDefinition

## 读取

```http
GET /api/form-definitions/{definition_key}/current
GET /api/form-definitions/{definition_key}/versions/{version}
```

公开读取只返回已发布或用于历史记录解释的已停用版本。响应包含定义键、版本、目标类型、适用模块、
记录类型、物性代码、可选方法、核心字段 Schema、JSON Schema、UI Schema、记录内条件规则、状态和校验和。目标类型为
`property_module` 或 `property_record`。

定义选择器还使用 `GET /api/form-definitions?target_kind=property_record&module_code={module_code}`，按定义键
返回当前已发布版本，包括系统自定义模板及管理员新提升的定义；停用项不出现在新建选项中。

## 常规定义管理

```http
POST /api/admin/form-definitions/{definition_key}/versions
PUT /api/admin/form-definitions/{definition_key}/versions/{version}
POST /api/admin/form-definitions/{definition_key}/versions/{version}/publish
POST /api/admin/form-definitions/{definition_key}/versions/{version}/retire
```

以上常规管理接口只有超级管理员可调用；管理员通过下述“自定义性质提升”接口直接发布通用性质，
无需超级管理员复核。创建草稿时版本号由服务端分配；发布前必须验证：

- 版本连续且同键同版本不存在；
- Schema 只使用允许的声明式关键字；
- 目标类型、模块、记录类型和方法组合已经注册且互相匹配；
- UI Schema 引用的字段存在于核心字段或 JSON Schema；
- 记录内条件规则使用受支持的规则类型；
- 内容校验和与保存内容一致。

`PUT` 只允许修改 `draft`。发布后定义内容不可修改；停用只改变是否可用于新建，不改变历史读取。
方法特有定义的 `definition_key` 必须包含方法代码，例如
`record.superconductive_properties.predicted_tc.allen_dynes`，版本号只表达该方法定义的演进。

## 自定义性质提升

```http
POST /api/admin/papers/{paper_id}/property-records/{record_key}/promote-definition
```

普通管理员和超级管理员均可调用。请求携带 `operation_id`、预期论文 revision、源记录校验和、目标
`property_code`、显示名称、描述、所属模块、`value_kind` 和单位规则（指定规范单位、无量纲或保留原文单位）。
源记录必须是当前已批准 revision 的自定义记录；审核页先完成论文批准，再显示独立提升动作，选择不提升
不影响论文批准或数据保留。目标模块必须已注册并与源模块一致。

管理员论文读取响应提供当前 revision 和源记录校验和；校验和按 RFC 8785 规范 JSON 后计算 SHA-256，
覆盖记录核心字段、定义绑定、扩展字段和 Evidence 关联，供提升请求回传并由服务端重新核对。

服务端从受限模板生成 `target_kind=property_record`、`record_type=property` 的核心字段 Schema 和空扩展
Schema，在一个事务内创建并发布 v1、写入提升审计事件。提升接口不接受客户端任意 Schema、Tc 规则、
Conditions 规则或其他目标类型。普通性质的全站定义键统一为 `record.property.<property_code>`，使用
定义键/版本唯一约束保证不同模块、并发管理员不能重复占用代码；种子定义和常规发布也遵守同一命名规则。
拒绝 `custom`、Tc 及其保留别名或已有代码。服务端校验类型和单位与来源相符，不进行未经确认的单位换算。

成功返回 201、目标定义键/版本/校验和及事件 ID；同 operation_id 同请求重试返回原结果，不重复发布。
同 operation_id 不同请求、同来源已提升、代码已占用、源 revision 或快照变化返回 409；普通用户返回 403。
锁定论文并重新验证公开资格，保证与论文升版、删除和其他审核动作串行。定义发布和审计必须同时成功。

新定义立即进入全站对应模块的定义选择器，记录仍分别属于各自论文。源记录继续使用原通用模板和
custom_property_key；发布不修改论文科学事实，不触发自动重绑或批量数据迁移。未来显式转换历史记录
不属于本次提升操作，也不调用只支持同键升版的 definition-upgrade 接口。源论文删除或升版不会删除
通用定义，提升事件保存必要来源快照；公开选择器不输出管理员审计内容。

## 记录内 Conditions、参数和分组规则

`core_schema` 校验固定核心列，`json_schema` 校验完整 `payload`，包括当前记录的 Conditions、
参数和预留分组。方法不同使用不同定义键；所有内嵌资料使用同一个记录定义版本，没有独立的条件版本。

初始定义覆盖以下内容，具体必填性按方法及论文可报告性设置：

| 分组 | 字段 |
| --- | --- |
| 计算 Conditions | 电子方法、泛函、赝势、SOC、声子/EPC 方法、k/q 网格、k/q 各自展宽与单位、截断能、软件 |
| 实验 Conditions | 样品、制备、装置、外场、压力不确定度 |
| 预测 Tc 参数 | λ、ωlog、μ*，及该方法支持的其他输入；保留原值、规范值、单位和字段证据 |

`predicted_tc` 必须存在 `payload.calculation_conditions` 且不得存在实验对象；`measured_tc` 反之。
发布验证同时检查核心记录类型和嵌套字段规则的组合。普通物性按定义可省略条件。缺失可选参数不从
Tc 反推；同一参数在本条记录只能保存一个值或明确范围，多个结果分别建记录。

预留分组用 `extensions[]` 声明通用字段条目的受限结构；用户能填写字段名称、类型、单位、值和证据，
但不能创建 Schema 路径、修改系统键或执行规则。分组 JSON Pointer、允许值类型和控件顺序均在发布
版本中固定。后端由条目所在路径判定归属，按论文审核保留；新版本发布不静默移动或丢弃旧分组字段。

不定义 `identity_rules`、`group_rules` 或 `record_properties` 输入选择器。
同一 Tc 记录内部用声明式字段规则校验，不跨记录寻找参数或推断归组。

JSON Schema 以 2020-12 为基准，首批允许对象、数组、字符串、有限数值、布尔、null、properties、required、
additionalProperties=false、items、enum、const、minimum/maximum、minItems/maxItems、minLength/maxLength、
if/then/else 和 allOf/anyOf/oneOf。拒绝远程引用、动态引用和自定义可执行关键字。UI Schema 仅包含字段
JSON Pointer、控件、顺序、标签及相同声明式条件，不携带独立校验规则。校验和使用 RFC 8785 规范 JSON
后的 SHA-256，覆盖目标身份、core_schema、JSON/UI Schema 及内嵌分组规则；状态和审计时间单独保存，停用不能改变内容校验和。

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
方法和 Evidence 保持不变；仅按显式预览转换 payload 和定义版本，Conditions、参数和用户新增字段的
任何变化或移除都必须列明并确认，不能随新版本静默丢弃。

预览校验和必须绑定论文 revision、记录完整快照（含内嵌 Conditions、参数和分组字段）、源/目标定义校验和以及目标
payload。应用在锁定论文后重新计算并验证；客户端不能仅通过修改预览返回值绕过校验。

应用成功后返回不可变 `upgrade_event_id`。`rollback` 必须携带该事件 ID、当前论文 revision、当前记录
校验和和预期前序事件。服务在现有论文编辑事务中恢复事件保存的升级前定义版本、核心字段和 `payload`
快照，并新增反向审计事件。事件已回滚、记录已再次升级或发生其他编辑时返回冲突，不覆盖后续修改。

回滚可以恢复已停用源定义，因为这是已有记录的历史恢复，不是新建；仍须通过该源定义的记录内
Conditions、参数和 Evidence 规则。应用与回滚均返回操作后 revision、记录校验和和事件 ID；立即回滚使用
操作后 revision，而非要求它等于升级前 revision。论文其他修改改变 revision 后必须拒绝旧回滚请求。

## 错误

| HTTP | 错误码 | 含义 |
| --- | --- | --- |
| 400 | `unsupported_schema_keyword` | 使用了不支持或可执行的 Schema 能力 |
| 403 | `definition_publish_forbidden` | 调用者不是超级管理员 |
| 403 | `property_promotion_forbidden` | 提升调用者不是有效管理员或超级管理员 |
| 409 | `property_promotion_conflict` | 代码、幂等键或同来源提升冲突 |
| 409 | `property_promotion_stale` | 来源 revision、记录快照或批准状态已变化 |
| 404 | `unknown_definition_version` | 定义键或版本不存在 |
| 409 | `definition_version_conflict` | 版本重复、跳号或发布后修改 |
| 409 | `definition_upgrade_stale` | 记录在预览后已变化 |
| 409 | `definition_rollback_stale` | 升级事件不是当前记录的可回滚前序事件 |
| 422 | `definition_invalid` | Schema、UI Schema 或记录内条件规则不一致 |
| 422 | `property_promotion_invalid` | 自定义来源、类型、单位或保留代码不符合提升规则 |

## 缓存

客户端和服务可以按 `definition_key + version + checksum` 缓存不可变定义。校验和不一致时丢弃缓存并
重新读取；定义服务不可用且没有可信缓存时，允许只读展示原始核心字段，但禁止无法校验的新写入。
