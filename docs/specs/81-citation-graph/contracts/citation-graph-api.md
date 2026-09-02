# API 契约：引用图谱

**GitHub Issue**：[ #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)

## `GET /api/knowledge-graph/overview`

公开分类概览。`material_family_id` 可重复传入；与可选的 `superconductor_kind` 取 AND。

```text
GET /api/knowledge-graph/overview?material_family_id=1&superconductor_kind=conventional&limit=30
```

`superconductor_kind` 只接受 `conventional` 或 `unconventional`；`limit` 范围 1–100，默认 30。

```json
{
  "nodes": [{
    "paper_id": 42,
    "label": "High-Temperature Superconductivity in Cuprates",
    "title": "High-temperature superconductivity in a copper oxide...",
    "year": 1986,
    "material_families": [{"id": 3, "name": "铜基超导体"}],
    "superconductor_kind": "unconventional",
    "citation_count": 12,
    "marks": ["origin", "breakthrough"]
  }],
  "edges": [{"citing_paper_id": 48, "cited_paper_id": 42}],
  "total_nodes": 1
}
```

`year` 对 SC-Wiki 论文始终为有效整数，不返回 `null`。只有原始外部参考文献的 `paper_references.year` 允许为空，且该字段不直接出现在公开节点契约中。

## `GET /api/knowledge-graph/papers/:paperId/neighbors`

公开分页展开接口。

```text
GET /api/knowledge-graph/papers/42/neighbors?direction=downstream&offset=0&limit=5
```

- `direction`：`upstream`（当前论文引用的工作）或 `downstream`（引用当前论文的工作）。
- `offset`：非负，默认 0。
- `limit`：1–50，默认 5；前端默认只请求 5。
- 结果按邻居的库内被引次数降序、`paper_id` 升序稳定排序。

```json
{
  "center_paper_id": 42,
  "direction": "downstream",
  "nodes": [],
  "edges": [],
  "offset": 0,
  "limit": 5,
  "remaining_count": 17
}
```

`remaining_count` 是同方向的精确未返回邻居数。服务端不递归展开，更不返回整层子图。

## `GET /api/knowledge-graph/search`

从全部当前已审核 Paper 标题和 DOI 搜索，供前端固定节点。

```text
GET /api/knowledge-graph/search?q=mercury&limit=10
```

返回 `nodes[]` 的节点形态；空关键词、超限参数返回 400。未被当前分类概览选中的论文仍允许返回。

## `PUT /api/admin/papers/:paperId/graph-marks`

管理员或超级管理员整体替换人工标记。

```json
{"marks": ["origin", "breakthrough"]}
```

- 只允许 `origin`、`breakthrough`，去重后保存。
- 未审核论文返回 409；普通用户由认证中间件拒绝。
- 成功返回当前 `marks`。

## 错误语义

| 状态 | `code` | 含义 |
| --- | --- | --- |
| 400 | `invalid_graph_filter` | 参数值、范围或方向非法 |
| 404 | `paper_not_found` | 目标不是可公开的当前已审核论文 |
| 409 | `paper_not_approved` | 管理员尝试标记非审核通过论文 |
| 503 | `reference_parser_unavailable` | GROBID 暂不可用；上传草稿仍可校对 |
