# 数据迁移指南

## 📋 概述

当你在本地开发环境上传了文献数据后，部署到生产环境时需要迁移这些数据。本指南提供了三种数据迁移方案。

---

## 🎯 方案一：直接复制数据库文件（最简单）

**适用场景：** VPS部署，数据量不大

### 步骤：

**1. 备份本地数据库**
```bash
cp data/superconductor.db data/superconductor_backup_$(date +%Y%m%d).db
```

**2. 上传到服务器**

使用 scp 上传（假设服务器IP是 `123.45.67.89`）：
```bash
scp data/superconductor.db root@123.45.67.89:/var/www/conventional-sc-dataset/data/
```

**3. 重启服务**
```bash
ssh root@123.45.67.89
systemctl restart superconductor
```

---

## 🎯 方案二：导出导入JSON（推荐）

**适用场景：** 所有部署方式，数据安全可靠

### 优点：
- ✅ 跨平台兼容（Windows → Linux）
- ✅ 可读性强，可手动编辑
- ✅ 版本控制友好
- ✅ 支持选择性导入

### 导出数据

**1. 在本地环境运行导出脚本：**
```bash
python -m backend.export_data
```

**2. 输出文件：**
- 位置：`data/data_export.json`
- 包含所有文献、截图、元素组合数据

**3. 查看导出信息：**
```
✅ 导出完成！
   文件位置: /path/to/data/data_export.json
   元素: 118 个
   元素组合: 15 个
   文献: 42 篇
   截图: 156 张
   文件大小: 23.45 MB
```

### 导入数据

**1. 上传JSON文件到服务器**

通过 scp：
```bash
scp data/data_export.json root@123.45.67.89:/var/www/conventional-sc-dataset/data/
```

或者通过 Railway CLI：
```bash
railway run scp data/data_export.json /app/data/
```

**2. 在服务器上运行导入脚本：**

普通导入（保留现有数据，跳过重复）：
```bash
python -m backend.import_data
```

清空现有数据后导入（⚠️ 谨慎使用）：
```bash
python -m backend.import_data --clear
```

**3. 验证导入结果：**
```
✅ 导入完成！
   元素组合: 15 个
   文献: 42 篇
   截图: 156 张
```

---

## 🎯 方案三：持久化存储（自动同步）

**适用场景：** Railway/Render部署，长期运营

### Railway 配置持久化存储

**1. 在 Railway 项目中添加 Volume**
- 打开 Railway 项目
- 点击服务 → "Variables" → "Add Volume"
- 挂载路径：`/app/data`
- 大小：选择合适的大小（如 1GB）

**2. 上传数据库文件**

使用 Railway CLI：
```bash
# 安装 CLI
npm install -g @railway/cli

# 登录
railway login

# 连接项目
railway link

# 上传数据库
railway run bash -c "cat > /app/data/superconductor.db" < data/superconductor.db
```

或者使用导出导入方案：
```bash
# 上传JSON
railway run bash -c "cat > /app/data/data_export.json" < data/data_export.json

# 执行导入
railway run python -m backend.import_data
```

### Render 配置持久化磁盘

**1. 在 Render 项目中添加 Disk**
- 打开 Render 项目设置
- 找到 "Disk" 选项
- 添加新磁盘
  - 名称：`data`
  - 挂载路径：`/opt/render/project/src/data`
  - 大小：1GB（免费）

**2. 部署后，使用导出导入方案迁移数据**

---

## 📊 各方案对比

| 方案 | 难度 | 速度 | 可靠性 | 适用场景 |
|------|------|------|--------|----------|
| 直接复制DB文件 | ⭐ 极简 | ⭐⭐⭐ 快 | ⭐⭐ 中 | VPS部署 |
| 导出导入JSON | ⭐⭐ 简单 | ⭐⭐ 中 | ⭐⭐⭐ 高 | 所有场景 |
| 持久化存储 | ⭐⭐⭐ 中等 | ⭐⭐⭐ 快 | ⭐⭐⭐ 高 | 云平台 |

---

## 🧩 Schema 升级：element_list 与超导类型标准化

前端的元素组合筛选与图表依赖以下数据库结构，请在部署或恢复备份后执行一次升级脚本：
- `compounds.element_list`：保存元素 JSON 列表，支持“仅包含/组合/包含所选元素”筛选
- `papers.superconductor_type`：仅允许「铜基、铁基、镍基、高压氢化物、碳基、有机、其他超导」七大类

### 运行升级脚本

```bash
# 如部署在 Railway/Render，请先设置数据库路径
export DATABASE_PATH=/app/data/superconductor.db

# 执行 schema 升级（幂等，可重复运行）
python -m backend.migrations.schema_202502
```

脚本会自动：
1. 检查并新增 `element_list` 列
2. 依据 `element_symbols` 补写 JSON 列表
3. 将 `conventional、carbon_organic` 等旧类型映射到七大类

### 升级后快速自检

```bash
sqlite3 $DATABASE_PATH "SELECT element_symbols, element_list FROM compounds LIMIT 5;"
sqlite3 $DATABASE_PATH "SELECT DISTINCT superconductor_type FROM papers;"
```

如仍出现空 `[]` 或旧类型值，可再次运行脚本或检查 `DATABASE_PATH` 是否指向持久化卷。

---

## 🔄 定期备份建议

### 自动备份脚本

创建 `backup.sh`：
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"

mkdir -p $BACKUP_DIR

# 导出JSON
python -m backend.export_data data_export_${DATE}.json

# 移动到备份目录
mv data_export_${DATE}.json $BACKUP_DIR/

# 压缩
gzip $BACKUP_DIR/data_export_${DATE}.json

echo "✅ 备份完成: $BACKUP_DIR/data_export_${DATE}.json.gz"

# 删除30天前的备份
find $BACKUP_DIR -name "data_export_*.json.gz" -mtime +30 -delete
```

**设置定时任务（每天凌晨2点）：**
```bash
crontab -e
```

添加：
```
0 2 * * * cd /var/www/conventional-sc-dataset && ./backup.sh
```

---

### 远程备份到 SSH 服务器

新增脚本 `scripts/remote_backup.sh` 可自动导出 JSON + 数据库文件，打包后通过 SSH 上传。支持秘钥或密码两种方式（若要在非交互环境使用密码，请安装 `sshpass`）。

环境变量 | 说明 | 默认值
---------|------|-------
`BACKUP_REMOTE_HOST` | 目标服务器 IP/域名 | `222.27.82.115`
`BACKUP_REMOTE_USER` | SSH 用户名 | `123`
`BACKUP_REMOTE_PORT` | SSH 端口 | `22`
`BACKUP_REMOTE_DIR` | 远程存放目录（自动创建） | `backups/conventional-sc`
`BACKUP_REMOTE_PASS` | SSH 密码（留空则走密钥/交互式输入） | *(空)*
`BACKUP_PREFIX` | 备份文件前缀（默认 `backup`，可设成 `backup_day`、`backup_week`） | `backup`
`BACKUP_WORKDIR` | 本地临时备份目录 | `./backups`
`DATABASE_PATH` | SQLite 路径 | `data/superconductor.db`

示例：以提供的 123/456 账户上传到 `/home/123/backups/conventional-sc`：

```bash
cd /path/to/Conventional-SC-Dataset
BACKUP_REMOTE_USER=123 \
BACKUP_REMOTE_PASS=456 \
BACKUP_REMOTE_HOST=222.27.82.115 \
BACKUP_REMOTE_DIR=/home/123/backups/conventional-sc \
./scripts/remote_backup.sh
```

脚本会：
1. 执行 `python -m backend.export_data backups/data_export_时间戳.json`
2. 复制当前 `superconductor.db`
3. 打包为 `backups/backup_时间戳.tar.gz`
4. 通过 SSH/ SCP 上传并自动创建远程目录
5. 删除本地中间的 JSON/DB 副本（tar 包保留，可用于本地回溯）

**定时任务示例（每天 3 点）：**

```
0 3 * * * cd /var/www/conventional-sc-dataset && \
BACKUP_REMOTE_PASS=456 BACKUP_REMOTE_USER=123 BACKUP_REMOTE_HOST=222.27.82.115 \
BACKUP_REMOTE_DIR=/home/123/backups/conventional-sc ./scripts/remote_backup.sh >> logs/backup.log 2>&1
```

> 建议改用 SSH key：`ssh-keygen` → `ssh-copy-id 123@222.27.82.115`，然后不必在环境变量里放密码。

#### 恢复远程备份

1. 从远程服务器下载最新压缩包：
   ```bash
   scp 123@222.27.82.115:/home/123/backups/conventional-sc/backup_20250201_030000.tar.gz backups/
   ```
2. 解压并取出文件：
   ```bash
   tar -xzf backups/backup_20250201_030000.tar.gz -C backups/
   cp backups/superconductor_20250201_030000.db data/superconductor.db
   ```
   或者运行 `python -m backend.import_data backups/data_export_20250201_030000.json` 将 JSON 数据导回新库。
3. 启动后端检查：http://localhost:8000 ，确认文献数量与截图可用。

---

### 自动备份与保留策略

`scripts/autobackup.sh` 封装了周期性备份及远程/本地保留策略：

命令 | 说明 | 保留策略
-----|------|---------
`./scripts/autobackup.sh -m day` | 日常备份，文件名形如 `backup_day_YYYYmmdd_HHMMSS.tar.gz` | 仅保留最近 14 个
`./scripts/autobackup.sh -m week` | 周度备份，文件名形如 `backup_week_YYYYmmdd_HHMMSS.tar.gz` | 仅保留最近 4 个

脚本逻辑：
1. 调用 `remote_backup.sh` 生成带前缀的备份并上传
2. 远程服务器：列出 `backups/.../${前缀}_*.tar.gz`，删除超过配额的旧文件
3. 本地 `backups/` 目录同步删除多余 tar 包，避免磁盘膨胀

示例计划任务：
```
# 每天 02:30 运行日备份
30 2 * * * cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m day >> logs/autobackup.log 2>&1

# 每周一 03:00 运行周备份
0 3 * * 1 cd /var/www/conventional-sc-dataset && BACKUP_REMOTE_PASS=456 ./scripts/autobackup.sh -m week >> logs/autobackup.log 2>&1
```

其余环境变量与 `remote_backup.sh` 相同，可按需覆盖。

---

## ⚠️ 重要提醒

### 部署前必须做的事：

1. **本地测试导出导入**
   ```bash
   # 导出
   python -m backend.export_data

   # 创建测试数据库
   mv data/superconductor.db data/superconductor_original.db
   python -m backend.init_db

   # 导入测试
   python -m backend.import_data

   # 验证数据完整性
   python -m backend.main
   # 访问 http://localhost:8000 检查数据
   ```

2. **备份原始数据库**
   ```bash
   cp data/superconductor.db data/superconductor_backup_before_deploy.db
   ```

3. **记录统计信息**
   - 文献数量
   - 截图数量
   - 数据库文件大小

### 数据迁移检查清单

- [ ] 导出数据成功
- [ ] JSON文件完整（能正常打开）
- [ ] 上传到服务器成功
- [ ] 导入数据成功
- [ ] 网页能正常访问
- [ ] 文献数量正确
- [ ] 截图能正常显示
- [ ] 搜索功能正常

---

## 🆘 常见问题

### Q1: 导出的JSON文件很大怎么办？

**A:** 压缩后上传
```bash
gzip data/data_export.json
# 上传 data_export.json.gz
# 服务器上解压
gunzip data_export.json.gz
```

### Q2: 导入时提示"文献已存在"？

**A:** 正常现象，脚本会自动跳过重复数据，不会覆盖现有文献。

### Q3: Railway/Render 部署后数据库是空的？

**A:** 因为容器重启会清空数据。必须配置持久化存储（Volume/Disk）。

### Q4: 如何只导出特定元素组合的数据？

**A:** 修改 `export_data.py`，添加过滤条件：
```python
# 例如只导出 Y-Ba-Cu-O 系统
papers = db.query(models.Paper).join(models.Compound).filter(
    models.Compound.element_symbols == "Ba-Cu-O-Y"
).all()
```

### Q5: 导入失败，如何回滚？

**A:** 如果导入前没有清空数据（`--clear`），原有数据不会受影响。如果使用了 `--clear`，从备份文件恢复：
```bash
cp data/superconductor_backup.db data/superconductor.db
```

---

## 📞 技术支持

如果遇到数据迁移问题：
1. 检查导出的JSON文件是否完整
2. 查看导入时的错误信息
3. 确认服务器上数据库路径正确
4. 验证持久化存储配置

---

**💡 建议：** 在正式部署前，先在本地测试一遍完整的导出→导入流程，确保数据不会丢失！
