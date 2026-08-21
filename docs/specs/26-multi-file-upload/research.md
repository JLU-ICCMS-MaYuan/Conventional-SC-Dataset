# 调研记录：#26

- 当前上传请求等同单文件单任务，首个文件完成即入队，无法表达多文件清单。
- `Paper.source_file_path` 只能表示一个文件，`PaperChunk` 也没有来源文件和页码范围。
- 多个上传请求复用整体 Redis JSON 会发生覆盖，必须由 #25 原子 patch 解决。
- Nginx 50M 针对整个 multipart，比应用 50 MiB 文件限制更早触发；canonical 路径需使用 51M 防御阈值。

**决定**：完整 manifest 优先；解析开始后不支持 revision 追加，降低竞态复杂度。
