# 分享与导出

## 功能说明

将论文和超导物性查询结果转换为便于分享或文献管理的结构化格式。

## 当前行为

- 论文 API 支持 JSON 和 RIS 等导出形式。
- 导出包含论文元数据及可用的关联超导记录。
- 测试文件覆盖 JSON/RIS 格式和搜索结果分享路径。

## 工作流程

客户端提交材料或论文选择；API 查询对应论文与记录；导出逻辑按目标格式序列化；客户端接收文本或 JSON 响应。

## 约束

- 导出内容受数据库现有元数据完整度限制。
- `SharePage` 当前主要调用 RAG PDF 上传，“分享”页面名称与导出能力并不完全对应。

## 代码与测试

- `backend/api/papers.py`
- `frontend/src/pages/SharePage.tsx`
- `tests/03_data_search_and_database_discovery/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 前端分享页面的最终产品边界待核验。
