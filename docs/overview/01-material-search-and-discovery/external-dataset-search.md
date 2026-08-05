# 外部数据集检索

## 功能说明

按元素集合查询 Alexandria 和 HTSC-2025 候选材料，为本地论文与物性数据提供补充发现入口。

## 当前行为

- Go API `POST /api/alexandria/search` 查询 `alexandria_entries` 和元素索引表，支持元素匹配、Tc 范围和空间群编号范围筛选。
- Go API `POST /api/htsc2025/search` 查询 `htsc2025_materials`，支持元素匹配和 Tc 范围筛选。
- `/search` 页面可以在 Local、Alexandria、HTSC-2025、All 四种来源之间切换，并根据数据源裁剪不支持的筛选项。
- Go API `POST /api/papers/search/all` 会聚合本地、Alexandria 和 HTSC-2025 结果，按来源和 Tc 进行分组排序，并在结果中插入 section 行。

## 工作流程

元素集合进入对应 Go API；Go 服务查询 MySQL 中的外部数据表或索引表；API 返回分页候选材料；前端将 Alexandria、HTSC-2025 字段适配为统一结果行。All 来源会先聚合三源结果，再按组展平给前端。

## 约束

- 外部数据表不使用本地论文审核状态，前端以 `External` 或外部来源标识呈现。
- Alexandria 目前要求 `imag = false` 且存在 `tc_max` 或 `tc_allen_dynes`；HTSC-2025 要求 `tc IS NOT NULL`。
- HTSC-2025 请求体包含压强范围字段，但当前 Go 查询未使用压强筛选。
- 文档只说明当前接口行为，不保证外部数据集的完整性、时效性或许可状态。

## 代码与测试

- Alexandria 与 HTSC-2025：`goserver/handlers/external.go`
- 三源聚合：`goserver/handlers/papers.go`
- 页面：`frontend/src/pages/SearchPage.tsx`
- 模型：`goserver/models/models.go`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 外部数据导入和刷新流程未在本次 Overview 扫描中完整核验。
