# 本地材料检索

## 功能说明

从元素组合或化学式定位主业务数据库中的超导材料，并返回关联论文和物性记录。

## 当前行为

- Go API `POST /api/papers/search/records` 支持 `formula_search`、`elements_exact_search`、`elements_combination_search` 和 `elements_contained_search` 四种模式。
- 化学式检索通过化学式提取元素并构建 `system_key`；元素检索在 `chemical_systems` 内按精确、组合或包含关系匹配材料体系。
- 本地检索的记录主体是 `tc_results`，JOIN `material_states`、`superconductors` 与 `papers`；一行代表「一个材料在一组条件下的一个 Tc」。Tc 只存在于 `tc_results`，因此旧的「按普通物性表 `name = critical_temperature` 取记录」在条件化模型下必然为空。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 筛选条件各自对应真实列：Tc 用 `tc_results.tc_value_k`，压强用 `material_states.pressure_value_gpa`，元素用 `material_states.superconductor_id`，关键词匹配论文字段或 `superconductors.chemical_formula`。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 请求的 `superconductor_type` 参数当前落到 `material_states.state_kind`，但该列的取值是 `theoretical`/`experimental`/`mixed`/`unknown`，描述数据来源性质而非材料分类；材料分类维度是 `material_states.material_family_id`（`material_families` 目录）。社区图表与图表组合编辑器已改用材料家族，本地检索尚未跟进，属待核验的语义不一致。（[Issue #72](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/72)）
- 图表可见性（`chart_only`）筛选不再生效：主次标记是旧 `key_properties` 的概念，条件化模型中普通物性没有主次语义，无真实列可依据。请求仍可携带该参数，但被忽略。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）
- 只返回 `papers.review_status = approved` 的记录，这是公开数据边界。
- `/search` 页面支持来源选择、分页、Formula/关键词、Tc 范围、压强范围、年份范围、超导类型、审核状态和图表可见性筛选；默认每页 50 条。
- Go 层对本地搜索结果使用请求参数生成缓存键；当前缓存键只包含元素、模式和化学式，筛选参数不完整纳入缓存键，属于需要核验的行为风险。

## 工作流程

用户选择元素或输入化学式，前端构造搜索模式、来源和筛选参数；Go API 查询 `ChemicalSystem` 与 `Superconductor` 取得候选材料 ID；再以 `tc_results` 为主体 JOIN `material_states`、`superconductors` 与 `papers`，返回年份、化学式、类型、压强、代表 Tc、空间群、数据来源、审核状态和 DOI 等字段。

## 约束

- 查询语义依赖 Go 侧简化的化学式元素提取规则，不等同于完整化学式解析器。
- 当前 Go 侧本地检索按 `papers.year DESC, tc_results.id ASC` 排序；前端演示中对“代表 Tc 降序”的产品期望不等同于当前已实现后端排序。
- 本地结果的 `space_group` 取 `material_states.reported_space_group_symbol`（无值时为 `-`），不再是固定占位；但它仍只是展示列，空间群筛选未实现。（[Issue #57](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/57)）

## 代码与测试

- 入口：`frontend/src/pages/SearchPage.tsx`
- API：`goserver/handlers/papers.go`
- 路由：`goserver/main.go`
- 模型：`goserver/models/models.go`、`backend/models.py`
- 测试：`tests/03_data_search_and_database_discovery/`

## 相关变更记录

- [Issue #57：修复论文详情页字段缺失与恒零值，记录搜索主体迁移到 tc_results](../../specs/57-paper-detail-data-parity/spec.md)

## 已知问题

- `space_group_min` 和 `space_group_max` 会从前端发送，但当前 Go 本地检索未实际应用空间群筛选。
- `superconductor_type` 筛选按 `state_kind` 过滤，与「材料分类」的用户预期不符；社区图表侧已迁到 `material_family_id`，本地检索的取值集合与前端 `SC_TYPE_MAP` 展示映射均未同步。（[Issue #72](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/72)）
