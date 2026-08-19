# 论文处理接口契约

## 输入

上传接口接收 PDF 及用户可选的材料类型。材料类型可以是现有建议、LLM 建议或用户自定义字符串。

## 处理结果

```json
{
  "processing_status": "processing|succeeded|failed",
  "processing_error": null,
  "paper_type": "theoretical|experimental|review|unknown",
  "theoretical_subtype": "calculation|method|theory|null",
  "sc_type": "hydride|cuprate|iron_based|nickel_based|carbon|organic|others|custom",
  "classification_reason": "string",
  "classification_evidence": [{"section": "string", "page": 1, "quote": "string"}],
  "sc_type_review_status": "none|pending|accepted|modified|merged|rejected"
}
```

## 错误

- `400`：文件类型或输入不合法。
- `413`：文件超过代理或应用配置的上限。
- `502/504`：代理到 Python/LLM 的依赖不可用或超时。
- `500`：抽取、数据库或内部工具错误；响应必须包含用户可读原因和稳定错误码。

## 兼容约束

论文整体 `paper_type` 不得覆盖物性数据的 `article_type`；失败响应不得被前端转换成成功。
