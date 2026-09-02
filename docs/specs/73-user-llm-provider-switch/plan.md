# 实施计划：顶栏 AI 供应商切换

**GitHub Issue**：[#73](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/73)

**日期**：2026-09-01

**Spec**：[spec.md](spec.md) · **决策**：[research.md](research.md)

## 摘要

在顶栏加入 AI 供应商选择器与配置面板，用户凭据存于 `localStorage`，经 `X-LLM-*` 请求头
传至后端。后端新增请求级 LLM 配置层：用 `contextvars` 保存本次请求的有效凭据，把现有
11 处硬编码 `settings.deepseek_*` 的客户端构造收敛到统一工厂 `get_llm_client()`。论文解析
在 RQ worker 内执行，凭据经独立短 TTL Redis 键传递并在任务终态清除。Base URL 在服务端
做协议与私有网段校验，防止匿名用户把后端当内网探测跳板。

## 技术上下文

- **语言与版本**：Python 3（FastAPI + Pydantic Settings）、TypeScript 5.6、React 19.2
- **主要依赖**：`openai` SDK、`langchain_openai.ChatOpenAI`、`rq` + Redis、MUI 7.3、Vite 5.4
- **数据存储**：不新增数据库表、不新增 Alembic 迁移。仅用浏览器 `localStorage` 与 Redis
  短生命周期键
- **测试体系**：后端 pytest（`tests/05_rag_question_answering/`、
  `tests/01_decentralized_uploading/`）；前端 vitest + Testing Library
- **目标平台**：Linux，nginx 反向代理 + FastAPI + RQ worker
- **性能目标**：请求级配置解析不引入可测量延迟（SC-005 要求未配置用户行为不变）
- **约束**：不改 Embedding 与 Qdrant（FR-014）；密钥零持久化（FR-007、FR-018）；
  未配置时行为完全向后兼容（FR-013）
- **规模范围**：前端 1 个全局组件 + 1 个 lib 模块；后端 6 个模块 11 处调用点收敛

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md KISS | 拒绝不必要复杂性 | contextvars 隐式传递，避免 11 处调用链逐层加参数 | 通过 |
| AGENTS.md DRY | 消除重复模式 | 11 处 `OpenAI(...)` 收敛为单一 `get_llm_client()` 工厂 | 通过 |
| AGENTS.md YAGNI | 只做当前所需 | 不做加密入库、多设备同步、配额计量、Anthropic 原生 SDK | 通过 |
| AGENTS.md DIP | 依赖抽象 | 调用点依赖工厂，不依赖 `settings` 具体字段 | 通过 |
| AGENTS.md 文档语言 | `docs/` 用简体中文 | 全部 Spec 产物为简体中文 | 通过 |
| Spec FR-014 | 不动 Embedding | `backend/ingest/embedder.py` 明确排除在改造清单外 | 通过 |
| Spec FR-018 | 密钥不入日志 | 工厂层不打印凭据；错误映射剥离 key；核对 nginx `log_format` | 待实施验证 |
| Spec FR-016 | 拒绝私有网段 | 服务端解析后校验 IP 网段 | 通过（残余 DNS rebinding 风险已在 research.md D-004 记录） |
| Overview 一致性 | 不把未落地设计写入 Overview | 实施完成后才由 overview-maintainer 回写 | 通过 |

## Feature 文档结构

```text
docs/specs/73-user-llm-provider-switch/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/
│   └── llm-provider-headers.md
├── tasks.md
└── checklists/
    └── requirements.md
```

不创建 `data-model.md`：本 Feature 无持久化实体，无数据库变更。

## 源代码结构

```text
frontend/src/
├── components/
│   ├── AppShell.tsx                  # 改：顶栏头像左侧插入选择器
│   └── LlmProviderSwitcher.tsx       # 新：选择器 + 配置面板
├── lib/
│   ├── llmProvider.ts                # 新：预设常量、localStorage 读写、请求头构造、URL 前端校验
│   ├── api.ts                        # 改：request/postStream 注入 X-LLM-* 头
│   └── useStreamingChat.ts           # 改：确认流式请求也带上凭据头

backend/
├── rag/
│   ├── llm_context.py                # 新：contextvars + LlmConfig + 解析与校验
│   ├── llm_client.py                 # 新：get_llm_client() 统一工厂
│   ├── config.py                     # 改：保留服务端默认，作为回退来源
│   ├── llm.py                        # 改：_client() 走工厂
│   ├── core/engine.py                # 改：3 处
│   ├── core/reranker.py              # 改：1 处 + 可用性判断
│   ├── agent/graph.py                # 改：4 处
│   ├── agent/mentor.py               # 改：ChatOpenAI 走工厂
│   ├── inspiration/curator.py        # 改
│   ├── inspiration/evidence.py       # 改
│   ├── inspiration/mode_router.py    # 改
│   ├── inspiration/reviewer.py       # 改
│   └── service.py                    # 改：线程池调用处 copy_context 传播
├── api/
│   ├── deps.py（或现有等价模块）      # 新增依赖：从请求头解析并设入 contextvars
│   ├── rag.py                        # 改：挂依赖；新增连接测试端点
│   └── upload_tasks.py               # 改：入队前落凭据
├── ingest/
│   ├── extractor.py                  # 改：走工厂
│   ├── upload_tasks.py               # 改：凭据键读写与清理
│   └── upload_jobs.py                # 改：worker 内设入 contextvars
└── ingest/embedder.py                # 不改（FR-014）

tests/
├── 05_rag_question_answering/
│   ├── test_llm_context.py           # 新：解析、回退、URL 校验、脱敏
│   └── test_llm_client_coverage.py   # 新：断言无调用点直读 deepseek_api_key
├── 01_decentralized_uploading/
│   ├── test_upload_llm_credentials.py    # 新：RQ 凭据传递与清理
│   └── LlmProviderSwitcher.test.tsx      # 新：前端组件
```

**结构选择**：

- `llm_context.py` 与 `llm_client.py` 分开：前者管「本次请求用哪套凭据」（解析、校验、
  上下文），后者管「据此造什么客户端」。职责单一，且 `mentor.py` 需要 `ChatOpenAI` 而非
  `OpenAI`，两种客户端共用同一份配置解析。
- 新建 `llm_client.py` 而非扩展 `llm.py`：`llm.py` 现在的职责是「JSON 流式调用 + 解析 +
  重试」，把客户端构造混进去会让它承担两件事。
- 前端 `llmProvider.ts` 与组件分离：`api.ts` 需要读凭据构造请求头，但不应依赖 React 组件。
- 凭据注入放在 `api.ts` 的 `request`/`postStream` 两个出口：现有 `authHeaders()` 已是同一
  模式，复用可一次覆盖全部 `api.*` 调用。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 / US1 | `AppShell.tsx` 顶栏插槽 + `LlmProviderSwitcher` | `LlmProviderSwitcher.test.tsx` 渲染位置断言；quickstart 场景 1 |
| FR-002, FR-003, FR-005 / US1 US2 | `llmProvider.ts` 的 `PROVIDER_PRESETS` 常量 | 组件测试：切换供应商后 placeholder 变化 |
| FR-004 | 无服务端预置密钥；`config.py` 不新增供应商字段 | 代码审查 + `test_llm_context.py` 断言预设不含 key |
| FR-006 / US3 | 「自定义」预设项，三项均可填 | 组件测试 + quickstart 场景 3 |
| FR-007, FR-009 / US5 | `llmProvider.ts` 的 `localStorage` 读写 + 掩码回显 | 组件测试：回显为 `sk-****abcd`；断言无网络持久化调用 |
| FR-008 / US5 | 配置面板常驻说明文案 | 组件测试断言文案存在 |
| FR-010 | `api.ts` 注入 `X-LLM-*` 头 | `contracts/llm-provider-headers.md` + 集成测试 |
| FR-011, FR-012 | `llm_client.get_llm_client()` + 11 处改造 | `test_llm_client_coverage.py` 静态扫描 + 各链路集成测试 |
| FR-013 / SC-005 | `llm_context.resolve()` 回退 `settings.completion_*` | 现有 RAG 与上传回归测试全通过 |
| FR-014 | `embedder.py` 排除在改造清单外 | 代码审查确认该文件未改 |
| FR-015, FR-016, FR-017 / US3 | `llm_context.validate_base_url()` 服务端校验 | `test_llm_context.py` 参数化用例覆盖 SC-004 全部网段 |
| FR-018 / SC-003 | 工厂不打印凭据；错误映射剥离；nginx `log_format` 核对 | 日志扫描测试 + 部署配置核对 |
| FR-019 | 错误类型区分用户凭据失败与服务端配置失败 | `test_llm_context.py` 断言不回退 |
| FR-020 / SC-007 | `upload:llm:{task_id}` 键 + 终态清理 | `test_upload_llm_credentials.py` 断言终态后键不存在 |
| FR-021 | 响应体附 `provider` 与 `model` 字段 | 集成测试断言字段值 |
| FR-022 / US5 | 「清除配置」按钮 | 组件测试：清除后回到默认态 |
| FR-023 / US4 | `POST /api/rag/llm/test-connection` 端点 | `contracts/` 契约 + 四类失败的后端测试 |

## 阶段与依赖

**阶段 0：前置依赖（不在本 Feature 实施范围）**

中英文切换 Issue 落地顶栏槽位与 i18n 词条。该 Issue 完成前不动代码。

**阶段 1：后端请求级配置基座（US2 的前提）**

1. `llm_context.py`：`LlmConfig` 数据类、contextvars、`resolve()` 回退逻辑、
   `validate_base_url()`、脱敏工具。
2. `llm_client.py`：`get_llm_client()` 与 `get_langchain_llm()`。
3. FastAPI 依赖：从请求头解析、校验并设入 contextvars。
4. 单元测试先行：解析、回退、URL 校验、脱敏。

**阶段 2：收敛 11 处调用点（FR-011、FR-012）**

按模块推进：`llm.py` → `reranker.py` → `engine.py` → `inspiration/*` →
`agent/graph.py` + `mentor.py` → `extractor.py`。每步跑对应回归测试。

`service.py:166` 线程池处的 `copy_context()` 传播必须在本阶段验证，这是
research.md D-001 标记的核心风险——失效时不报错，只是静默用了服务端凭据。

**阶段 3：RQ 凭据传递（FR-020、US2 场景 3）**

入队前写 `upload:llm:{task_id}`；worker 读取并设入上下文；终态清理。

**阶段 4：前端入口（US1、US3、US5）**

`llmProvider.ts` → `LlmProviderSwitcher.tsx` → `AppShell.tsx` 插槽 →
`api.ts` 注入请求头。

**阶段 5：连接测试与收尾（US4）**

测试端点 + 四类错误映射；nginx 头透传与日志脱敏核对；Overview 回写。

依赖顺序：阶段 1 → 2 → 3 可独立于前端推进；阶段 4 依赖阶段 1 的头部契约；
阶段 5 依赖 1 与 4。

## 实施期已知坑点

1. **vitest include 白名单**：`vitest.config.ts` 用逐目录白名单而非 `tests/**`。新增
   `.test.tsx` 若落在未列入的目录，用例会被静默跳过——不报错、不计数。新增前端测试目录
   必须同步更新该 include。
2. **contextvars 不跨线程池**：`service.py:166` 的 `run_in_executor` 必须
   `copy_context()`，否则灵感探索链路静默使用服务端凭据。
3. **nginx 自定义头**：需确认 `X-LLM-*` 被透传，且访问日志不记录 `$http_x_llm_api_key`。
4. **`ChatOpenAI` 实例缓存**：`mentor.py:51` 每次调用应新建实例，不得跨请求复用。
5. **重建后端要重启 nginx**：否则 nginx 缓存旧容器 IP 导致全站 502，看起来像功能失败。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| contextvars 隐式传递 | 11 处调用点跨 6 模块且调用链为同步函数，逐层加参数要改动整条链上每个中间函数 | 逐层显式传参：改动面远超本 Feature 需要 |
| RQ 独立凭据键 + 双重清理 | 解析在 worker 进程执行，与请求上下文完全隔离 | 混入任务状态：有随状态查询接口泄露给前端的实际风险 |
| 服务端 URL 网段校验 | `/api/rag/chat` 匿名可用，未校验等于提供匿名内网探测代理 | 不校验：安全不可接受；域名白名单：废掉已确认的自定义端点需求 |
