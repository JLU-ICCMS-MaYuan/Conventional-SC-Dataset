# 本地材料检索

## 功能说明

从元素组合或化学式定位主业务数据库中的超导材料，并返回关联论文和物性记录。

## 当前行为

- Go API `POST /api/papers/search/records` 支持 `formula_search`、`elements_exact_search`、`elements_combination_search` 和 `elements_contained_search` 四种模式。
- 化学式检索通过化学式提取元素并构建 `system_key`；元素检索在 `chemical_systems` 内按精确、组合或包含关系匹配材料体系。
- 当前本地检索以 `key_properties.name = critical_temperature` 且存在数值的物性记录为主结果，再关联 `papers` 生成扁平展示行。
- `/search` 页面支持来源选择、分页、Formula/关键词、Tc 范围、压强范围、年份范围、超导类型、审核状态和图表可见性筛选；默认每页 50 条。
- Go 层对本地搜索结果使用请求参数生成缓存键；当前缓存键只包含元素、模式和化学式，筛选参数不完整纳入缓存键，属于需要核验的行为风险。

## 工作流程

用户选择元素或输入化学式，前端构造搜索模式、来源和筛选参数；Go API 查询 `ChemicalSystem` 与 `Superconductor` 取得候选材料 ID；再 JOIN `key_properties` 与 `papers`，返回年份、体系名称、类型、压强、代表 Tc、空间群占位、数据来源、审核状态和 DOI 等字段。

## 约束

- 查询语义依赖 Go 侧简化的化学式元素提取规则，不等同于完整化学式解析器。
- 当前 Go 侧本地检索按 `papers.year DESC, key_properties.id ASC` 排序；前端演示中对“代表 Tc 降序”的产品期望不等同于当前已实现后端排序。
- 本地结果的 `space_group` 当前由 Go API 固定返回 `-`，不是可搜索的结构空间群字段。

## 代码与测试

- 入口：`frontend/src/pages/SearchPage.tsx`
- API：`goserver/handlers/papers.go`
- 路由：`goserver/main.go`
- 模型：`goserver/models/models.go`、`backend/models.py`
- 测试：`tests/03_data_search_and_database_discovery/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- `space_group_min` 和 `space_group_max` 会从前端发送，但当前 Go 本地检索未实际应用空间群筛选。
