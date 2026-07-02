# III. Superconductivity Data Search and Database Discovery

## Definition

Superconductivity Data Search and Database Discovery 是 SC-Wiki 的发现入口。它把本地结构化超导数据检索和外部数据库发现放在同一个大功能下：用户可以先通过周期表、化学式或元素体系查找本地论文和超导记录，也可以进一步把 Alexandria、HTSC-2025 等外部来源纳入同一发现视野。

## Current Status

当前状态是已落地。代码已经支持首页周期表选择、化学式搜索、四种检索模式、组合页文献浏览、关键词/年份/审核状态筛选、分页、引用导出、Alexandria 电声耦合数据库接口、HTSC-2025 常压高温超导体基准数据集接口，以及把本地、Alexandria 和 HTSC-2025 结果合并排序的搜索接口。

## Local Structured Search

本地结构化检索是这个功能的第一层，也是网站的主要前门。它围绕 `periodic_table_elements`、`chemical_systems`、`superconductors`、`papers` 和 `superconductor_records` 工作。

当前支持四种查询模式：

- `formula_search`：按用户输入的化学式表达式搜索同元素体系内的超导体，并按化学式身份、计量相似度、变量或范围约束匹配程度排序。
- `elements_exact_search`：只返回元素集合与当前选择完全一致的体系。
- `elements_combination_search`：返回所选元素的所有已存在子组合。
- `elements_contained_search`：返回所有包含所选元素的体系。

旧 URL 参数仍有兼容映射，例如 `only` 对应 `elements_exact_search`，`combination` 对应 `elements_combination_search`，`contains` 或 `contain` 对应 `elements_contained_search`。

## Local Browsing Flow

用户可以从首页 `/` 或周期表内容页 `/elements` 选择元素，也可以直接输入化学式表达式。前端会把元素集合排序后进入 `/compound/{element_symbols}`，并通过查询参数保留当前检索模式和化学式表达式。

组合页承担本地浏览任务。它展示当前元素体系下的论文、超导体和物理记录，支持关键词、年份范围、审核状态、分页和导出。列表内容包括标题、年份、作者、期刊、DOI、化学式、压强、空间群、Tc、稳定性、计算设置和记录摘要。

这部分不是数据上传，也不是 RAG 问答。它解决的是“用户如何发现和浏览已经进入数据库的结构化超导数据”。

## External Sources

外部数据库发现是这个功能的第二层，用于把本地数据库之外的候选材料也纳入探索范围。

Alexandria 能力主要面向电声耦合相关材料数据。代码中有 `backend/alexandria_db.py`、`backend/alexandria_import.py` 和 `backend/api/alexandria.py`。接口支持按元素搜索、列出元素、查看材料详情、下载材料数据、查看统计和生成 CIF。

HTSC-2025 能力主要面向常压高温超导体基准数据集。代码中有 `backend/api/htsc2025.py`。接口支持按元素搜索、查看统计和按名称查看详情。

本地数据库能力来自主业务表和 `backend/api/papers.py`。合并搜索时，系统把本地记录、Alexandria 结果和 HTSC-2025 结果转换为统一结果项，再按来源和 Tc 等规则排序。

## Discovery Flow

完整发现流程分为两个层次。

第一层是本地检索。用户从周期表、化学式或元素体系进入本地数据库结果，查看已经上传、维护或审核过的结构化数据。

第二层是外部扩展。对于更广的材料发现，`/api/papers/search/all` 会调用本地、Alexandria 和 HTSC-2025 三类来源，并按统一格式返回。

化学式搜索当前仍应理解为本地数据库优先能力，不应默认扩展到 Alexandria 或 HTSC-2025。外部数据库发现主要适合元素集合或体系层面的扩展搜索，而不是所有化学式相似检索都天然跨外部数据源。

## Code and API Evidence

本地检索接口：

- `POST /api/compounds/search`
- `GET /api/papers/compound/{element_symbols}`
- `POST /api/papers/search-by-mode`
- `GET /api/papers/{paper_id}`
- `POST /api/papers/export`

本地检索代码：

- `backend/api/compounds.py`
- `backend/api/papers.py`
- `backend/repositories/superconductors.py`
- `backend/formula_similarity.py`
- `frontend/static/js/periodic_table.js`
- `frontend/static/js/compound_page.js`

Alexandria 接口：

- `POST /api/alexandria/search`
- `GET /api/alexandria/elements`
- `GET /api/alexandria/material/{mat_id}`
- `GET /api/alexandria/material/{mat_id}/download`
- `GET /api/alexandria/stats`
- `GET /api/alexandria/material/{mat_id}/cif`

HTSC-2025 接口：

- `POST /api/htsc2025/search`
- `GET /api/htsc2025/stats`
- `GET /api/htsc2025/detail/{name}`

合并搜索接口：

- `POST /api/papers/search/all`

主入口装配在 `backend/main.py`：

- `app.include_router(compounds.router)`
- `app.include_router(papers.router)`
- `app.include_router(alexandria.router)`
- `app.include_router(htsc2025.router)`

## Relationship With Local Data

本地检索展示的是 SC-Wiki 自己的数据资产。外部数据库发现不是本地数据上传的替代品。外部结果可以帮助用户发现候选材料、比较本地数据库覆盖范围，或获取结构和物性线索；本地数据仍通过上传、维护和审核形成平台自己的可信数据资产。

外部来源也不天然进入首页 Tc-Year 或 Tc-Pressure 图表。图表主要读取本地 `superconductor_records` 中被标记为 `show_in_chart` 的记录。外部数据如果要成为主站图表数据，应经过明确导入和审核。

## Limitations

本地检索依赖结构化字段质量。化学式相似检索不是跨体系文本模糊搜索，不会返回额外元素、缺失元素或只部分元素重合的体系。组合页也不是全文搜索引擎，它主要围绕元素体系、化学式、年份、审核状态和结构化超导记录工作。

外部数据源的可用性依赖本地数据文件、导入脚本和数据路径。Alexandria 的大 JSON 响应需要 GZip 压缩支持。不同来源的字段语义不完全一致，因此合并搜索只能提供发现层的一致展示，不能假设所有数据都具有相同审核等级。

## Future Direction

后续可以把本地检索和外部发现做成更统一的探索界面，让用户在同一个结果页中区分本地已审核数据、本地未审核数据和外部候选数据。也可以把外部搜索结果转成待审核导入候选，让管理员一键把外部材料纳入本地结构化记录，并为外部来源增加来源标识、字段置信度、版本号和引用说明。
