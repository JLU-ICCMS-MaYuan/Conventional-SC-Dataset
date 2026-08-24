# 快速验收：删除 phase_label

## 前置条件

- 当前目录为仓库根目录。
- 前端依赖已安装；Python 测试依赖可用。
- fresh MySQL 验证环境可选，不使用现有运行库做破坏性迁移。

## 前端回归

```bash
npm --prefix frontend run test:upload-ui
```

预期：上传编辑器不再渲染“物相”，空间群和 `state_kind` 仍可保存。

## Python 回归

```bash
pytest backend/tests/test_upload_jobs.py backend/tests/test_scientific_drafts.py
```

预期：新草稿不含 `phase_label`，旧草稿含该字段时归一化后忽略，持久化对象不含该属性。

## Schema 回归

```bash
pytest tests/02_maintenance_and_verification/test_issue32_schema.py
go test ./goserver/models
```

预期：`material_states` 不包含 `phase_label`，空间群字段和 `state_kind` 仍存在。

## 迁移与结构场景

验证同材料同压力下 `Fm-3m` 与 `R3m` 为独立状态；没有空间群的多个结构候选不得静默合并；旧 `clathrate` 不转为空间群。
