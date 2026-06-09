# 安装与部署

## 1. 目标

本文档描述如何让当前项目在本地或服务器上运行，重点覆盖 Python 依赖、数据目录、环境变量、启动方式和服务管理。

## 2. 运行前提

- Python 3.10+ 环境
- 已安装 `requirements.txt` 中依赖
- 可连接的 MySQL 数据库
- 能设置 JWT 与邮件相关环境变量

## 3. 本地开发启动

### 3.1 安装依赖
```bash
pip install -r requirements.txt
```

### 3.2 创建表结构
```bash
python -m alembic upgrade head
```

### 3.3 初始化基础元素数据
```bash
python -m backend.init_db
```

### 3.4 启动方式

#### 使用启动脚本
```bash
./start.sh
```

#### 直接使用 uvicorn
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

如果是本地开发，希望修改 Python 代码后自动重启，可使用：

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

注意：`--reload` 只适合开发，不适合生产。

## 4. 数据库

当前系统默认使用 MySQL。表结构由 Alembic 管理，`backend.init_db` 只负责初始化 `periodic_table_elements` 基础元素数据。

部署时需要保证：

- MySQL 服务可访问
- 数据库和账号已创建
- 字符集建议使用 `utf8mb4`
- `DATABASE_URL` 指向目标库

## 5. 关键环境变量

### 5.1 JWT
```bash
JWT_SECRET_KEY=your_long_random_secret
```

### 5.2 邮件服务
```bash
SMTP_SERVER=smtp.example.com
SMTP_PORT=465
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_password
SMTP_SENDER_EMAIL=your_email@example.com
```

### 5.3 端口
```bash
PORT=8000
```

### 5.4 数据库
```bash
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4
```

## 6. 生产部署建议

### 6.1 应用启动
- 推荐使用 `gunicorn + uvicorn worker` 或 systemd 管理服务
- 反向代理可使用 Nginx 或现有面板方案

### 6.2 systemd 示例
```ini
[Unit]
Description=Conventional-SC-Dataset
After=network.target

[Service]
WorkingDirectory=/var/www/Conventional-SC-Dataset
Environment="JWT_SECRET_KEY=your_long_random_secret"
Environment="PORT=8000"
ExecStart=/path/to/python -m gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 6.3 反向代理
- 将外部域名流量代理到应用监听端口
- 生产环境应启用 HTTPS

## 7. 部署后的初始化动作

### 7.1 初始化数据库
```bash
python -m alembic upgrade head
python -m backend.init_db
```

`backend.init_db` 不再执行 `create_all` 或 `ALTER TABLE`。

### 7.2 创建超级管理员
```bash
python -m backend.create_superadmin
```

### 7.3 验证页面
- `/`
- `/login`
- `/admin/login`
- `/tc-pre`
- `/docs` 或健康检查接口如 `/health`

## 8. 部署注意事项

- 修改后端 Python 代码后，如果服务未启用自动重载，必须重启服务
- 邮件、JWT、数据目录权限是最常见的部署问题来源
- `start.sh` 更适合单机直接启动，不等于完整生产部署方案
