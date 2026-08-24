# 接口契约：结构候选、预览与导出

**GitHub Issue**：[#49](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/49)

## 草稿响应扩展

`GET /api/upload-tasks/{task_id}` 和现有任务详情响应在当前 `state_schema_version` 下增加：

```json
{
  "structure_candidates": [
    {
      "candidate_id": "sc-01",
      "material_state_ref": "ms-01",
      "source_kind": "pdf_derived",
      "status": "valid",
      "confirmation": "unreviewed",
      "validation": {"atom_count": 14, "elements": ["La", "H"], "ase_valid": true},
      "derivation": {"kind": "space_group_expansion", "label": "推导"},
      "sources": [{"file_id": "file-1", "page": 4, "table": "Table 2", "quote": "..."}],
      "representations": {
        "primitive": {"cif": {"available": true}, "poscar": {"available": true}},
        "conventional": {"cif": {"available": true}, "poscar": {"available": true}}
      }
    }
  ]
}
```

响应不得包含服务器绝对路径、Redis key、RQ job id、LLM 原始响应或无权限候选。

## 草稿更新

`PUT /api/upload-tasks/{task_id}/draft` 接受候选确认、排除、人工修正和导出偏好。服务端必须
重新验证用户提交的结构文本，不信任客户端的 `validation`、`hash` 或 `status`。

```json
{
  "structure_candidates": [
    {
      "candidate_id": "sc-01",
      "confirmation": "confirmed",
      "user_note": "核对 Table 2，保留该压力相"
    }
  ]
}
```

## 预览与导出

- `GET /api/papers/{paper_id}/structures/{structure_id}/preview?cell=conventional`：只返回已授权
  论文当前 revision 的惯用胞预览数据，默认 `cell=conventional`。
- `GET /api/papers/{paper_id}/structures/{structure_id}/download?cell=primitive|conventional&format=cif|poscar`：
  返回对应派生文件流，并在响应中声明 `Content-Disposition` 和结构表示标签。

导出前必须执行论文权限、revision 一致性和结构存在性检查。非法 `cell` 或 `format` 返回 400；
无权限或未批准 revision 返回统一 404/403 语义，具体状态沿用现有论文 API 契约，不泄露候选存在性。

## 提交约束

论文提交只接收 `confirmation=confirmed` 且 `validation.ase_valid=true` 的候选；服务端重新
构造和校验派生结构，在同一事务中创建 `StructureModel`、`PaperEvidence` 和
`StructureModelEvidence`。任何失败整体回滚。
