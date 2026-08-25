# 灵感探索

## 功能说明

在普通问答之外，围绕检索证据生成研究想法卡片，并执行结构化的可行性评审。

## 当前行为

- 前端支持启用灵感探索模式并展示想法、证据和评审状态。
- 后端包含 session、router、retrieval、evidence 和 reviewer 等独立组件。
- 流式协议可以返回灵感卡片和评审相关事件。
- 测试文件覆盖灵感模式的主要模块接口。

## 工作流程

用户开启灵感模式并提交问题；路由器确定探索路径；检索器收集候选证据；生成器产生想法；reviewer 根据证据输出可行性评价；前端逐步展示事件。

## 约束

- 想法和评审由 LLM 与当前检索证据共同生成，不构成科研结论。
- 缺少聊天配置或证据数据时能力不可用或降级。
- 会话与事件类型必须保持前后端契约一致。

## 代码与测试

- `backend/rag/inspiration/`
- `backend/rag/core/engine.py`
- `backend/api/rag.py`
- `frontend/src/pages/RagPage.tsx`
- `frontend/src/lib/useStreamingChat.ts`
- `tests/05_rag_question_answering/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 生成结果的质量评估和人工反馈闭环待核验。
