# Conventional-SC-Dataset 协作规范

## 1. 仓库业务逻辑大纲

### 1.1 元素周期表选择与组合检索
- 目标：让用户通过元素周期表进入超导体系检索流程。
- 主要入口：`/`、`frontend/static/js/periodic_table.js`、`/api/compounds/search`
- 核心约束：检索模式仅支持 `only`、`combination`、`contains` 三种；元素组合在后端会做排序与标准化。

### 1.2 元素组合页与文献浏览
- 目标：展示某一元素体系或相关体系的文献列表，并支持二次筛选。
- 主要入口：`/compound/{element_symbols}`、`frontend/static/js/compound_page.js`、`/api/papers/compound/{element_symbols}`、`/api/papers/by-elements`
- 核心约束：列表页支持审核状态、关键词、年份、分页；不同筛选模式会决定组合范围与展示方式。

### 1.3 文献上传与物理数据录入
- 目标：让注册用户向指定体系提交新文献及其物理参数。
- 主要入口：组合页上传弹窗、`/api/papers/`
- 核心约束：必须登录；依赖 DOI 解析；支持多组物理数据与最多 5 张截图；单体系内 DOI 不能重复。

### 1.4 批量导入与数据处理
- 目标：支持通过表格或 JSON 将历史数据批量导入数据库。
- 主要入口：首页快速上传、`/api/papers/batch-upload`、`backend/import_data.py`、`backend/export_data.py`
- 核心约束：批量上传只接受约定格式文件；导入过程中会创建元素组合、文献、物理数据，并做元素标准化。

### 1.5 用户认证与邮箱验证
- 目标：支持普通用户注册登录，以及管理员申请流程。
- 主要入口：`/login`、`/register`、`/admin/register`、`/api/auth/*`
- 核心约束：注册采用邮箱验证码两步流程；管理员账号必须经超级管理员审批后方可登录后台。

### 1.6 管理员/超级管理员审批与审核
- 目标：控制管理员权限流转，并对文献进行审核与全局管理。
- 主要入口：`/admin/dashboard`、`/admin/superadmin`、`/admin/papers`、`/api/admin/*`
- 核心约束：超级管理员负责管理员审批与权限变更；管理员负责文献审核、编辑、图表显示控制。

### 1.7 首页图表与统计展示
- 目标：在首页展示超导研究趋势、数据库分布和贡献者排行。
- 主要入口：`/`、`frontend/static/js/chart.js`、`/api/papers/stats/*`
- 核心约束：动态图表依赖数据库数据；图表展示与 `show_in_chart` 状态相关。

### 1.8 Tc 预测实验模块
- 目标：提供独立的结构文件与 PDOS 文件上传预测实验。
- 主要入口：`/tc-pre`、`frontend/static/js/tc_pre.js`、`/api/tc-predict/`
- 核心约束：不写入数据库；必须包含 H 相关结构与 `PDOS_H` 文件；当前属于实验功能。

### 1.9 运维支撑模块
- 目标：保障数据库初始化、导入导出、迁移、部署、备份与服务运行。
- 主要入口：`start.sh`、`backend/init_db.py`、`backend/create_superadmin.py`、`backend/migrate_ids.py`、`scripts/*.sh`
- 核心约束：部署依赖环境变量、SQLite 数据目录和服务管理方式；运维脚本默认面向当前仓库结构。

## 2. 文档使用要求
- 修改业务逻辑前，先阅读 `docs/README.md` 和对应专题文档。
- 新增业务能力时，必须同步补充 `docs/` 中对应模块文档。
- 如果变更跨多个模块，先更新 `docs/business-overview.md` 中的模块关系，再更新专题文档。

## 3. 提交修改规范
- 未理解业务模块边界前，不要直接修改代码或文档。
- 每次提交都必须写清楚时间、修改目的、修改内容。
- 时间统一使用 `YYYY-MM-DD HH:mm:ss` 格式。
- 提交说明必须可读，不能只写“update”“fix”“modify”等模糊词。
- Git 提交说明必须使用中文书写。

### 3.1 提交说明模板
```text
[时间] 2026-04-15 14:30:00
[修改目的] 修正文献列表接口在可空物理参数下的响应校验问题
[修改内容] 将 PaperData 的 pressure/tc 响应字段改为可空；补充相关文档说明
[影响范围] 文献列表接口、组合页加载流程、接口文档
[验证方式] 本地调用 /api/papers/compound/La-H 返回 200，前端页面可正常加载
```

### 3.2 文档修改要求
- 文档应优先描述“当前代码真实行为”，不要把规划功能写成已实现功能。
- 页面、API、脚本、命令之间的映射关系必须清楚。
- 对未落地能力必须显式标注“规划中”或“未实现”。
