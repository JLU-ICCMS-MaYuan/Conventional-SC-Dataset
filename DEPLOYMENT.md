# 超导文献数据库 - 部署指南

## 📌 重要提醒

**GitHub Pages 和 Gitee Pages 不适用于本项目！**

原因：
- GitHub/Gitee Pages 只能托管纯静态网站（HTML/CSS/JS）
- 本项目是动态 Web 应用，需要：
  - Python 后端服务器（FastAPI）
  - 数据库（SQLite）
  - 服务器端文件处理

---

## 🎯 推荐部署方案

### 方案一：Railway 云平台（⭐ 最推荐）

**适合人群：** 无服务器运维经验，想快速上线

**优点：**
- ✅ 完全免费（每月 500 小时运行时间 + 5GB 流量）
- ✅ 5分钟内完成部署
- ✅ 自动提供 HTTPS 域名
- ✅ 可绑定自定义域名
- ✅ 自动从 Git 仓库部署

**缺点：**
- ⚠️ 免费版有流量限制
- ⚠️ 需要配置持久化存储（否则重启数据会丢失）

#### 部署步骤：

**1. 准备工作**
```bash
# 确保所有代码已提交到 Git
git add .
git commit -m "准备部署到 Railway"
git push
```

**2. 注册 Railway**
- 访问：https://railway.app/
- 使用 GitHub 账号登录

**3. 创建新项目**
- 点击 "New Project"
- 选择 "Deploy from GitHub repo"
- 授权 Railway 访问你的 GitHub 仓库
- 选择 `conventional-sc-dataset` 仓库

**4. 配置环境变量（可选）**
- 在 Railway 项目设置中添加：
  - `DATABASE_PATH=/app/data/superconductor.db`（如果需要自定义数据库路径）

**5. 配置持久化存储（重要！）**
- 在 Railway 项目中，点击 "Variables" → "Add Volume"
- 挂载路径：`/app/data`
- 这样数据库文件就不会在重启时丢失

**6. 部署完成**
- Railway 会自动检测 `railway.json` 配置
- 自动安装依赖（requirements.txt）
- 自动初始化数据库
- 自动启动服务

**7. 访问网站**
- 部署成功后，Railway 会提供一个域名，类似：
  - `https://conventional-sc-dataset.railway.app`

**8. 绑定自定义域名（可选）**
- 在 Railway 项目设置中点击 "Settings" → "Domains"
- 添加你的域名（如 `superconductor.example.com`）
- 按照提示在域名注册商处添加 CNAME 记录

---

### 方案二：Render 云平台（备选方案）

**适合人群：** Railway 受限时的替代方案

**优点：**
- ✅ 免费版更稳定
- ✅ 操作类似 Railway
- ✅ 自带数据库持久化

**缺点：**
- ⚠️ 免费版有 15 分钟无活动后自动休眠（首次访问需等待启动）

#### 部署步骤：

**1. 注册 Render**
- 访问：https://render.com/
- 使用 GitHub 账号登录

**2. 创建 Web Service**
- 点击 "New +" → "Web Service"
- 连接你的 GitHub 仓库
- 选择 `conventional-sc-dataset`

**3. 配置设置**
```
Name: superconductor-database
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python -m backend.init_db && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**4. 添加持久化磁盘**
- 在 "Environment" 中添加 "Disk"
- 名称：`data`
- 挂载路径：`/opt/render/project/src/data`
- 大小：1GB（免费）

**5. 部署**
- 点击 "Create Web Service"
- 等待部署完成（约 3-5 分钟）

**6. 访问网站**
- Render 会提供一个免费域名，类似：
  - `https://superconductor-database.onrender.com`

---

### 方案三：VPS 服务器部署（适合长期运营）

**适合人群：** 有一定 Linux 基础，需要完全控制

**推荐服务商：**
- 阿里云（国内，需备案）
- 腾讯云（国内，需备案）
- Vultr（国外，无需备案，最低 $5/月）
- DigitalOcean（国外，无需备案，$4/月）

**优点：**
- ✅ 完全控制服务器
- ✅ 无流量限制
- ✅ 性能稳定
- ✅ 可运行多个项目

**缺点：**
- ⚠️ 需要付费（最低约 20-30 元/月）
- ⚠️ 需要自己配置 nginx、SSL 证书等
- ⚠️ 需要维护服务器安全

#### 部署步骤（Ubuntu 22.04 示例）：

**1. 购买并连接 VPS**
```bash
# 通过 SSH 连接服务器
ssh root@你的服务器IP
```

**2. 安装依赖**
```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 3.11
apt install -y python3.11 python3.11-venv python3-pip git nginx

# 安装 certbot（用于免费 SSL 证书）
apt install -y certbot python3-certbot-nginx
```

**3. 克隆项目**
```bash
# 创建项目目录
mkdir -p /var/www
cd /var/www

# 克隆代码（替换为你的仓库地址）
git clone https://gitee.com/你的用户名/conventional-sc-dataset.git
cd conventional-sc-dataset

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python -m backend.init_db
```

**4. 配置 systemd 服务**
```bash
# 创建服务文件
nano /etc/systemd/system/superconductor.service
```

写入以下内容：
```ini
[Unit]
Description=Superconductor Literature Database
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/conventional-sc-dataset
Environment="PATH=/var/www/conventional-sc-dataset/venv/bin"
ExecStart=/var/www/conventional-sc-dataset/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
systemctl daemon-reload
systemctl start superconductor
systemctl enable superconductor
systemctl status superconductor
```

**5. 配置 Nginx 反向代理**
```bash
# 创建 Nginx 配置
nano /etc/nginx/sites-available/superconductor
```

写入：
```nginx
server {
    listen 80;
    server_name 你的域名.com;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用站点：
```bash
ln -s /etc/nginx/sites-available/superconductor /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

**6. 配置 SSL 证书（免费 HTTPS）**
```bash
certbot --nginx -d 你的域名.com
```

**7. 配置域名解析**
- 在你的域名注册商（如阿里云、Cloudflare）添加 A 记录：
  - 记录类型：A
  - 主机记录：@ 或 www
  - 记录值：你的服务器 IP

**8. 完成！**
- 访问 `https://你的域名.com`

---

### 方案四：Docker 部署（适合开发者）

**适合人群：** 熟悉 Docker，希望环境一致性

创建 `Dockerfile`：
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 初始化数据库
RUN python -m backend.init_db

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

创建 `docker-compose.yml`：
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

运行：
```bash
docker-compose up -d
```

---

## 🎯 我的推荐

**如果你是第一次部署 Web 应用：**
→ 选择 **Railway**，5 分钟搞定，免费够用

**如果你需要稳定运营、有少量预算：**
→ 选择 **VPS**（Vultr/DigitalOcean），完全控制

**如果你只是测试功能：**
→ 选择 **Render**，免费但有休眠限制

---

## ⚠️ 部署后注意事项

1. **数据备份**
   - 定期备份 `data/superconductor.db` 数据库文件
   - Railway/Render 需要配置持久化存储

2. **安全性**
   - VPS 部署记得配置防火墙
   - 定期更新系统和依赖

3. **监控**
   - Railway/Render 自带监控面板
   - VPS 可以用 Uptime Robot 监控网站状态

4. **域名绑定**
   - 所有方案都支持自定义域名
   - 需要在域名注册商处添加 DNS 记录

---

## 💰 成本对比

| 方案 | 月费用 | 流量限制 | 适合场景 |
|------|--------|----------|----------|
| Railway | 免费 | 5GB/月 | 小型项目、测试 |
| Render | 免费 | 无限制（有休眠） | 个人项目 |
| VPS | 20-50元 | 1TB+ | 长期运营 |

---

## 🤔 常见问题

**Q: 免费方案够用吗？**
A: 如果是学术用途、小范围使用，Railway/Render 免费版完全够用

**Q: 数据会丢失吗？**
A: 配置了持久化存储就不会，记得按照文档配置 Volume

**Q: 可以绑定自己的域名吗？**
A: 可以！所有方案都支持，在平台设置中添加即可

**Q: 国内访问速度如何？**
A: Railway/Render 服务器在国外，国内访问稍慢但可接受。如需快速访问，建议用国内 VPS

**Q: 需要备案吗？**
A: Railway/Render 不需要。国内 VPS（阿里云/腾讯云）如果绑定域名需要备案

---

## 📞 需要帮助？

如果部署遇到问题，请提供：
1. 选择的部署方案
2. 错误日志截图
3. 具体报错信息
