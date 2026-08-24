# 上传草稿契约：删除 phase_label

## 新请求

`GET/PUT /api/rag/upload-tasks/{task_id}/draft` 和提交链路中的 `material_states[]` 不包含 `phase_label`。

```json
{
  "material": "Li2MgH16",
  "pressure_value_gpa": 250,
  "state_kind": "theoretical",
  "reported_space_group_symbol": "Fm-3m",
  "reported_space_group_number": 225
}
```

## 兼容读取

- 旧草稿含 `phase_label` 时，GET/PUT/submit 在兼容窗口内不得失败。
- 归一化结果删除该键；新保存和新 AI 输出不得重新产生该键。
- 旧值不得自动填入空间群字段。

## 校验

- `reported_space_group_number` 为空或 1–230。
- 空间群符号和群号可独立为空；不得由自由文本 `phase_label` 推断。
- `state_kind` 仅允许 `theoretical/experimental/mixed/unknown`。

## 失败语义

- 空间群群号越界返回稳定校验错误。
- 旧字段只被忽略，不返回“未知字段”错误。
- 提交时所有材料状态仍必须有材料；非综述论文仍需至少一个材料状态。
