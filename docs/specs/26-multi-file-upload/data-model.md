# 数据模型：#26

## UploadFile（Redis/临时）

`file_id/task_id/role/original_filename/media_type/kind/size/sha256/sort_order/upload_status/extraction_status/error`。内部存储路径不进入 API。

## PaperFile（MySQL/永久）

`id/paper_id/role/original_filename/stored_path/sha256/size/media_type/sort_order/created_at`。`paper_id + sort_order` 唯一，`sha256` 建索引。

## Paper 扩展

`upload_task_id` nullable unique；旧 `source_file_path` 暂保留并指向 main 文件用于兼容。

## PaperChunk 扩展

`paper_file_id/page_start/page_end`，每段可回溯到具体文件和页码范围。

## Evidence

永久保存 `paper_id/paper_file_id/field_path/chunk_index/section/page_start/page_end/quote`，正式 API 仅按权限和字段白名单返回。
