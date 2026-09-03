# 可用性与配置

## 功能说明

集中解析 RAG 数据路径、异步数据库、Qdrant、Embedding 和 LLM 设置，并分别报告检索与聊天能力是否可用。

## 当前行为

- `RagSettings` 管理数据根目录、数据库、向量库和 LLM 参数。
- 默认数据根指向仓库外的相邻数据集目录。
- 健康检查分别判断数据库、向量库和聊天配置，检索可用与聊天可用不是同一状态。
- 服务层在缺少数据或 LLM 时返回明确的不可用错误或降级信息。
- 顶栏可配置服务端默认、DeepSeek、Kimi、GLM、Qwen、OpenAI、Claude 或自定义的 OpenAI 兼容端点。
  用户配置通过 `X-LLM-Provider`、`X-LLM-Base-URL`、`X-LLM-Model`、`X-LLM-Api-Key` 传递，
  仅保存在浏览器 `localStorage`，服务端不把 API key 写入数据库或公开任务状态。
- 个人 API Key 输入默认掩码；用户可在当前表单内显式显示或隐藏它，关闭面板后仍只以掩码摘要展示。

## 工作流程

应用首次调用时加载设置；服务健康检查验证文件和目录；搜索端点要求数据库与向量能力；对话端点额外检查当前请求的 LLM 凭据。
用户配置失败时不会静默回退到服务端密钥。`POST /api/rag/llm/test-connection` 用最小请求验证模型和凭据，
并映射认证失败、模型不存在、不可达和超时错误。
`GET /api/rag/llm/current` 仅返回供应商显示名、模型名和来源（`server` / `browser`），供顶栏明确显示
当前模型；响应不包含 Base URL、API key、请求头或密钥掩码。
部署可用 `LLM_PROVIDER_NAME` 显式标注网关上游，例如当前默认配置为 `OpenAI · gpt-5.6-sol`；不再仅按
Base URL 推断。超级管理员可在工作台更新默认供应商、Base URL、模型和密钥，配置原子写入 API 与
Worker 共用的 `/data/runtime/default_llm.json`，后续调用立即生效。仅超级管理员可读取或修改该配置，
密钥字段从不回显，空密钥表示保留既有值。工作台默认以摘要卡片展示当前模型；只有点击“编辑”才打开
可修改表单，当前角色卡片使用普通文本布局并对溢出截断。

## 约束

- 缺少 `RAG_DATA_ROOT` 对应数据、Qdrant 或 API key 时，部分或全部能力不可用。
- 主应用数据库正常不表示 RAG 数据库正常。
- 配置值可能来自环境变量，文档不记录任何实际密钥。

## 代码与测试

- `backend/rag/config.py`
- `backend/rag/service.py`
- `backend/api/rag.py`
- `tests/05_rag_question_answering/`

## 相关变更记录

实现来源：[Issue #73：顶栏 AI 供应商切换](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/73)。

## 已知问题

- 外部数据目录的部署和同步流程待核验。
