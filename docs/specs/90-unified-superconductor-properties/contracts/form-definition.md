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

发布后定义内容不可修改。停用只改变是否可用于新建，不改变历史读取。

## 记录版本升级

```http
POST /api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/preview
POST /api/admin/papers/{paper_id}/property-records/{record_key}/definition-upgrade/apply
```

预览返回目标版本、字段转换、将清除的字段和校验问题。执行必须携带预览结果的校验和；记录在预览后
发生变化时返回冲突，不得套用过期转换。

## 错误

| HTTP | 错误码 | 含义 |
| --- | --- | --- |
| 400 | `unsupported_schema_keyword` | 使用了不支持或可执行的 Schema 能力 |
| 403 | `definition_publish_forbidden` | 调用者不是超级管理员 |
| 404 | `unknown_definition_version` | 定义键或版本不存在 |
| 409 | `definition_version_conflict` | 版本重复、跳号或发布后修改 |
| 409 | `definition_upgrade_stale` | 记录在预览后已变化 |
| 422 | `definition_invalid` | Schema、UI Schema 或组级规则不一致 |

## 缓存

客户端和服务可以按 `definition_key + version + checksum` 缓存不可变定义。校验和不一致时丢弃缓存并
重新读取；定义服务不可用且没有可信缓存时，允许只读展示原始核心字段，但禁止无法校验的新写入。
