# 技术决策与备选方案：顶栏 AI 供应商切换

**关联**：[spec.md](spec.md) · [plan.md](plan.md) · Issue [#73](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/73)

## 现状调研

### 生成式 LLM 调用点分布

`rg -n "OpenAI\(|ChatOpenAI\(" backend` 结果显示 13 处客户端构造，其中生成式 LLM 相关
11 处，Embedding 相关 2 处：

| 文件 | 行 | 凭据来源 | 本 Feature 处理 |
| --- | --- | --- | --- |
| `backend/rag/llm.py` | 18 | `settings.completion_*` | 改为请求级配置 |
| `backend/rag/core/engine.py` | 115, 291, 597 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/core/reranker.py` | 55 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/agent/graph.py` | 62, 142, 186, 196 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/agent/mentor.py` | 51 | `ChatOpenAI` + `deepseek_*` | 改为请求级配置 |
| `backend/rag/inspiration/curator.py` | 66 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/inspiration/evidence.py` | 92 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/inspiration/mode_router.py` | 57 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/rag/inspiration/reviewer.py` | 75 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/ingest/extractor.py` | 54 | `settings.deepseek_*` | 改为请求级配置 |
| `backend/ingest/embedder.py` | 34 | `settings.embedding_*` | **不改**（FR-014） |

`reranker.py:39` 还有一处 `if not settings.deepseek_api_key` 的可用性判断，同样需要改为
基于请求级配置判断。

### 关键约束：调用栈同步且无上下文参数

`backend/rag/core/engine.py`、`inspiration/*.py`、`agent/graph.py` 都是同步函数，且函数
签名不含任何上下文参数。调用链形如：

```
api/rag.py (async, 有 Request)
  → service.chat_stream (async)
    → run_in_executor → agent.run (sync)
      → graph 节点 (sync) → OpenAI(...)
```

凭据要穿过 `run_in_executor` 的线程边界到达最内层同步函数。

### 关键约束：论文解析在 RQ worker 内

`backend/ingest/upload_tasks.py:443` 的 `enqueue_processing(task_id)` 只传 `task_id`，
worker 进程通过 `get_state(task_id)` 从 Redis 读任务状态。任务状态已用 `setex` 带 TTL
存储（`upload_tasks.py:78`），凭据可沿用同一机制但需独立键与更短生命周期。

## 决策

### D-001：凭据传递用 contextvars，不改函数签名

**决策**：用 `contextvars.ContextVar` 保存请求级 LLM 配置，在 FastAPI 依赖或中间件里
设置，各调用点通过统一工厂 `get_llm_client()` 读取。

**理由**：
- 11 个调用点分布在 6 个模块，逐层加 `llm_config` 参数要改动整条调用链上的每个中间
  函数，涉及面远超本 Feature 需要，违反 KISS。
- `contextvars` 是 Python 标准库为「异步上下文内的隐式参数」设计的机制，asyncio 任务
  会自动继承上下文。
- 统一工厂符合依赖倒置：调用点依赖抽象工厂，不依赖 `settings` 具体字段。

**已知代价与对策**：`run_in_executor` 到线程池时 contextvars **不会**自动传播。必须在
提交任务前 `contextvars.copy_context()` 并用 `ctx.run(fn, ...)` 包装，`service.py:166`
的线程池调用处需显式处理。这一点必须在实施时验证，否则灵感探索链路会静默回落到服务端
默认凭据——这类失败不报错，只是花错了钱，测试必须覆盖。

**备选方案**：
- *逐层传参*：显式、无隐式状态，但改动面过大且每加一个调用点都要再穿一遍。
- *线程局部存储*：不兼容 asyncio 单线程多任务模型，同一线程内多个并发请求会互相污染。

### D-002：凭据经自定义请求头传递，不进 body

**决策**：新增 `X-LLM-Provider`、`X-LLM-Base-URL`、`X-LLM-Model`、`X-LLM-Api-Key`
四个请求头，由前端 `api.ts` 统一注入。

**理由**：
- 现有 `frontend/src/lib/api.ts` 已有 `authHeaders()` 统一注入 `Authorization` 的模式，
  凭据注入放在同一处即可覆盖全部 `api.*` 调用，符合 DRY。
- 放进 body 需要改动每个端点的 Pydantic 请求模型（`RagChatRequest` 等多个），且
  `FormData` 上传场景不好塞。
- 请求头对 SSE 流式端点（`postStream`）同样适用。

**已知代价**：
- 需确认 nginx `proxy_set_header` 透传自定义头，以及头部总大小不超
  `large_client_header_buffers` 默认值。密钥通常 50~100 字符，四个头合计远小于默认 8k，
  但 nginx 配置须核对。
- 反向代理与访问日志可能记录请求头。必须核查 nginx `log_format` 不含 `$http_x_llm_api_key`，
  这是 FR-018 的一部分。

**备选方案**：
- *body 传递*：改动面大，且 `FormData` 场景别扭。
- *短期 session token 换取凭据*：服务端要暂存凭据，与「服务端不保管凭据」的定调冲突。

### D-003：RQ 任务凭据用独立 Redis 键 + 短 TTL

**决策**：入队时把凭据写入 `upload:llm:{task_id}` 独立键，TTL 取任务处理超时上界（建议
2 小时），worker 启动任务时读取并设入 contextvars，任务到达终态（成功/失败/取消）时
主动 `DELETE`。

**理由**：
- 凭据不混入 `task_key(task_id)` 的任务状态，避免被 `/upload-tasks/{task_id}` 等状态查询
  接口连带返回给前端——任务状态本身是要回显给用户的，凭据不能在同一结构里。
- 独立键可设远短于 `TASK_TTL`（24 小时）的生存期，缩小暴露窗口。
- 主动删除 + TTL 双保险：worker 崩溃不清理时，TTL 兜底。

**已知代价**：多一个键的生命周期要维护。清理点必须覆盖 `cleanup_transient_data` 与
所有终态分支，遗漏会让凭据滞留至 TTL 到期。

**备选方案**：
- *混入任务状态*：省一个键，但有随状态查询接口泄露给前端的真实风险，否决。
- *只靠 TTL 不主动删*：实现更简单，但正常完成的任务凭据仍要在 Redis 里躺满 TTL，暴露
  窗口无谓放大。

### D-004：SSRF 防护在服务端解析后校验

**决策**：服务端在构造客户端前校验 Base URL——协议必须为 https（`localhost` 与
`127.0.0.1` 放行 http），主机名解析为 IP 后拒绝私有、回环、链路本地网段（用户显式填写的
localhost 例外）。

**理由**：
- `/api/rag/chat` 不要求登录，匿名用户可指定任意 URL，未校验等于给出一个内网探测代理。
- `169.254.169.254` 是云厂商元数据接口，能读到实例凭据，必须显式拒绝。
- 先解析域名再判 IP，可挡住指向内网的公网域名（如 DNS 指向 `192.168.x` 的域名）。

**已知局限**：解析时校验与实际连接之间存在时间窗，理论上可被 DNS rebinding 绕过。彻底
防御需在 socket 连接层校验（自定义 `httpx` transport）。本 Feature 采用解析后校验，
接受这一残余风险并在文档中记录；若后续要求提高，再单独处理。这是明确的取舍，不是遗漏。

**备选方案**：
- *域名白名单*：最安全，但直接废掉「完全自定义端点」这一已确认需求（FR-006），否决。
- *不校验*：把后端变成匿名可用的内网探测跳板，否决。

### D-005：用户凭据失败不静默回退服务端默认

**决策**：用户自带凭据调用失败时抛出可区分错误，明确指出失败源于用户凭据，不改用服务端
默认配置重试。

**理由**：
- 静默回退会让用户以为自己的配置生效了，实际在花部署方的额度——这是计费归属的错误。
- 用户配置错了应该立刻知道，而不是看到一个能用但来源不明的回答。

**备选方案**：*自动回退* 体验上更"顺"，但掩盖配置错误且错配成本，否决。

### D-006：Claude 走 OpenAI 兼容层，不引入 Anthropic SDK

**决策**：预置 Claude 项的 Base URL 指向 Anthropic 的 OpenAI 兼容端点，沿用现有
`openai` 客户端。

**理由**：
- 引入 Anthropic 原生 SDK 需要第二套客户端构造、第二套流式解析、第二套错误映射，为一个
  预置项翻倍客户端层复杂度，违反 YAGNI。
- Anthropic 提供 OpenAI 兼容层，能满足 `chat.completions` + `stream` 的用法。

**实施期须验证**：兼容层对 `response_format={"type": "json_object"}` 的支持程度。
`backend/rag/llm.py:52` 依赖该参数，若 Claude 兼容层不支持，需在预置项上标注该限制或
降级为提示词约束 JSON。这一点未经实测，不能假定可用。

**备选方案**：*引入 Anthropic SDK* 兼容性最好，但复杂度代价与单个预置项的收益不匹配。

## 待实施期验证的事项

以下事项未经实际运行验证，实施时必须逐项确认，不得假定：

1. contextvars 穿越 `service.py:166` 线程池边界后确实生效（D-001 的核心风险）。
2. nginx 透传 `X-LLM-*` 自定义请求头，且访问日志不记录密钥头（D-002）。
3. Anthropic OpenAI 兼容层对 `json_object` response_format 的支持（D-006）。
4. LangChain `ChatOpenAI`（`mentor.py:51`）接受动态传入的 base_url 与 key，且不缓存
   跨请求的客户端实例。
5. 各预置供应商的实际 Base URL 与默认模型名，需逐一核对官方文档，不凭记忆填写。
