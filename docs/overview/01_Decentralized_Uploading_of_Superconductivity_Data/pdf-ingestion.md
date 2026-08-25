# PDF 摄入

## 功能说明

登录用户可同时维护多条论文上传任务。一个任务对应一篇论文，包含恰好一个正文和任意数量的补充材料或附件；所有文件均为 PDF、TXT 或 Markdown。系统异步读取全文并生成可编辑 AI 草稿。用户确认并提交前不写入 MySQL；管理员审核通过后，论文才进入公开查询和正式 Qdrant 索引。

## 工作流程

1. 论文上传区始终显示在任务中心上方，不会因正在查看或解析其他任务而消失。用户可拖拽或点击选择一组文件；这组文件共同创建一个任务并填写一张表单。默认第一份合法文件为正文，其余为附件，开始上传前可调整角色、逐项移除或清空本地清单。
2. 页面先声明完整文件清单和角色。每个文件不超过 50 MB（50 MiB）；非法类型、超限和本地重复文件逐项拒绝，不影响同批其他合法文件。Python 执行精确大小校验，Nginx canonical 上传路由允许 51 MB multipart 请求体。
3. 浏览器最多并行上传 3 个文件。Python 将原文件保存到 `/data/upload_PDFs/<task_id>`；所有文件完成后原子锁定清单并只入队一次。
4. RQ Worker 按文件提取正文，然后执行 LLM 分段阅读、LLM 全文汇总和等待用户校对。部署默认使用 2 个 Worker 进程处理两篇论文，可通过 `UPLOAD_LLM_CONCURRENCY` 调整。
5. 文本提取后、分段 LLM 前，系统用 DOI、标题页和开头文本检查正文与附件的一致性。信息缺失不阻塞；明确冲突显示警告并要求用户在提交前确认。
6. Markdown 保存到 `/data/parsed_markdown`；每个分段先建立状态清单，结果采用临时文件加原子替换保存。任务详情提供“AI 临时表单”和“分段解析与证据”页签；无分段时显示提取或等待状态。后台分类证据用 `current_paper` 和 `referenced_work` 区分本文工作与被引用工作，普通草稿只返回本文研究对象；引用材料不再作为普通字段或最终科学数据输出。
7. 解析中的临时表单只读并持续合并结果。`reading` 和 `summarizing` 阶段的分类字段显示“候选尚未汇总”，不把正常的分段差异标成正式冲突；标题、DOI 等非分类单值字段出现不同候选时仍标记“有冲突”并并列显示，不静默覆盖。内容超过统一展示高度的字段卡片默认收起，短字段直接完整显示；每张长卡片可通过文字按钮独立展开或收起，完整候选和来源证据始终保留，轮询更新与窗口变化会重新判断溢出，任务切换不会继承前一任务的展开状态。任务进入 `ready` 后同一页签原地切换为可编辑最终草稿。（[Issue #47](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/47)）
8. 用户停止编辑 5 秒后自动保存，也可立即保存。草稿按 `material_states[]` 组织：材料家族建议、结构家族建议、不同元素种类数、压力和材料维度相互独立；目录候选由数据库驱动，界面统一显示规范中文名。AI 分类只进入审核上下文，不在提交阶段写正式目录 ID。元素种类数由服务器根据化学式重算。论文只报告空间群而没有完整 CIF/POSCAR 时，符号与国际群号分别保存在 reported 字段；`phase_label` 不再生成或写入；λ 和 ωlog 属于 `calculation_context`；Tc 属于 `tc_results`；其余数据才进入普通 `properties`。点击提交后，一篇论文、全部 `paper_files`、正式文本块、Evidence 和条件化科学实体图在一个 MySQL 事务中写入并进入 `pending`。
9. MySQL 事务成功后，系统保留 PDF、附件、组合及分文件 Markdown 和精简 `result.json` 审核快照；删除 Redis state/draft、用户任务索引、RQ 处理 Job、分段 JSON 和其他 LLM 中间产物。快照写入失败时不执行该临时清理，以便后续恢复。
10. 管理员对照 AI 建议、用户值和原文证据审核，在同一页面认可建议、改选已有分类或输入新名称。只有批准事务会写入人工确认的材料/结构家族 ID，必要的新目录项也在该事务中创建；审核事件保存分类上下文和最终选择快照。快照同时绑定 `task_id`、`paper_id` 和 `paper_revision`，只有与论文当前 revision 一致的 pending 快照可以读取。`approved` 会同步发布 Qdrant 后幂等删除临时快照；`rejected` 幂等删除临时快照；`pending` 保留临时快照。

## 分类规则

- 全文分段读取后再汇总判断，不能只按摘要或化学式分类。
- 只有 `scope=current_paper` 的论文类型和材料类型证据可以进入分类候选及全文汇总；`scope=referenced_work` 或缺少 `scope` 的旧证据只作为背景保留。论文类型中的 `unknown` 表示当前分段无法判断，会在汇总前丢弃，不作为冲突候选。
- 理论贡献主导、实验用于验证理论时为 `theoretical`；实验发现主导、理论用于解释现象时为 `experimental`；两者同等重要时按 `experimental`。
- 理论二级类型为 `calculation`、`method`、`theory`。新算法、新模型或研究工具归 `method`。
- 论文整体类型与每个材料状态及 Tc 结果的理论/实验类型分开保存。
- 分段与汇总契约明确提取 GPa 压力、空间群符号/群号、`lambda_ep` 和 `omega_log_k`；没有原文证据的数值保持 `null`，不得推测。
- 材料家族只允许规范名、内部编码或 seed 别名的确定性精确匹配；不根据化学式含某元素机械判断，也不做模糊猜测。未知名称由管理员在论文审核中确认是否创建，不进入独立治理队列。
- 旧顶层 `sc_type` 只在草稿 GET 时一次性转换；PUT 和 submit 返回 `legacy_classification_contract`，不再接受旧格式。
- 分段分类结果带内部契约版本。缺少当前版本的旧缓存会重新执行分段读取，不会根据旧文本猜测或补写证据主体。

## 持久化与可见性

- Redis：任务阶段、文件清单、错误、进度和未提交草稿；每个用户有活动任务索引，上限 100 个。状态带 `state_schema_version`，API 和 Worker 共用同一契约版本。
- `ready` 从用户主动打开详情、编辑或保存草稿起滑动保留 24 小时；后台轮询不续期。`failed/duplicate/cancelled` 从进入状态起固定保留 24 小时。
- `uploading` 连续 1 小时无进度转为失败；队列、解析、汇总和提交中的任务不按创建时间强制过期。
- MySQL：用户提交后的最终候选值和 `pending/approved/rejected` 审核状态；不保存处理进度、失败历史或 AI 原始判断。
- 文件目录：未提交终态任务到期后删除原文件、组合及分文件 Markdown、AI 产物和 duplicate 候选副本；清理 Job 携带最小 `CleanupContext`，即使 Redis state 已过期仍能定位用户索引、RQ Job 和候选副本。删除文件前必须用 `papers.upload_task_id` 查询永久认领，数据库不可用时延后，不得依据 Redis 缺失直接删除。
- 清理职责分为 `cleanup_transient_data`、`cleanup_unsubmitted_files` 和 `cleanup_duplicate_candidate`。已提交任务只执行临时清理并保留正式文件与待审快照；未提交的 `failed/duplicate/cancelled` 才执行全部清理。
- 已提交论文通过 `paper_files` 永久认领所有来源文件；`paper_chunks` 和正式证据保存来源文件与页码范围。
- 统计、搜索和 RAG 只使用 `approved` 论文。统一论文详情的权限为：匿名仅 approved；登录用户可看 approved/pending；上传者还可看自己的 rejected 和 `review_comment`；管理员可看全部及 `admin_internal_note`。内部路径始终不公开。

## 上传任务中心

- `GET /api/upload-tasks` 从 Redis 恢复当前用户活动任务，不依赖浏览器保存的单个 task ID，也不为 duplicate 刷新查询 Paper 表。未知状态契约版本返回稳定错误，不静默猜测权限。
- 列表在解析记录旁显示服务端 `cleanup_at` 驱动的倒计时；少于一小时显示分秒，到期待 Worker 执行时显示“等待清理”。
- 每个任务行提供明确的“查看解析/收起解析”按钮并标识当前任务；同一时刻只展开一个任务详情，切换任务不清空上传区尚未提交的本地文件。
- 当前解析详情顶部提供随详情滚动保持可达的操作栏，显示当前文件名、处理阶段和加载状态，并提供“收起解析”。收起只清除浏览器中的当前详情选择及对应活动任务键，不取消或删除后台任务，也不清空上传区尚未提交的本地文件。
- 运行任务可请求取消，Worker 在文件、分段和汇总边界停止；当前阻塞的 LLM 请求允许完成或超时。
- 单项和批量清理只处理失败、重复和已取消任务，运行中或正在提交的任务会被跳过。
- 对外任务和解析 DTO 使用字段白名单，不返回绝对路径、RQ job ID、Redis key、提示词或原始 LLM 响应。

## 重复文件

- 同一任务内文件哈希相同：直接拒绝重复文件。与已有正式论文哈希相同：删除新副本并返回已有论文权限动作。
- DOI 相同但文件不同：禁止创建草稿，将新文件保存为该论文的管理员候选附件，不覆盖原文件。
- Worker 检测重复时查询 MySQL 一次，并把已有论文 ID、状态、允许动作、原因和固定 24 小时截止时间写入 Redis；后续任务列表和详情只读该快照。点击论文后由统一 `/api/papers/{id}` 再查 MySQL 并最终鉴权，不再错误跳转到仅本人上传接口。
- 旧 Worker 留下的不完整 duplicate 状态由 `python -m backend.scripts.migrate_upload_task_states --apply` 一次性回填；默认不带 `--apply` 时只 dry-run。迁移后的 `cleanup_at` 沿用旧 `updated_at`，不会重新获得 24 小时。
- 候选附件列表和下载接口仅管理员可访问；duplicate 到期或被主动清理时，仅删除该 `task_id` 的候选 PDF/JSON，不影响同论文其他候选。

## 失败语义

- 上传、抽取、LLM 和数据库错误必须返回或记录明确原因，前端不得显示假成功。
- 超过 50 MB 的文件会在选择或上传阶段明确提示；即使 Nginx 返回非 JSON 的 HTTP 413，页面也显示相同的大小限制信息。
- 扫描版或正文过短的 PDF 明确提示需要可搜索文本；本功能不包含 OCR。
- 审核通过后若向量发布失败，Go API 返回 `502`，保留临时证据；管理员重复审核即可幂等重试。

## 主要实现

- `backend/api/rag.py`
- `backend/api/upload_tasks.py`
- `backend/ingest/upload_contracts.py`
- `backend/ingest/upload_jobs.py`
- `backend/ingest/scientific_drafts.py`
- `backend/ingest/upload_tasks.py`
- `backend/rag/llm.py`
- `frontend/src/components/UploadTaskEditor.tsx`
- `frontend/src/components/MultiFileUploadPanel.tsx`
- `frontend/src/components/UploadTaskCenter.tsx`
- `frontend/src/components/UploadParsingDetail.tsx`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/AdminPage.tsx`
- `goserver/handlers/admin.go`
- `goserver/handlers/papers.go`
- `goserver/handlers/stats.go`
- `backend/services/classification_catalog.py`
- `frontend/src/components/ClassificationAutocomplete.tsx`
- `goserver/handlers/classifications.go`

## 相关变更记录

- [Issue #46：打通论文上传提取与条件化超导数据模型](../../specs/46-upload-scientific-data-pipeline/spec.md)
- [Issue #45：修复论文分段分类证据误归属与全文汇总前伪冲突](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/45)
- [Issue #48：修复页面滚动时左侧导航和解析收起操作不可达](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/48)
- [Issue #51：建立材料状态多维分类目录并统一 AI、上传与审核流程](../../specs/51-material-state-classification/spec.md)
