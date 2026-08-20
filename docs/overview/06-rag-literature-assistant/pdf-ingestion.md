# PDF 摄入

## 功能说明

登录用户上传 PDF、TXT 或 Markdown 后，系统异步读取全文并生成可编辑 AI 草稿。用户确认并提交前不写入 MySQL；管理员审核通过后，论文才进入公开查询和正式 Qdrant 索引。

## 工作流程

1. 页面允许选择不超过 50 MB（50 MiB）的 PDF、TXT 或 Markdown；Python API 执行精确文件大小校验。Nginx 上传路由允许 51 MB 请求体，以容纳 50 MB 文件之外的 multipart 表单边界。
2. Python 将原文件保存到 `/data/upload_PDFs`，在 Redis 创建 24 小时任务并返回 `202 + task_id`。
3. RQ Worker 依次执行保存原文件、提取正文、LLM 分段阅读、LLM 全文汇总和等待用户校对五个阶段。
4. Markdown 保存到 `/data/parsed_markdown`；AI 原值、证据和用户草稿分别保存在临时 JSON 与 Redis，不写入正式业务表。
5. 用户停止编辑 5 秒后自动保存，也可立即保存；点击提交后，论文、物性和正式文本块在一个 MySQL 事务中写入并进入 `pending`。
6. 管理员对照 AI 建议、用户值和原文证据审核。`approved` 会同步发布 Qdrant 后清理临时证据；`rejected` 清理临时证据；`pending` 保留证据。

## 分类规则

- 全文分段读取后再汇总判断，不能只按摘要或化学式分类。
- 理论贡献主导、实验用于验证理论时为 `theoretical`；实验发现主导、理论用于解释现象时为 `experimental`；两者同等重要时按 `experimental`。
- 理论二级类型为 `calculation`、`method`、`theory`。新算法、新模型或研究工具归 `method`。
- 论文整体类型与每条物性的实验/理论来源 `article_type=e|t` 分开保存。
- 材料类型允许已有建议、LLM 自由文本和用户自由文本；管理员在论文审核时确认最终值。

## 持久化与可见性

- Redis：任务阶段、错误、进度和未提交草稿，按最后操作时间滑动保留 24 小时。
- MySQL：用户提交后的最终候选值和 `pending/approved/rejected` 审核状态；不保存处理进度、失败历史或 AI 原始判断。
- 文件目录：未提交任务的原文件、Markdown 和 AI 产物在任务过期后删除；已提交论文的原文件和 Markdown 永久保留，审核期 AI 产物保留到管理员通过或拒绝。
- 公开 API、统计和 RAG 只返回 `approved` 论文；原 PDF、Markdown、待审数据和内部文件路径不公开。

## 重复文件

- 文件哈希与已有原文件相同：删除新副本并打开已有论文。
- DOI 相同但文件不同：禁止创建草稿，将新文件保存为该论文的管理员候选附件，不覆盖原文件。
- 候选附件列表和下载接口仅管理员可访问。

## 失败语义

- 上传、抽取、LLM 和数据库错误必须返回或记录明确原因，前端不得显示假成功。
- 超过 50 MB 的文件会在选择或上传阶段明确提示；即使 Nginx 返回非 JSON 的 HTTP 413，页面也显示相同的大小限制信息。
- 扫描版或正文过短的 PDF 明确提示需要可搜索文本；本功能不包含 OCR。
- 审核通过后若向量发布失败，Go API 返回 `502`，保留临时证据；管理员重复审核即可幂等重试。

## 主要实现

- `backend/api/rag.py`
- `backend/ingest/upload_jobs.py`
- `backend/ingest/upload_tasks.py`
- `backend/rag/llm.py`
- `frontend/src/components/UploadTaskEditor.tsx`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/AdminPage.tsx`
- `goserver/handlers/admin.go`
- `goserver/handlers/stats.go`
