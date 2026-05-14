# Conventional-SC-Dataset 文档导航

本目录用于描述当前代码已经落地的业务逻辑、角色分工、系统入口和运维方式。宗旨是：以当前代码真实行为为准，帮助开发者快速定位功能边界。

## 业务逻辑分类

当前系统可归纳为 **8 个业务模块 + 1 个运维支撑模块**：

1. 元素周期表选择与组合检索
2. 元素组合页与文献浏览
3. 文献上传与物理数据录入
4. 批量导入与数据处理
5. 用户认证与邮箱验证
6. 管理员/超级管理员审批与审核
7. 首页图表与统计展示
8. Tc 预测实验模块
9. 运维支撑模块

## 文档结构

- [business-overview.md](/home/mayuan/code/Conventional-SC-Dataset/docs/business-overview.md)：业务总览、角色分工、模块关系、页面与接口入口
- [current-state-and-gaps.md](/home/mayuan/code/Conventional-SC-Dataset/docs/current-state-and-gaps.md)：系统现状、已实现能力、未实现能力、数据库承接差距
- [business-search-and-discovery.md](/home/mayuan/code/Conventional-SC-Dataset/docs/business-search-and-discovery.md)：元素选择、组合模式、组合页浏览、筛选、导出
- [business-paper-ingestion.md](/home/mayuan/code/Conventional-SC-Dataset/docs/business-paper-ingestion.md)：单篇上传、批量上传、物理参数、截图、导入导出
- [business-auth-and-review.md](/home/mayuan/code/Conventional-SC-Dataset/docs/business-auth-and-review.md)：注册登录、邮箱验证、管理员审批、文献审核、全局管理
- [business-visualization-and-tc-predict.md](/home/mayuan/code/Conventional-SC-Dataset/docs/business-visualization-and-tc-predict.md)：首页图表、贡献者排行、Tc 预测实验模块
- [operations-installation-and-deployment.md](/home/mayuan/code/Conventional-SC-Dataset/docs/operations-installation-and-deployment.md)：安装、部署、环境变量、启动方式
- [operations-cli-and-maintenance.md](/home/mayuan/code/Conventional-SC-Dataset/docs/operations-cli-and-maintenance.md)：初始化、导入导出、迁移、管理员创建、备份、服务维护

## 快速定位

- 如果你要快速判断某个产品设想是否已经落地，先看 `current-state-and-gaps.md`
- 如果你要理解用户如何从首页进入某个化合物体系，先看 `business-search-and-discovery.md`
- 如果你要理解文献如何进入数据库，先看 `business-paper-ingestion.md`
- 如果你要理解管理员体系和审核流，先看 `business-auth-and-review.md`
- 如果你要理解首页图表和实验预测页，先看 `business-visualization-and-tc-predict.md`
- 如果你要理解部署、迁移、备份和命令，先看 `operations-*` 文档

## 当前代码主入口

- 首页：`/`
- 元素组合页：`/compound/{element_symbols}`
- 登录页：`/login`
- 管理员注册页：`/admin/register`
- 管理员审核面板：`/admin/dashboard`
- 超级管理员面板：`/admin/superadmin`
- 全局文献管理页：`/admin/papers`
- Tc 预测实验页：`/tc-pre`

## 文档维护原则

- 优先描述当前已实现逻辑，不把规划功能写成现状
- 功能说明必须关联页面、前端脚本、后端接口或命令
- 跨模块改动应同步更新总览文档
