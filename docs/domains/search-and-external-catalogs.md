# 检索与外部目录

## 职责

用户可从元素体系和化学式进入 SC-Wiki，并在主库、Alexandria 和 HTSC-2025
数据源中发现论文与超导相关数据。RAG 的语义/向量检索属于
[rag-and-knowledge-graph.md](rag-and-knowledge-graph.md)。

## 当前入口

- React 路由提供 `/elements`、`/periodic-table`、`/compound/:elementSymbols`。
- FastAPI 注册元素、化合物、文献、Alexandria 与 HTSC-2025 路由。
- Memory Bank 中的“化学式相似检索”限定为同一元素体系内的结构化匹配，不等同于
  任意关键词或跨体系模糊搜索。

## 证据

- `frontend/src/App.tsx`
- `backend/main.py`
- `backend/api/papers.py`
- `backend/api/alexandria.py`
- `backend/api/htsc2025.py`

## 已知缺口

- 当前文档不把搜索结果表格重构视为已交付能力；后续改造应从 `type:idea` 转为
  `type:feature` 后再建立 Spec。
