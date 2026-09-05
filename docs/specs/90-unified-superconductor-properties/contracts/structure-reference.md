# 契约：结构候选检索与 `structure_ref`

## 目的

物性录入不要求用户上传结构。用户填写部分材料条件后，系统可以查找已公开结构并提示是否复用。
查询和关联是两个步骤：查询只读，明确确认后才把 `structure_ref` 写入物性或 Context。

## 候选查询

接口由 Python 结构/上传服务提供，调用方必须是当前草稿或管理员编辑论文的有权用户：

```text
GET /api/rag/structure-references/search
```

请求查询参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `chemical_formula` | 是 | 材料化学式，按现有公式归一化规则处理 |
| `pressure_gpa` | 是 | 当前材料状态的规范压强，必须非负 |
| `space_group_symbol` | 否 | 规范空间群符号；填写时精确匹配 |
| `space_group_number` | 否 | 空间群编号；填写时精确匹配 |
| `geometry_method` | 否 | 结构几何优化方法，标准化后精确匹配 |
| `calculation_code` | 否 | 计算程序，标准化后精确匹配 |
| `exchange_correlation` | 否 | 交换关联泛函，标准化后精确匹配 |
| `nuclear_treatment` | 否 | 核处理方式，标准化后精确匹配 |

匹配规则：

1. 化学式必须标准化后相等。
2. 候选规范压强与请求压强的绝对差必须 `<=0.01 GPa`。
3. 请求中填写的空间群符号或编号必须分别相等；未填写的字段不筛选。
4. 请求中填写的方法字段按大小写、空白和分隔符归一化后精确相等；未填写的字段不筛选。
5. 只搜索已批准论文的当前 revision，且规范身份至少有一个公开来源 `StructureModel`。
6. 结果按压强绝对差升序，再按 `structure_ref` 稳定排序；接口不得因排序而自动选中候选。

返回示例：

```json
{
  "ok": true,
  "data": {
    "query": {
      "chemical_formula": "LaH10",
      "pressure_gpa": 170,
      "space_group_number": 225
    },
    "candidates": [
      {
        "structure_ref": "structure-opaque-1",
        "pressure_gpa": 170.004,
        "pressure_delta_gpa": 0.004,
        "space_group_symbol": "Fm-3m",
        "space_group_number": 225,
        "method": {
          "geometry_method": "relax",
          "calculation_code": "Quantum ESPRESSO",
          "exchange_correlation": "PBE",
          "nuclear_treatment": "harmonic"
        },
        "sources": [
          {
            "paper_id": 432,
            "paper_revision": 2,
            "structure_model_id": 17,
            "title": "公开论文标题"
          }
        ]
      }
    ]
  }
}
```

`sources` 只用于候选解释和审计；确认后不会复制来源论文的 Evidence，也不会把来源
`StructureModel` 的数据库主键暴露为 `structure_ref`。

## 确认与写入

- 前端在候选列表中提供“关联此结构”和“跳过”两个明确结果；候选提示不阻断继续录入。
- 用户确认后，提交请求在 `superconductor_properties[].structure_ref` 或
  `context.structure_ref` 写入不透明引用；同一请求内多条记录可复用同一个引用。
- 多候选未选择、压强距离相同、无候选、用户跳过或用户清空选择时，写入 `null`。
- 已有非空引用不被新的查询结果覆盖；用户必须主动清空或替换。
- 后端保存前验证引用仍存在且至少有一个已公开来源，并验证记录与 Context 的引用一致。

## 错误

| HTTP | code | 条件 |
| --- | --- | --- |
| 400 | `invalid_structure_query` | 化学式/压强缺失、压强为负或字段格式无效 |
| 403 | `structure_candidate_forbidden` | 无权访问当前草稿或管理员编辑对象 |
| 404 | `structure_ref_not_found` | 确认的引用不存在 |
| 409 | `structure_ref_unavailable` | 引用已无公开来源，或来源 revision 不再公开 |
| 422 | `structure_ref_conflict` | 物性和 Context 使用了不同结构引用 |

错误响应沿用统一结构：

```json
{
  "detail": {
    "code": "structure_ref_conflict",
    "message": "物性记录与 Context 的 structure_ref 不一致",
    "issues": [
      {"field": "material_states[0].superconductor_properties[2].structure_ref"}
    ]
  }
}
```

## 兼容与权限

- 旧草稿中缺少 `structure_ref` 时按 `null` 读取，不触发候选查询。
- 候选只返回已批准当前 revision 的公开元数据；待审核、拒绝和草稿结构不可见。
- `structure_ref` 是 API 稳定引用，数据库内部可以使用自增 ID，但不得要求客户端持久化或输入该 ID。
