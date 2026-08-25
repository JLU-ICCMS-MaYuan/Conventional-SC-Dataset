# 接口契约：材料状态分类

## 通用术语对象

普通接口不返回稳定编码：

```json
{
  "id": 1,
  "name": "氢基超导体",
  "aliases": ["氢化物", "Hydride"]
}
```

结构家族选择增加 `is_primary`。停用项不进入新选择列表；读取历史记录时由后端解析到当前规范项。

## GET /api/classification-catalogs

**权限**：公开读取启用项；不返回审计、待审核建议或内部编码。

**响应 200**：

```json
{
  "material_families": [
    {"id": 1, "name": "氢基超导体", "aliases": ["氢化物", "Hydride"]}
  ],
  "structure_families": [
    {"id": 1, "name": "笼状结构", "aliases": ["clathrate"]}
  ],
  "material_dimensionalities": [
    {"value": "three_dimensional", "name": "三维"},
    {"value": "unknown", "name": "未知"}
  ]
}
```

缓存可以使用短期 ETag，但目录修改后必须失效。

## 上传草稿 GET

`GET /api/rag/upload-tasks/{task_id}/draft` 的每个 `material_states[]` 返回：

```json
{
  "material": "LaH10",
  "material_family": {"id": 1, "name": "氢基超导体", "status": "confirmed"},
  "structure_families": [
    {"id": 2, "name": "笼状结构", "is_primary": true, "status": "confirmed"}
  ],
  "element_count": 2,
  "material_dimensionality": "three_dimensional",
  "pressure_value_gpa": 150
}
```

待确认名称使用 `id=null` 和 `status=pending`：

```json
{
  "material_family": {
    "id": null,
    "name": "待确认名称",
    "status": "pending"
  }
}
```

普通草稿不得包含 `sc_type`、`type_code`、`type_proposal_raw` 或 `referenced_materials`。旧草稿 GET 可以附加 `classification_migration_warnings: string[]`，但响应仍只使用新结构。

## 上传草稿 PUT 与 submit

- PUT 和 submit 拒绝顶层 `sc_type` 或材料状态外的分类字段，返回 `400 legacy_classification_contract`。
- 正式选择必须同时提供可用目录 `id` 和后端查询得到的规范 `name`；后端以 ID 为准并重写名称，不信任浏览器名称。
- 待确认项必须 `id=null/status=pending/name` 非空。
- 每个非综述材料状态必须有正式材料家族或待确认材料家族；完全缺失返回 `400 material_family_required`。
- 元素种类数由后端重新计算，浏览器提交值只用于显示，不作为事实来源。
- submit 可以写入 pending 论文和分类建议；批准论文前所有主材料家族及元素种类数必须确认。

## PUT /api/admin/papers/{paper_id}/material-classifications

**权限**：管理员或超级管理员；管理员不得审核自己上传的论文。

**请求**：

```json
{
  "material_states": [
    {
      "id": 42,
      "material_family_id": 1,
      "material_dimensionality": "three_dimensional",
      "structure_families": [
        {"id": 2, "is_primary": true}
      ]
    }
  ]
}
```

**行为**：只更新属于论文当前 revision 的状态；事务性替换结构家族关联并验证唯一主项。未知、停用、跨论文或旧 revision ID 返回 400/404，不产生部分更新。

## GET /api/admin/classification-proposals

**权限**：管理员或超级管理员。

支持 `status`、`dimension`、`limit`、`offset`。响应包含待确认名称、材料状态摘要、论文信息、内部分类证据和允许动作。

## POST /api/admin/classification-proposals/{id}/map

**权限**：管理员或超级管理员。

```json
{
  "target_id": 1,
  "reason": "论文明确归类为氢化物"
}
```

把建议映射到已有启用目录项，更新材料状态归属，结论为 `mapped_existing`，追加审核证据和审计。请求幂等；终态建议不能改写。

## POST /api/admin/classification-proposals/{id}/recommend

**权限**：管理员或超级管理员。

```json
{
  "resolution_kind": "alias_created",
  "target_id": 1,
  "reason": "该名称是氢基超导体的可靠同义词"
}
```

普通管理员只把建议转为 `under_review`，不能建立可匹配别名或正式项。

## 超级管理员目录治理

```text
POST  /api/superadmin/classification-catalogs/{dimension}
PATCH /api/superadmin/classification-catalogs/{dimension}/{id}
POST  /api/superadmin/classification-catalogs/{dimension}/{id}/merge
POST  /api/superadmin/classification-proposals/{id}/resolve
GET   /api/superadmin/classification-audits
```

所有写请求要求非空 `reason`。创建和重命名验证规范名及别名唯一；停用被引用项允许历史读取但不能新选；合并迁移归属和别名。成功写入和审计同事务，失败不产生半审计。

## 论文审核批准门

`POST /api/admin/papers/{id}/review` 当 `status=approved` 时额外验证：

- 当前 revision 每个材料状态的 `material_family_id` 非空且指向启用或可历史读取的正式项；
- `element_count` 为 1–118；
- 不存在该论文当前 revision 的未解决材料家族建议。

失败返回 `409 classification_incomplete` 和缺失状态 ID，不改变论文状态。

## 错误语义

| code | HTTP | 含义 |
| --- | --- | --- |
| `catalog_unavailable` | 503 | 目录读取失败，客户端可重试 |
| `legacy_classification_contract` | 400 | 新写请求仍含旧字段 |
| `material_family_required` | 400 | 状态既无正式项也无待确认名称 |
| `classification_not_found` | 404 | 目录项或建议不存在 |
| `classification_inactive` | 409 | 试图新选停用或已合并项 |
| `alias_conflict` | 409 | 规范化别名已属于其他项 |
| `classification_incomplete` | 409 | 论文不满足批准门 |
| `proposal_already_resolved` | 409 | 终态建议被重复改写 |
| `forbidden` | 403 | 角色无权执行治理动作 |
