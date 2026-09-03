# 契约：Tc 草稿条件字段

**GitHub Issue**：[#84](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/84)

## 请求规则

以下规则适用于 `PUT /api/rag/upload-tasks/{task_id}/draft`、`POST /api/rag/upload-tasks/{task_id}/submit` 和 `PUT /api/rag/papers/{paper_id}/scientific-draft` 的 `material_states[].tc_results[]`。

```json
{
  "result_kind": "experimental",
  "tc_method": "experimental",
  "tc_value_k": 203,
  "calculation_context": null
}
```

实验条目不得带有对象形式的 `calculation_context`，也不得带其参数键。服务端拒绝示例：

```json
{
  "detail": {
    "code": "experimental_tc_calculation_context_forbidden",
    "message": "第 1 个材料状态的第 2 条 Tc 选择 experimental 方法时不能包含计算上下文"
  }
}
```

错误状态为 400；科学数据写入必须作为整体事务失败。

## 客户端状态转换

`non-experimental → experimental`：保留 Tc 值、范围、原始值、单位和证据，删除 `calculation_context` 与其全部子键。

`experimental → non-experimental`：允许创建空的计算上下文供用户填写，不从已删除值中恢复旧参数。
