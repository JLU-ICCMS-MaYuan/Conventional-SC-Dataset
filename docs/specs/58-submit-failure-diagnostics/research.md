# 技术研究：提交审核失败的可诊断性与必填定位

**GitHub Issue**：[#58](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/58)

**日期**：2026-08-26

**Spec**：[spec.md](spec.md)

## D1：超长 `##` 行的处理方式

**决策**：在 `_split_by_h2` 中按长度阈值 300 字符判定；超长行不作为章节边界，其文本并入前一节正文，沿用前一节的 `section_name`。首个真实章节之前的超长行归入「全文」。

**理由**：实测数据把两类清楚分开。全部已解析论文的 28 个 `##` 标题长度分布：

| 长度 | 性质 |
|---|---|
| 1、11、22 | 公式残片（`∫`、`∫ λ ω ω ω =`） |
| 65、77、81、101 | 真实标题与关键词行 |
| 178、204 | 真实标题（致谢、NOTE ADDED） |
| 389、633、1213、1389 | 被误判的正文段落 |

真实标题上界 204，误判正文下界 389，300 落在中间且两侧余量均超过 90 字符。

关键证据是 `_split_by_h2` 只把 `match.end()` 之后的文本作为 `body`，**标题行本身从不进入任何 chunk 的 `content`**。用三个探针在 ThH10 上验证：

```
原文含: True | content 含: False | transition-metal hydrides are extremely promi
原文含: True | content 含: False | lends further conﬁdence in structure predicti
原文含: True | content 含: False | Detailed crystal structure of predicted phase
```

因此单纯截断 `section_name` 会永久丢失这些文字——它们没有第二个副本。

**备选方案**：

- *仅截断到 500*：改动最小，但丢弃实测最长 1389 字符中的 889 字符真实正文，搜索与 RAG 无法引用。用户已明确否决。
- *截断 + 标题全文追加到 content*：不丢数据，但会把真实短标题也重复写进正文，制造冗余并污染 chunk 内容。
- *模型判定标题*：精度更高但引入 LLM 调用、延迟与成本，实测数据用长度即可分离，违反 YAGNI。

**证据**：`backend/ingest/chunker.py:114-139`（`_split_by_h2` 的 body 起点为 `match.end()`）；长度分布由 `/data/parsed_markdown/**/*.md` 全量统计得出。

## D2：写入层截断仍然保留

**决策**：D1 之后仍在写入 `PaperChunk` 前对 `section_name` 与 `heading` 按 500 安全截断。

**理由**：D1 是启发式判定，不保证覆盖全部解析噪声形态（例如 250 字符的误判段落）。写入层截断是与判定逻辑无关的第二道防线，保证任何解析结果都不会因长度触发 `DataError`。两者职责不同：D1 保正确性（文字不丢），D2 保可用性（提交不炸）。

**备选方案**：*只做 D1 不做 D2*——一旦出现阈值以下的异常长标题仍会 500，故障模式与修复前相同。*只做 D2 不做 D1*——已被用户否决，见 D1。

**证据**：`backend/models.py:536-537` 两列均为 `String(500)`；`backend/api/rag.py:1102-1103` 为唯一写入点。

## D3：不修改列宽

**决策**：`paper_chunks.section_name` 与 `heading` 保持 `varchar(500)`，不新增迁移。

**理由**：问题的性质是写入未受控，不是列太窄。真实标题最长 204 字符，500 已有充裕余量；放宽到 `TEXT` 只会让误判正文以「章节名」身份静默入库，掩盖解析噪声而非修复它，并且仍然丢失该文字（因为它不进 `content`）。同时避免一次纯为掩盖问题而做的 schema 迁移。

**备选方案**：*改为 `TEXT`*——无需截断逻辑，但把噪声固化进数据，且 D1 的正文归属问题依然存在。

**证据**：长度分布统计；`alembic/versions/20260609_0001_initial_mysql_schema.py:121`。

## D4：未捕获异常的错误响应位置

**决策**：在 `backend/main.py` 注册全局异常处理器，返回与既有 `_upload_error` 一致的 `{code, message}` 结构；`code` 用稳定标识（如 `internal_error`），`message` 为面向用户的中文文案，不含异常原文。

**理由**：前端 `backendErrorReason`（`UploadTaskEditor.tsx:117-127`）已能解析 `detail` 为字符串或 `{code, message}` 两种形态，无需改协议即可复用。放在 `main.py` 的全局处理器而非 `rag.py` 的局部 `try`，是因为「任何路由的任何未预期异常都应有结构化响应」是应用级横切关注点，逐个路由包 `try` 会重复且必然漏；这也符合 DRY 与 Overview「必须返回或记录明确原因」的约束。

异常原文（`str(exc)`）不进入响应体：实测该异常原文为 `(asyncmy.errors.DataError) (1406, "Data too long for column 'section_name' at row 1")`，含表名列名与驱动细节，对用户无意义且泄漏内部结构。完整信息记录到服务端日志。

**备选方案**：

- *在 `_submit_upload_draft_locked` 局部捕获*：只覆盖提交路径，其他路由的 500 仍是纯文本；且与已有的 `except Exception: update_state(...); raise` 回滚逻辑纠缠。
- *沿用 `_map_internal_error`*：它面向 RAG 服务的已知异常类型（`RagDataUnavailableError` 等）做 502 映射，语义是「下游服务错误」，与「本服务未预期异常」不同，复用会混淆错误语义。

**证据**：`backend/main.py:14-27`（无异常处理器）；`backend/api/rag.py:36-41`（`_upload_error` 契约）、`:490-500`（`_map_internal_error` 的 RAG 专用语义）；`frontend/src/lib/api.ts:26-39`（`detail.code`/`detail.message` 提取）。

## D5：前端校验错误的数据结构与定位机制

**决策**：`validate()` 返回 `ValidationIssue[]`（含 `stateIndex?: number`、`field: string`、`message: string`），空数组表示通过。提交失败时：展开 `stateIndex` 对应卡片（`setCollapsedStates`）、按 `field` 定位 DOM 并 `scrollIntoView` + `focus`、字段渲染 `error`/`helperText`、横幅汇总全部 `message`。

**理由**：现有 `validate()` 返回 `string | null` 且遇错即 `return`（`UploadTaskEditor.tsx:619-649`），结构上无法承载多条错误与字段位置，必须改签名。改为清单后三项能力（汇总、展开、聚焦）都由同一份数据驱动，避免为每项能力各自再扫一遍草稿。

卡片展开能力已存在（`collapsedStates` + `setCollapsedStates`，`:260`、`:915`），不需新建机制；`data-testid="material-states-list"`（`:895`）表明该组件已有测试锚点约定，字段定位沿用同类 `data-*` 锚点而非依赖 MUI 内部 DOM 结构。

**备选方案**：

- *保留单条返回，仅加滚动*：无法满足 FR-009 的「汇总全部缺失项」，用户仍需反复提交逐条发现。
- *用 `ref` 数组持有每个输入框*：材料状态与物性数量动态可变，ref 管理复杂度高于按 `data-*` 属性查询，违反 KISS。

**证据**：`UploadTaskEditor.tsx:619-649`（现 `validate` 签名与提前 return）、`:260`/`:915`（折叠状态机制）、`:895`（既有 testid 约定）、`:949`（材料输入框）。

## D6：后端专属校验错误的前端定位

**决策**：后端 `_upload_error` 的 `message` 已含「第 N 个材料状态」，前端从 `detail.message` 解析该序号定位卡片；不新增后端字段。

**理由**：后端 12 处校验错误中，涉及材料状态的均已在 message 内写明序号（如 `f"第 {state_index + 1} 个材料状态缺少材料"`）。在不改后端契约的前提下即可满足 FR-010，改动面最小。

需要说明的权衡：从展示文案解析结构化信息是脆弱耦合，文案改写会静默失效。选择它是因为本 Feature 的后端改动已集中在异常处理与分段逻辑，再扩一次校验错误响应体结构会显著放大范围与回归面。缓解方式是为该解析写明确的单元测试，文案变更时测试立即失败。若后续 #57/#59 需要更强的字段级定位，再统一升级为 `detail.state_index` 字段。

**备选方案**：*后端在 `detail` 增加 `state_index`/`field`*——更健壮，但需改 `_upload_error` 全部 12 个调用点并同步前端，超出本 Feature「让失败可诊断」的最小范围；已记入 Spec 范围外「不统一前后端校验规则集」。

**证据**：`backend/api/rag.py:254`、`:282`、`:287`、`:293`、`:301`、`:307`、`:311` 等均在 message 中包含 `state_index + 1`。

## D7：分段逻辑变更的影响边界

**决策**：只影响此后新解析或重新解析的论文；不回溯改写已入库 `paper_chunks`。

**理由**：`chunk_paper` 在提交时调用（`backend/api/rag.py:1091`），已入库论文的 chunk 不会重算。回溯需要重新解析全部历史论文并重建向量索引，是独立的数据迁移决策，且当前受影响的已入库论文数量为零——实测 `structure_models` 与相关表显示只有少量测试数据，而真正触发该问题的 ThH10 从未提交成功。

这符合 Skill 的历史兼容要求：适用对象明确（新解析）、退出条件明确（无需长期兼容分支）、不在读取路径添加为旧数据服务的分支。

**证据**：`backend/api/rag.py:1091`（`chunk_paper` 调用点在提交事务内）；失败任务 `946c56c2...` 从未成功入库。

## D8：测试层次

**决策**：分段逻辑用后端单元测试（真实 Markdown 片段，断言探针文字进入 `content`）；异常处理器用后端集成测试（真实 FastAPI 路由触发异常，断言响应体结构与不含敏感内容）；校验定位用前端组件测试（真实渲染，断言卡片展开、字段错误态、横幅汇总）。

**理由**：Skill 要求「回归测试必须复现用户看到的实际故障边界」。故障边界分别是：分段函数的输出内容归属、HTTP 响应体形态、DOM 上的可见反馈。分段与校验可在单元/组件层完整覆盖；异常处理器必须经真实路由才能验证 Starlette 处理链，纯函数测试无法证明。

数据库列长度约束不在测试中 Mock：截断逻辑的正确性用「输出长度 ≤ 500」断言即可，无需真实 MySQL；而端到端的「提交成功」由 quickstart 人工验收覆盖（SC-001）。

**证据**：`backend/tests/test_upload_jobs.py` 已有 chunker 相关测试可扩展；`tests/01_decentralized_uploading/` 为前端上传 UI 测试目录，命令 `cd frontend && npm run test:upload-ui`。
