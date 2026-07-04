# 05 检索增强问答：API 接口调整方案

## 规划接口

- `POST /api/rag/chat`：保留非流式问答。
- `POST /api/rag/chat/stream`：保留 SSE 流式问答。
- `POST /api/rag/extracted-candidates`：规划 AI 提取候选记录。
- `GET /api/rag/evidence/{evidence_id}`：规划证据详情查询。

## 验收标准

- 流式事件稳定。
- 证据详情能关联论文或结构化记录。
- 候选记录接口不绕过审核。
