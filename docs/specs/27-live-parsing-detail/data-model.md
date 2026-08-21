# 数据模型：#27

## ChunkManifestItem

`chunk_id/file_id/file_role/index/section/page_start/page_end/status/attempt/updated_at/error_code`。

## ChunkPublicResult

`chunk_id/status/candidates/evidence[{field,quote,page_start,page_end}]/error`。原始 prompt、response、path 和内部评分不属于模型。

## Summary

`status=waiting|processing|completed|incomplete|failed`，包含完成/失败计数、结构化草稿和安全证据引用。

稳定 ID 由 task revision、file_id 和文件内 index 组成；重试不改变 completed 项 ID。
