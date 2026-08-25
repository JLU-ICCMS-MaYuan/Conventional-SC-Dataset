# Quickstart：材料分类审核与迁移验收

## 1. Fresh MySQL 8.4

准备名称含 `test` 的隔离空库：

```bash
export FRESH_MYSQL_DATABASE_URL='mysql+pymysql://root:password@127.0.0.1:3306/scwiki_issue51_test'
pytest -q tests/01_decentralized_uploading/test_issue51_fresh_mysql_migration.py
```

验收：

- `alembic upgrade head` 成功；
- head 为 `20260825_0013`；
- 不存在三个旧治理表；
- 两类目录没有 `merged_into_id` 和 `is_active`；
- `paper_review_events.classification_snapshot` 存在；
- 主结构生成列为 VIRTUAL，迁移不会返回 MySQL 1215。

不得把该命令指向生产库；测试会拒绝数据库名不含 `test` 的 URL。

## 2. Python 提交边界

```bash
pytest -q tests/01_decentralized_uploading/test_issue51_classification_workflow.py
```

确认提交只创建本文材料状态，不创建 proposal/evidence，不把引用工作变成材料状态。

## 3. Go 审核闭环

```bash
cd goserver
go test ./...
```

专项用例应覆盖已有 ID、别名、创建新材料/结构家族、完整回滚、幂等、拒绝不创建和快照。

## 4. 前端

```bash
npm test -- --run tests/01_decentralized_uploading
npm run typecheck
npm run build
```

人工验收审核弹窗：

1. AI 建议、贡献者提交和本文/引用作用域可见。
2. 材料家族下拉来自数据库。
3. 可改选已有项，也可输入新名称。
4. 可维护多个结构家族和唯一主项。
5. 确认审核只发送一个 `/review` 请求。
6. 管理员页面不存在分类建议/治理页签。

## 5. 启动验证

使用当前源码构建的 Python 镜像执行 `python -m backend.scripts.run_migrations`。只有迁移容器成功退出后，Go 和 Python 服务才应启动。
