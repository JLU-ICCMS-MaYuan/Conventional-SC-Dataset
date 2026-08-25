# 快速验收：材料状态多维分类

## 前置条件

1. 使用包含 Issue #51 迁移的 fresh MySQL 测试库。
2. 启动 Python、Go、Redis、Worker 和前端；准备普通用户、管理员和超级管理员账户。
3. 准备一个新上传任务、一个含旧顶层 `sc_type` 的 Redis 草稿，以及一个同时提及本文材料和引用材料的固定 PDF/分段产物。

## 1. Schema 与 seed

```bash
alembic upgrade head
pytest -q tests/02_maintenance_and_verification/test_issue51_classification_schema.py
```

预期：七个材料家族和“笼状结构”可查询；别名唯一、材料维度 Check、结构主项唯一约束均通过；目标 `papers` 表不再含 `referenced_materials`。

## 2. Python 规范化与上传提交

```bash
pytest -q backend/tests/test_classification_catalog.py backend/tests/test_upload_jobs.py backend/tests/test_upload_workflow.py
```

预期：

- `hydride`、`氢化物` 和 `高压氢化物` 的家族结果均为“氢基超导体”；
- `carbon` 和 `others` 不获得正式 ID；
- `LaH10` 元素种类数为 2；
- 引用工作不进入普通草稿或正式材料状态，但管理员证据保留 scope；
- 新 PUT/submit 拒绝顶层 `sc_type`。

## 3. 前端候选与待确认状态

```bash
npm --prefix frontend run test:upload-ui
npm --prefix frontend run build
```

预期：点击材料家族输入框能看到数据库中文候选；输入已审核别名自动选择规范项；未知名称显示“尚未归入正式材料家族”，不会出现英文编码或原生 `datalist`。

## 4. 管理员与超级管理员

```bash
cd goserver && go test ./handlers ./middleware ./models
```

预期：

- 普通管理员可以映射已有项，但不能创建、停用或合并正式项；
- 超级管理员治理动作产生一条不可变审计；
- 别名冲突和重复处理返回 409；
- 分类未完成的论文不能批准，数据不发生部分更新。

## 5. 旧草稿一次性兼容

1. 打开含 `sc_type=hydride` 的旧草稿。
2. 确认每个缺少家族的材料状态显示“氢基超导体”，页面没有 `sc_type` 字段。
3. 点击保存并重新读取。

预期：Redis 持久草稿只保留 `material_states[].material_family`；`carbon/others` 显示待确认并带迁移警告。

## 6. 旧数据库迁移 dry-run

```bash
python -m backend.scripts.migrate_material_classifications \
  --legacy-database-url "$LEGACY_DATABASE_URL" \
  --target-database-url "$DATABASE_URL" \
  --report /tmp/material-classification-migration.json
```

预期：默认不写数据库；报告逐条标记 `ready/ambiguous/unmapped/conflict`。只有人工核对报告后增加 `--apply` 才写入 `ready` 项。

## 7. 浏览器验收

1. 桌面和 390px 宽度打开上传草稿。
2. 展开材料家族和结构家族候选，使用键盘搜索、选择和清除。
3. 模拟目录 API 503，确认错误可见且草稿其他字段仍可编辑。
4. 管理员打开待审核论文，映射未知名称并批准。
5. 超级管理员打开分类治理面板，新增别名并检查审计。

预期：菜单不被材料状态容器裁切，文本不溢出，加载/失败/空状态明确，所有普通页面只显示规范中文名。

## 8. 收敛检查

```bash
git diff --check
git status --short
```

逐项对照 `spec.md` 的 FR-001–FR-024 和 SC-001–SC-008；未运行或失败的验证对应任务不得标记完成。
