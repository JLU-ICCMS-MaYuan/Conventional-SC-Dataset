# PDF 解析管线

## 功能说明

本功能描述上传任务从文件接收到生成待校对草稿、再到提交落库与发布向量索引的完整处理链路，是 01 目录的主线文档。文件校验与摄入约束见 [PDF 摄入](pdf-ingestion.md)；晶体结构附件的审核与默认结构选择见 [上传、审核与默认结构](upload-review-and-default-selection.md)。

## 入口与任务创建

- 前端入口是 `/upload`。用户声明一组文件，每个文件带 `client_id`、`role`（`main` / `supplementary` / `attachment`）、文件名和大小；支持 PDF、TXT、MD、CIF、POSCAR，单文件最大 50 MB，同时上传最多 3 个。
- `POST /api/upload-tasks`（`backend/api/upload_tasks.py`）调用 `create_task`：任务状态存入 Redis（带 TTL），同一用户活动任务上限 100；`TASK_ID_PATTERN` 为 32 位十六进制。
- 上传的原始文件落盘到 `upload_PDFs/{task_id}/`，状态中记录 `sha256`、大小和角色。
- “开始上传并解析”后，任务被推入 RQ 队列 `scwiki-upload`，由 worker 容器（`rq worker --with-scheduler scwiki-upload`）执行 `backend.ingest.upload_jobs.process_upload_task`（`backend/ingest/upload_jobs.py`）。
- `/api/upload-tasks` 在 Docker 部署中由 Go 未匹配路由转发到 Python FastAPI；前端按约 2 秒间隔轮询 `/api/upload-tasks/{task_id}` 与 `/parsing` 获取进度。

## 五阶段状态机

`process_upload_task` 把处理过程划分为五个阶段，`stage_index` 与前端“第 X/5 步”一一对应：

| 步骤 | status / stage | 行为 | 主要产物 |
| --- | --- | --- | --- |
| 1 | 保存原始文件 | 文件落盘并记录哈希 | `upload_PDFs/{task_id}/` |
| 2 | `extracting` | 提取论文正文 | `parsed_markdown/{task_id}/{file_id}.md`、合并稿 `parsed_markdown/{task_id}.md` |
| 3 | `reading` | AI 分段阅读 | `review_artifacts/{task_id}/` 分段结果与 manifest |
| 4 | `summarizing` | AI 汇总草稿 | 归一化草稿（Redis）、`result.json` 快照 |
| 5 | `ready` | 等待用户校对 | 终态清理排程 |

### 第 2 步：提取论文正文（extracting）

- PDF 经 `pdf_extractor.py` 转为带页标记（`<!-- page: N -->`）的 Markdown；TXT/MD 直接读取；已提取过的文件直接复用缓存的 `.md`。
- CIF/POSCAR 原生附件不走文本提取，而是经 ASE 校验（`structure_extractor.build_structure_candidate`）生成结构候选；校验失败的候选标记为 `blocked`，等待人工处理。
- 任务解析生成的结构候选以 `material_state_ref="unassigned:*"` 标记，需在校对页「未分配结构候选」区分配到具体材料状态并确认（`material_state_ref` 变为 `material_states[N]`、`confirmation=confirmed`）后才会在提交时写入 `structure_models`；未确认的候选只作为附件文件保存，不落库。（[Issue #77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)）
- 非结构 PDF 的正文还会经 `extract_structure_candidates` 从文本中抽取结构候选。
- 多文件任务逐文件处理并更新 `extraction_status`，全部完成后用 `compare_file_identities` 做身份一致性检查（同一论文的 DOI/标题线索），结果写入状态 `consistency`。
- 正文为空时直接失败（`论文正文为空，无法生成可校对草稿`）。

### 第 3 步：AI 分段阅读（reading）

- `chunker.py` 把合并前的各文件 Markdown 切成 `Chunk`，`_chunks_with_preamble` 为每个文件补一个前言段；分段清单写入 `review_artifacts/{task_id}/chunk_manifest.json`，每段状态在 `waiting / processing / completed / failed` 间流转。
- 逐段调用 `_read_chunk`（LLM 提取，DeepSeek/OpenAI 配置），分段结果以 JSON 存到 `review_artifacts/{task_id}/chunks/`；任一分段异常即整任务失败。
- 每完成一段更新 `completed_chunks / total_chunks`，前端进度条（如“4/28 段”）即来源于此。

### 第 4 步：AI 汇总草稿（summarizing）

- `_summary_classification_candidates` 先过滤掉非当前论文的过期证据，再把分段候选交给 `complete_json(SUMMARY_SYSTEM_PROMPT, ...)` 汇总为一份结构化草稿。
- 汇总 prompt（`SUMMARY_SYSTEM_PROMPT`）与正文提取（`extractor.py`）都要求以英文产出六个叙述字段（`summary`、`keywords_tags`、`methodology`、`key_finding`、`research_motivation`、`knowledge_graph_title`），与英文论文原文语言一致；某字段无原文依据时保持为空，不编造内容。（[Issue #74](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/74)）
- 正文 PDF 在 Worker 中额外提交给本地 GROBID 的 `processFulltextDocument` 接口。GROBID 返回的 TEI `biblStruct` 会提取 DOI、题名、作者、年份和原始引文，随论文版本保存到 `paper_references`；GROBID 不可用或解析不完整时保存状态，不由 LLM 猜造引用边。（[Issue #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)）
- `_normalize_draft` 把草稿归一化为当前数据契约：论文元信息（含单选 `superconductor_kind` 和多选 Material family）、`material_states`（材料、压强/温度/磁场、计算与实验上下文、`tc_results`、More type labels）、分类证据等。旧草稿的状态级 `superconductor_kind` 只在读取时一次性提升：唯一的非 `unknown` 值保留，冲突时回退 `unknown`；新提交拒绝该旧字段。
- 汇总后执行查重：先按归一化 DOI（`normalize_doi`）查 `papers`，再按原始文件 SHA-256 查；命中即进入 `_handle_duplicate`，任务以 `duplicate` 状态短路结束。
- 草稿写入 Redis（`save_draft`），同时把 `ai_values` 与证据快照（分类证据、材料状态各字段证据）写入 `review_artifacts/{task_id}/result.json`。

### 第 5 步：等待用户校对（ready）

- `processing_status=succeeded`，任务进入可校对状态；`_schedule_terminal_cleanup` 通过 RQ scheduler 排程终态清理。
- 取消（`cancelled`）与失败（`failed`，`error_code=paper_processing_failed` 并记录 `failed_stage`）同样进入终态清理排程；清理由 `cleanup_upload_task` 执行。

## 用户校对与提交落库

- 用户在前端校对编辑草稿后调用 `POST /api/upload-tasks/{task_id}/submit`（`backend/api/rag.py`），全程持有任务锁，重复提交按已提交结果幂等返回。
- `_create_pending_paper` 在一个数据库事务内完成：
  - 创建 `Paper`（`review_status=pending`、`content_revision=1`、`upload_task_id` 关联任务、论文级 `superconductor_kind`）与 `PaperFile`（角色、存储路径、SHA-256、排序）。
  - `persist_scientific_draft`（`backend/ingest/scientific_drafts.py`）把草稿落成科学实体图：`superconductors` → `material_states` → `structure_models`（含经用户确认的原生 CIF/POSCAR 附件，服务端重新 ASE 校验并以常规晶胞 CIF 为规范表示，不信任浏览器提交的校验/哈希字段）→ `calculation_contexts` / `experimental_contexts` → `tc_results` → `superconductor_properties`，并返回证据链接目标。
  - `chunk_paper` 对正文重新分段写入 `paper_chunks`；草稿证据按 `(file_id, chunk_index)` 或页码范围匹配到具体 chunk，写入 `paper_evidences` 并挂接 `add_scientific_evidence_link`。
  - 违反完整性约束时整体回滚，返回 409 `scientific_data_integrity_error`。
- `_record_submitted_upload` 把 `ai_values / user_values / evidence` 快照写回 `result.json`，`cleanup_transient_data` 清理临时数据但保留审核快照；任务状态置为 `submitted`。

## 审核通过与向量发布

- 提交后的论文进入待审核队列，审核决策属于 02 目录的论文与记录审核。
- 审核通过后，管理员调用 `POST /api/papers/{paper_id}/publish`：`embed_and_index_chunks`（`backend/ingest/embedder.py`）把 `paper_chunks` 内容向量化并写入 Qdrant `paper_chunks` collection，此后 RAG 检索可用；论文未通过审核时调用返回 409 `paper_not_approved`。

## 当前边界与待核验

- 旧 Neo4j 材料/作者图谱同步（`backend/ingest/sync_neo4j.py`）仍不在上传链路中自动触发；Issue #81 的论文引用图不依赖该同步，公开查询直接读取 MySQL 中的 `paper_references`。
- `backend/ingest/PIPELINE.md` 描述的 `enrich_papers.py` → `clean_results/*.json` → `key_properties` 链路属于旧 `pipeline.py` 摄入路径；当前多文件上传链路不经过 `enrich_single` 与 `key_properties`。
- 解析质量依赖 LLM 配置（`DEEPSEEK_*` / `OPENAI_*`）；向量化发布依赖 Embedding 配置（`EMBEDDING_*`）与 Qdrant；缺省配置时对应阶段失败。

## 代码与测试

- 任务 API：`backend/api/upload_tasks.py`；提交与发布：`backend/api/rag.py`。
- 解析主流程：`backend/ingest/upload_jobs.py`；任务状态与存储：`backend/ingest/upload_tasks.py`、`upload_contracts.py`。
- 提取与分段：`pdf_extractor.py`、`chunker.py`、`extractor.py`；结构候选：`structure_extractor.py`；落库：`scientific_drafts.py`；向量化：`embedder.py`。
- 测试：`backend/tests/test_upload_workflow.py`、`tests/01_decentralized_uploading/`。
