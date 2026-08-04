# 外部数据集检索

## 功能说明

按元素集合查询 Alexandria 和 HTSC-2025 候选材料，为本地论文与物性数据提供补充发现入口。

## 当前行为

- Alexandria 模块从 JSON 数据构建内存索引，支持按元素查询、材料详情、统计和 CIF 相关接口。
- HTSC-2025 模块读取独立 JSON 数据，支持分页搜索、材料详情和统计。
- 化合物页分别加载两类外部结果；论文 API 还提供本地、Alexandria、HTSC-2025 三源聚合接口。

## 工作流程

元素集合进入对应 API；数据访问层读取或查询外部数据文件；API 返回分页候选材料；前端与本地论文结果分区展示。三源聚合接口会进一步执行分组和排序。

## 约束

- 外部数据文件不属于主业务数据库，缺失或格式不匹配时相应能力不可用。
- `/api/papers/search/all` 已注册，但当前 React 页面未发现直接调用。
- 文档只说明本地接口行为，不保证外部数据集的完整性、时效性或许可状态。

## 代码与测试

- Alexandria：`backend/api/alexandria.py`、`backend/alexandria_db.py`
- HTSC-2025：`backend/api/htsc2025.py`
- 聚合：`backend/api/papers.py`
- 页面：`frontend/src/pages/CompoundPage.tsx`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 外部数据文件的部署位置和更新流程待核验。
