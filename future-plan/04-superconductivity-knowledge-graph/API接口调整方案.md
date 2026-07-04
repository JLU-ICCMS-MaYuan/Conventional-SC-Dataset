# 04 超导发展知识图谱：API 接口调整方案

## 接口设计目标

API 需要服务论文关系图谱，而不是材料参数图谱。接口默认返回人工审核通过的论文节点和论文关系边，支持首页里程碑图谱、材料局部图谱、论文节点展开和论文详情查询。

## 默认首页图谱接口

`GET /api/knowledge-graph/overview`

用途：打开 `SC-knowledge` 时，返回超导领域里程碑论文图谱。

请求参数：

- `limit`：默认 10，最大 10。
- `scope`：默认 `approved_milestone`，表示只返回已审核里程碑论文关系。

响应字段：

- `nodes`：论文节点列表。
- `edges`：论文关系边列表。
- `data_scope`：数据范围说明，例如“已审核里程碑论文关系”。
- `generation_basis`：生成依据，例如“综述正文提炼 + 人工审核”。

节点字段建议包含：

- `id`
- `node_type`
- `doi`
- `title`
- `year`
- `journal`
- `superconductor_category`
- `is_milestone`
- `contribution_summary`

关系边字段建议包含：

- `id`
- `source_paper_id`
- `target_paper_id`
- `relation_type`
- `relation_label`
- `direction`
- `evidence_review_id`
- `evidence_summary`
- `review_status`

## 材料局部图谱接口

`GET /api/knowledge-graph/material/{formula}`

用途：根据材料体系或化学式返回该材料相关的代表论文关系图。

请求参数：

- `limit`：默认 10，最大 10。
- `relation_scope`：可选，限制关系类型。

响应字段：

- `center`：材料中心节点。
- `nodes`：该材料相关代表论文节点。
- `edges`：论文之间或材料到论文之间的关系边。
- `data_scope`：数据范围说明。

注意：材料中心节点只作为检索主题入口，不用于承载 Tc、压强、空间群等参数节点。

## 论文展开接口

`GET /api/knowledge-graph/papers/{paper_id}/neighbors`

用途：用户点击某篇论文节点后，返回这一篇论文的一层关联论文。

请求参数：

- `limit`：默认 10，最大 10。
- `relation_types`：可选，限制关系类型。
- `exclude_node_ids`：可选，前端当前已经展示的节点 ID，用于避免重复返回。

响应字段：

- `center_paper_id`
- `new_nodes`
- `new_edges`
- `highlight_edges`
- `has_more`

规则：

- 每次只返回一层关联论文。
- 已存在节点不重复返回到 `new_nodes`。
- 已存在节点之间的新关系放入 `highlight_edges`。

## 论文详情接口

`GET /api/knowledge-graph/papers/{paper_id}`

用途：返回论文节点详情，用于右侧详情面板。

响应字段：

- `doi`
- `title`
- `year`
- `journal`
- `abstract`
- `contribution_summary`
- `superconductor_category`
- `related_formulas`
- `parameter_summary`
- `review_status`
- `relations_summary`

`parameter_summary` 可包含 Tc、压强、空间群、结构等摘要信息，但这些字段只用于详情面板，不作为默认图谱节点。

## AI 提炼预览接口

`POST /api/knowledge-graph/review-papers/{paper_id}/extract-relations`

用途：从综述论文正文中提炼候选论文关系，供管理员审核。

请求字段：

- `paper_id`
- `body_text`
- `reference_list`

响应字段：

- `candidate_papers`
- `candidate_relations`
- `metadata_completions`
- `warnings`

规则：

- `body_text` 是关系提炼的主要依据。
- `reference_list` 只用于补全 DOI、标题、年份、期刊等元数据。
- 不能仅根据参考文献列表生成论文关系边。
- 抽取结果默认进入待审核状态，不直接展示给普通用户。

## 人工审核接口

`POST /api/knowledge-graph/relations/{relation_id}/review`

用途：管理员审核 AI 提炼出的论文关系边。

请求字段：

- `review_status`：`approved`、`rejected`。
- `review_comment`
- `is_milestone_relation`

只有 `approved` 的关系边才能进入默认首页或材料局部图谱。

## 关系类型

API 中建议使用稳定英文枚举，前端再映射为中文标签：

| 枚举 | 中文标签 |
| --- | --- |
| `first_discovery` | 首次发现 |
| `theoretical_basis` | 理论基础 |
| `experimental_validation` | 实验验证 |
| `development_extension` | 发展延续 |
| `material_system_extension` | 材料体系扩展 |
| `supporting_evidence` | 作证或支撑 |
| `correction_or_dispute` | 修正或争议 |
| `same_research_direction` | 同方向里程碑 |

## 验收标准

- `GET /api/knowledge-graph/overview` 默认最多返回 10 篇已审核里程碑论文。
- 首页图谱不返回 Tc、压强、空间群等属性节点。
- `GET /api/knowledge-graph/papers/{paper_id}/neighbors` 每次只返回一层关联论文。
- AI 提炼接口明确正文为主、参考文献列表为辅。
- 参考文献列表不能单独生成论文关系边。
- 所有前端可见关系边都必须处于已审核状态。
- API 响应中的节点和边都能追溯到综述证据或人工审核记录。
