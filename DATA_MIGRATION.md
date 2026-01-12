# 数据迁移与备份手册

本文整合了超导文献数据库在不同环境之间迁移、备份、恢复的完整流程。无论你是在本地开发、VPS、Railway/Render 还是其他云平台，都可以按需选择最合适的方案。

---

## 1. 准备工作

在迁移或备份前，请先确认以下事项：

1. **数据库路径**  
   默认 `data/superconductor.db`，若使用持久化卷或自定义路径，需设置 `DATABASE_PATH` 环境变量。

2. **脚本依赖**  
   - Python ≥ 3.10，已执行 `pip install -r requirements.txt`
   - 若需要 SSH 密码方式上传，请安装 `sshpass`（`sudo apt install sshpass`）
   - 确保 `scripts/remote_backup.sh`、`scripts/autobackup.sh` 具备执行权限（`chmod +x`）

3. **敏感信息管理**  
   建议使用 `.env` 或系统环境变量保存 SSH/SMTP 等敏感配置，避免写入仓库。

---

## 2. 迁移方案速览

| 方案 | 描述 | 难度 | 速度 | 适用场景 |
|------|------|------|------|----------|
| A. 复制 `superconductor.db` | 直接拷贝 SQLite 文件 | ⭐ | ⭐⭐⭐ | VPS、本地测试、数据量小 |
| B. JSON 导出/导入 | `export_data` + `import_data` | ⭐⭐ | ⭐⭐ | 所有环境，安全可控 |
| C. 持久化卷/磁盘 | 容器卷或 VPS 路径持久化 | ⭐⭐ | ⭐⭐⭐ | Railway / Render / Docker |

---

## 3. 方案 A：复制数据库文件

1. **备份现有数据库**
   ```bash
   cp data/superconductor.db data/superconductor_backup_$(date +%Y%m%d).db
   ```

2. **上传到服务器**
   ```bash
   scp data/superconductor.db user@server:/var/www/conventional-sc-dataset/data/
   ```

3. **重启服务（示例）**
   ```bash
   ssh user@server
   systemctl restart superconductor
   ```

优点是简单快速；缺点是平台差异（Windows→Linux）可能导致路径/权限问题。

---

## 4. 方案 B：JSON 导出/导入（推荐）

### 导出

```bash
python -m backend.export_data data/data_export.json
```

脚本会打印包括元素数、文献数、截图数在内的统计信息，便于后续校验。

### 导入

1. 上传 `data_export.json` 到目标环境（scp、Railway CLI 等方式均可）。
2. 在目标环境执行：
   ```bash
   python -m backend.import_data          # 追加导入
   python -m backend.import_data --clear  # （可选）清空再导入
   ```
3. 访问 http://服务器:端口 检查文献数量与截图是否正确。

**优势**：跨平台、安全、可版本管理；支持选择性导入（可在 `export_data.py` 中加入过滤条件）。

---

## 5. 方案 C：持久化存储

### Railway
1. 在服务 “Variables” 面板添加卷，路径 `~ /app/data`
2. 通过 CLI 上传数据库或 JSON，再执行 `import_data`

### Render
1. 在 “Disks” 设置中新增磁盘，挂载到 `/opt/render/project/src/data`
2. 发布后在容器中执行导入脚本

### Docker
在 `docker run` / `docker-compose` 中将宿主机的 `./data` 映射到容器 `/app/data`，即可实现持久化。

---

## 6. Schema 升级（必须执行）

新版前端和 API 依赖两项变更：
- `compounds.element_list` JSON 列
- 统一的超导体类型（铜基、铁基、镍基、高压氢化物、碳基、有机、其他超导）

执行以下命令（幂等，可重复）：

```bash
export DATABASE_PATH=/path/to/superconductor.db  # 如在容器中请指向挂载卷
python -m backend.migrations.schema_202502
```

完成后可用 SQLite 检查：
```bash
sqlite3 $DATABASE_PATH "SELECT element_symbols, element_list FROM compounds LIMIT 5;"
sqlite3 $DATABASE_PATH "SELECT DISTINCT superconductor_type FROM papers;"
```

---

## 7. 远程备份与恢复

### 7.1 `scripts/remote_backup.sh`

功能：
- `-b`：导出 JSON + DB，打包并上传到远程服务器
- `-l`：列出远程备份
- `-r backup_xxx.tar.gz`：下载备份并覆盖本地数据库

关键环境变量（均可在执行前覆盖）：

| 变量 | 含义 | 默认 |
|------|------|------|
| `BACKUP_REMOTE_HOST` | 远程 IP/域名 | 222.27.82.115 |
| `BACKUP_REMOTE_PORT` | SSH 端口 | 22 |
| `BACKUP_REMOTE_USER` | SSH 用户 | 123 |
| `BACKUP_REMOTE_DIR`  | 远程目录 | backups/conventional-sc |
| `BACKUP_REMOTE_PASS` | SSH 密码（留空走密钥） | 空 |
| `BACKUP_PREFIX`      | 文件前缀（如 `backup_day`） | backup |
| `BACKUP_WORKDIR`     | 本地临时目录 | ./backups |
| `DATABASE_PATH`      | SQLite 文件 | data/superconductor.db |

示例：

```bash
BACKUP_REMOTE_USER=123 BACKUP_REMOTE_PASS=456 \
BACKUP_REMOTE_HOST=222.27.82.115 BACKUP_REMOTE_DIR=/home/123/backups \
./scripts/remote_backup.sh -b
```

> 强烈建议改用 SSH key（`ssh-keygen` + `ssh-copy-id`），避免在 Cron 中保存明文密码。

### 7.2 自动备份 `scripts/autobackup.sh`

| 命令 | 说明 | 默认保留 |
|------|------|----------|
| `./scripts/autobackup.sh -m day`  | 日备份，生成 `backup_day_*.tar.gz` | 14 个 |
| `./scripts/autobackup.sh -m week` | 周备份，生成 `backup_week_*.tar.gz` | 4 个 |

脚本流程：
1. 调用 `remote_backup.sh -b`
2. 远程、 本地同步删除超出配额的历史文件

Cron 示例：
```
30 2 * * * cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m day >> logs/autobackup.log 2>&1
0 3 * * 1 cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m week >> logs/autobackup.log 2>&1
```

> 运行前请创建 `logs/` 目录：`mkdir -p /var/www/conventional-sc-dataset/logs`

### 7.3 恢复流程

1. 从远程下载压缩包：
   ```bash
   scp 123@222.27.82.115:/home/123/backups/backup_day_20260112_120000.tar.gz backups/
   ```
2. 解压并覆盖数据库：
   ```bash
   tar -xzf backups/backup_day_20260112_120000.tar.gz -C backups/
   cp backups/superconductor_20260112_120000.db data/superconductor.db
   ```
3. 如需导入 JSON，执行：
   ```bash
   python -m backend.import_data backups/data_export_20260112_120000.json
   ```
4. 重启服务并验证页面数据。

---

## 8. 迁移/备份检查清单

- [ ] 执行 `export_data`/`remote_backup` 成功
- [ ] JSON / tar 文件未损坏，可打开或 `tar -tzf` 查看
- [ ] 目标环境导入成功，无报错
- [ ] 运行 schema 升级脚本
- [ ] 首页、文献详情、图表可正常访问
- [ ] 文献数量、截图数量与备份时一致
- [ ] 搜索/审核等关键功能可用
- [ ] 已配置定期备份（Cron 或其他方案）

---

## 9. 常见问题

**Q1: 导出的 JSON 太大？**  
A: 使用 `gzip data/data_export.json` 压缩后再上传，目标环境 `gunzip` 解压。

**Q2: 导入提示“文献已存在”？**  
A: 正常现象，脚本会跳过已存在的 DOI；如需覆盖，请用 `--clear`。

**Q3: Railway/Render 重启后数据丢失？**  
A: 因为未挂载持久化卷。请参考方案 C 配置 Volume/Disk。

**Q4: 只想迁移某个元素组合？**  
A: 修改 `backend/export_data.py`，在查询时加过滤条件（示例已写在文件中）。

**Q5: 如何回滚导入？**  
A: 使用事先备份的 `superconductor_backup_xxx.db` 覆盖 `data/superconductor.db` 即可。

---

## 10. 建议流程

1. 本地执行导出 → 导入完整流程，确认无误
2. 在目标环境初始化数据库并执行 schema 升级脚本
3. 实施正式迁移：复制数据库或导入 JSON
4. 配置自动备份（day + week），并启用 SSH key
5. 记录当前文献数/截图数，用于后续审计

如遇特殊情况，可先查阅日志，再按问题排查。如果仍无法解决，建议提供导出/导入日志、系统环境、命令等信息，以便进一步定位。
