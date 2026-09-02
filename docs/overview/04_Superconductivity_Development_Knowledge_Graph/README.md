# 超导论文引用发展知识图谱

## 功能边界

本功能只展示 SC-Wiki 已审核通过的论文，并用 MySQL 中由 GROBID 解析、可追溯的引用事实组织论文之间的上游和下游关系。Material family 是论文级多选分类，Superconductor type 是论文级单选分类；两者都沿用现有审核分类体系。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [超导知识图谱](superconductivity-knowledge-graph.md) | 分类概览、节点搜索、引用边和分页展开 | Go API、MySQL、vis-network |
| [知识图谱数据同步](knowledge-graph-data-sync.md) | 上传时解析引用、提交保存、审核后匹配和历史重试 | Python Worker、GROBID、MySQL、Redis |
| [知识图谱边关系](knowledge-graph-edges.md) | 定义真实引用边、节点去重和被引计数 | `paper_references`、当前论文版本 |
| [知识图谱节点标题](knowledge-graph-node-titles.md) | 提供节点短标题并在缺失时回退原标题 | `papers.knowledge_graph_title` |

## 当前能力

- `/knowledge` 支持 Material family 多选、常规/非常规 Superconductor type 组合筛选，以及标题或 DOI 搜索后固定节点。
- 节点按 `paper_id` 去重，圆点大小按库内已审核下游论文的去重数量缩放。
- 箭头方向为“引用论文 → 被引论文”。点击节点后，上游和下游分别按被引次数排序，每次最多请求 5 篇，并显示剩余数量。
- 通过 GROBID 保存 DOI、题名、作者、年份和原始引文。未匹配引文保留在数据库，目标论文以后审核通过时自动重试。
- 管理员和超级管理员可以人工维护 `origin`（源头）与 `breakthrough`（突破）标记；系统不会用引用数自动认定里程碑。

## 数据与兼容边界

MySQL 是引用事实和公开图查询的唯一来源。旧 Neo4j、`graph.json`、`builds_on`、`RELATES_TO` 和材料/作者关系仍可能服务于历史功能，但不参与本引用图的边生成、计数或公开查询。图查询不要求数据库无环，而是在遍历和前端数据集内按 `paper_id` 去重并避免重复展开。

## 相关实现

- Go API：`goserver/handlers/knowledge_graph.go`、`goserver/handlers/paper_graph_marks.go`
- Python 解析与匹配：`backend/services/citation_graph.py`、`backend/ingest/upload_jobs.py`
- 前端：`frontend/src/pages/KnowledgeGraphPage.tsx`
- Schema：`alembic/versions/20260902_0004_paper_citation_graph.py`
- 规格：`docs/specs/81-citation-graph/`
