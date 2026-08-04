# 数据库初始化与迁移

## 功能说明

建立主业务数据库结构、应用 Alembic 版本迁移并幂等填充 118 个周期表元素。

## 当前行为

- `start.sh` 在未设置 `DATABASE_URL` 时使用 `data/local_dev.db`，执行 `alembic upgrade head` 和 `python -m backend.init_db` 后启动 Uvicorn。
- `backend.init_db` 调用 `Base.metadata.create_all` 并填充元素数据。
- FastAPI startup 事件也会调用 SQLite 初始化逻辑。
- Alembic 环境允许 `DATABASE_URL` 覆盖配置文件连接串。

## 工作流程

完整脚本启动时先解析数据库地址并创建数据目录，然后应用迁移、执行初始化、启动应用。其他入口可能直接启动 Uvicorn，由应用 startup 执行部分初始化。

## 约束

- 直接导入后端且未设置环境变量时默认使用 `data/dev.db`，与 `start.sh` 的 `data/local_dev.db` 不同。
- `Procfile` 直接启动 Uvicorn，不显式运行 Alembic。
- 自动 `create_all` 不等同于完整迁移流程，部署入口必须明确选择。

## 代码与测试

- `start.sh`
- `Procfile`
- `backend/main.py`
- `backend/init_db.py`
- `backend/database.py`
- `alembic/env.py`、`alembic/versions/`
- `tests/02_maintenance_and_verification/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 多启动入口的数据库默认值和迁移行为尚未统一。
