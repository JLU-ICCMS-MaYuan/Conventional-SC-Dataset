# 本地材料检索

## 功能说明

从元素组合或化学式定位主业务数据库中的超导材料，并返回关联论文和物性记录。

## 当前行为

- 统一仓储支持 `formula_search`、`elements_exact_search`、`elements_combination_search` 和 `elements_contained_search` 四种模式。
- 化学式检索会执行解析、规范化和相似度排序；元素检索按精确、组合或包含关系匹配材料体系。
- React 元素页生成元素或化学式查询，化合物页调用 `/api/papers/search-by-mode` 展示结果。

## 工作流程

用户选择元素或输入化学式，前端构造搜索模式和参数；论文 API 调用超导体仓储；仓储查询 `ChemicalSystem`、`Superconductor` 等模型；API 再组织论文和超导记录作为结果。

## 约束

- 查询语义依赖当前化学式解析与元素规范化规则。
- 分页和排序已在代码与测试文件中覆盖，但没有本次运行结果或大数据性能结论。
- 当前 React 源码引用缺失的 `frontend/src/lib` 模块，源码构建状态待核验。

## 代码与测试

- 入口：`frontend/src/pages/ElementsPage.tsx`、`frontend/src/pages/CompoundPage.tsx`
- API：`backend/api/papers.py`、`backend/api/compounds.py`
- 仓储：`backend/repositories/superconductors.py`
- 模型：`backend/models.py`
- 测试：`tests/03_data_search_and_database_discovery/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 当前前端与后端的部分请求路径存在一致性风险，部署产物行为需单独核验。
