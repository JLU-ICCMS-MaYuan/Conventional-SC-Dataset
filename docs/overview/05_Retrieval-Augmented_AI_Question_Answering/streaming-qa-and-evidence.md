# 流式问答与证据

## 功能说明

基于检索结果构造上下文，通过 SSE 持续返回回答、引文、证据和状态事件，并在 React 中维护多轮会话。

## 当前行为

- `/api/rag/chat/stream` 使用 `text/event-stream` 返回流式事件。
- 问答引擎先检索上下文，再调用 OpenAI 兼容的 LLM 接口生成回答。
- 事件包含回答增量、引文、证据、Top 结果及灵感模式相关数据。
- React hook `useStreamingChat` 消费 SSE，并在浏览器本地保存多个会话、证据、想法和评审元数据。

## 工作流程

用户提交问题；服务检查聊天配置；检索引擎生成上下文；问答引擎调用 LLM；API 将内部事件编码为 SSE；前端逐事件更新消息、证据卡片和会话状态。

## 约束

- 需要检索数据可用且配置 LLM API key。
- 引文和证据来自当前检索结果，不等同于人工审稿结论。
- 浏览器本地会话不构成服务端持久化或跨设备同步。

## 代码与测试

- `backend/api/rag.py`
- `backend/rag/service.py`
- `backend/rag/core/engine.py`
- `frontend/src/pages/RagPage.tsx`
- `frontend/src/lib/useStreamingChat.ts`
- `tests/05_rag_question_answering/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 外部 LLM 的可用性、费用和响应稳定性不由本项目保证。
