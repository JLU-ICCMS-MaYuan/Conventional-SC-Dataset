# 超导知识图谱

## 功能说明

`/knowledge` 展示 SC-Wiki 已审核论文的引用发展图。它用于查看一个材料家族或超导类型的论文演化、识别库内重要论文，并按需查看单篇论文的来源和重要分支。

## 当前行为

- Go API 直接查询 MySQL，不读取 `graph.json` 或代理 Neo4j：
  - `GET /api/knowledge-graph/overview`
  - `GET /api/knowledge-graph/papers/:paperId/neighbors`
  - `GET /api/knowledge-graph/search`
  - `GET /api/knowledge-graph/stats`
- 概览默认最多返回 30 个节点；可按论文级 Material family 多选和 `papers.superconductor_kind` 筛选。 `unknown` 不进入常规/非常规筛选，但仍可被搜索并固定。
- 节点短标题优先使用 `knowledge_graph_title`，同时返回原标题、年份、Material family、Superconductor type、库内被引次数和人工里程碑标记。
- 边方向固定为 `citing_paper_id -> cited_paper_id`。上游是当前论文引用的论文，下游是引用当前论文的论文。
- 邻居接口单方向分页，默认每次 5 篇，按库内被引次数降序、`paper_id` 升序排序，并返回 `remaining_count`。服务端不递归加载整棵图。
- 标题或 DOI 搜索从全部当前已审核论文中执行，搜索到的节点可以加入当前图视图。

## 数据约束

- 公开节点和边的两端都必须是 `review_status=approved` 且 `approved_revision=content_revision` 的当前论文。
- `papers.year` 在数据库和提交/审核流程中必须有值；参考文献的 `paper_references.year` 可以为空，因为外部引文可能解析不到年份。
- 被引次数是 `COUNT(DISTINCT citing_paper_id)`，只统计库内当前已审核论文。同一来源重复列出目标论文不会增加计数。
- 节点唯一键为 `paper_id`，不是树路径。循环或时间异常的原始引用不被删除，查询侧按已访问论文避免重复。

## 代码与测试

- API：`goserver/handlers/knowledge_graph.go`
- 管理标记：`goserver/handlers/paper_graph_marks.go`
- 页面：`frontend/src/pages/KnowledgeGraphPage.tsx`
- 测试：`goserver/handlers/knowledge_graph_test.go`、`backend/tests/test_citation_graph.py`
