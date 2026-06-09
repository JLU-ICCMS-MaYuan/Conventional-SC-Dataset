# CLI 与维护操作

## 1. 目标

本文档汇总当前仓库中与初始化、迁移、导入导出、管理员创建、备份和服务维护相关的命令。

## 2. 常用前提

执行命令前建议确认：

```bash
pwd
python --version
```

并确保位于项目根目录。

## 3. 数据库初始化

```bash
python -m alembic upgrade head
python -m backend.init_db
```

用途：
- 使用 Alembic 创建或升级数据表
- 初始化 118 个元素基础数据
- `backend.init_db` 不再负责 `create_all` 或临时 `ALTER TABLE`

## 4. 创建超级管理员

```bash
python -m backend.create_superadmin
```

用途：
- 系统首次部署后创建最高权限账号
- 超级管理员可继续审批管理员申请

## 5. 数据导出

```bash
python -m backend.export_data
python -m backend.export_data /path/to/export.json
```

用途：
- 导出 `mysql-redesign-v1` JSON
- 包含 `users`、`papers`、`superconductor_records`
- 不导出图片，因为图片存储已下线

## 6. 数据导入

```bash
python -m backend.import_data data/data_export.json
python -m backend.import_data data/data_export.json --clear
```

用途：
- 导入 `mysql-redesign-v1` JSON
- `--clear` 会先清理用户、论文、超导体和记录等业务数据，应谨慎使用
- 旧数据可以后续整理成该 JSON 格式后导入

## 7. 组合 ID 迁移

```bash
python -m backend.migrate_ids
```

用途：
- 该脚本面向旧组合表
- 新 MySQL 结构不依赖 `element_id_list`，该脚本当前不作为新结构维护入口

## 8. 批量上传辅助

### 8.1 下载批量上传示例
- 前端入口会调用 `/api/papers/batch-upload-example`
- 当前返回 501，等待新 `superconductor_records` 表格格式确定

### 8.2 服务端批量处理
- 接口：`POST /api/papers/batch-upload`
- 当前接口保留入口，但新 MySQL 结构下的批量导入逻辑未实现

## 9. 服务维护

### 9.1 直接脚本启动
```bash
./start.sh
```

### 9.2 systemd 场景
```bash
systemctl restart Conventional-SC-Dataset
systemctl stop Conventional-SC-Dataset
systemctl start Conventional-SC-Dataset
journalctl -u Conventional-SC-Dataset -f
```

## 10. 备份建议

### 10.1 MySQL 备份
```bash
mysqldump -u user -p superconductor_dataset > backup_$(date +%F).sql
```

### 10.2 使用脚本
- `scripts/autobackup.sh`
- `scripts/remote_backup.sh`

适用场景：
- 定时备份数据库
- 同步到远程服务器
- 结合计划任务执行

## 11. 常见维护问题

### 11.1 修改代码后页面未更新
- 静态文件改动通常刷新浏览器即可
- 后端 Python 改动通常需要重启服务
- 如果使用 `uvicorn --reload`，开发环境下会自动重启

### 11.2 邮件验证码发不出去
- 检查 SMTP 环境变量
- 检查服务日志
- 确认发件箱授权码配置正确

### 11.3 后台无法登录
- 检查邮箱是否已验证
- 管理员是否已被超级管理员批准
- JWT 密钥是否正确配置

### 11.4 需要重建数据库
```bash
python -m alembic upgrade head
python -m backend.init_db
```

如果要完全重置，应先自行备份当前 MySQL 数据库，再处理建表、元素初始化和管理员重建流程。
