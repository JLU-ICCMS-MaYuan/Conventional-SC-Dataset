# 04 超导发展知识图谱当前规划

## 总体定位

负责把论文、材料、物性参数和结构化记录组织为可查询关系层，为 RAG 和未来图谱页面提供基础。

## 当前状态

部分落地。

## 文档导航

- [总体规划](README.md)
- [前端设计](frontend-design.md)
- [后端设计](backend-design.md)
- [API 设计](api-design.md)

## 核心建设内容

### 前端

- 当前没有独立知识图谱页面。
- 未来页面展示材料节点、论文节点、物性边、年份和压力关系。
- 未完成的图谱探索能力需要标注「有待建设」。

### 后端

- 当前 KG 查询位于 `backend/rag/knowledge_graph.py`。
- 短期复用主业务数据库，不急于引入图数据库。
- 后续抽象独立图谱服务，供 RAG 和前端图谱共用。

### API

- 当前通过 `POST /api/rag/chat` 间接调用 KG。
- 未来新增 `/api/knowledge-graph/material/{formula}` 查询材料局部图。
- 未来新增 `/api/knowledge-graph/search` 支持按元素、Tc、压强和年份筛选。

## 数据模型与数据流

图谱关系来自 `papers`、`superconductors`、`superconductor_records`，重点字段包括化学式、Tc、压力、lambda、omega_log、论文年份和 DOI。

## 验收标准

- KG 数值查询与 RAG 回答一致。
- 空关系有明确提示。
- 审核状态过滤正确。
