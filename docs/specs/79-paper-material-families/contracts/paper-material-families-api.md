# 接口契约：论文级 Material family

**GitHub Issue**：[#79](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/79)

**日期**：2026-09-02

## 统一选择项

```json
{
  "id": 1,
  "name": "氢基超导体",
  "name_zh": "氢基超导体",
  "name_en": "Hydride superconductor",
  "status": "confirmed"
}
```

- `confirmed` 必须有目录 `id`。
- `pending` 必须没有 `id` 且有非空 `name`。
- 列表按 `id` 或规范化名称去重。

## 上传草稿

`GET/PUT /api/rag/upload-tasks/{task_id}/draft`

```json
{
  "paper": {
    "paper_type": "experimental",
    "theoretical_subtype": null,
    "material_families": [
      { "id": 1, "name": "氢基超导体", "status": "confirmed" },
      { "id": null, "name": "自定义家族", "status": "pending" }
    ]
  },
  "material_states": [
    {
      "material": "LaH10",
      "structure_families": [],
      "tc_results": []
    }
  ]
}
```

PUT 草稿允许空 `material_families`。新写入的 `material_states[].material_family` 返回 400 `legacy_classification_contract`。

## 提交

`POST /api/rag/upload-tasks/{task_id}/submit`

- `paper.material_families` 为空：400 `material_family_required`。
- 选择项形态非法：400 `invalid_material_family`。
- Paper type 与理论子分类的既有错误语义不变。

## 管理员科学数据整体保存

`PUT /api/rag/papers/{paper_id}/scientific-draft`

```json
{
  "paper_type": "experimental",
  "material_families": [
    { "id": 1, "name": "氢基超导体", "status": "confirmed" }
  ],
  "material_states": [],
  "structure_candidates": []
}
```

列表为空返回 400 `material_family_required`。成功响应保持 #76 结构。该请求校验并携带当前论文级候选；已有正式关联在升版时通过复合外键级联到新版本，不在 Python 重写阶段删除。最终关联仍只由 Go 批准事务整体替换，避免提前创建待确认目录项。

## 管理审核

审核请求和分类快照使用顶层 `material_families[]`；`material_states[]` 中只携带 `structure_families[]` 等状态级分类。批准时列表为空返回 409 `classification_incomplete`，事务不创建目录、不改变论文状态。

## 论文详情

管理详情与公开详情在论文对象顶层返回：

```json
{
  "material_families": [
    { "id": 1, "code": "hydride", "name": "氢基超导体", "name_zh": "氢基超导体", "name_en": "Hydride superconductor" }
  ],
  "material_states": [
    { "structure_families": [] }
  ]
}
```

不再返回 `material_states[].material_family`。

## 社区统计与筛选

- Material family 条件按论文级关联匹配。
- 命中某 family 后，该论文的全部材料结果均参与筛选结果。
- 同一论文可分别命中多个 family 查询。
- 未提供 family 条件时不展开论文—family 关联，聚合和总计不因多标签重复。

## 兼容边界

- AI 汇总归一化可以有限读取状态级候选并提升到论文级；该兼容只存在于内部解析结果，不接受客户端新 PUT。
- 已持久化旧数据通过 Alembic 一次性迁移，不在正常详情查询中保留双读。
