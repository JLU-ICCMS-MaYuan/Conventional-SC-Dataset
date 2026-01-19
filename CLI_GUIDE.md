# 🚀 项目核心管理命令手册

在执行以下命令前，请确保：
1. 已进入项目根目录：`cd /var/www/Conventional-SC-Dataset`
2. 已激活 Conda 环境：`conda activate Conventional-SC-Dataset`
3. 已设置数据目录变量：`export DATA_DIR=/var/lib/Conventional-SC-Dataset/data`

---

### 1. 数据库初始化 (Initialize Database)
用于首次安装时创建数据表并填充 118 个化学元素基础数据。
```bash
python3 -m backend.init_db
```
*   **注意**：如果数据库文件已存在，此操作不会删除现有数据，只会尝试补全缺失的表。

### 2. 数据导出 (Data Export)
将数据库中的所有文献、物理数据和图片导出为可迁移的 JSON 文件及图片包。
```bash
# 默认导出到 data/data_export.json
python3 -m backend.export_data

# 也可以指定导出路径
python3 -m backend.export_data /path/to/backup.json
```
*   **产物**：一个 JSON 文件和 `data/images/` 文件夹（包含所有图片）。

### 3. 数据导入 (Data Import)
从 JSON 文件中恢复数据。支持标准化清洗（自动过滤非标准元素符号）。
```bash
# 导入并追加数据
python3 -m backend.import_data data/data_export.json

# 清空当前数据库并重新导入（慎用！）
python3 -m backend.import_data data/data_export.json --clear
```
*   **优势**：支持通过 `file_path` 链接本地图片并自动生成缩略图。

### 4. 创建超级管理员 (Create Superadmin)
手动创建一个具有最高权限的账号（用于系统首次初始化后登录）。
```bash
python3 -m backend.create_superadmin
```
*   **交互**：运行后会提示您输入邮箱和密码。

### 5. 数据结构迁移 (Data Migration)
当系统升级或数据库结构发生变化（如最近增加的 `element_id_list`）时使用。
```bash
python3 -m backend.migrate_ids
```
*   **作用**：将旧的字符串式关联转换为高效的 JSON ID 列表关联。

### 6. 数据库自动备份 (Auto Backup)
建议配合宝塔或 Cron 定时任务运行。
```bash
# 手动快速备份数据库文件
cp /var/lib/Conventional-SC-Dataset/data/superconductor.db /var/lib/Conventional-SC-Dataset/data/backup_$(date +%F).db
```

---

## 🛠️ 生产环境运维命令 (Systemd)

作为 `root` 用户执行：

*   **查看系统日志（实时）**：用于排查上传报错、登录失败等。
    ```bash
    journalctl -u Conventional-SC-Dataset -f
    ```
*   **重启应用服务**：修改代码或配置后必须执行。
    ```bash
    systemctl restart Conventional-SC-Dataset
    ```
*   **停止/启动应用**：
    ```bash
    systemctl stop Conventional-SC-Dataset
    systemctl start Conventional-SC-Dataset
    ```

---

### 💡 维护小贴士
*   **数据迁移**：如果您要搬家服务器，只需要带走 `data_export.json` 和 `images/` 文件夹。
*   **安全建议**：定期将导出的 JSON 文件下载到您的本地电脑或上传至阿里云 OSS。
*   **权限修复**：如果在上传图片时遇到错误，通常是权限问题，运行：`chown -R sc-app:sc-app /var/lib/Conventional-SC-Dataset`。
