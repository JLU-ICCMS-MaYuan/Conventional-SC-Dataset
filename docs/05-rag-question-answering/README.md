# 05 检索增强问答当前规划

## 总体定位

负责自然语言问答、结构化 KG 查询、向量检索、证据引用和 LLM 回答生成。

## 当前状态

已落地。

## 文档导航

- [总体规划](README.md)
- [前端设计](frontend-design.md)
- [后端设计](backend-design.md)
- [API 设计](api-design.md)

## 核心建设内容

### 前端

- `/rag` 页面展示对话、流式输出、引用和证据卡片。
- 未来增加“从回答生成待审核数据”入口，并标注「有待建设」。
- 证据卡片应区分主业务记录、论文片段、KG 结果和外部来源。

### 后端

- RAG 后端由 `backend/api/rag.py`、`backend/rag/service.py` 和 `backend/rag/rag/engine.py` 组成。
- 需要区分数据库、Chroma 向量库和 LLM 三类可用性。
- 未来把 PDF 摄入结果转入主业务待审核队列。

### API

- `POST /api/rag/chat`：非流式问答。
- `POST /api/rag/chat/stream`：SSE 流式问答。
- `POST /api/rag/upload-pdf`：上传 PDF 进入 RAG 摄入流程。
- 未来新增 AI 提取候选记录接口。

## 数据模型与数据流

问题先经过意图判断，再调用 KG 或向量检索，整理证据后交给 LLM 生成回答。AI 提取结果不得绕过审核直接公开。

## 验收标准

- 健康检查准确。
- 流式输出稳定。
- 引用能追溯到来源。
