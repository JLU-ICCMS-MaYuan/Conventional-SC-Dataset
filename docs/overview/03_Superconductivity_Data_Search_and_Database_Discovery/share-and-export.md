# 分享与导出

## 功能说明

将检索结果、外部结构文件或图表组合转换为便于分享、下载或继续分析的结构化格式。

## 当前行为

- `/search` 页面存在“导出 RIS”的按钮文案，但当前代码只触发前端提示，未发现已注册的 RIS 导出后端接口。
- Alexandria 详情组件提供 CIF 和完整数据下载按钮，但当前 Go 路由只注册 `/api/alexandria/search`，下载端点是否由 Python 反代提供需核验。
- HTSC 详情组件可在前端从详情数据中的 CIF 文本生成本地下载。
- `/share` 页面可对已选图表组合触发 JSON 导出，但前端调用的 `/api/chart-groups/:id/export` 当前未在 Go 路由注册。
- 离线全量数据导出由 `backend/scripts/export_data.py` 生成 JSON 载荷，不属于前端交互导出。

## 工作流程

前端导出入口会根据数据类型走不同路径：HTSC CIF 可由浏览器本地拼接下载；图表组合导出尝试请求后端；离线全量导出由命令行脚本读取数据库并写出 JSON。RIS 导出和部分外部数据下载当前只确认有前端入口，后端契约待核验。

## 约束

- 导出内容受数据库现有元数据完整度限制。
- 前端存在的导出按钮不等同于后端接口已闭环。
- `/share` 当前主要是图表社区页面，论文上传已迁移到 `/upload`。

## 代码与测试

- `frontend/src/pages/SearchPage.tsx`
- `frontend/src/pages/share.tsx`
- `frontend/src/components/AlexandriaDetail.tsx`
- `frontend/src/components/HtscDetail.tsx`
- `backend/scripts/export_data.py`
- `tests/03_data_search_and_database_discovery/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- RIS 导出、Alexandria 下载和图表组合后端导出接口需要继续联调核验。
