# VII. External Superconductivity Database Discovery

## Definition

External Superconductivity Database Discovery 是七大功能中真正新增的一项。它指 SC-Wiki 不只查询本地用户提交和维护的数据，还能接入外部超导相关数据源，把外部材料数据库与本地元素体系检索统一到同一发现流程中。

## Current Status

当前状态是已落地。代码已经包含 Alexandria 电声耦合数据库接口、HTSC-2025 常压高温超导体基准数据集接口，以及把本地、Alexandria 和 HTSC-2025 结果合并排序的搜索接口。

## External Sources

Alexandria 能力主要面向电声耦合相关材料数据。代码中有 `backend/alexandria_db.py`、`backend/alexandria_import.py` 和 `backend/api/alexandria.py`。接口支持按元素搜索、列出元素、查看材料详情、下载材料数据、查看统计和生成 CIF。

HTSC-2025 能力主要面向常压高温超导体基准数据集。代码中有 `backend/api/htsc2025.py`。接口支持按元素搜索、查看统计和按名称查看详情。

本地数据库能力来自主业务表和 `backend/api/papers.py`。合并搜索时，系统把本地记录、Alexandria 结果和 HTSC-2025 结果转换为统一结果项，再按来源和 Tc 等规则排序。

## Discovery Flow

外部数据库发现通常从元素选择开始。用户在首页选择元素或进入元素组合页后，本地数据库先提供论文和超导记录。对于更广的发现，`/api/papers/search/all` 会调用本地、Alexandria 和 HTSC-2025 三类来源，并按统一格式返回。

旧文档里提到化学式搜索第一版只保证本地数据库结果，不覆盖 Alexandria 或 HTSC-2025。这个边界仍然重要：外部数据库发现主要适合元素集合或体系层面的扩展搜索，而不是所有化学式相似检索都天然跨外部数据源。

## Code and API Evidence

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

- `app.include_router(alexandria.router)`
- `app.include_router(htsc2025.router)`

## Relationship With Local Data

外部数据库发现不是本地数据上传的替代品。外部结果可以帮助用户发现候选材料、比较本地数据库覆盖范围，或获取结构和物性线索；本地数据仍通过上传、维护和审核形成平台自己的可信数据资产。

外部来源也不天然进入首页 Tc-Year 或 Tc-Pressure 图表。图表主要读取本地 `superconductor_records` 中被标记为 `show_in_chart` 的记录。外部数据如果要成为主站图表数据，应经过明确导入和审核。

## Limitations

外部数据源的可用性依赖本地数据文件、导入脚本和数据路径。Alexandria 的大 JSON 响应需要 GZip 压缩支持。不同来源的字段语义不完全一致，因此合并搜索只能提供发现层的一致展示，不能假设所有数据都具有相同审核等级。

## Future Direction

后续可以把外部搜索结果转成待审核导入候选，让管理员一键把外部材料纳入本地结构化记录。也可以为外部来源增加来源标识、字段置信度、版本号和引用说明，避免用户把外部发现结果误认为已经被 SC-Wiki 审核通过。
