# 实施任务：上传任务分层清理与待审核快照生命周期

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：锁定现有错误方向和跨服务调用边界。

- [x] T001 在 `tests/01_decentralized_uploading/` 建立 #35 专项测试入口并确认现有读时 MySQL 补丁失败信号。
- [x] T002 核对 `goserver/handlers/admin.go` 审核事务与 Python 快照删除调用顺序。

## 阶段 2：基础能力

**目的**：建立共享契约和可安全组合的清理原语。

- [x] T003 [P] 在 `tests/01_decentralized_uploading/test_issue35_duplicate_contract.py` 先写状态版本、新 duplicate 和纯 Redis GET 失败测试。
- [x] T004 [P] 在 `tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py` 先写三类清理、CleanupContext 和幂等失败测试。
- [x] T005 在 `backend/ingest/upload_contracts.py` 增加状态契约版本与清理上下文纯规则。
- [x] T006 在 `backend/ingest/upload_tasks.py` 实现三类清理原语、RQ Job 删除和携带上下文的调度。

## 阶段 3：用户故事 1——提交后释放临时资源（P1，MVP）

**目标**：提交后只保留正式文件、正式 Markdown、MySQL 数据和审核快照。

**独立验收**：提交成功后的保留/删除矩阵与幂等重试通过。

### 测试

- [x] T007 [US1] 在 `tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py` 增加提交响应丢失、上传者校验和快照写入失败测试。

### 实施

- [x] T008 [US1] 在 `backend/api/rag.py` 实现按 upload_task_id 的提交恢复和提交后临时清理。
- [x] T009 [US1] 验证 `backend/api/rag.py` 的 Paper/File/Chunk/Evidence 事务提交后才触发清理。

## 阶段 4：用户故事 2——审核完成后删除快照（P1）

**目标**：pending 保留当前 revision 快照，审核终态后幂等删除。

**独立验收**：Python 快照 API 与 Go 审核后置调用通过。

### 测试

- [x] T010 [P] [US2] 在 `tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py` 增加 pending、终态、revision 不一致测试。
- [x] T011 [P] [US2] 在 `goserver/handlers/` 增加审核事务成功后调用及失败不回滚测试。

### 实施

- [x] T012 [US2] 在 `backend/api/rag.py` 收敛审核快照字段、revision 校验和幂等删除语义。
- [x] T013 [US2] 在 `goserver/handlers/admin.go` 保证只有 approved/rejected 成功后触发快照清理。

## 阶段 5：用户故事 3——未提交任务完整清理（P1）

**目标**：三个终态在 Redis 缺失后仍能完整回收且正式文件零误删。

**独立验收**：真实临时目录和 Redis/RQ 边界测试通过。

### 测试

- [x] T014 [US3] 在 `tests/01_decentralized_uploading/test_issue35_cleanup_lifecycle.py` 增加三个终态、候选副本、Redis 缺失和 MySQL 故障测试。

### 实施

- [x] T015 [US3] 在 `backend/api/upload_tasks.py` 和 `backend/ingest/upload_tasks.py` 接入主动与到期完整清理。
- [x] T016 [US3] 确认批量清理只处理可清理终态并复用同一安全原语。

## 阶段 6：用户故事 4——稳定 Redis 契约（P1）

**目标**：新任务使用当前契约，旧任务一次迁移，GET 不查询 Paper 表。

**独立验收**：迁移前后 Redis 状态和容器契约检查通过。

### 测试

- [x] T017 [US4] 在 `tests/01_decentralized_uploading/test_issue35_duplicate_contract.py` 增加 dry-run/apply、24 小时基准和重复执行测试。

### 实施

- [x] T018 [US4] 撤销 `backend/api/upload_tasks.py` 的 duplicate 读时 MySQL 兼容。
- [x] T019 [US4] 在 `backend/ingest/upload_jobs.py` 和创建路径写入当前状态契约版本。
- [x] T020 [US4] 新增 `backend/scripts/migrate_upload_task_states.py` 并迁移现存旧 duplicate 状态。
- [x] T021 [US4] 增加 API/Worker 部署契约检查并验证运行容器。

## 最终阶段：完善与跨故事事项

- [x] T022 运行 `tests/01_decentralized_uploading`、相关 Go 测试、前端测试和生产构建。
- [x] T023 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md` 的已实现清理事实。
- [x] T024 对照 FR-001–FR-016、SC-001–SC-008 执行收敛检查并更新 #35。

## 依赖与执行顺序

- T003–T006 阻断全部用户故事。
- US1 建立提交后清理，是 US2 审核快照生命周期的前提。
- US3 复用基础清理原语，可在 US1 后实施。
- US4 必须在最终部署前完成，旧状态迁移只执行一次。
- 同一 Python 文件上的任务串行执行。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001–FR-011 / US1–US3 | T004–T016 | 分层清理、幂等、fail-closed 和审核快照 |
| FR-012–FR-015 / US4 | T003、T017–T021 | Redis 契约、迁移和部署检查 |
| FR-016 / US1 | T007–T009 | 提交响应丢失恢复 |
| SC-001–SC-008 | T022–T024 | 专项、全量、部署与文档验收 |

## MVP 与增量策略

1. 完成基础能力和 US1，先保证提交后不误删且不残留任务状态。
2. 完成 US2，闭合 pending 到审核终态的快照生命周期。
3. 完成 US3，闭合未提交终态的完整回收。
4. 完成 US4 和一次性迁移，移除错误兼容并保证部署一致。

## 阶段 8：收敛修正

**来源**：对照 #33 当前 Paper/PaperFile Schema 复核 Worker 真实重复检测路径。

- [x] T025 [US4] 在 `tests/01_decentralized_uploading/test_issue35_duplicate_contract.py` 增加真实 ORM 回归测试，证明重复检测从 `paper_files` 读取正文哈希和路径。
- [x] T026 [US4] 在 `backend/ingest/upload_jobs.py` 移除对已删除 `papers.source_file_path` 的依赖，统一使用当前 `PaperFile` 契约。
- [x] T027 [US2] 在 `goserver/handlers/admin_review_event_test.go` 补充审核事务先提交、快照清理失败不回滚的 Handler 级测试。
- [x] T028 重新运行上传目录、Go Handler、前端上传测试和生产构建。
- [ ] T029 在开发 MySQL 执行已确认的 #33 Schema 迁移后，重建 API/Worker 并核对同镜像、契约版本和真实提交/重复路径。
