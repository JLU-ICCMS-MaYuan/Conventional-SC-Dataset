# API 契约：材料分类目录与论文审核

## GET /api/classification-catalogs

返回数据库目录，普通用户可读，不暴露内部编码或英文维护字段。

```json
{
  "material_families": [
    {"id": 1, "name": "氢基超导体", "aliases": ["hydride", "高压氢化物"]}
  ],
  "structure_families": [
    {"id": 1, "name": "笼状结构", "aliases": ["clathrate"]}
  ],
  "material_dimensionalities": [
    {"value": "three_dimensional", "name": "三维"}
  ]
}
```

候选为空是合法响应；数据库错误返回 `503 catalog_unavailable`。

## POST /api/admin/papers/{paper_id}/review

**权限**：管理员或超级管理员；不能审核自己上传的论文。

批准请求：

```json
{
  "status": "approved",
  "comment": "证据充分",
  "review_request_id": "uuid",
  "material_states": [
    {
      "id": 18,
      "material_family": {"id": 1, "name": "氢基超导体"},
      "material_dimensionality": "three_dimensional",
      "structure_families": [
        {"id": 1, "name": "笼状结构", "is_primary": true},
        {"id": 0, "name": "层状结构", "is_primary": false}
      ]
    }
  ],
  "classification_context": {
    "classification_reason": "AI 与贡献者的原始理由",
    "classification_scope": []
  }
}
```

### 选择语义

- `id > 0`：必须是数据库已有项，服务端忽略请求中的显示名并使用数据库规范名。
- `id = 0/null` 且 `name` 非空：先按规范名、英文名、编码和 seed 别名精确匹配；没有结果才创建新项。
- 名称为空、重复结构项、超过一个主结构、非法材料维度、跨论文或旧 revision 状态均拒绝。
- `classification_context` 只进入内部审核快照，最大 256 KiB，不进入公开论文 DTO。

### 事务顺序

幂等检查 → 锁定当前 revision → 解析或创建目录 → 写最终分类 → 完整性校验 → 更新论文 → 写审核事件。

任一步失败不产生部分写入。拒绝或退回请求忽略 `material_states`，不得创建目录或覆盖分类。

### 典型错误

| code | HTTP | 含义 |
| --- | --- | --- |
| `classification_incomplete` | 409 | 材料家族或元素数仍不完整 |
| `classification_not_found` | 404 | 论文、状态或已有目录 ID 不存在 |
| `classification_invalid` | 400 | 选择、维度或主结构约束无效 |
| `classification_name_conflict` | 409 | 名称与其他目录或 seed 别名冲突 |
| `forbidden` | 403 | 无审核权限或审核自己的论文 |

## POST /api/admin/papers/batch-review

- `status=approved`：返回 400，提示逐篇确认材料分类。
- `status=rejected|pending`：维持原批量审核行为，不创建分类。

## 已删除接口

- `PUT /api/admin/papers/{id}/material-classifications`
- `/api/admin/classification-proposals*`
- `/api/superadmin/classification-proposals*`
- `/api/superadmin/classification-catalogs*`
- `GET /api/superadmin/classification-audits`

目录的新建只发生在单篇论文批准事务中。
