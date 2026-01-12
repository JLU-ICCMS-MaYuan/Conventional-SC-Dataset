# 超导文献数据库

基于元素周期表的超导文献收集与检索平台，支持文献上传、审核、图表展示以及远程备份。

## 核心功能
- 周期表选元素，跳转元素组合文献页
- 文献上传（DOI 解析、截图、物理参数录入）
- 管理员/超级管理员审核与审批
- Tc/压强图表、组合筛选、引用导出（APS/BibTeX/RIS）
- 远程备份脚本，支持日/周自动保留策略

## 快速上手
> 更完整的环境与备份指南见 [INSTALL.md](INSTALL.md)。

1) 克隆项目并进入目录  
   `git clone https://example.com/your_repo/conventional-sc-dataset.git && cd conventional-sc-dataset`
2) 创建虚拟环境并安装依赖  
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   sudo apt update
   sudo apt install -y python3 python3-venv python3-pip git sqlite3 sshpass
   ```
3) 初始化数据库  
   `python -m backend.init_db`
4) 启动开发服务器  
   `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`
5) 访问  
   - 主页：http://localhost:8000  
   - API 文档：http://localhost:8000/docs

可选：创建超级管理员  
`python -m backend.create_superadmin`

## 管理后台
- 登录：`/admin/login`
- 注册：`/admin/register`（待超级管理员审批）
- 审核面板：`/admin/dashboard`
- 超级管理员审批：`/admin/superadmin`

详见 [ADMIN_SYSTEM.md](ADMIN_SYSTEM.md)。

## 备份与恢复
- 手动/自动远程备份：`scripts/remote_backup.sh`、`scripts/autobackup.sh`
- 日备份保留 14 个，周备份保留 4 个（可配合 Cron）
- 完整迁移、Schema 升级与恢复说明见 [INSTALL.md](INSTALL.md)

## 环境变量要点
- `DATABASE_PATH`：自定义数据库路径（如挂载卷）
- `JWT_SECRET_KEY`：生产环境必填，32+ 随机字符
- SMTP 相关：`SMTP_SERVER/PORT/USERNAME/PASSWORD/SENDER`（用于邮箱验证）

## 目录结构（节选）
```
backend/         # FastAPI 后端
frontend/        # 模板与静态资源
scripts/         # 备份与自动备份脚本
data/            # 默认 SQLite 数据库目录
```

## 其他
- 建议使用 SSH key 而非明文密码运行备份脚本。***
