# 上传科学草稿 API 契约

## GET/PUT 草稿

`GET /api/rag/upload-tasks/{task_id}/draft` 与
`PUT /api/rag/upload-tasks/{task_id}/draft` 返回/接受：

```json
{
  "paper": {"title": "...", "paper_type": "theoretical"},
  "material_states": [
    {
      "material": "Li2MgH16",
      "pressure_value_gpa": 300,
      "pressure_raw": "300",
      "pressure_unit_raw": "GPa",
      "reported_space_group_symbol": "Fd-3m",
      "reported_space_group_number": 227,
      "calculation_context": {
        "lambda_ep": 3.35,
        "omega_log_k": null,
        "phonon_nuclear_treatment": "unknown"
      },
      "tc_results": [],
      "properties": []
    }
  ]
}
```

新响应不得输出 `key_properties` 作为科学事实来源。旧请求可在服务端转换，保存响应必须为新契约。

## 提交

`POST /api/rag/upload-tasks/{task_id}/submit` 沿用现有成功响应：

```json
{"ok": true, "paper_id": 123, "review_status": "pending"}
```

新增/明确错误：

| code | HTTP | 含义 |
|---|---:|---|
| `material_state_required` | 400 | 非综述论文没有材料状态 |
| `material_formula_invalid` | 400 | 材料无法规范化为化学式 |
| `pressure_invalid` | 400 | 压力负值、范围不完整或单位不可安全换算 |
| `space_group_invalid` | 400 | 群号超界或已知符号—群号冲突 |
| `calculation_parameter_invalid` | 400 | λ、ωlog 或 μ* 为负 |
| `scientific_data_integrity_error` | 409 | 非 DOI 的数据库完整性约束失败 |

权限、任务所有权、重复 DOI、附件一致性确认和幂等语义保持现状。

## 兼容边界

- 兼容对象：当前 Redis 中 schema version 2 的扁平草稿。
- 转换位置：后端 `_normalize_draft`；前端同时保留防御性归一化。
- 退出条件：这些 ready 草稿按现有 24 小时生命周期过期后，可删除旧转换分支。
- 失败行为：无法确定材料或单位时不猜测，提交返回可操作错误。
