# #90 验证记录

## 已完成验证

- Python 语法：`DATABASE_URL=sqlite:////tmp/scwiki90.db JWT_SECRET_KEY=test python3 -m compileall -q backend` 通过。
- 模块化记录与旧草稿转换：`backend/tests/test_issue90_properties.py`，3 项通过。
- 上传状态契约回归：`backend/tests/test_upload_contracts.py`，2 项通过；原有实现保持可用。
- 迁移阶段控制器：`backend/tests/test_issue90_migration_phase.py`，2 项通过。
- SQLite fresh metadata：目标模型可创建 `property_modules`、`property_records`、`form_definitions`、审计、Evidence 和迁移映射表。
- 前端：`cd frontend && npm run build` 通过；`material-states-editor.test.tsx` 12 项通过。
- `git diff --check` 通过。

## 迁移执行边界

`alembic/versions/20260907_issue90_expand_modular_property_schema.py` 负责 Expand 和 v1 定义种子；
`backend/scripts/migrate_issue90_properties.py` 负责 Copy/Reconcile，按源表、源 ID、论文 revision
和目标表幂等。Read switch、Write switch、Observe、Contract 由
`backend/services/issue90_migration.py` 顺序门控制。Contract 迁移默认不删除旧表，必须显式配置确认值。

当前环境未安装 `go`/`gofmt`，Go 单元测试和格式化无法执行；该项在具备 Go 工具链的 CI/部署环境中补跑后，
才能宣称 Go 侧验证完成。
