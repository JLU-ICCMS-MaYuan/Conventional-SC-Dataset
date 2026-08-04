# PDF 摄入

## 功能说明

接收 PDF 文件并通过摄入流水线提取文献内容，写入 RAG 数据库和检索存储。

## 当前行为

- API 校验上传文件类型并写入临时文件。
- 服务将临时路径和原始文件名交给摄入流水线。
- 摄入模块负责抽取、结构化和存储，完成后返回处理结果。
- 缺少必要数据环境时返回明确错误。

## 工作流程

客户端上传 PDF；API 创建临时文件；摄入器提取文档与元数据；数据写入 RAG 数据库和向量存储；API 清理临时资源并返回结果。

## 约束

- 只接受 PDF 类型，文件内容仍可能因损坏或版式无法正确抽取。
- 摄入目标是独立 RAG 存储，不是主业务 `Paper` 表。
- 当前 `SharePage` 主要调用此能力，但页面名称不能改变其实际数据边界。

## 代码与测试

- `backend/api/rag.py`
- `backend/rag/service.py`
- `backend/rag/ingest/`
- `frontend/src/pages/SharePage.tsx`
- `tests/05_rag_question_answering/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 摄入失败后的跨数据库回滚和重复文档策略待核验。
