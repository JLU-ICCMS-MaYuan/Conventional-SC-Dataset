# 数据模型：材料状态分类与审核快照

## material_families

| 字段 | 约束 | 含义 |
| --- | --- | --- |
| `id` | PK | 正式稳定 ID |
| `code` | UNIQUE、内部字段 | 服务端自动生成或 seed 编码 |
| `name_zh` | UNIQUE、非空 | 普通界面显示的规范中文名 |
| `name_en` | 可空 | seed 或维护数据中的英文名 |
| `normalized_name` | UNIQUE、非空 | 确定性查重键 |
| `created_by_user_id` | 可空 FK | 审核内创建者；seed 为空 |
| `created_at/updated_at` | 时间 | 生命周期信息 |

不包含 `is_active` 或 `merged_into_id`，不提供在线重命名、停用或合并。

## material_family_aliases

保存可靠 seed 别名。`normalized_alias` 全局唯一，只参与精确匹配，不提供在线写 API。

## structure_families / structure_family_aliases

与材料家族结构相同。首批 seed 为“笼状结构”；审核者可在批准事务中创建新的规范结构家族。

## material_states

保留以下独立分类字段：

| 字段 | 含义 |
| --- | --- |
| `material_family_id` | 人工确认后的材料家族 FK，可空直到批准 |
| `element_count` | 规范化化学式中的不同元素种类数 |
| `material_dimensionality` | 七值受控枚举 |
| 压力字段 | 独立的数值、范围和原文 |

材料家族缺失或 `element_count` 无效时不得批准。

## material_state_structure_families

材料状态与结构家族的多对多关系。复合主键防止重复关系；`primary_marker` 为 `VIRTUAL GENERATED` 列，唯一约束保证每个状态最多一个主结构家族。

## paper_review_events.classification_snapshot

可空 JSON，只在单篇批准时写入。结构：

```json
{
  "context": {
    "classification_reason": "AI/贡献者理由",
    "classification_scope": []
  },
  "material_states": [
    {
      "id": 18,
      "material_family": {"id": 1, "name": "氢基超导体"},
      "material_dimensionality": "three_dimensional",
      "structure_families": [
        {"id": 1, "name": "笼状结构", "is_primary": true}
      ]
    }
  ]
}
```

快照中的最终名称必须来自数据库查询结果，而不是直接信任请求名称。

## 删除的旧结构

- `classification_proposals`
- `classification_evidences`
- `classification_audit_events`
- `material_families.merged_into_id/is_active`
- `structure_families.merged_into_id/is_active`

AI 建议与证据由 review artifact 和批准快照承载；不再建立第二套分类状态机。
