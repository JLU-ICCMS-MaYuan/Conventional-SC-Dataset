# 知识图谱边关系

## 引用边

本 Feature 只定义一种论文到论文的事实边：

```text
引用论文 --cites--> 被引论文
```

它由 `paper_references` 中 `match_status='matched'` 的记录投影而来。源端必须绑定当前 `paper_revision`，源端和目标端都必须是当前已审核论文。目标论文只按 `papers.id` 绑定，不把引用事实错误绑定到某个内容版本。

## 去重与排序

- 同一篇来源论文重复列出同一个目标时，数据库保留每条原始引文，但图只保留一条 `(citing_paper_id, cited_paper_id)` 边。
- 被引次数是当前已审核来源论文的 `COUNT(DISTINCT citing_paper_id)`，不是外部平台总被引次数。
- 邻居按被引次数降序、`paper_id` 升序稳定排序。概览和搜索都按 `paper_id` 去重。
- `C -> A`、`C -> B`、`B -> A` 只创建一个 A 节点，并保留三条有向边；前端数据集的节点键为 `paper:<paper_id>`。

## 上游、下游与异常

- 上游：当前论文的参考文献目标，即当前论文引用的来源。
- 下游：目标为当前论文的来源论文，即谁引用了当前论文。
- 每次请求默认最多返回 5 篇，可用 `offset` 继续加载；服务端不递归展开整棵树。
- 数据库不强制 DAG。真实文献关系即使形成环也不删除；遍历使用访问集和节点去重。年份异常或循环关系应由管理员核验。

## 不属于引用边的关系

旧 Neo4j 的 `BUILDS_ON`、`RELATES_TO`、`STUDIES`、`AUTHORED` 和 `SHARES_STRUCTURE` 不参与本 Feature 的引用边生成。特别是 `papers.builds_on` 仍是 LLM 叙述字段，不能转换成真实论文引用关系。

## 代码与测试

- SQL 投影：`goserver/handlers/knowledge_graph.go`
- 前端去重：`frontend/src/pages/KnowledgeGraphPage.tsx`
- 解析和匹配：`backend/services/citation_graph.py`
- 查询测试：`goserver/handlers/knowledge_graph_test.go`
