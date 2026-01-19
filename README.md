# 超导文献数据库

基于元素周期表的超导文献收集与检索平台，支持文献上传、审核、图表展示以及远程备份。

## 核心功能
- 周期表选元素，跳转元素组合文献页
- 文献上传（DOI 解析、截图、物理参数录入）
- 管理员/超级管理员审核与审批
- Tc/压强图表、组合筛选、引用导出（APS/BibTeX/RIS）
- 远程备份脚本，支持日/周自动保留策略



可选：创建超级管理员  
`python -m backend.create_superadmin`

## 管理后台
- 登录：`/admin/login`
- 注册：`/admin/register`（待超级管理员审批）
- 审核面板：`/admin/dashboard`
- 超级管理员审批：`/admin/superadmin`

详见 [ADMIN_SYSTEM.md](ADMIN_SYSTEM.md)。

