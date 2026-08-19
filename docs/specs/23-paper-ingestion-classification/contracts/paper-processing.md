# 论文处理接口契约

## 输入

上传接口要求登录，接收 PDF/TXT/MD，持久化原文件并立即返回 `202` 与任务编号。

## 处理结果

```json
{
  "task_id": "uuid",
  "stage": "saving_file|extracting|reading|summarizing|ready",
  "stage_index": 1,
  "stage_total": 5,
  "processing_status": "processing|succeeded|failed",
  "processing_error": null,
  "completed_chunks": 0,
  "total_chunks": 0,
  "paper_type": "theoretical|experimental|review|unknown",
  "theoretical_subtype": "calculation|method|theory|null",
  "sc_type": "hydride|cuprate|iron_based|nickel_based|carbon|organic|others|custom",
  "classification_reason": "string",
  "classification_evidence": [{"section": "string", "page": 1, "quote": "string"}],
  "sc_type_review_status": "none|pending|accepted|modified|rejected"
}
```

## 草稿接口

- `GET /api/rag/upload-tasks/{task_id}`：查询状态，限上传者或管理员。
- `GET /api/rag/upload-tasks/{task_id}/draft`：读取 AI/用户草稿和证据。
- `PUT /api/rag/upload-tasks/{task_id}/draft`：续期 24 小时并保存草稿。
- `POST /api/rag/upload-tasks/{task_id}/retry`：仅重跑失败或未完成段。
- `POST /api/rag/upload-tasks/{task_id}/submit`：校验并原子写入 MySQL，返回 `paper_id` 和 `pending`。
- `GET /api/rag/papers/{paper_id}/candidate-attachments`：管理员查看同 DOI、不同哈希的候选附件。
- `GET /api/rag/papers/{paper_id}/candidate-attachments/{attachment_id}`：管理员鉴权下载候选附件。
- `POST /api/rag/papers/{paper_id}/publish`：仅将已审核通过论文的正式 MySQL 文本块发布到 Qdrant。

## 错误

- `400`：文件类型或输入不合法。
- `413`：文件超过代理或应用配置的上限。
- `502/504`：代理到 Python/LLM 的依赖不可用或超时。
- `500`：抽取、数据库或内部工具错误；响应必须包含用户可读原因和稳定错误码。
- `401/403`：未登录或不是任务所有者/管理员。
- `409`：相同 DOI 已存在；响应包含已有论文 ID和重复文件处理结果。

## 兼容约束

论文整体 `paper_type` 不得覆盖物性数据的 `article_type`；失败响应不得被前端转换成成功。
新审核状态只允许 `pending/approved/rejected`；历史 `needs_revision` 只读兼容。
