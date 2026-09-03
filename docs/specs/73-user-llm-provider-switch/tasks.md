# 实施任务：顶栏 AI 供应商切换

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[contracts/llm-provider-headers.md](contracts/llm-provider-headers.md)、
[quickstart.md](quickstart.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

**当前状态**：核心代码已实现；供应商官方文档实测、完整回归与人工验收仍待执行。

## 阶段 0：阻塞依赖

- [x] T001 确认中英文切换 Issue 已合入，`frontend/src/components/AppShell.tsx` 顶栏已有
      可插入的右侧操作区容器，且 i18n 词条机制可用

## 阶段 1：准备

**目的**：核实外部事实，避免凭记忆写配置。

- [ ] T002 [P] 逐一核对 6 家供应商官方文档，确认 Base URL 与一个可用默认模型名，把结果
      回写 [contracts/llm-provider-headers.md](contracts/llm-provider-headers.md) 第 2 节
- [ ] T003 [P] 实测 Anthropic OpenAI 兼容层是否支持
      `response_format={"type":"json_object"}`；不支持则在 research.md D-006 记录结论并
      决定标注限制还是降级为提示词约束
- [ ] T004 [P] 核查 nginx 配置：确认 `X-LLM-*` 自定义头被透传，且 `log_format` 不含
      `$http_x_llm_api_key`；需要改动则记录待改配置项

## 阶段 2：基础能力（阻断全部用户故事）

**目的**：建立请求级 LLM 配置层与统一客户端工厂。

- [x] T005 新建 `backend/rag/llm_context.py`：定义 `LlmConfig` 数据类（provider、
      base_url、model、api_key）、`ContextVar` 容器、`set_llm_config()` /
      `get_llm_config()`
- [x] T006 在 `backend/rag/llm_context.py` 实现 `resolve_llm_config()`：四个字段齐全时用
      用户配置，否则回退 `settings.completion_*`，回退时 provider 标为 `server-default`
      （FR-013）
- [x] T007 在 `backend/rag/llm_context.py` 实现 `validate_base_url()`：协议校验 + 域名
      解析后的私有/回环/链路本地网段拒绝，localhost 与 127.0.0.1 例外放行（FR-015~017），
      按 contracts 第 3 节的错误码返回
- [x] T008 在 `backend/rag/llm_context.py` 实现 `mask_api_key()` 脱敏工具（`sk-****abcd`）
      与 `UserCredentialError` 异常类型（FR-018、FR-019）
- [x] T009 新建 `backend/rag/llm_client.py`：`get_llm_client()` 返回配置好的 `OpenAI`
      实例，`get_langchain_llm()` 返回 `ChatOpenAI` 实例；两者均从 contextvars 取配置，
      构造前调用 `validate_base_url()`（FR-011）
- [x] T010 [P] 新建 `backend/tests/test_llm_context.py`：覆盖用户配置
      生效、字段缺失回退、四类 URL 拒绝（参数化覆盖 SC-004 全部网段）、脱敏输出、
      凭据失败不回退（FR-019）
- [x] T011 新建 `backend/api/` 下的 FastAPI 依赖：从 `X-LLM-*` 请求头解析并设入
      contextvars，非法头值返回 400（contracts 第 1 节）

## 阶段 3：用户故事 2——全部 AI 功能改用所选供应商（P1，MVP 核心）

**目标**：用户配置生效后，全部生成式 LLM 调用改用其供应商。

**独立验收**：quickstart 场景 4，四条链路 `provider` 字段均为所选供应商。

### 实施：调用点收敛

- [x] T012 改造 `backend/rag/llm.py` 的 `_client()`：改用 `get_llm_client()`，
      `_stream_json` 的 model 参数改取请求级配置
- [x] T013 改造 `backend/rag/core/engine.py` 三处客户端构造（约 115、291、597 行）为
      `get_llm_client()`，model 取请求级配置
- [x] T014 改造 `backend/rag/core/reranker.py`：第 55 行客户端构造走工厂，并把第 39 行
      `if not settings.deepseek_api_key` 的可用性判断改为基于请求级配置
- [x] T015 改造 `backend/rag/agent/graph.py` 四处客户端构造（约 62、142、186、196 行）
- [x] T016 改造 `backend/rag/agent/mentor.py` 的 `_build_llm()` 为 `get_langchain_llm()`，
      确认每次调用新建实例、不跨请求缓存（plan 坑点 4）
- [x] T017 [P] 改造 `backend/rag/inspiration/curator.py` 第 66 行走工厂
- [x] T018 [P] 改造 `backend/rag/inspiration/evidence.py` 第 92 行走工厂
- [x] T019 [P] 改造 `backend/rag/inspiration/mode_router.py` 第 57 行走工厂
- [x] T020 [P] 改造 `backend/rag/inspiration/reviewer.py` 第 75 行走工厂
- [x] T021 [P] 改造 `backend/ingest/extractor.py` 的 `_openai_client()` 走工厂
- [x] T022 确认 `backend/ingest/embedder.py` **未被改动**（FR-014）

### 实施：上下文传播

- [x] T023 改造 `backend/rag/service.py:166` 的 `run_in_executor` 调用：用
      `contextvars.copy_context()` + `ctx.run()` 包装，使配置跨线程池传播（plan 坑点 2）
- [x] T024 在 `backend/api/rag.py` 的 `/chat`、`/chat/stream`、`/search` 等 AI 端点挂上
      T011 的依赖
- [x] T025 在 `/chat` 与 `/chat/stream` 响应中加入 `provider` 与 `model` 字段，流式在
      `done` 事件携带（FR-021、contracts 第 5 节）
- [x] T026 实现用户凭据失败的错误映射：抛 `UserCredentialError` 并映射为
      `LLM_USER_CREDENTIAL_FAILED`，确认不回退服务端配置（FR-019、contracts 第 6 节）

### 验证

- [x] T027 新建 `backend/tests/test_llm_client_coverage.py`：断言
      `backend/rag/` 与 `backend/ingest/extractor.py` 中生成式 LLM 调用点直读
      `settings.deepseek_api_key` 的处数为 0（SC-008）
- [ ] T028 集成测试覆盖灵感探索链路跨线程池后配置仍生效——这是最易静默失败处，测试须断言
      实际使用的 base_url，不能只断言调用成功

## 阶段 4：用户故事 2 延伸——RQ 上传解析凭据传递（P1）

**目标**：后台解析任务使用发起者选定的供应商，且凭据不滞留。

**独立验收**：quickstart 场景 9，三种终态后 Redis 键均不存在。

- [x] T029 在 `backend/ingest/upload_tasks.py` 新增 `upload:llm:{task_id}` 键的写入
      （`setex`，TTL 取任务处理超时上界）、读取与删除三个原语，键结构独立于
      `task_key(task_id)`（FR-020、research D-003）
- [x] T030 改造 `backend/ingest/upload_tasks.py:443` 的 `enqueue_processing()`：入队前把
      当前请求级配置写入凭据键
- [x] T031 改造 `backend/ingest/upload_jobs.py` 的 `process_upload_task()`：任务开始时读取
      凭据键并设入 contextvars
- [x] T032 在 `backend/ingest/upload_jobs.py` 与 `upload_tasks.py` 的全部终态分支（成功、
      失败、取消、`cleanup_transient_data`）中删除凭据键
- [x] T033 在上传任务状态回显中加入 `provider` 字段（FR-021）
- [ ] T034 新建 `tests/01_decentralized_uploading/test_upload_llm_credentials.py`：断言
      入队后键存在且带 TTL、worker 内配置生效、三种终态后键被删除（SC-007）
- [x] T035 确认 `/upload-tasks/{task_id}` 等状态查询接口的响应体不含凭据键内容

## 阶段 5：用户故事 1——顶栏入口（P1）

**目标**：全站顶栏可见供应商入口并可切换。

**独立验收**：quickstart 场景 1，7 个页面状态一致。

- [x] T036 新建 `frontend/src/lib/llmProvider.ts`：`PROVIDER_PRESETS` 常量（按
      contracts 第 2 节，不含任何密钥）、`localStorage` 读写、`buildLlmHeaders()`、
      前端 URL 校验（与服务端同规则，仅作即时反馈）
- [x] T037 新建 `frontend/src/components/LlmProviderSwitcher.tsx`：顶栏按钮显示当前供应商
      名（未配置显示「默认模型」）+ 配置面板
- [x] T038 在 `frontend/src/components/AppShell.tsx` 顶栏头像左侧插入
      `LlmProviderSwitcher`，位置预留在未来中英文切换器左侧（FR-001）
- [x] T039 改造 `frontend/src/lib/api.ts`：在 `request()` 与 `postStream()` 注入
      `X-LLM-*` 头，仅当本地已保存且非 `server-default` 时注入（FR-010）
- [x] T040 核对 `frontend/src/lib/useStreamingChat.ts` 的流式请求确实携带凭据头
- [ ] T041 新建 `tests/01_decentralized_uploading/LlmProviderSwitcher.test.tsx`：渲染位置、
      8 个选项、切换供应商后 placeholder 变化、清除配置回到默认态
- [ ] T042 若 T041 的目录未列入 `vitest.config.ts` 的 `include` 白名单，同步添加——否则
      用例被静默跳过，不报错不计数（plan 坑点 1）

## 阶段 6：用户故事 5——凭据说明与掩码（P1）

**目标**：用户填密钥前就知道它存在哪里。

**独立验收**：quickstart 场景 3。

- [x] T043 [US5] 在 `LlmProviderSwitcher.tsx` 密钥输入框下方加入常驻说明「密钥仅保存在你
      当前浏览器，不会上传或存入服务器数据库」（FR-008）
- [x] T044 [US5] 密钥输入默认掩码 + 可见性切换；已保存配置重新打开时以 `sk-****abcd`
      回显（FR-009）
- [x] T045 [US5] 加入「清除配置」按钮，清除后回退服务端默认（FR-022）
- [ ] T046 [US5] 组件测试断言说明文案存在、回显为掩码形式、清除后回到默认态

## 阶段 7：用户故事 3——自定义端点（P2）

**目标**：清单外的供应商与自建网关可用。

**独立验收**：quickstart 场景 6。

- [x] T047 [US3] 「自定义」预设项：三项均空且必填，Base URL placeholder 为示例地址
      （FR-006）
- [x] T048 [US3] 表单层接入 T036 的前端 URL 校验，即时提示非 https 与内网地址
- [ ] T049 [US3] 端到端验证 quickstart 场景 6 的 5 类地址，含 DNS 解析到私有网段的域名

## 阶段 8：用户故事 4——连接测试（P3）

**目标**：保存前知道凭据是否可用。

**独立验收**：quickstart 场景 7。

- [x] T050 [US4] 在 `backend/api/rag.py` 新增 `POST /api/rag/llm/test-connection`：最小
      `chat.completions` 调用，`max_tokens=1`，读超时 15 秒，`max_retries=0`
      （contracts 第 4 节）
- [x] T051 [US4] 实现四类错误映射：`LLM_AUTH_FAILED`、`LLM_UNREACHABLE`、
      `LLM_MODEL_NOT_FOUND`、`LLM_TIMEOUT`（FR-023）
- [x] T052 [US4] 在 `LlmProviderSwitcher.tsx` 加「测试连接」按钮，成功显示实测耗时，失败
      显示对应提示
- [ ] T053 [US4] 后端测试覆盖四类失败的判定准确性（SC-006）

## 最终阶段：完善与跨故事事项

- [ ] T054 执行 nginx 配置变更（若 T004 发现需要），确认头透传与日志脱敏
- [ ] T055 密钥零泄露审计：按 quickstart 场景 8 检索数据库、后端日志、nginx 日志、错误
      响应体，四处均须命中 0 次（SC-003）
- [ ] T056 运行完整回归：`tests/05_rag_question_answering/`、
      `tests/01_decentralized_uploading/` 与前端 vitest，确认未配置用户行为不变（SC-005）
- [ ] T057 按 [quickstart.md](quickstart.md) 逐场景人工验收，填写验收汇总表
- [x] T058 用 `big-project-overview-maintainer` 回写
      `docs/overview/05_Retrieval-Augmented_AI_Question_Answering/availability-and-configuration.md`
      与 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-parsing-pipeline.md`
- [ ] T059 更新根 `README.md` 的模型配置说明，写明服务端默认与用户自带凭据两条路径
- [ ] T060 用 `big-project-issue-manager` 完成 Issue #73 的关闭检查并勾选
      Documentation Impact

## 依赖与执行顺序

- T001 是硬阻塞，未完成不动代码。
- 阶段 1（T002–T004）可与阶段 2 并行，但 T002 结论需在 T036 前到位。
- 阶段 2（T005–T011）阻断全部用户故事。
- 阶段 3、4 属后端，可独立于前端推进；阶段 5 依赖 T011 确定的头部契约。
- T012–T021 中标 [P] 的分属不同文件，可并行；T013、T015 各自集中在单文件内多处，须串行。
- T023 必须在 T028 之前，否则测试无从验证传播。
- 阶段 6 依赖阶段 5 的组件存在。
- 最终阶段依赖全部前序阶段。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 / US1 | T038, T041 | 顶栏头像左侧插槽 + 位置断言 |
| FR-002, FR-003, FR-005 | T002, T036, T037, T041 | 预设常量与 placeholder 行为 |
| FR-004 | T036, T022 | 预设不含密钥；不新增服务端供应商字段 |
| FR-006 / US3 | T047–T049 | 自定义端点三项可填 |
| FR-007, FR-009, FR-022 / US5 | T036, T044, T045, T046 | localStorage 存储、掩码回显、清除 |
| FR-008 / US5 | T043, T046 | 常驻说明文案 |
| FR-010 | T011, T039, T040 | 请求头注入与解析 |
| FR-011, FR-012 | T005–T009, T012–T021, T027 | 统一工厂 + 11 处收敛 + 静态扫描 |
| FR-013 / SC-005 | T006, T056 | 回退逻辑与回归验证 |
| FR-014 | T022 | 明确排除 embedder |
| FR-015–FR-017 / SC-004 | T007, T010, T048, T049 | 服务端校验为主，前端仅即时反馈 |
| FR-018 / SC-003 | T004, T008, T054, T055 | 脱敏 + nginx 日志 + 四处审计 |
| FR-019 | T008, T026, T010 | 可区分错误且不静默回退 |
| FR-020 / SC-007 | T029–T032, T034, T035 | 独立键 + 三终态清理 |
| FR-021 | T025, T033 | provider/model 回显 |
| FR-023 / SC-006 | T050–T053 | 四类失败映射 |
| SC-001 | T038, T041, T057 | 7 页面一致性 |
| SC-002 | T028, T057 | 四链路 provider 核对 |
| SC-008 | T027 | 静态扫描断言 0 处 |

## MVP 与增量策略

1. **MVP**：T001–T035（阶段 0–4）+ T036–T046（阶段 5–6）。此时用户可切换供应商、自带
   密钥、全部 AI 功能生效，且知道密钥存在哪里。
2. **增量 1**：阶段 7 自定义端点，覆盖清单外供应商。
3. **增量 2**：阶段 8 连接测试，降低配置返工。
4. 每个增量完成后已有故事保持可用；最终阶段的审计与文档回写在全部增量后统一执行。
