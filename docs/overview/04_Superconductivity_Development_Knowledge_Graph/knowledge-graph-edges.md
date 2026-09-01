# 知识图谱边关系

## 功能说明

定义和生成知识图谱中节点之间的关系边，包括论文之间的 `BUILDS_ON`、`RELATES_TO`，论文与材料的 `STUDIES`，论文与作者的 `AUTHORED`，以及材料之间的 `SHARES_STRUCTURE`。

## 当前行为

### BUILDS_ON 关系（Paper → Paper，部分可用）

- **数据来源**：AI 从论文中提取"前驱工作"（prerequisite works）。`backend/ingest/enrich_papers.py` 的提示词要求 AI 识别核心方法/结论直接依赖的前人工作（0-3 个），如 "Allen-Dynes Tc equation"、"BCS theory" 等理论框架或计算公式。
- **存储格式**：MySQL `papers.builds_on` (JSON)，例如 `[{"work": "Allen-Dynes Tc equation", "hint": "Allen, Dynes, 1975"}]`。`work` 字段是方法/理论名称，`hint` 是作者和年份提示。
- **同步到 Neo4j**：`backend/ingest/sync_neo4j.py` 的 `sync_builds_on()` 方法读取 `builds_on` 字段，为每个前驱工作创建 `BUILDS_ON` 关系。但目标节点是占位符（`paper_id: -1`），并设置 `work_name` 和 `work_hint` 属性，未实现到真实论文节点的匹配。
- **当前状态**：关系已创建但目标断开，知识图谱前端无法渲染这些边。原因是 AI 提取的是方法名称而非论文 DOI 或标题，缺少从 `work_name` 到真实 `paper_id` 的映射逻辑。

### RELATES_TO 关系（Paper ↔ Paper，未实现）

- **当前状态**：`backend/api/kg_live.py` 查询时包含 `RELATES_TO` 边，但 `backend/ingest/sync_neo4j.py` 中没有创建逻辑，Neo4j 中此关系为空。
- **可能实现方式**：基于共同研究材料（通过 `STUDIES` 关系推导）、基于作者共现（通过 `AUTHORED` 关系推导）、基于向量相似度（定期批量计算 Qdrant 嵌入的余弦相似度）、或让 AI 提取论文引言中提到的相关研究。

### STUDIES 关系（Paper → Material，已实现）

- **数据来源**：AI 提取的 `research_materials` 和 `material_relations` 字段（`backend/ingest/enrich_papers.py`）。
- **同步逻辑**：`sync_neo4j.py` 的 `sync_studies()` 方法读取这些字段，为每个研究材料创建 `STUDIES` 关系，关系属性包含 `role`（"discovers"/"investigates"/"predicts"）和 `evidence`（原文证据）。

### AUTHORED 关系（Researcher → Paper，已实现）

- **数据来源**：论文元数据的 `authors` 字段（JSON 数组）。
- **同步逻辑**：`sync_neo4j.py` 的 `sync_researchers()` 方法读取作者列表，为每个作者创建 `Researcher` 节点（如不存在）并建立 `AUTHORED` 关系。

### SHARES_STRUCTURE 关系（Material ↔ Material，已实现）

- **生成逻辑**：`sync_neo4j.py` 的 `sync_shares_structure()` 方法通过 Cypher 查询匹配相同空间群和晶体结构的材料对，创建无向的 `SHARES_STRUCTURE` 关系。
- **约束**：仅在材料节点的 `space_group` 和 `crystal_structure` 属性均非空时生效。

## 工作流程

论文上传后，`enrich_papers.py` 通过 AI 提取 `builds_on`、`research_materials`、`material_relations` 等字段并保存到 MySQL。审批通过后，`publish_approved_paper()` 触发增量同步，或管理员运行 `sync_neo4j.py` 全量同步，将这些字段转换为 Neo4j 关系。前端查询知识图谱时，API 从 Neo4j 读取节点及其关系边并返回给前端渲染。

## 约束

- `BUILDS_ON` 关系的目标节点当前是占位符（`paper_id: -1`），需要实现从 `work_name`/`hint` 到真实论文的匹配逻辑（通过 DOI、标题模糊匹配或维护"经典工作 → 论文 ID"映射表）。
- `RELATES_TO` 关系未实现，知识图谱缺少论文间的相关性连接，图显示稀疏。
- `STUDIES` 和 `AUTHORED` 关系依赖 AI 提取质量和论文元数据完整性。
- 关系同步的触发时机：审批通过时自动增量同步（`publish_approved_paper()`），或手动全量同步（`sync_neo4j.py`）。

## 代码与测试

- AI 提取：`backend/ingest/enrich_papers.py` `PROMPT` 任务 3/6
- 数据模型：`backend/models.py` `Paper.builds_on`
- 同步脚本：`backend/ingest/sync_neo4j.py` `sync_builds_on()`、`sync_studies()`、`sync_researchers()`、`sync_shares_structure()`
- 增量同步：`backend/api/rag.py` `publish_approved_paper()`
- 查询工具：`backend/rag/tools/neo4j.py` `traverse_graph()`、`find_path()`
- 前端 API：`backend/api/kg_live.py` `/overview` 返回 `edges`

## 相关变更记录

- [Issue #70：知识图谱节点专用标题](../../specs/70-knowledge-graph-title/spec.md) - 间接关联，同步逻辑涉及节点属性

## 已知问题

- `BUILDS_ON` 关系目标节点是占位符，前端无法渲染这些边。待实现匹配逻辑。
- `RELATES_TO` 关系完全缺失，需要基于材料、作者或向量相似度生成。
- 同一前驱工作可能被多篇论文引用，但当前每次引用都创建独立的占位符节点（`paper_id: -1`），未合并去重。
- 缺少关系删除逻辑：论文删除时需要同步清理 Neo4j 中的相关关系（当前 `delete_paper_from_graph()` 使用 `DETACH DELETE` 可自动清理）。
