# PDF 摄入

## 功能说明

接收 PDF、TXT 或 Markdown 文件并通过摄入流水线提取文献内容，创建待审核论文占位记录，并在后台执行文本抽取、LLM 富化、关键物性写入和向量化。

## 当前行为

- `/api/rag/upload-pdf` 只接受 PDF，`/api/rag/upload-text` 只接受 TXT/MD。
- API 会把文件保存到 `data/uploads`，并尝试立即创建 `papers` 占位记录，状态为 `pending`，前端展示为“解析中”。
- 后台任务对 PDF 执行文本抽取，对 TXT/MD 直接读取文本；随后写入论文元信息、向量化文本块，并通过 LLM 富化写入 `key_properties`。
- 上传者 ID 会从 Bearer token 中解析，无法解析时允许为空。
- 上传历史由 `/api/papers/my-uploads` 返回当前用户上传论文及关键物性。

## 工作流程

客户端在 `/upload` 选择论文文件；API 保存文件并创建占位论文；后台管线执行文本抽取、`store_extraction()`、`chunk_and_embed()`、`enrich_single()` 和 `ingest_paper()`；完成后删除上传临时文件，前端上传历史可进入论文编辑详情。

## 约束

- PDF、TXT、MD 以外的文件会被拒绝；PDF 可能因扫描件或文本过短导致后台处理失败。
- 论文占位和关键物性会写入主业务表；向量数据写入 Qdrant。
- 后台富化失败不阻塞初始上传响应，失败只会影响后续结构化物性和检索质量。

## 代码与测试

- `backend/api/rag.py`
- `backend/ingest/pipeline.py`
- `backend/ingest/store_papers.py`
- `backend/ingest/embedder.py`
- `backend/ingest/enrich_papers.py`
- `frontend/src/pages/UploadPage.tsx`
- `tests/05_rag_question_answering/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 上传占位记录与后台富化失败之间的用户提示、重试和重复文档策略待核验。
