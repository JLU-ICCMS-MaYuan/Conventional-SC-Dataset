# 安装与运维手册

本文提供一个从零开始部署「超导文献数据库」的完整指南，涵盖环境准备、依赖安装、数据库初始化、运行服务以及远程自动备份配置。

---

## 1. 准备系统环境

必备组件：

| 组件 | 版本 | 说明 |
|------|------|------|
| 操作系统 | Linux / macOS / WSL | 推荐 Ubuntu 22.04+ |
| Python | 3.10+ | 建议使用虚拟环境隔离依赖 |
| pip | 最新 | Python 包管理器 |
| Git | 2.x | 拉取代码 |
| SQLite3 | 3.x | 本地数据库（若系统已有可跳过） |
| Node/浏览器 | 最新 | 仅用于前端调试 |

可选（针对自动备份脚本）：
- `sshpass`：若需要在 Cron 中使用密码方式连接远程服务器，可执行 `sudo apt install sshpass`
- `cron` 或 `systemd`：用于计划任务

Ubuntu/Debian 快速安装命令（示例）：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git sqlite3 sshpass
```

> 若使用 SSH key，则 `sshpass` 可选。

---

## 2. 获取项目代码

```bash
git clone https://your_repo_url/conventional-sc-dataset.git
cd conventional-sc-dataset
```

若需中文镜像，可从 Gitee 或内部仓库克隆。

---

## 3. 创建 Python 虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

---

## 4. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

若安装失败，可升级 pip：

```bash
python -m pip install --upgrade pip
```

---

### step 5和6建议直接运行脚本，运行后可跳过5，6
```bash
# 运行启动脚本
./start.sh
```
## 5. 初始化数据库

首次部署需要创建 SQLite 数据库及基础数据：

```bash
python -m backend.init_db
```

- 数据库文件默认位于 `data/superconductor.db`
- 若需自定义路径，可设置环境变量 `DATABASE_PATH`

---

## 6. 启动开发服务器

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

打开浏览器访问：
- 主页：http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 7. 创建管理员账户（可选）

```bash
python -m backend.create_superadmin
```

按照提示输入邮箱、姓名、密码，即可在 `/admin/login` 登录后台。

---

## 8. 配置远程备份脚本

### 8.1 手动备份

脚本：`scripts/remote_backup.sh`

环境变量 | 说明 | 默认值
---------|------|-------
`BACKUP_REMOTE_HOST` | 远程服务器 IP/域名 | `example.com`
`BACKUP_REMOTE_PORT` | SSH 端口 | `example_port`
`BACKUP_REMOTE_USER` | SSH 用户 | `example_user`
`BACKUP_REMOTE_DIR` | 远程存储目录 | `backups/conventional-sc`
`BACKUP_REMOTE_PASS` | SSH 密码（留空走密钥） | *(空)*
`BACKUP_WORKDIR` | 本地临时目录 | `./backups`
`BACKUP_PREFIX` | 备份前缀，如 `backup_day` | `backup`
`DATABASE_PATH` | SQLite 路径 | `data/superconductor.db`

示例（使用密码）：

```bash
BACKUP_REMOTE_USER=example_user \
BACKUP_REMOTE_PASS=example_psaaword \
BACKUP_REMOTE_HOST=example.com \
BACKUP_REMOTE_DIR=/home/example_user/backups/conventional-sc \
./scripts/remote_backup.sh -b
```

常用子命令：
- `-b`：导出 JSON + 数据库，打包并上传
- `-l`：列出远程备份
- `-r backup_xxx.tar.gz`：下载并覆盖本地数据库

> 如果使用 SSH key，运行 `ssh-copy-id example_user@example.com` 即可取消 `BACKUP_REMOTE_PASS`。

### 8.2 自动备份调度

脚本：`scripts/autobackup.sh`

命令 | 功能 | 默认保留
-----|------|---------
`./scripts/autobackup.sh -m day` | 日备份，文件前缀 `backup_day` | 14 个
`./scripts/autobackup.sh -m week` | 周备份，文件前缀 `backup_week` | 4 个

脚本流程：
1. 调用 `remote_backup.sh -b` 生成备份
2. 根据模式清理远程/本地多余 tar 包

Cron 示例：

```
# 每天 02:30 运行日备份
30 2 * * * cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m day >> logs/autobackup.log 2>&1

# 每周一 03:00 运行周备份
0 3 * * 1 cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m week >> logs/autobackup.log 2>&1
```

> 记得确保 `logs/` 目录存在：`mkdir -p /var/www/conventional-sc-dataset/logs`

---

## 9. 恢复备份

1. 列出远程 tar 包：
   ```
   ./scripts/remote_backup.sh -l
   ```
2. 从远程拉取 tar 包：
   ```bash
   ./scripts/remote_backup.sh -r backup_xxx.tar.gz
   ```
3. 或使用 JSON 导入：
   ```bash
   python -m backend.import_data backups/data_export_20260112_120000.json
   ```

---

## 10. 生产环境建议

- **环境变量**：在 `.env` 或部署平台中设置敏感信息（数据库路径、SMTP 配置、密钥等）
- **进程管理**：使用 systemd、Supervisor 或 Docker 保持服务常驻
- **TLS/反向代理**：Nginx/Traefik 等代理提供 HTTPS
- **日志**：建议将 `uvicorn`、后台脚本输出重定向到日志文件便于排查
- **定期备份**：至少每日一次，结合周备份策略

如需完整部署方案（Railway、Render、VPS、Docker 等），请参考仓库中的 `DEPLOYMENT.md`。

---

完成以上步骤，即可在本地或服务器上稳定运行超导文献数据库，并具备安全的备份恢复能力。若遇到问题，可先检查日志/环境变量，再针对性排查。祝部署顺利!
