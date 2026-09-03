# 契约：用户 LLM 凭据请求头与连接测试端点

**关联**：[../spec.md](../spec.md) · [../plan.md](../plan.md)

## 1. 请求头契约

前端 `frontend/src/lib/api.ts` 在 `request` 与 `postStream` 两个出口统一注入。仅当用户
已保存本地配置且所选项不是「服务端默认」时注入。

| 请求头 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- |
| `X-LLM-Provider` | 是 | 供应商标识，仅用于日志与响应回显 | `kimi` |
| `X-LLM-Base-URL` | 是 | OpenAI 兼容端点根地址 | `https://api.moonshot.cn/v1` |
| `X-LLM-Model` | 是 | 模型名，自由文本 | `moonshot-v1-8k` |
| `X-LLM-Api-Key` | 是 | 用户密钥，明文传输（依赖 TLS） | `sk-xxxxxxxx` |

**取值约束**：

- 四个头必须同时出现。缺任一个则整组视为无效，回退服务端默认配置（FR-013），并在响应中
  以 `provider: "server-default"` 标明。
- `X-LLM-Api-Key` 值中不得含换行或非 ASCII 字符（HTTP 头限制）。含非法字符时返回 400。
- 头名大小写不敏感，按 HTTP 规范处理。

**日志约束**（FR-018）：

- 后端任何日志记录不得包含 `X-LLM-Api-Key` 的值。
- nginx `log_format` 不得引用 `$http_x_llm_api_key`。
- 异常堆栈与错误响应体中出现的凭据必须经脱敏工具处理为 `sk-****abcd` 形式。

## 2. 供应商预设常量

前端常量，不含密钥。Base URL 与模型名以浅灰 placeholder 呈现，用户可编辑（FR-003）。

| 标识 | 展示名 | Base URL placeholder | 默认模型 placeholder |
| --- | --- | --- | --- |
| `server-default` | 服务端默认 | 不可填 | 不可填 |
| `deepseek` | DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| `kimi` | Kimi | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| `glm` | 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-plus` |
| `qwen` | 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| `openai` | OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `claude` | Claude | `https://api.anthropic.com/v1` | `claude-sonnet-4-5` |
| `custom` | 自定义 | `https://your-gateway.example.com/v1` | 空 |

> 实施时必须逐一核对各供应商官方文档确认 Base URL 与模型名，不得沿用本表未经验证的值。
> Claude 项还需实测 OpenAI 兼容层对 `response_format={"type":"json_object"}` 的支持
> （见 [../research.md](../research.md) D-006）。

## 3. Base URL 校验规则

服务端在构造客户端前执行（FR-017）。前端同步实现同一规则仅作即时反馈。

**允许**：

- `https://` 任意公网主机。
- `http://localhost[:port]`、`http://127.0.0.1[:port]`——支持本地模型（FR-015 例外）。

**拒绝**：

| 拒绝原因 | 判定 | 错误码 |
| --- | --- | --- |
| 协议非 https | scheme 非 `https`，且主机不是 localhost/127.0.0.1 | `LLM_URL_INSECURE` |
| 私有网段 | 解析后 IP 属 `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16` | `LLM_URL_PRIVATE` |
| 链路本地 | 解析后 IP 属 `169.254.0.0/16`（含云元数据 `169.254.169.254`） | `LLM_URL_PRIVATE` |
| 回环 | 解析后 IP 属 `127.0.0.0/8` 或 `::1`，且用户未显式填写 localhost | `LLM_URL_PRIVATE` |
| 唯一本地地址 | IPv6 `fc00::/7` | `LLM_URL_PRIVATE` |
| 无法解析 | 域名解析失败 | `LLM_URL_UNRESOLVABLE` |

校验在域名解析之后按 IP 判定，以挡住 DNS 指向内网的公网域名。解析与实际连接之间的
时间窗风险已在 research.md D-004 记录为接受的残余风险。

## 4. 连接测试端点

```
POST /api/rag/llm/test-connection
```

**鉴权**：与 `/api/rag/chat` 一致，不要求登录。

**请求**：凭据经第 1 节请求头传递，body 为空。

**成功响应** `200`：

```json
{
  "ok": true,
  "data": {
    "provider": "kimi",
    "model": "moonshot-v1-8k",
    "latency_ms": 842
  }
}
```

**失败响应** `400` / `502`，四类可区分错误（FR-023）：

| 场景 | 状态码 | `code` | `message` |
| --- | --- | --- | --- |
| 密钥无效或过期 | 400 | `LLM_AUTH_FAILED` | API Key 无效或已过期 |
| 地址不可达或非 LLM 端点 | 502 | `LLM_UNREACHABLE` | 服务地址不可达 |
| 模型名不存在 | 400 | `LLM_MODEL_NOT_FOUND` | 模型名不存在 |
| 超过 15 秒未响应 | 504 | `LLM_TIMEOUT` | 连接测试超时，请重试 |
| URL 校验未通过 | 400 | 见第 3 节 | 对应提示 |

响应体不得回显 `X-LLM-Api-Key` 的任何完整片段。

**测试请求形态**：向目标端点发一次最小 `chat.completions` 调用（`max_tokens` 取 1），
读超时 15 秒，`max_retries=0`。不使用 `/models` 列表接口，因为部分中转站不实现该接口。

## 5. AI 响应的供应商回显

受影响端点：`POST /api/rag/chat`、`POST /api/rag/chat/stream`、上传解析任务状态。

在既有响应 `data` 中增加两个字段（FR-021）：

```json
{
  "provider": "kimi",
  "model": "moonshot-v1-8k"
}
```

未配置用户返回 `provider: "server-default"` 与服务端实际模型名。流式端点在 `done`
事件的 `data` 中携带同样字段。

## 6. 当前模型展示元数据

```
GET /api/rag/llm/current
```

**鉴权**：不要求登录，与 RAG 健康检查一致。

**成功响应** `200`：

```json
{
  "ok": true,
  "data": {
    "provider": "server-default",
    "provider_name": "DeepSeek",
    "model": "deepseek-chat",
    "source": "server"
  }
}
```

`provider` 保持内部稳定标识；`provider_name` 是供顶栏展示的名称。若服务端 Base URL 无法映射到
已知供应商，返回「服务端默认」/`Server default` 的本地化回退名。个人配置请求返回
`source: "browser"` 及其请求级供应商、模型名。

**禁止字段**：响应不得包含 `api_key`、`base_url`、`X-LLM-*`、请求头、密钥掩码或任何可用于重建
凭据的字段。

## 7. 用户凭据失败的错误契约

用户自带凭据调用失败时（FR-019），**不得**改用服务端默认配置重试。错误响应须标明失败源：

```json
{
  "ok": false,
  "detail": {
    "code": "LLM_USER_CREDENTIAL_FAILED",
    "message": "你配置的 AI 供应商调用失败：API Key 无效或已过期。可在顶栏切回默认模型。",
    "provider": "kimi"
  }
}
```
