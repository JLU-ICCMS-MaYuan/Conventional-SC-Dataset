# Conventional-SC-Dataset 接口框架说明

- 生成时间：2026-06-08T03:11:26.507562+00:00
- 分析文件数：118
- 后端路由数：68
- 图谱节点/边：290 / 523

## 架构分层

- **后端 API 层**：FastAPI 路由、认证、文献、化合物、管理、Alexandria、HTSC-2025、AI筛选与Tc预测接口。（11 个文件节点）
- **后端领域与数据层**：SQLAlchemy 模型、CRUD、数据库连接、导入导出、DOI/图片/引用等工具。（24 个文件节点）
- **前端交互层**：HTML 模板、CSS 和 JavaScript 页面逻辑，承载周期表、组合页、多数据源浏览和管理页面。（20 个文件节点）
- **运维与计算脚本层**：启动、初始化、导入、备份和Tc预测辅助脚本。（4 个文件节点）
- **文档与论文层**：项目文档、业务说明和 PaperSpine 论文产物。（56 个文件节点）
- **配置与轻量数据层**：Git、环境、依赖、示例数据和小型JSON fixture。（2 个文件节点）

## 接口模块

### `backend/api/admin.py`
- `GET /all-admins` -> `get_all_admins`
- `GET /all-users` -> `get_all_users`
- `POST /approve-user` -> `approve_user`
- `GET /my-reviews` -> `get_my_reviewed_papers`
- `GET /papers/all` -> `get_all_papers`
- `POST /papers/batch-chart-visibility` -> `batch_chart_visibility`
- `POST /papers/batch-delete` -> `batch_delete_papers`
- `POST /papers/batch-review` -> `batch_review_papers`
- `GET /papers/unreviewed` -> `get_unreviewed_papers`
- `DELETE /papers/{paper_id}` -> `delete_paper`
- `GET /papers/{paper_id}` -> `get_paper_detail`
- `PUT /papers/{paper_id}` -> `update_paper`
- `GET /papers/{paper_id}/images` -> `get_paper_images`
- `DELETE /papers/{paper_id}/images/{image_id}` -> `delete_paper_image`
- `POST /papers/{paper_id}/review` -> `review_paper`
- `GET /pending-approvals` -> `get_pending_approvals`
- `DELETE /users/{user_id}` -> `delete_user`
- `PUT /users/{user_id}/permissions` -> `update_user_permissions`
- `GET /users/{user_id}/submitted-papers` -> `get_user_submitted_papers`

### `backend/api/ai_papers.py`
- `GET /compounds/{element_symbols}` -> `get_ai_compound_info`
- `GET /papers/compound/{element_symbols}` -> `get_ai_papers_by_compound`
- `GET /papers/crystal-structures` -> `get_ai_crystal_structures`
- `POST /papers/search-by-mode` -> `search_ai_papers_by_mode`
- `GET /papers/{paper_id}/images/{image_order}` -> `get_ai_paper_image`

### `backend/api/alexandria.py`
- `GET /elements` -> `list_alexandria_elements`
- `GET /material/{mat_id}` -> `get_alexandria_material`
- `GET /material/{mat_id}/cif` -> `get_alexandria_cif`
- `GET /material/{mat_id}/download` -> `download_alexandria_material`
- `POST /search` -> `search_alexandria`
- `GET /stats` -> `alexandria_stats`

### `backend/api/auth_routes.py`
- `POST /login` -> `login`
- `GET /me` -> `get_me`
- `POST /register` -> `register_step1`
- `POST /verify-email` -> `register_step2`

### `backend/api/compounds.py`
- `POST /check` -> `check_compound_exists`
- `POST /search` -> `search_compounds`
- `GET /{element_symbols}` -> `get_compound_info`

### `backend/api/elements.py`
- `GET /` -> `get_all_elements`
- `GET /{symbol}` -> `get_element_by_symbol`

### `backend/api/htsc2025.py`
- `GET /detail/{name}` -> `htsc2025_detail`
- `POST /search` -> `search_htsc2025`
- `GET /stats` -> `htsc2025_stats`

### `backend/api/papers.py`
- `POST /` -> `create_paper`
- `POST /batch-upload` -> `batch_upload_papers`
- `GET /batch-upload-example` -> `get_batch_upload_example`
- `GET /compound/{element_symbols}` -> `get_papers_by_compound`
- `GET /crystal-structures` -> `get_crystal_structures`
- `POST /export` -> `export_papers`
- `GET /images/{image_id}` -> `get_image_by_id`
- `POST /search-by-mode` -> `search_papers_by_mode`
- `GET /stats/chart-data` -> `get_chart_data`
- `GET /stats/user-ranking` -> `get_user_ranking`
- `GET /{paper_id}` -> `get_paper_detail`
- `GET /{paper_id}/images/{image_order}` -> `get_paper_image`

### `backend/api/tc_predict.py`
- `POST /` -> `predict_tc`

### `backend/main.py`
- `GET /` -> `read_root`
- `GET /admin/dashboard` -> `admin_dashboard_page`
- `GET /admin/login` -> `admin_login_page`
- `GET /admin/my-reviews` -> `admin_my_reviews_page`
- `GET /admin/papers` -> `admin_papers_page`
- `GET /admin/register` -> `admin_register_page`
- `GET /admin/superadmin` -> `superadmin_dashboard_page`
- `GET /compound/{element_symbols}` -> `compound_page`
- `GET /health` -> `health_check`
- `GET /login` -> `user_login_page`
- `GET /periodic-table` -> `periodic_table_page`
- `GET /register` -> `user_register_page`
- `GET /tc-pre` -> `tc_prediction_page`

## 合并 origin/master 后的关键结构变化

- 组合页数据源从单一本地文献库扩展为 `local`、`ai`、`alexandria`、`htsc2025` 多模式。
- `backend/api/papers.py` 和 `backend/api/ai_papers.py` 通过 `get_papers_by_compounds_count` 返回分页总数，前端可稳定显示 page/total/has_next。
- `backend/api/alexandria.py` 提供 EPC 材料搜索、详情下载和 CIF 导出；其真实数据依赖 `backend/alexandria_import.py` 生成本地 SQLite。
- `backend/api/htsc2025.py` 读取 `data/htsc2025.json`，为常压高温超导候选提供搜索、统计和详情接口。
- 前端 `frontend/static/js/compound_page.js` 统一承接本地论文、AI筛选论文、Alexandria、HTSC-2025 和测试数据的渲染分支。

## 建议的接口框架边界

- 保持本地文献库和 AI 筛选库的响应模型一致，但在 UI 和论文中明确来源差异。
- Alexandria/HTSC-2025 属于外部或计算数据适配器，不应写入主文献审核流。
- Tc 预测模块保持实验工具边界，输出不直接进入 reviewed paper records。
