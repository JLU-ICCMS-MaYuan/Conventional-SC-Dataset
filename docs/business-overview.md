# 业务总览

## 1. 系统定位

Conventional-SC-Dataset 是一个围绕“元素体系 - 超导文献 - 物理参数 - 审核管理”组织的数据库型网站。核心目标不是做全文文献平台，而是让用户围绕特定元素组合快速查到超导体系文献、上传数据、审核数据并在首页图表中呈现结构化结果。

## 2. 角色分工

### 2.1 匿名访客
- 可以浏览首页、元素体系页、图表和公开文献
- 不能上传文献
- 不能进入后台管理页面

### 2.2 普通注册用户
- 可以注册、邮箱验证、登录
- 可以在元素组合页上传文献
- 可以使用首页快速批量上传入口
- 不能审核文献、不能审批管理员

### 2.3 管理员
- 具备普通用户能力
- 可以审核文献、修改文献、查看全局文献列表
- 可以控制文献是否进入首页动态图表

### 2.4 超级管理员
- 具备管理员能力
- 可以审批管理员申请
- 可以修改用户权限、查看管理员与用户信息

## 3. 业务模块与依赖关系

### 3.1 元素选择与检索模块
- 负责从首页进入具体体系
- 是文献浏览和上传的前置入口

### 3.2 文献浏览模块
- 负责列表页展示、筛选、分页、导出
- 依赖元素组合检索结果

### 3.3 文献采集模块
- 负责 DOI 解析、物理参数录入、截图上传、批量导入
- 依赖认证模块和元素组合模块

### 3.4 认证与审核模块
- 负责用户注册登录、管理员审批、文献审核
- 决定文献是否被视为可信内容

### 3.5 图表与预测模块
- 首页图表依赖数据库中已有文献和图表显示标记
- Tc 预测模块是独立实验能力，不依赖数据库持久化

### 3.6 运维支撑模块
- 负责初始化、导入导出、迁移、部署、备份
- 为其他所有模块提供环境和数据基础

## 4. 页面与前端脚本映射

| 页面 | 模板 | 前端脚本 | 主要职责 |
|---|---|---|---|
| `/` | `frontend/templates/index.html` | `periodic_table.js`、`chart.js`、认证脚本 | 元素选择、快速上传、首页图表 |
| `/compound/{element_symbols}` | `frontend/templates/compound.html` | `compound_page.js` | 文献浏览、筛选、上传、导出 |
| `/login` | `frontend/templates/login.html` | 认证脚本 | 登录 |
| `/admin/register` | `frontend/templates/admin_register.html` | 认证脚本 | 管理员注册 |
| `/admin/dashboard` | `frontend/templates/admin_dashboard.html` | 管理后台脚本 | 文献审核 |
| `/admin/superadmin` | `frontend/templates/superadmin_dashboard.html` | 管理后台脚本 | 管理员审批与权限管理 |
| `/admin/papers` | `frontend/templates/admin_papers.html` | `admin_papers.js` | 全局文献管理 |
| `/tc-pre` | `frontend/templates/tc_pre.html` | `tc_pre.js` | 实验预测 |

## 5. API 分层

### 5.1 元素与组合
- `/api/elements/*`
- `/api/compounds/*`

### 5.2 文献
- `/api/papers/*`

### 5.3 认证
- `/api/auth/*`

### 5.4 管理后台
- `/api/admin/*`

### 5.5 实验预测
- `/api/tc-predict/*`

## 6. 当前系统的边界

- 当前主数据源是 SQLite 数据库，不是外部搜索引擎
- 文献元数据依赖 DOI 解析接口，上传时并非全部字段都由用户手填
- Tc 预测模块不写库、不审核、不参与首页文献图表闭环
- 规划中的互动评论、弹幕、点击图表跳转等功能当前代码未落地

## 7. 功能完成度与数据库承接评估

如果你要判断“某个功能是否已经落地”，或者想确认“数据库现在到底承接到了哪一步”，请继续阅读：

- [当前功能现状与数据库承接差距](/home/mayuan/code/Conventional-SC-Dataset/docs/current-state-and-gaps.md)

本页只负责描述系统模块与边界，不展开写“已实现 / 未实现 / 部分实现”的完整对照。
