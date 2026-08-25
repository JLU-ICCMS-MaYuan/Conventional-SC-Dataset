# Tasks：材料分类审核简化与迁移修复

## 说明

本任务表替代 Issue #51 第一版的独立 proposal、目录治理和超级管理员二次审批任务。Git 历史保留旧实现记录；当前复选框只表示最新 Spec 的完成状态。

## 文档与测试门

- [x] T001 [US3] 更新 `spec.md`、`plan.md`、`research.md`、`data-model.md`、API 契约和 Quickstart，明确审核内一次确认。
- [x] T002 [US3] 重写 `tests/01_decentralized_uploading/issue51_classification_api_test.go`，先覆盖原子审核闭环。
- [x] T003 [US1] 重写 Python 提交测试，证明不创建旧治理实体。
- [x] T004 [US3] 用前端测试证明治理页签移除且审核只发送一次请求。
- [x] T005 [US1] 新增 `tests/01_decentralized_uploading/test_issue51_fresh_mysql_migration.py`。

## 数据库与模型

- [x] T006 [SC-007] 修复 `0012` 的 MySQL 8.4 自增列 CHECK 和 STORED 生成列兼容问题。
- [x] T007 [FR-023] 新增 `0013` 删除旧治理表、合并/停用字段并加入审核快照。
- [x] T008 [FR-013] 同步 SQLAlchemy 与 GORM 目录、材料状态和审核事件模型。

## 后端与 API

- [x] T009 [US5] 修改 Python 提交链路，仅持久化本文材料状态和科学维度。
- [x] T010 [US3] 精简 Go 分类处理，只保留目录读取和审核事务 helper。
- [x] T011 [US3] 把目录匹配/创建、最终分类和审核快照并入单篇审核事务。
- [x] T012 [FR-024] 禁止批量批准绕过分类确认。
- [x] T013 [FR-023] 删除旧治理和独立分类更新路由。

## 前端

- [x] T014 [US3] 删除分类治理页签和面板。
- [x] T015 [US3] 审核弹窗支持材料家族、结构家族、材料维度及新名称。
- [x] T016 [FR-019] 前端改为一次审核请求并在成功后刷新目录。

## 验证与文档收敛

- [x] T017 [SC-007] 在 fresh MySQL 8.4 执行 `alembic upgrade head`。
- [x] T018 [SC-008] 通过 Python、Go、Vitest、TypeScript 和生产构建。
- [x] T019 使用 `big-project-overview-maintainer` 更新受影响 Overview。
- [x] T020 核对 Git diff，仅提交本 Feature 文件并报告 commit hash。

## 可追踪性

| 需求 | 任务 | 证据 |
| --- | --- | --- |
| FR-008～010 | T003、T010、T015 | 目录和精确匹配测试 |
| FR-011～014 | T002、T007～T011 | 审核快照与无旧治理实体断言 |
| FR-019～021 | T002、T011、T016 | 单事务、回滚和幂等测试 |
| FR-023～024 | T004、T007、T012～T014 | Schema、路由和 UI 不存在断言 |
| SC-007～008 | T005、T017～T018 | 真实 MySQL 与全量验证输出 |
